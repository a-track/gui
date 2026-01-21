from PyQt6.QtWidgets import (QHeaderView, QMenu, QWidgetAction, QCheckBox,
                             QVBoxLayout, QWidget, QLineEdit, QPushButton,
                             QHBoxLayout, QLabel, QDateEdit, QScrollArea,
                             QDialog, QDoubleSpinBox, QTableWidgetItem)
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QDate
from PyQt6.QtGui import QPainter, QColor

class NumberFilterDialog(QDialog):
    def __init__(self, col_name, op_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Custom Filter")
        self.value = 0.0
        self.ok = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Show rows where '{col_name}' is {op_text}:"))

        self.spin = QDoubleSpinBox()
        self.spin.setRange(-999999999, 999999999)
        self.spin.setDecimals(2)
        layout.addWidget(self.spin)

        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept_val)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def accept_val(self):
        self.value = self.spin.value()
        self.ok = True
        self.accept()

class DateRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Date Range")
        self.start_date = None
        self.end_date = None
        self.ok = False

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("From:"))
        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDate(QDate.currentDate().addYears(-1))
        layout.addWidget(self.start_edit)

        layout.addWidget(QLabel("To:"))
        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDate(QDate.currentDate())
        layout.addWidget(self.end_edit)

        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept_val)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def accept_val(self):
        self.start_date = self.start_edit.date()
        self.end_date = self.end_edit.date()
        self.ok = True
        self.accept()

