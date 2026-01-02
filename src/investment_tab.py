from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDateEdit, QMessageBox, QMenu, QDialog, QDialogButtonBox, QApplication)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QAction
from datetime import datetime

from transactions_dialog import NumericTableWidgetItem
from excel_filter import ExcelHeaderView
from utils import format_currency

from delegates import DateDelegate


class RestrictedExcelHeaderView(ExcelHeaderView):
    def mouseReleaseEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex == 0:

            self.sectionClicked.emit(logicalIndex)
            self.table.scrollToTop()

    def paintSection(self, painter, rect, logicalIndex):

        QHeaderView.paintSection(self, painter, rect, logicalIndex)


class InvestmentTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.tracked_accounts = []
        self.acc_id_to_col = {}
        self.init_ui()

    def showEvent(self, event):
        self.refresh_data()
        super().showEvent(event)

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

        info_label = QLabel(
            "Enter valuations based on the account's Valuation Method (Total Value or Price/Qty). Changes valid only after Save.")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

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

    def get_tracked_accounts(self):
        """Fetch investment accounts configured for tracking."""
        all_accounts = self.budget_app.get_all_accounts()

        tracked = [
            acc for acc in all_accounts
            if getattr(acc, 'is_investment', False)
            and getattr(acc, 'valuation_strategy', 'No Valuation') not in ['No Valuation', None, '']
        ]
        tracked.sort(key=lambda x: x.account.lower())
        return tracked

    def refresh_data(self):
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        

        self.save_btn.setEnabled(False)
        self.table.clear()

        try:
            self.tracked_accounts = self.get_tracked_accounts()

            headers = ["Date"] + [acc.account for acc in self.tracked_accounts]

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

            self.table.horizontalHeader().setToolTip(
                "Double-click cells to edit. Right-click rows to delete.")
            for i, acc in enumerate(self.tracked_accounts):
                if acc.valuation_strategy == 'Price/Qty':
                    tip = f"Valuation Method: Price/Qty\nEnter the price per single share/unit.\nTotal Value will be calculated as Price * Quantity."
                else:
                    tip = f"Valuation Method: Total Value\nEnter the total market value of the holding."

                item = self.table.horizontalHeaderItem(i+1)
                if item:
                    item.setToolTip(tip)

            self.acc_id_to_col = {acc.id: i+1 for i,
                                  acc in enumerate(self.tracked_accounts)}

            if not self.tracked_accounts:
                self.table.setRowCount(0)
                return

            try:
                raw_data = self.budget_app.get_investment_history_matrix_data()

                pivot_data = {}
                for (date_str, acc_id, val) in raw_data:
                    if date_str not in pivot_data:
                        pivot_data[date_str] = {}
                    pivot_data[date_str][acc_id] = val

                dates = sorted(pivot_data.keys(), reverse=True)
                self.table.setRowCount(len(dates))

                for r, date_str in enumerate(dates):

                    date_item = QTableWidgetItem(date_str)
                    date_item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                    date_item.setData(Qt.ItemDataRole.UserRole, date_str)

                    self.table.setItem(r, 0, date_item)

                    row_vals = pivot_data[date_str]
                    for c, acc in enumerate(self.tracked_accounts):
                        val = row_vals.get(acc.id)

                        if val is not None:
                            precision = 4 if acc.valuation_strategy == 'Price/Qty' else 2
                            item_text = format_currency(val, precision=precision)
                        else:
                            item_text = ""

                        item = NumericTableWidgetItem(item_text)
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        self.table.setItem(r, c + 1, item)

                self.table.resizeColumnsToContents()
                self.table.setColumnWidth(0, 120)
                self.table.horizontalHeader().setStretchLastSection(False)

            except Exception as e:
                print(f"Error refreshing investment data: {e}")
                QMessageBox.critical(
                    self, "Error", "Failed to load investment data.")

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

        label = QLabel("Select Date for new entry:")
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

            for r in range(self.table.rowCount()):
                item = self.table.item(r, 0)
                if item and item.text() == new_date:
                    QMessageBox.warning(
                        self, "Warning", "This date already exists.")
                    return

            self.table.blockSignals(True)
            self.table.insertRow(0)

            date_item = QTableWidgetItem(new_date)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled |
                               Qt.ItemFlag.ItemIsSelectable)
            date_item.setBackground(QColor("#e3f2fd"))
            self.table.setItem(0, 0, date_item)

            for c in range(len(self.tracked_accounts)):
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
        date_item = self.table.item(row, 0)
        if not date_item:
            return
        date_str = date_item.text()

        menu = QMenu()
        delete_action = QAction(f"Delete All Entries for {date_str}", self)
        delete_action.triggered.connect(lambda: self.delete_row(row, date_str))
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_row(self, row, date_str):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete all investment valuations for {date_str}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            conn = self.budget_app._get_connection()
            try:
                conn.execute(
                    "DELETE FROM investment_valuations WHERE date = ?", (date_str,))
                conn.commit()
                self.table.removeRow(row)
                QMessageBox.information(self, "Deleted", "Entries deleted.")
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

        data_to_save = []
        data_to_delete = []
        dates_to_delete = set()

        rows = self.table.rowCount()

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

                for c, acc in enumerate(self.tracked_accounts):
                    item = self.table.item(r, c + 1)

                    if not item or not item.text().strip():

                        data_to_delete.append((date_str, acc.id))
                        continue

                    text = item.text().strip()

                    try:
                        # Clean currency formatting
                        clean_text = text.replace("'", "").replace(",", "")
                        val = float(clean_text)
                        if val < 0:
                            raise ValueError(f"Value must be >= 0 (Row {r+1})")

                        data_to_save.append((date_str, acc.id, val))
                    except ValueError:
                        raise ValueError(
                            f"Invalid value '{text}' for {acc.account} on {date_str}")

            if dates_to_delete:
                conn = self.budget_app._get_connection()
                try:
                    for old_date in dates_to_delete:
                        conn.execute(
                            "DELETE FROM investment_valuations WHERE date = ?", (old_date,))
                    conn.commit()
                finally:
                    conn.close()

            if data_to_save:
                self.budget_app.add_investment_valuations_bulk(data_to_save)

            if data_to_delete:
                self.budget_app.delete_investment_valuations_bulk(
                    data_to_delete)

            QApplication.restoreOverrideCursor()
            self.status_label.setText("Saved successfully")

            QMessageBox.information(
                self, "Success", "Changes saved successfully.")
            self.refresh_data()

        except ValueError as ve:
            QApplication.restoreOverrideCursor()
            self.status_label.setText("Validation Error")
            QMessageBox.warning(self, "Validation Error", str(ve))
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.status_label.setText("Error saving")
            QMessageBox.critical(self, "Error", f"Save failed: {e}")
        finally:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

    def has_unsaved_changes(self):
        return self.save_btn.isEnabled()

    def filter_content(self, text):
        """Filter table rows based on text matching."""
        search_text = text.lower()
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        
        for row in range(rows):
            should_show = False
            if not search_text:
                should_show = True
            else:
                for col in range(cols):
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        should_show = True
                        break
            self.table.setRowHidden(row, not should_show)
