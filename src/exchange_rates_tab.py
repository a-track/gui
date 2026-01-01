from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDateEdit, QMessageBox, QMenu, QDialog, QDialogButtonBox, QApplication)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QAction
from datetime import datetime

from transactions_dialog import NumericTableWidgetItem
from excel_filter import ExcelHeaderView
from delegates import DateDelegate


class RestrictedExcelHeaderView(ExcelHeaderView):
    def mouseReleaseEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex == 0:

            self.sectionClicked.emit(logicalIndex)
            self.table.scrollToTop()

    def paintSection(self, painter, rect, logicalIndex):

        QHeaderView.paintSection(self, painter, rect, logicalIndex)


class ExchangeRatesTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.currencies = []
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Add Date Row")
        add_btn.setToolTip("Add a new historical date entry")
        add_btn.clicked.connect(self.add_date_row)
        btn_layout.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()

        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 6px 15px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.save_btn.setToolTip(
            "Commit all changes to the database. Unsaved changes will be lost on refresh.")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #b3d9ff;
                color: black;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 9pt;
            }
        """)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        self.date_delegate = DateDelegate(self.table)
        self.table.setItemDelegateForColumn(0, self.date_delegate)

        layout.addWidget(self.table)

        layout.addWidget(
            QLabel("Tip: Right-click on a row to delete the entire date entry."))

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.status_label)

    def get_display_currencies(self):
        """Fetch active currencies (excluding CHF/MULTI) used as columns."""
        accounts = self.budget_app.get_all_accounts()
        currencies = set()
        for acc in accounts:
            if acc.currency and acc.currency.upper() not in ['CHF', 'MULTI']:
                currencies.add(acc.currency.upper())
        return sorted(list(currencies))

    def refresh_data(self):
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.save_btn.setEnabled(False)
        self.table.clear()

        try:
            self.currencies = self.get_display_currencies()
            headers = ["Date"] + self.currencies
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)

            self.header_view = RestrictedExcelHeaderView(self.table)
            self.table.setHorizontalHeader(self.header_view)

            col_types = {0: 'date'}
            for i in range(1, len(headers)):
                col_types[i] = 'number'
            self.header_view.set_column_types(col_types)

            self.table.setSortingEnabled(True)

            self.table.horizontalHeader().setSortIndicatorShown(False)

            self.table.verticalHeader().hide()
            self.table.horizontalHeader().setVisible(True)

            self.table.horizontalHeader().setToolTip("Double-click to edit rates.")
            for i, curr in enumerate(self.currencies):

                item = self.table.horizontalHeaderItem(i+1)
                if item:
                    item.setToolTip(
                        f"Exchange Rate for {curr} relative to CHF.\n(e.g. 1 {curr} = X.XX CHF)")

            raw_data = self.budget_app.get_history_matrix_data()

            pivot_data = {}
            for (date_str, curr, rate) in raw_data:
                if date_str not in pivot_data:
                    pivot_data[date_str] = {}
                pivot_data[date_str][curr] = rate

            dates = sorted(pivot_data.keys(), reverse=True)
            self.table.setRowCount(len(dates))

            for r, date_str in enumerate(dates):

                date_item = QTableWidgetItem(date_str)
                date_item.setFlags(Qt.ItemFlag.ItemIsEnabled |
                                   Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                date_item.setData(Qt.ItemDataRole.UserRole, date_str)

                self.table.setItem(r, 0, date_item)

                rates = pivot_data[date_str]
                for c, curr in enumerate(self.currencies):
                    val = rates.get(curr, "")
                    if val:
                        item_text = f"{val:.6f}".rstrip('0').rstrip('.')
                    else:
                        item_text = ""

                    item = NumericTableWidgetItem(item_text)
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(r, c + 1, item)

            self.table.resizeColumnsToContents()
            self.table.setColumnWidth(0, 120)
            self.table.horizontalHeader().setStretchLastSection(False)
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)

    def on_item_changed(self, item):
        self.save_btn.setEnabled(True)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 6px 15px;
            }
        """)

    def add_date_row(self):

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Date")
        layout = QVBoxLayout(dialog)

        label = QLabel("Select Date for new Rates:")
        layout.addWidget(label)

        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        date_edit.setDisplayFormat("yyyy-MM-dd")
        layout.addWidget(date_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_date = date_edit.date().toString("yyyy-MM-dd")

            existing_dates = []
            for r in range(self.table.rowCount()):
                item = self.table.item(r, 0)
                if item:
                    existing_dates.append(item.text())

            if new_date in existing_dates:
                QMessageBox.warning(
                    self, "Warning", "This date already exists in the table.")
                return

            self.table.blockSignals(True)
            self.table.insertRow(0)

            date_item = QTableWidgetItem(new_date)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled |
                               Qt.ItemFlag.ItemIsSelectable)
            date_item.setBackground(QColor("#e3f2fd"))
            self.table.setItem(0, 0, date_item)

            for c in range(len(self.currencies)):

                item = QTableWidgetItem("")
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(0, c + 1, item)

            self.table.blockSignals(False)
            self.on_item_changed(None)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return

        row = item.row()
        date_str = self.table.item(row, 0).text()

        menu = QMenu()
        delete_action = QAction(f"Delete All Rates for {date_str}", self)
        delete_action.triggered.connect(lambda: self.delete_row(row, date_str))
        menu.addAction(delete_action)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_row(self, row, date_str):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete all exchange rates for {date_str}?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:

            conn = self.budget_app._get_connection()
            try:
                conn.execute(
                    "DELETE FROM exchange_rates WHERE date = ?", (date_str,))
                conn.commit()
                self.table.removeRow(row)
                QMessageBox.information(self, "Deleted", "Rates deleted.")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
            finally:
                conn.close()

    def validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def save_changes(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status_label.setText("Saving changes...")
        self.status_label.repaint()

        rates_to_save = []
        rates_to_delete = []
        dates_to_delete = set()

        rows = self.table.rowCount()
        cols = self.table.columnCount()

        try:
            for r in range(rows):
                date_item = self.table.item(r, 0)
                if not date_item:
                    continue
                date_str = date_item.text()

                if not self.validate_date(date_str):
                    raise ValueError(
                        f"Invalid date format '{date_str}'. Use YYYY-MM-DD (Row {r+1})")

                original_date = date_item.data(Qt.ItemDataRole.UserRole)
                if original_date and original_date != date_str:
                    dates_to_delete.add(original_date)

                for c in range(1, cols):
                    currency = self.currencies[c-1]
                    item = self.table.item(r, c)

                    if not item or not item.text().strip():
                        rates_to_delete.append((date_str, currency))
                        continue

                    text = item.text().strip()

                    try:
                        rate = float(text)
                        if rate <= 0:
                            raise ValueError(f"Rate must be > 0 (Row {r+1})")

                        rates_to_save.append((date_str, currency, rate))
                    except ValueError:

                        raise ValueError(
                            f"Invalid rate '{text}' for {currency} on {date_str}")

            if dates_to_delete:
                conn = self.budget_app._get_connection()
                try:
                    for old_date in dates_to_delete:
                        conn.execute(
                            "DELETE FROM exchange_rates WHERE date = ?", (old_date,))
                    conn.commit()
                finally:
                    conn.close()

            success_upsert = True
            if rates_to_save:
                success_upsert = self.budget_app.add_exchange_rates_bulk(
                    rates_to_save)

            success_delete = True
            if rates_to_delete:
                success_delete = self.budget_app.delete_exchange_rates_bulk(
                    rates_to_delete)

            if success_upsert and success_delete:
                QApplication.restoreOverrideCursor()
                self.status_label.setText("Saved successfully")
                QMessageBox.information(
                    self, "Success", "All changes saved successfully.")
                self.refresh_data()
            else:
                QApplication.restoreOverrideCursor()
                self.status_label.setText("Error saving")
                QMessageBox.critical(self, "Error", "Database save failed.")

        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.status_label.setText("Error saving")
            QMessageBox.critical(self, "Error", f"Save failed: {e}")
        finally:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

    def has_unsaved_changes(self):
        return self.save_btn.isEnabled()
