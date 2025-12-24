from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDateEdit, QMessageBox, QMenu, QInputDialog, QDialog, QDialogButtonBox, QApplication)
from PyQt6.QtCore import Qt, QDate, QRect
from PyQt6.QtGui import QColor, QAction, QPainter
from datetime import datetime

from transactions_dialog import NumericTableWidgetItem
from excel_filter import ExcelHeaderView
from delegates import DateDelegate

class RestrictedExcelHeaderView(ExcelHeaderView):
    def mouseReleaseEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex == 0:
            # Sort only, no menu
            self.sectionClicked.emit(logicalIndex)
            self.table.scrollToTop()
        # Ignore other columns

    def paintSection(self, painter, rect, logicalIndex):
        # Draw standard header (text, bg) ONLY
        QHeaderView.paintSection(self, painter, rect, logicalIndex)

class ExchangeRatesTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.currencies = [] # List of currency codes matching table columns
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Controls
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
        self.save_btn.setToolTip("Commit all changes to the database. Unsaved changes will be lost on refresh.")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setEnabled(False) # Enabled on edit
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)

        # Matrix Table
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
        
        # Context Menu for Deletion
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Set Date Delegate
        self.date_delegate = DateDelegate(self.table)
        self.table.setItemDelegateForColumn(0, self.date_delegate)
        
        layout.addWidget(self.table)
        
        # Legend
        layout.addWidget(QLabel("Tip: Right-click on a row to delete the entire date entry."))

        # Status Label
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
        self.table.blockSignals(True)
        self.save_btn.setEnabled(False)
        self.table.clear()
        
        # 1. Setup Columns
        self.currencies = self.get_display_currencies()
        headers = ["Date"] + self.currencies
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # Custom Header
        self.header_view = RestrictedExcelHeaderView(self.table)
        self.table.setHorizontalHeader(self.header_view)
        
        # Config (only needed for painting logic in parent class, though we disabled menu)
        col_types = {0: 'date'}
        for i in range(1, len(headers)):
            col_types[i] = 'number'
        self.header_view.set_column_types(col_types)
        
        self.table.setSortingEnabled(True)
        # Disable the default sort arrow
        self.table.horizontalHeader().setSortIndicatorShown(False)
        
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setVisible(True)
        
        # Add Header Tooltips
        self.table.horizontalHeader().setToolTip("Double-click to edit rates.")
        for i, curr in enumerate(self.currencies):
            # Item 0 is Date
            item = self.table.horizontalHeaderItem(i+1)
            if item:
                item.setToolTip(f"Exchange Rate for {curr} relative to CHF.\n(e.g. 1 {curr} = X.XX CHF)")
        
        # 2. Fetch Data
        raw_data = self.budget_app.get_history_matrix_data()
        
        # 3. Pivot Data: {date_str: {currency: rate}}
        pivot_data = {}
        for (date_str, curr, rate) in raw_data:
            if date_str not in pivot_data:
                pivot_data[date_str] = {}
            pivot_data[date_str][curr] = rate
            
        # 4. Populate Rows
        dates = sorted(pivot_data.keys(), reverse=True)
        self.table.setRowCount(len(dates))
        
        for r, date_str in enumerate(dates):
            # Date Column (Editable)
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
            date_item.setData(Qt.ItemDataRole.UserRole, date_str)
            # date_item.setBackground(QColor("#f5f5f5"))
            self.table.setItem(r, 0, date_item)
            
            # Currency Columns
            rates = pivot_data[date_str]
            for c, curr in enumerate(self.currencies):
                val = rates.get(curr, "")
                if val:
                    item_text = f"{val:.6f}".rstrip('0').rstrip('.')
                else:
                    item_text = ""
                
                item = NumericTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, c + 1, item)
                
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 120)  # Ensure Date column is wide enough
        self.table.horizontalHeader().setStretchLastSection(False)  # constant width for all columns
        self.table.blockSignals(False)

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
        # Dialog to pick date
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
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_date = date_edit.date().toString("yyyy-MM-dd")
            
            # Check if date already exists in table
            existing_dates = []
            for r in range(self.table.rowCount()):
                item = self.table.item(r, 0)
                if item:
                    existing_dates.append(item.text())
            
            if new_date in existing_dates:
                QMessageBox.warning(self, "Warning", "This date already exists in the table.")
                return

            # Insert new row at top
            self.table.blockSignals(True)
            self.table.insertRow(0)
            
            # Date Item
            date_item = QTableWidgetItem(new_date)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            date_item.setBackground(QColor("#e3f2fd")) # Highlight new row
            self.table.setItem(0, 0, date_item)
            
            # Empty Rate Items
            for c in range(len(self.currencies)):
                # Optional: Pre-fill with previous date's rates? 
                # For now leave empty to force explicit entry.
                item = QTableWidgetItem("") 
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(0, c + 1, item)
            
            self.table.blockSignals(False)
            self.on_item_changed(None) # Enable save

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
            # Delete from DB immediately? Or wait for Save?
            # It's safer/clearer to do immediately for "Delete Row" actions usually, 
            # effectively acting as a "command" rather than an "edit".
            conn = self.budget_app._get_connection()
            try:
                conn.execute("DELETE FROM exchange_rates WHERE date = ?", (date_str,))
                conn.commit()
                self.table.removeRow(row)
                QMessageBox.information(self, "Deleted", "Rates deleted.")
                # If we had pending unsaved changes elsewhere, they are still pending.
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
        # UI Feedback
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status_label.setText("Saving changes...")
        self.status_label.repaint() # Force update
        
        rates_to_save = [] # list of (date, currency, rate)
        rates_to_delete = [] # list of (date, currency)
        dates_to_delete = set()
        
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        
        try:
            for r in range(rows):
                date_item = self.table.item(r, 0)
                if not date_item: continue
                date_str = date_item.text()
                
                if not self.validate_date(date_str):
                     raise ValueError(f"Invalid date format '{date_str}'. Use YYYY-MM-DD (Row {r+1})")

                # Detect Rename
                original_date = date_item.data(Qt.ItemDataRole.UserRole)
                if original_date and original_date != date_str:
                    dates_to_delete.add(original_date)
                
                for c in range(1, cols): # Skip date col
                    currency = self.currencies[c-1]
                    item = self.table.item(r, c)
                    
                    # Handle empty cells (implicit or explicit)
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
                        # Re-raise with context
                        raise ValueError(f"Invalid rate '{text}' for {currency} on {date_str}")

            # 1. Handle Renames
            if dates_to_delete:
                conn = self.budget_app._get_connection()
                try:
                    for old_date in dates_to_delete:
                        conn.execute("DELETE FROM exchange_rates WHERE date = ?", (old_date,))
                    conn.commit()
                finally:
                    conn.close()

            # 2. Bulk Save (Upsert)
            success_upsert = True
            if rates_to_save:
                success_upsert = self.budget_app.add_exchange_rates_bulk(rates_to_save)
            
            # 3. Bulk Delete
            success_delete = True
            if rates_to_delete:
                success_delete = self.budget_app.delete_exchange_rates_bulk(rates_to_delete)

            if success_upsert and success_delete:
                QApplication.restoreOverrideCursor()
                self.status_label.setText("Saved successfully")
                QMessageBox.information(self, "Success", "All changes saved successfully.")
                self.refresh_data() # Reset UI state
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
