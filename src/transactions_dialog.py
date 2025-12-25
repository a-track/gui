from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QCheckBox, QHeaderView, QWidget, QMessageBox,
                             QProgressBar, QComboBox, QStyledItemDelegate)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import datetime
from delegates import ComboBoxDelegate, DateDelegate
from utils import safe_eval_math
from excel_filter import ExcelHeaderView
import re
from custom_widgets import NoScrollComboBox

# Define a role for identifying the Total row to keep it at the top
TOTAL_ROW_ROLE = Qt.ItemDataRole.UserRole + 1


# Define a role for identifying the Total row to keep it at the top
TOTAL_ROW_ROLE = Qt.ItemDataRole.UserRole + 1

class TotalAwareTableWidgetItem(QTableWidgetItem):
    """Base class that ensures the Total row stays at the top/bottom as pinned."""
    def __lt__(self, other):
        try:
            # Check if THIS item is a Total Row item
            am_i_total = self.data(TOTAL_ROW_ROLE)
            # Check if OTHER item is a Total Row item
            is_other_total = other.data(TOTAL_ROW_ROLE)
            
            # If both are total (shouldn't happen often in 1 table): 
            # fall back to equality or text sort
            if am_i_total and is_other_total:
                return self.text() < other.text()

            # Handle mixing TotalAware items with raw QTableWidgetItems (legacy safety)
            # 'other' might not have data() if it's not a QTableWidgetItem 
            # (though in __lt__ it usually is).
            
            sort_order = self.tableWidget().horizontalHeader().sortIndicatorOrder()
            is_asc = (sort_order == Qt.SortOrder.AscendingOrder)

            # If I am Total:
            # ASC: I want to be First (Smallest). So I < Other is TRUE.
            # DESC: I want to be First (Largest). So I > Other. I < Other is FALSE.
            if am_i_total:
                return is_asc

            # If Other is Total:
            # ASC: Other is First (Smallest). I > Other. I < Other is FALSE.
            # DESC: Other is First (Largest). I < Other. I < Other is TRUE.
            if is_other_total:
                return not is_asc

            # Special handling for explicit "Total" text (fallback)
            if self.text() == "Total":
                return is_asc
            if getattr(other, 'text', lambda: "")() == "Total":
                return not is_asc

            # Delegate to actual content sort
            return self.actual_lt(other)
            
        except (ValueError, AttributeError, Exception):
            return super().__lt__(other)

    def actual_lt(self, other):
        return super().__lt__(other)


class StringTableWidgetItem(TotalAwareTableWidgetItem):
    """For text columns that need to respect the Total Row."""
    pass


class NumericTableWidgetItem(TotalAwareTableWidgetItem):
    def actual_lt(self, other):
        # Helper to clean string: remove everything except digits, dot, minus
        def get_val(t):
            if not t: return 0.0
            # Remove currency suffixes like " CHF"
            t = t.split(' ')[0]
            # Remove commas
            clean = re.sub(r'[^\d.-]', '', t)
            return float(clean) if clean else 0.0
            
        return get_val(self.text()) < get_val(other.text())


class AlwaysTopTableWidgetItem(NumericTableWidgetItem):
    pass

class ConfirmedTableWidgetItem(TotalAwareTableWidgetItem):
    """
    Shows no text but sorts/filters based on hidden data.
    """
    FILTER_ROLE = Qt.ItemDataRole.UserRole + 99
    
    def __init__(self, value):
        super().__init__("") # No visible text
        self.setData(self.FILTER_ROLE, value)
        
    def actual_lt(self, other):
        # We need to sort by the hidden role value
        try:
            val_self = self.data(self.FILTER_ROLE) or ""
            val_other = other.data(self.FILTER_ROLE) or ""
            return val_self < val_other
        except:
            return super().__lt__(other)