class ExcelHeaderView(QHeaderView):
    
    filterChanged = pyqtSignal()

    FILTER_DATA_ROLE = Qt.ItemDataRole.UserRole + 99

    def __init__(self, table, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.table = table
        self.setSectionsClickable(True)
        self.setHighlightSections(True)

        self.filters = {}

        self.column_types = {}
        self.disabled_filters = set()

        self.icon_size = 14
        self.padding = 6
        self.filters_enabled = True

    def _get_value(self, item):
        
        if not item:
            return ""
        val = item.data(self.FILTER_DATA_ROLE)
        if val is not None:
            return str(val)
        return item.text()

    def set_column_types(self, types):
        
        self.column_types = types

    def set_filter_enabled(self, col, enabled):
        if not enabled:
            self.disabled_filters.add(col)
        elif col in self.disabled_filters:
            self.disabled_filters.remove(col)

    def set_filters_enabled(self, enabled):
        
        self.filters_enabled = enabled
        self.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super().paintSection(painter, rect, logicalIndex)

        if logicalIndex in self.disabled_filters or not self.filters_enabled:
            painter.restore()
            return

        is_filtered = self.is_column_filtered(logicalIndex)
        is_sorted = (self.table.horizontalHeader(
        ).sortIndicatorSection() == logicalIndex)
        sort_order = self.table.horizontalHeader().sortIndicatorOrder()

        icon_rect = QRect(
            rect.right() - self.icon_size - self.padding,
            rect.top() + (rect.height() - self.icon_size) // 2,
            self.icon_size,
            self.icon_size
        )

        painter.setBrush(QColor("#f0f0f0"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(icon_rect)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if is_filtered:

            painter.setBrush(QColor("#2196F3"))
            painter.drawRoundedRect(icon_rect, 3, 3)
            painter.setPen(QColor("white"))
            painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "Y")

        elif is_sorted:

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QColor("black"))
            arrow = "\u25B2" if sort_order == Qt.SortOrder.AscendingOrder else "\u25BC"
            painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, arrow)

        else:

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QColor("#888888"))
            painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "\u25BC")

        painter.restore()

    def mouseReleaseEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex == -1 or logicalIndex in self.disabled_filters or not self.filters_enabled:
            super().mouseReleaseEvent(event)
            return

        width = self.sectionSize(logicalIndex)
        height = self.height()
        x = self.sectionViewportPosition(logicalIndex)

        hit_zone_width = self.icon_size + self.padding * 3
        icon_rect = QRect(
            x + width - hit_zone_width,
            0,
            hit_zone_width,
            height
        )

        if icon_rect.contains(event.pos()):
            self.show_filter_menu(
                logicalIndex, event.globalPosition().toPoint())
        else:

            self.sectionClicked.emit(logicalIndex)
            super().mouseReleaseEvent(event)

            self.table.scrollToTop()

    def is_column_filtered(self, col):
        f = self.filters.get(col, {})
        return (bool(f.get('hidden_values')) or
                bool(f.get('date_range')) or
                bool(f.get('number_filter')))

    def show_filter_menu(self, col, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #ccc; padding: 4px; }
            QMenu::item:selected { background-color: #e0e0e0; color: black; }
        """)

        col_type = self.column_types.get(col, 'text')
        col_name = self.model().headerData(col, Qt.Orientation.Horizontal)

        is_filtered = self.is_column_filtered(col)
        clear_action = menu.addAction(f"Clear Filter from '{col_name}'")
        clear_action.setEnabled(is_filtered)
        clear_action.triggered.connect(
            lambda: self.clear_filter_for_column(col))

        menu.addSeparator()

        if col_type == 'number':
            num_menu = menu.addMenu("Number Filters")

            def set_num_filter(op):
                op_text = "greater than" if op == 'gt' else "less than"
                dlg = NumberFilterDialog(col_name, op_text, self)
                if dlg.exec() == QDialog.DialogCode.Accepted and dlg.ok:
                    if col not in self.filters:
                        self.filters[col] = {}

                    self.filters[col]['number_filter'] = {
                        : op, 'value': dlg.value}
                    self.apply_filters()
                    self.viewport().update()

            num_menu.addAction("Greater Than...").triggered.connect(
                lambda: set_num_filter('gt'))
            num_menu.addAction("Less Than...").triggered.connect(
                lambda: set_num_filter('lt'))

            menu.addSeparator()

        if col_type == 'date':
            date_menu = menu.addMenu("Date Filters")

            def set_date_range():
                dlg = DateRangeDialog(self)

                if dlg.exec() == QDialog.DialogCode.Accepted and dlg.ok:
                    if col not in self.filters:
                        self.filters[col] = {}

                    self.filters[col]['date_range'] = (
                        dlg.start_date, dlg.end_date)
                    self.apply_filters()
                    self.viewport().update()

            date_menu.addAction("Between...").triggered.connect(set_date_range)
            menu.addSeparator()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        search_box = QLineEdit()
        search_box.setPlaceholderText("Search...")
        layout.addWidget(search_box)

        select_all_cb = QCheckBox("(Select All)")
        layout.addWidget(select_all_cb)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(150)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #ddd; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(2)

        unique_values = set()

        def match_other_filters(r, current_col):

            if not self.filters:
                return True

            for c, f_data in self.filters.items():
                if c == current_col:
                    continue

                item = self.table.item(r, c)
                if not item:
                    return False

                val = self._get_value(item)

                if 'hidden_values' in f_data and val in f_data['hidden_values']:
                    return False

                if 'number_filter' in f_data:
                    nf = f_data['number_filter']
                    try:
                        clean = val.split(' ')[0].replace(
                            , "").replace(",", "")
                        num = float(clean)
                        if nf['op'] == 'gt' and not (num > nf['value']):
                            return False
                        elif nf['op'] == 'lt' and not (num < nf['value']):
                            return False
                    except:
                        pass

                if 'date_range' in f_data:
                    dr = f_data['date_range']
                    try:
                        d = QDate.fromString(val, "yyyy-MM-dd")
                        if d.isValid():
                            if d < dr[0] or d > dr[1]:
                                return False
                    except:
                        pass

            return True

        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):

                pass

            if match_other_filters(row, col):
                item = self.table.item(row, col)
                if item:
                    unique_values.add(self._get_value(item))

        sorted_values = sorted(list(unique_values), key=str.lower)

        checkboxes = {}
        current_hidden = self.filters.get(col, {}).get('hidden_values', set())

        def add_checkbox(val):
            cb = QCheckBox(val if val else "(Blanks)")
            cb.setChecked(val not in current_hidden)
            content_layout.addWidget(cb)
            checkboxes[val] = cb

        for val in sorted_values:
            add_checkbox(val)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        if not current_hidden:
            select_all_cb.setChecked(True)
        elif len(current_hidden) == len(sorted_values):
            select_all_cb.setChecked(False)
        else:
            select_all_cb.setCheckState(Qt.CheckState.PartiallyChecked)

        def on_search(text):
            text = text.lower()
            for val, cb in checkboxes.items():
                if text in val.lower():
                    cb.show()
                else:
                    cb.hide()

        search_box.textChanged.connect(on_search)

        def on_select_all(state):
            is_checked = (state == Qt.CheckState.Checked.value)
            for cb in checkboxes.values():
                if not cb.isHidden():
                    cb.setChecked(is_checked)

        select_all_cb.stateChanged.connect(on_select_all)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.setStyleSheet(
            )
        cancel_btn.setStyleSheet(
            )

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def apply():
            new_hidden = set()
            for val, cb in checkboxes.items():
                if not cb.isChecked():
                    new_hidden.add(val)

            if col not in self.filters:
                self.filters[col] = {}
            self.filters[col]['hidden_values'] = new_hidden

            self.apply_filters()
            menu.close()
            self.viewport().update()

        ok_btn.clicked.connect(apply)
        cancel_btn.clicked.connect(menu.close)

        wa = QWidgetAction(menu)
        wa.setDefaultWidget(container)
        menu.addAction(wa)
        menu.exec(global_pos)

    def apply_filters(self):

        TOTAL_ROW_ROLE = Qt.ItemDataRole.UserRole + 1

        for row in range(self.table.rowCount()):
            should_hide = False

            item0 = self.table.item(row, 0)
            if item0 and item0.data(TOTAL_ROW_ROLE):

                self.table.setRowHidden(row, False)
                continue

            for col, f_data in self.filters.items():
                item = self.table.item(row, col)
                if not item:
                    continue

                val = self._get_value(item)

                if 'hidden_values' in f_data and val in f_data['hidden_values']:
                    should_hide = True
                    break

                if 'number_filter' in f_data:
                    nf = f_data['number_filter']
                    try:

                        clean = val.split(' ')[0].replace(
                            , "").replace(",", "")
                        num = float(clean)
                        if nf['op'] == 'gt' and not (num > nf['value']):
                            should_hide = True
                            break
                        elif nf['op'] == 'lt' and not (num < nf['value']):
                            should_hide = True
                            break
                    except:
                        pass

                if 'date_range' in f_data:
                    dr = f_data['date_range']

                    try:
                        d = QDate.fromString(val, "yyyy-MM-dd")
                        if d.isValid():
                            if d < dr[0] or d > dr[1]:
                                should_hide = True
                                break
                    except:
                        pass

            self.table.setRowHidden(row, should_hide)

        self.table.scrollToTop()
        self.table.viewport().update()

        self.filterChanged.emit()

    def clear_filters(self):
        self.filters = {}
        self.apply_filters()
        self.viewport().update()

    def clear_filter_for_column(self, col):
        if col in self.filters:
            del self.filters[col]
            self.apply_filters()
            self.viewport().update()

class BooleanTableWidgetItem(QTableWidgetItem):
    
    FILTER_ROLE = ExcelHeaderView.FILTER_DATA_ROLE

    def __init__(self, value, display_text=""):
        super().__init__(display_text)
        self.setData(self.FILTER_ROLE, value)

    def __lt__(self, other):
        try:
            val_self = self.data(self.FILTER_ROLE) or ""
            val_other = other.data(self.FILTER_ROLE) or ""
            return val_self < val_other
        except:
            return super().__lt__(other)