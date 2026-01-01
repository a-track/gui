from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QLineEdit, QComboBox,
                             QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from excel_filter import ExcelHeaderView
from transactions_dialog import NumericTableWidgetItem
from custom_widgets import NoScrollComboBox


class CategoriesDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)

        self.budget_app = budget_app
        self.parent_window = parent

        self.setWindowTitle('Manage Categories')
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout()

        type_parent_layout = QHBoxLayout()

        type_parent_layout.addWidget(QLabel('Category Type:'))
        self.category_type_combo = NoScrollComboBox()
        self.category_type_combo.addItems(['Expense', 'Income'])
        self.category_type_combo.currentTextChanged.connect(
            self.on_category_type_changed)
        type_parent_layout.addWidget(self.category_type_combo)

        type_parent_layout.addWidget(QLabel('Main Category:'))
        self.parent_category_combo = NoScrollComboBox()
        self.parent_category_combo.setEditable(True)
        self.parent_category_combo.setInsertPolicy(
            QComboBox.InsertPolicy.InsertAtTop)
        self.parent_category_combo.currentTextChanged.connect(
            self.on_parent_category_changed)
        type_parent_layout.addWidget(self.parent_category_combo)

        type_parent_layout.addStretch()
        layout.addLayout(type_parent_layout)

        sub_category_layout = QHBoxLayout()
        sub_category_layout.addWidget(QLabel('Category:'))
        self.sub_category_input = QLineEdit()
        self.sub_category_input.setPlaceholderText('Enter Category name')
        sub_category_layout.addWidget(self.sub_category_input)

        sub_category_layout.addStretch()

        add_btn = QPushButton('Add Category')
        add_btn.clicked.connect(self.add_category)
        add_btn.setStyleSheet(
            'background-color: #4CAF50; color: white; padding: 8px;')
        sub_category_layout.addWidget(add_btn)

        layout.addLayout(sub_category_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ['ID', 'Category Type', 'Main Category', 'Category', 'Delete'])

        header_tooltips = [
            "System ID",
            "Income or Expense",
            "Main grouping",
            "Specific item (Category)",
            "Delete Category"
        ]
        for col, tooltip in enumerate(header_tooltips):
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tooltip)

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #b3d9ff;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 11px;
            }
        """)

        self.table.verticalHeader().hide()

        self.header_view = ExcelHeaderView(self.table)
        self.table.setHorizontalHeader(self.header_view)

        self.header_view.set_filter_enabled(4, False)

        self.header_view.set_column_types({
            0: 'number'
        })

        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()
        for col in range(5):
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.Interactive)

        self.table.verticalHeader().setDefaultSectionSize(35)
        layout.addWidget(self.table)

        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.load_categories()

    def on_category_type_changed(self, category_type):
        """When category type changes, update the parent categories combo"""
        self.load_parent_categories(category_type)

    def on_parent_category_changed(self, parent_category):
        """When parent category changes - placeholder for future functionality"""

    def load_parent_categories(self, category_type=None):
        """Load parent categories filtered by type"""
        categories = self.budget_app.get_all_categories()
        parent_categories = set()

        for category in categories:
            if category_type is None or category.category_type == category_type:
                parent_categories.add(category.category)

        current_text = self.parent_category_combo.currentText()
        self.parent_category_combo.clear()
        self.parent_category_combo.addItems(sorted(list(parent_categories)))

        index = self.parent_category_combo.findText(current_text)
        if index >= 0:
            self.parent_category_combo.setCurrentIndex(index)

    def load_categories(self):
        try:
            self.table.blockSignals(True)
            categories = self.budget_app.get_all_categories()
            self.populate_table(categories)

            self.table.resizeColumnsToContents()

            total_width = self.table.horizontalHeader().length() + 80
            if total_width > self.width():
                self.resize(total_width, self.height())

            self.table.setColumnWidth(0, 50)
            self.table.setColumnWidth(1, max(100, self.table.columnWidth(1)))
            self.table.setColumnWidth(2, max(120, self.table.columnWidth(2)))
            self.table.setColumnWidth(3, max(120, self.table.columnWidth(3)))
            self.table.setColumnWidth(4, max(50, self.table.columnWidth(4)))

            self.table.blockSignals(False)
            self.show_status(f'Loaded {len(categories)} categories')

            current_type = self.category_type_combo.currentText()
            self.load_parent_categories(current_type)

        except Exception as e:
            print(f"Error loading categories: {e}")
            self.table.blockSignals(False)
            self.show_status('Error loading categories', error=True)

    def populate_table(self, categories):
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        try:
            self.table.setRowCount(0)

            valid_categories = [
                c for c in categories if c.id and c.category and str(c.category).strip()]

            self.table.setRowCount(len(valid_categories))

            for row, category in enumerate(valid_categories):
                try:

                    id_item = NumericTableWidgetItem(str(category.id))
                    # Allow editing ID
                    id_item.setFlags(id_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    id_item.setToolTip("Double click to change ID")
                    id_item.setBackground(QColor(240, 240, 240))
                    id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 0, id_item)

                    type_item = QTableWidgetItem(category.category_type or "")
                    self.table.setItem(row, 1, type_item)

                    parent_item = QTableWidgetItem(category.category or "")
                    self.table.setItem(row, 2, parent_item)

                    sub_item = QTableWidgetItem(category.sub_category or "")
                    self.table.setItem(row, 3, sub_item)

                    action_widget = QWidget()
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(1, 1, 1, 1)
                    action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                    delete_btn = QPushButton('✕')
                    delete_btn.setFixedSize(22, 22)
                    delete_btn.setStyleSheet('''
                        QPushButton {
                            background-color: #ff4444;
                            color: white;
                            border: none;
                            border-radius: 11px;
                            font-weight: bold;
                            font-size: 9px;
                            margin: 0px;
                            padding: 0px;
                        }
                        QPushButton:hover {
                            background-color: #cc0000;
                        }
                        QPushButton:pressed {
                            background-color: #990000;
                        }
                    ''')
                    delete_btn.setProperty('cat_id', category.id)
                    delete_btn.clicked.connect(self.delete_category)
                    delete_btn.setToolTip('Delete category')

                    action_layout.addWidget(delete_btn)
                    action_widget.setLayout(action_layout)

                    self.table.setCellWidget(row, 4, action_widget)
                except Exception as e:
                    print(f"Error populating category row {row}: {e}")

            self.table.setColumnWidth(0, 50)
            self.table.resizeColumnsToContents()
        finally:
            self.table.setSortingEnabled(True)
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)

        total_width = self.table.horizontalHeader().length() + 80
        if total_width > self.width():
            self.resize(total_width, self.height())

        self.table.setColumnWidth(0, max(100, self.table.columnWidth(0)))
        self.table.setColumnWidth(1, max(120, self.table.columnWidth(1)))
        self.table.setColumnWidth(2, max(120, self.table.columnWidth(2)))
        self.table.setColumnWidth(3, max(70, self.table.columnWidth(3)))

        self.table.blockSignals(False)
        self.show_status(f'Loaded {len(categories)} categories')

        current_type = self.category_type_combo.currentText()
        self.load_parent_categories(current_type)

    def on_cell_changed(self, row, column):
        try:

            if column not in [0, 1, 2, 3]:
                return

            item = self.table.item(row, column)
            if not item:
                return

            id_item = self.table.item(row, 0)
            if not id_item:
                return

            try:
                cat_id = int(id_item.text())
            except ValueError:
                self.show_status("Invalid ID format", error=True)
                QTimer.singleShot(0, self.load_categories)
                return

            if column == 0:
                # Handle ID change
                delete_btn = self.table.cellWidget(row, 4).findChild(QPushButton)
                if not delete_btn:
                     QTimer.singleShot(0, self.load_categories)
                     return

                old_id = delete_btn.property('cat_id')
                
                try:
                    new_id = int(item.text().strip())
                except ValueError:
                    self.show_status("Invalid ID format", error=True)
                    QTimer.singleShot(0, self.load_categories)
                    return
                
                if old_id == new_id:
                    return

                # Pre-check existence using full list scan for robustness
                all_cats = self.budget_app.get_all_categories()
                existing_cat = next((c for c in all_cats if c.id == new_id), None)
                
                if existing_cat:
                    self.show_status(f"Category ID {new_id} already exists", error=True)
                    QMessageBox.warning(self, "ID Exists", f"Category ID {new_id} already exists.\nPlease choose a unique ID.")
                    QTimer.singleShot(0, self.load_categories)
                    return

                reply = QMessageBox.question(
                    self, 'Confirm ID Change', 
                    f'Are you sure you want to change Category ID from {old_id} to {new_id}?\n'
                    f'This will update all linked transactions and budgets.',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    success, msg = self.budget_app.update_category_id(old_id, new_id)
                    if success:
                         self.show_status(f'Category ID updated to {new_id}')
                         # Delay reload to avoid commitData warning
                         QTimer.singleShot(0, self.load_categories)
                         if hasattr(self.parent_window, 'refresh_global_state'):
                            self.parent_window.refresh_global_state()
                    else:
                        self.show_status(f'Error: {msg}', error=True)
                        QTimer.singleShot(0, self.load_categories)
                else:
                    QTimer.singleShot(0, self.load_categories)

                return

            new_value = item.text().strip()

            categories = self.budget_app.get_all_categories()
            orig_cat_obj = next(
                (c for c in categories if c.id == cat_id), None)

            if not orig_cat_obj:
                self.show_status("Error: Category not found in DB", error=True)
                return

            kwargs = {}
            if column == 1:
                kwargs['new_type'] = new_value
            elif column == 2:
                kwargs['new_category'] = new_value
            elif column == 3:
                kwargs['new_sub_category'] = new_value
            else:
                return

            success = self.budget_app.update_category(cat_id, **kwargs)

            if success:
                self.show_status(f'Category updated successfully')
                self.load_categories()
            else:
                self.show_status(
                    f'Error updating category (possibly duplicate)', error=True)

                self.table.blockSignals(True)
                if column == 1:
                    item.setText(orig_cat_obj.category_type)
                elif column == 2:
                    item.setText(orig_cat_obj.category)
                elif column == 3:
                    item.setText(orig_cat_obj.sub_category)
                self.table.blockSignals(False)

        except Exception as e:
            print(f"Error in on_cell_changed: {e}")
            self.show_status('Error updating category', error=True)

            try:
                self.table.blockSignals(True)
                categories = self.budget_app.get_all_categories()
                orig_cat = next(
                    (c for c in categories if c.id == cat_id), None)
                if orig_cat:
                    if column == 1:
                        item.setText(orig_cat.category_type)
                    elif column == 2:
                        item.setText(orig_cat.category)
                    elif column == 3:
                        item.setText(orig_cat.sub_category)
                self.table.blockSignals(False)
            except:
                pass

    def revert_cell(self, row, column, sub_category):
        try:
            self.table.blockSignals(True)

            categories = self.budget_app.get_all_categories()
            category = next(
                (c for c in categories if c.sub_category == sub_category), None)

            if category:
                value = ""
                if column == 0:
                    value = category.category_type
                elif column == 1:
                    value = category.category

                self.table.item(row, column).setText(value)
        finally:
            self.table.blockSignals(False)

    def add_category(self):
        category_type = self.category_type_combo.currentText()
        parent_category = self.parent_category_combo.currentText().strip()
        sub_category = self.sub_category_input.text().strip()

        if not parent_category or not sub_category:
            self.show_status(
                'Please enter both main category and category', error=True)
            return

        success = self.budget_app.add_category(
            sub_category, parent_category, category_type)

        if success:
            self.show_status('Category added successfully!')
            self.sub_category_input.clear()
            self.load_categories()
        else:
            self.show_status('Error adding category', error=True)

    def delete_category(self):
        try:
            button = self.sender()
            cat_id = button.property('cat_id')

            categories = self.budget_app.get_all_categories()
            cat_obj = next((c for c in categories if c.id == cat_id), None)

            if not cat_obj:
                self.show_status('Error: Category not found', error=True)
                return

            sub_category = cat_obj.sub_category

            reply = QMessageBox.question(
                self,
                'Confirm Delete',
                f'Delete category "{sub_category}"?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                success, message = self.budget_app.delete_category(cat_id)
                if success:
                    self.show_status('Category deleted successfully!')
                    self.load_categories()
                else:
                    self.show_status(f'Error: {message}', error=True)

        except Exception as e:
            print(f"Error deleting category: {e}")
            self.show_status('Error deleting category', error=True)

    def show_status(self, message, error=False):
        try:
            self.status_label.setText(message)
            if error:
                self.status_label.setStyleSheet(
                    'color: #f44336; padding: 5px; font-weight: bold;')
            else:
                self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')

            QTimer.singleShot(5000, self._safe_clear_status)
        except RuntimeError:
            pass

    def _safe_clear_status(self):
        try:
            self.status_label.setText('')
        except RuntimeError:
            pass