class TransactionLoaderThread(QThread):
    finished = pyqtSignal(list)
    progress = pyqtSignal(int)
    
    def __init__(self, budget_app, year, month, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.year = year
        self.month = month
    
    def run(self):
        try:
            if self.year == 'All':
                transactions = self.budget_app.get_all_transactions()
            else:
                transactions = self.budget_app.get_transactions_by_month(self.year, self.month)
            self.finished.emit(transactions)
        except Exception as e:
            print(f"Error loading transactions: {e}")
            self.finished.emit([])

class TransactionsDialog(QDialog):
    
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        self.all_transactions = []
        self.filtered_transactions = []
        
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle('View All Transactions')
        self.setMinimumSize(1000, 600)
        
        layout = QVBoxLayout()
        
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel('Year:'))
        self.year_combo = NoScrollComboBox()
        self.populate_years()
        self.year_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.year_combo)
        
        filter_layout.addWidget(QLabel('Month:'))
        self.month_combo = NoScrollComboBox()
        self.populate_months()
        self.month_combo.setCurrentText('All') # Default to All
        self.month_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.month_combo)
        
        filter_layout.addSpacing(15)
        # Show All Dates Checkbox
        self.show_all_dates_checkbox = QCheckBox("Show All Dates")
        self.show_all_dates_checkbox.toggled.connect(self.on_show_all_dates_toggled)
        filter_layout.addWidget(self.show_all_dates_checkbox)

        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        self.info_label = QLabel('Loading transactions...')
        self.info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px;')
        layout.addWidget(self.info_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Filter Controls
        filter_controls_layout = QHBoxLayout()
        
        self.confirm_all_button = QPushButton('Confirm All Visible Transactions')
        self.confirm_all_button.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        ''')
        self.confirm_all_button.clicked.connect(self.confirm_all_visible)
        self.confirm_all_button.setEnabled(False)
        filter_controls_layout.addWidget(self.confirm_all_button)
        
        self.all_confirmed_label = QLabel('✓ All transactions confirmed')
        self.all_confirmed_label.setStyleSheet('''
            QLabel {
                color: #4CAF50;
                font-weight: bold;
                padding: 8px 16px;
                background-color: #f0f9f0;
                border: 1px solid #4CAF50;
                border-radius: 4px;
            }
        ''')
        self.all_confirmed_label.setVisible(False)
        filter_controls_layout.addWidget(self.all_confirmed_label)
        
        filter_controls_layout.addStretch()
        
        self.reset_filters_btn = QPushButton("Reset Filters")
        self.reset_filters_btn.clicked.connect(self.reset_filters)
        self.reset_filters_btn.setStyleSheet("padding: 5px;")
        filter_controls_layout.addWidget(self.reset_filters_btn)
        filter_controls_layout.addStretch()
        layout.addLayout(filter_controls_layout)

        self.table = QTableWidget()
        
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Date', 'Type', 'Amount', 'Amount To', 'Qty', 'Account', 'Account To', 'Inv. Acc', 'Payee', 
            'Category', 'Notes', 'Confirmed', 'Delete'
        ])

        # Use Excel-Style Header
        self.header_view = ExcelHeaderView(self.table)
        self.table.setHorizontalHeader(self.header_view)
        
        # Hide Vertical Header (Row Numbers)
        self.table.verticalHeader().setVisible(False)

        # Configure Column Types for Filters
        self.header_view.set_column_types({
            1: 'date',
            3: 'number',
            4: 'number',
            5: 'number'
        })
        
        # Disable filters for ID, Delete
        self.header_view.set_filter_enabled(0, False)
        self.header_view.set_filter_enabled(13, False)
        
        # Header Tooltips
        self.header_view.filterChanged.connect(self.update_count_label)
        
        # Header Tooltips
        header_tooltips = [
            "Unique transaction identifier",
            "Date the transaction occurred",
            "Income, Expense, or Transfer",
            "Transaction value (Source Currency)",
            "Transaction value (Destination Currency)",
            "Number of shares/units (for Investments)",
            "Source Account",
            "Destination Account (for Transfers)",
            "Associated Investment Account",
            "Recipient or Payer",
            "Budget Category",
            "Additional notes",
            "Verify this transaction against your real bank statement.\n(Optional - for your own tracking)",
            "Delete transaction"
        ]
        for col, tooltip in enumerate(header_tooltips):
            item = self.table.horizontalHeaderItem(col)
            if item: item.setToolTip(tooltip)
            
        self.table.setSortingEnabled(True)
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)
        
        self.table.setAlternatingRowColors(True)
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
        
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 120) # Date
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 90) # Amount
        self.table.setColumnWidth(4, 90) # Amount To
        self.table.setColumnWidth(5, 70) # Qty
        self.table.setColumnWidth(6, 150) # Account From
        self.table.setColumnWidth(7, 150) # Account To
        self.table.setColumnWidth(8, 120) # Inv Acc
        self.table.setColumnWidth(12, 80) # Confirmed
        self.table.setColumnWidth(13, 70) # Actions
        
        header = self.table.horizontalHeader()
        content_columns = [9, 10, 11] # Payee, Category, Notes
        for col in content_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.verticalHeader().setDefaultSectionSize(35)
        
        # Set Delegates
        self.date_delegate = DateDelegate(self.table)
        self.table.setItemDelegateForColumn(1, self.date_delegate)

        self.account_delegate = ComboBoxDelegate(self.table, self.get_account_options)
        self.table.setItemDelegateForColumn(6, self.account_delegate)
        self.table.setItemDelegateForColumn(7, self.account_delegate) # Also for Account To
        
        self.invest_account_delegate = ComboBoxDelegate(self.table, self.get_investment_account_options)
        self.table.setItemDelegateForColumn(8, self.invest_account_delegate)

        self.category_delegate = ComboBoxDelegate(self.table, self.get_category_options)
        self.table.setItemDelegateForColumn(10, self.category_delegate) # Verify index
        
        layout.addWidget(self.table)
        
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Set Default to Current Year
        self.set_current_month_year()
        
        # Load transactions
        self.load_transactions()

    def reset_filters(self):
        if hasattr(self, 'header_view'):
            self.header_view.clear_filters()
        
        self.set_current_month_year()
        
        self.load_transactions()
    
    def get_account_options(self):
        accounts = self.budget_app.get_all_accounts()
        return [f"{a.account} {a.currency}" for a in accounts if getattr(a, 'is_active', True)] # Intentionally similar to display format
    
    def get_category_options(self):
        categories = self.budget_app.get_all_categories()
        # Return sub_category
        return sorted([c.sub_category for c in categories])
    
    def populate_years(self):
        current_year = datetime.datetime.now().year
        years = list(range(current_year - 5, current_year + 2))
        self.year_combo.addItems([str(year) for year in years])
    
    def populate_months(self):
        months = ['All'] + [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        self.month_combo.addItems(months)
    
    def set_current_month_year(self):
        now = datetime.datetime.now()
        current_year = str(now.year)
        current_month = now.strftime('%B')
        
        self.year_combo.blockSignals(True)
        self.month_combo.blockSignals(True)
        
        index = self.year_combo.findText(current_year)
        if index >= 0:
            self.year_combo.setCurrentIndex(index)
        
        index = self.month_combo.findText('All')
        if index >= 0:
            self.month_combo.setCurrentIndex(index)

        self.year_combo.blockSignals(False)
        self.month_combo.blockSignals(False)
    
    def on_show_all_dates_toggled(self, checked):
        self.year_combo.setEnabled(not checked)
        self.month_combo.setEnabled(not checked)
        self.load_transactions()
        
    def load_transactions(self):
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            return

        self.progress_bar.setVisible(True)
        self.info_label.setText('Loading transactions...')
        
        show_all_dates = False
        if hasattr(self, 'show_all_dates_checkbox'):
            show_all_dates = self.show_all_dates_checkbox.isChecked()
            
        if show_all_dates:
             selected_year = 'All'
             selected_month = 0
        else:
             selected_year = int(self.year_combo.currentText())
             month_text = self.month_combo.currentText()
             selected_month = 0 if month_text == 'All' else self.month_combo.currentIndex()

        self.loader_thread = TransactionLoaderThread(self.budget_app, selected_year, selected_month, parent=self)
        self.loader_thread.finished.connect(self.on_transactions_loaded)
        self.loader_thread.start()
        
    def on_transactions_loaded(self, transactions):
        self.progress_bar.setVisible(False)
        
        # Filter out invalid/empty transactions (ghost records)
        valid_transactions = [t for t in transactions if t.date and str(t.date).strip()]
        
        self.all_transactions = valid_transactions
        self.filtered_transactions = valid_transactions
        
        self.populate_table(self.filtered_transactions)
        
        if hasattr(self, 'header_view'):
            self.header_view.apply_filters()
            self.table.resizeColumnsToContents()
        else:
            self.update_count_label()
            
        self.update_confirm_all_button_state()
        
    def update_count_label(self):
        total_count = len(self.filtered_transactions)
        visible_count = 0
        
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                visible_count += 1
                
        show_all = False
        if hasattr(self, 'show_all_dates_checkbox'):
            show_all = self.show_all_dates_checkbox.isChecked()
            
        if show_all:
            period_str = "All Dates"
        else:
            selected_year = self.year_combo.currentText()
            selected_month = self.month_combo.currentText()
            period_str = f"{selected_month} {selected_year}"
        
        if visible_count == total_count:
            text = f'Showing {total_count} transactions for {period_str}'
        else:
            text = f'Showing {visible_count} of {total_count} transactions for {period_str}'
            
        self.info_label.setText(text)
        self.update_confirm_all_button_state()

    def apply_filters(self):
        # Reset filters when period changes to avoid confusion
        if hasattr(self, 'header_view'):
            self.header_view.filters = {}
            # We don't need to call clear_filters() fully because load_transactions 
            # will rebuild the table anyway. Just clearing state is enough.
            self.header_view.viewport().update()
            
        # Redispatch to load_transactions which now handles the DB fetch
        self.load_transactions()

    def is_loading(self):
        """Check if background loader is running"""
        return hasattr(self, 'loader_thread') and self.loader_thread.isRunning()

    def cleanup(self):
        """Cleanup resources before closing"""
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            self.loader_thread.quit()
            self.loader_thread.wait()
    
    def populate_table(self, transactions):
        self.table.blockSignals(True)
        self.table.setRowCount(len(transactions))
        self.table.setSortingEnabled(False)
        
        # Pre-fetch accounts for fast lookup
        accounts = self.budget_app.get_all_accounts()
        accounts_map = {acc.id: f'{acc.account} {acc.currency}' for acc in accounts}
        
        for row, trans in enumerate(transactions):
            # Safe date handling for invalid rows (though we filtered them, good to be safe)
            if not trans.date:
                continue # Skip rows with no date
            
            id_item = NumericTableWidgetItem(str(trans.id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            id_item.setBackground(QColor(240, 240, 240))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)
            
            date_item = QTableWidgetItem(str(trans.date))
            self.table.setItem(row, 1, date_item)
            
            type_item = QTableWidgetItem(str.title(trans.type))
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Type read-only for now
            self.table.setItem(row, 2, type_item)
            
            amount_value = trans.amount
            
            amount_item = NumericTableWidgetItem(f"{amount_value:.2f}" if amount_value is not None else "")
            if amount_value is not None:
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, amount_item)
            
            # Amount To (Column 4)
            to_amount_value = trans.to_amount
            to_amount_item = NumericTableWidgetItem(f"{to_amount_value:.2f}" if to_amount_value is not None else "")
            if to_amount_value is not None:
                to_amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
            if trans.type != 'transfer':
                to_amount_item.setFlags(to_amount_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                to_amount_item.setBackground(QColor(245, 245, 245))
                
            self.table.setItem(row, 4, to_amount_item)
            
            # Qty (Column 5)
            qty_value = trans.qty
            qty_item = NumericTableWidgetItem(str(qty_value) if qty_value is not None else "")
            if qty_value is not None:
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, qty_item)

            account_name = accounts_map.get(trans.account_id, "")
            self.table.setItem(row, 6, QTableWidgetItem(account_name))

            # Account To (Column 7)
            to_account_name = accounts_map.get(trans.to_account_id, "")
            to_account_item = QTableWidgetItem(to_account_name)
            if trans.type != 'transfer':
                to_account_item.setFlags(to_account_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                to_account_item.setBackground(QColor(245, 245, 245)) # Grey out
            self.table.setItem(row, 7, to_account_item)
            
            # Inv Account (Column 8)
            inv_account_name = accounts_map.get(trans.invest_account_id, "")
            inv_account_item = QTableWidgetItem(inv_account_name)
            
            # Allow linking Investment Account for Investment, Income (Dividends), and Expense (Fees)
            if trans.type not in ['investment', 'income', 'expense']:
                inv_account_item.setFlags(inv_account_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                inv_account_item.setBackground(QColor(245, 245, 245)) # Grey out
                
            self.table.setItem(row, 8, inv_account_item)
            
            payee_item = QTableWidgetItem(trans.payee or "")
            if trans.type == 'transfer':
                payee_item.setFlags(payee_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 9, payee_item)
            
            sub_category_item = QTableWidgetItem(trans.sub_category or "")
            if trans.type == 'transfer':
                sub_category_item.setFlags(sub_category_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 10, sub_category_item)
            
            # Notes (Column 11)
            notes_item = QTableWidgetItem(trans.notes or "")
            self.table.setItem(row, 11, notes_item)
            
            # Confirmed (Column 12)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout()
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            checkbox = QCheckBox()
            checkbox.setChecked(trans.confirmed)
            checkbox.setProperty('trans_id', trans.id)
            checkbox.stateChanged.connect(self.on_checkbox_changed)
            
            checkbox_layout.addWidget(checkbox)
            checkbox_widget.setLayout(checkbox_layout)
            
            # Add hidden item for sorting/filtering
            conf_val = "Yes" if trans.confirmed else "No"
            conf_item = ConfirmedTableWidgetItem(conf_val)
            conf_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable) # Read-only backing
            conf_item.setForeground(QColor(0, 0, 0, 0)) # Redundant but safe
            self.table.setItem(row, 12, conf_item)
            
            self.table.setCellWidget(row, 12, checkbox_widget)
            
            # Actions (Column 13)
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
            delete_btn.setProperty('trans_id', trans.id)
            delete_btn.clicked.connect(self.on_delete_clicked)
            delete_btn.setToolTip('Delete transaction')
            
            action_layout.addWidget(delete_btn)
            action_widget.setLayout(action_layout)
            
            self.table.setCellWidget(row, 13, action_widget)
            
            self.color_row_by_type(row, trans.type)
        
        self.table.resizeColumnsToContents()
        
        # Enforce minimum width for Date column to ensure visibility during editing
        self.table.setColumnWidth(1, max(150, self.table.columnWidth(1)))
        
        # Autosize window width
        total_width = self.table.horizontalHeader().length() + 80 # + padding for scrollbar/margins
        if total_width > self.width():
            self.resize(total_width, self.height())
            
        self.table.blockSignals(False)
        self.table.setSortingEnabled(True)

    def on_cell_changed(self, row, column):
        try:
            item = self.table.item(row, column)
            if not item:
                return

            # Check if confirmed (Column 12 is Confirmed Checkbox, backing is item)
            conf_item = self.table.item(row, 12)
            if conf_item and conf_item.text() == "Yes":
                self.show_status("Cannot edit confirmed transaction", error=True)
                QMessageBox.warning(self, "Transaction Confirmed", 
                    "This transaction is confirmed and cannot be modified.\n"
                    "Please uncheck the confirmation box first.")
                self.revert_cell(row, column)
                return
                
            trans_id_item = self.table.item(row, 0)
            if not trans_id_item:
                return
                
            trans_id = int(trans_id_item.text())
            new_value = item.text().strip()
            
            # Map column to db field
            # 1: Date, 3: Amount, 4: Amount To, 5: Qty, 6: Account, 7: Account To, 8: Inv Acc, 9: Payee, 10: Sub Category, 11: Notes
            field = None
            
            if column == 1: # Date
                field = 'date'
                try:
                    datetime.datetime.strptime(new_value, '%Y-%m-%d')
                except ValueError:
                    self.show_status(f'Invalid date format: {new_value}. Use YYYY-MM-DD', error=True)
                    self.revert_cell(row, column)
                    return
            elif column == 3: # Amount
                field = 'amount'
                try:
                    new_value = safe_eval_math(new_value)
                except ValueError:
                    self.show_status('Invalid amount expression', error=True)
                    self.revert_cell(row, column)
                    return
            elif column == 4: # Amount To
                # Double check we are allowed to edit this
                trans_type = self.table.item(row, 2).text().lower()
                if trans_type != 'transfer':
                     # This shouldn't be reachable via UI due to flags, but good for safety
                     self.revert_cell(row, column)
                     return
                     
                field = 'to_amount'
                try:
                    new_value = safe_eval_math(new_value)
                except ValueError:
                    self.show_status('Invalid amount expression', error=True)
                    self.revert_cell(row, column)
                    return
            elif column == 5: # Qty
                field = 'qty'
                if new_value:
                    try:
                        new_value = float(new_value)
                    except ValueError:
                        self.show_status('Invalid quantity', error=True)
                        self.revert_cell(row, column)
                        return
                else:
                    new_value = None
            elif column == 6: # Account From
                field = 'account_id'
                account_id = self.budget_app.get_account_id_from_name_currency(new_value)
                if account_id is None:
                    self.show_status(f'Account "{new_value}" not found.', error=True)
                    self.revert_cell(row, column)
                    return
                new_value = account_id
            elif column == 7: # Account To (Transfer only)
                field = 'to_account_id'
                account_id = self.budget_app.get_account_id_from_name_currency(new_value)
                if account_id is None:
                    self.show_status(f'Account "{new_value}" not found.', error=True)
                    self.revert_cell(row, column)
                    return
                new_value = account_id
            elif column == 8: # Inv Account (Investment only)
                field = 'invest_account_id'
                if not new_value: # Allow clearing the investment account
                    new_value = None
                else:
                    account_id = self.budget_app.get_account_id_from_name_currency(new_value)
                    if account_id is None:
                        self.show_status(f'Investment Account "{new_value}" not found.', error=True)
                        self.revert_cell(row, column)
                        return
                    new_value = account_id
            elif column == 9: # Payee
                field = 'payee'
            elif column == 10: # Category (Sub Category)
                field = 'category_id'
                # Resolve sub_category name to ID
                categories = self.budget_app.get_all_categories()
                cat_obj = next((c for c in categories if c.sub_category == new_value), None)
                
                if not cat_obj and new_value: 
                    # If user typed something invalid (though usually it's a combo box)
                    self.show_status(f'Category "{new_value}" not found.', error=True)
                    self.revert_cell(row, column)
                    return
                
                new_value = cat_obj.id if cat_obj else None
            elif column == 11: # Notes
                field = 'notes'
            
            if field:
                success = self.budget_app.update_transaction(trans_id, **{field: new_value})
                if success:
                    self.show_status(f'Updated transaction #{trans_id}')
                    # Update local model
                    trans = self.filtered_transactions[row]
                    setattr(trans, field, new_value)
                    
                    if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                        self.parent_window.update_balance_display()
                else:
                    self.show_status(f'Error updating transaction #{trans_id}', error=True)
                    self.revert_cell(row, column)
                    
        except Exception as e:
            print(f"Error in on_cell_changed: {e}")
            self.show_status('Error updating transaction', error=True)
            self.revert_cell(row, column)

    def revert_cell(self, row, column):
        """Revert cell to value from local model"""
        try:
            self.table.blockSignals(True)
            trans = self.filtered_transactions[row]
            
            value = ""
            if column == 1:
                value = str(trans.date)
            elif column == 3:
                value = f"{trans.amount:.2f}" if trans.amount is not None else ""
            elif column == 4:
                value = f"{trans.to_amount:.2f}" if trans.to_amount is not None else ""
            elif column == 5:
                value = str(trans.qty) if trans.qty is not None else ""
            elif column == 6:
                value = self.get_account_name_by_id(trans.account_id)
            elif column == 7:
                value = self.get_account_name_by_id(trans.to_account_id)
            elif column == 8:
                value = self.get_account_name_by_id(trans.invest_account_id)
            elif column == 9:
                value = trans.payee or ""
            elif column == 10:
                value = trans.sub_category or ""
            elif column == 11:
                value = trans.notes or ""
                
            self.table.item(row, column).setText(value)
        except Exception as e:
            print(f"Error reverting cell: {e}")
        finally:
            self.table.blockSignals(False)
    
    def get_account_name_by_id(self, account_id):
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return f'{account.account} {account.currency}'
        return ""
    
    def color_row_by_type(self, row, trans_type):
        color_map = {
            'income': QColor(230, 255, 230),
            'expense': QColor(255, 230, 230),
            'transfer': QColor(230, 230, 255),
            'investment': QColor(255, 255, 230) # Light yellow for investment
        }
        
        if trans_type in color_map:
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(color_map[trans_type])
    
    def on_checkbox_changed(self, state):
        try:
            checkbox = self.sender()
            trans_id = checkbox.property('trans_id')
            self.budget_app.toggle_confirmation(trans_id)
            self.show_status(f'Transaction #{trans_id} confirmation toggled!')
            
            if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                self.parent_window.update_balance_display()
            
            self.update_confirm_all_button_state()
            
        except Exception as e:
            print(f"Error in on_checkbox_changed: {e}")
            self.show_status('Error updating confirmation!', error=True)
            
    def confirm_all_visible(self):
        try:
            unconfirmed_transactions = []
            
            for row in range(self.table.rowCount()):
                if self.table.isRowHidden(row):
                    continue
                    
                checkbox_widget = self.table.cellWidget(row, 12)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox and not checkbox.isChecked():
                        trans_id = checkbox.property('trans_id')
                        unconfirmed_transactions.append(trans_id)
            
            if not unconfirmed_transactions:
                self.show_status('All visible transactions are already confirmed!')
                return
            
            reply = QMessageBox.question(
                self,
                'Confirm All Transactions',
                f'Are you sure you want to confirm all {len(unconfirmed_transactions)} unconfirmed transactions?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                confirmed_count = 0
                for trans_id in unconfirmed_transactions:
                    try:
                        self.budget_app.toggle_confirmation(trans_id)
                        confirmed_count += 1
                    except Exception as e:
                        print(f"Error confirming transaction {trans_id}: {e}")
                
                # Refresh data completely to be safe
                self.load_transactions()
                
                if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()
                
                self.show_status(f'Successfully confirmed {confirmed_count} transactions!')
                
        except Exception as e:
            print(f"Error in confirm_all_visible: {e}")
            self.show_status('Error confirming transactions!', error=True)

    def update_confirm_all_button_state(self):
        has_unconfirmed = False
        all_confirmed = True
        
        visible_rows = 0
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
                
            visible_rows += 1
            checkbox_widget = self.table.cellWidget(row, 12)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    if not checkbox.isChecked():
                        has_unconfirmed = True
                        all_confirmed = False
                        break
        
        self.confirm_all_button.setEnabled(visible_rows > 0 and has_unconfirmed)
        self.all_confirmed_label.setVisible(visible_rows > 0 and all_confirmed)
    
    def on_delete_clicked(self):
        try:
            button = self.sender()
            trans_id = button.property('trans_id')
            
            # Find row index to check confirmation
            index = self.table.indexAt(button.parentWidget().pos())
            if index.isValid():
                row = index.row()
                conf_item = self.table.item(row, 9)
                if conf_item and conf_item.text() == "Yes":
                    self.show_status("Cannot delete confirmed transaction", error=True)
                    QMessageBox.warning(self, "Transaction Confirmed", 
                        "This transaction is confirmed and cannot be deleted.\n"
                        "Please uncheck the confirmation box first.")
                    return
            
            reply = QMessageBox.question(
                self, 
                'Confirm Delete', 
                f'Delete transaction #{trans_id}?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.budget_app.delete_transaction(trans_id)
                self.show_status(f'Transaction #{trans_id} deleted!')
                self.refresh_table()
                
                if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()
                
        except Exception as e:
            print(f"Error in on_delete_clicked: {e}")
            self.show_status('Error deleting transaction!', error=True)
    
    def refresh_table(self):
        self.load_transactions()
        self.show_status('Table refreshed!')
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))

    def get_account_options(self):
        accs = self.budget_app.get_all_accounts()
        return sorted([f'{a.account} {a.currency}' for a in accs if a.account])

    def get_investment_account_options(self):
        accs = self.budget_app.get_all_accounts()
        # Filter only Investment accounts
        options = sorted([f'{a.account} {a.currency}' for a in accs if getattr(a, 'is_investment', False) and a.account])
        return [""] + options

    def cleanup(self):
        """Cleanup threads before closing"""
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            self.loader_thread.quit()
            self.loader_thread.wait(1000) # Wait up to 1s
            if self.loader_thread.isRunning():
                self.loader_thread.terminate()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)