from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QComboBox, QHeaderView, QWidget, QCheckBox,
                             QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import datetime


from delegates import ComboBoxDelegate, DateDelegate
import datetime
from excel_filter import ExcelHeaderView
from transactions_dialog import NumericTableWidgetItem, AlwaysTopTableWidgetItem
from custom_widgets import NoScrollComboBox



class AccountPerspectiveDialog(QDialog):
    
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        self.selected_account_id = None
        self.all_transactions_for_account = []
        self.filtered_transactions = []
        self.running_balance_history = {}
        
        self.setWindowTitle('Account Perspective')
        self.setMinimumSize(1200, 600)
        
        layout = QVBoxLayout()
        
        hbox_top = QHBoxLayout() # New combined top layout
        
        hbox_top.addWidget(QLabel('Select Account:'))
        
        self.account_combo = NoScrollComboBox()
        self.populate_accounts_combo()
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        hbox_top.addWidget(self.account_combo)
        
        hbox_top.addSpacing(20)
        
        # Balance Label (Init early to prevent crash)
        self.current_balance_label = QLabel('Current Balance: 0.00')
        self.current_balance_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #4CAF50;')
        hbox_top.addWidget(self.current_balance_label)
        
        hbox_top.addSpacing(20)
        
        hbox_top.addWidget(QLabel('Year:'))
        self.year_combo = NoScrollComboBox()
        self.populate_years()
        self.year_combo.currentTextChanged.connect(self.apply_filters)
        hbox_top.addWidget(self.year_combo)
        
        hbox_top.addWidget(QLabel('Month:'))
        self.month_combo = NoScrollComboBox()
        self.populate_months()
        self.month_combo.currentTextChanged.connect(self.apply_filters)
        hbox_top.addWidget(self.month_combo)
        
        hbox_top.addStretch()
        
        layout.addLayout(hbox_top)
        
        button_layout = QHBoxLayout()
        
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
        button_layout.addWidget(self.confirm_all_button)
        
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
        button_layout.addWidget(self.all_confirmed_label)
        
        button_layout.addStretch()
        
        button_layout.addStretch()
        
        # Reset Filters Button
        self.reset_filters_btn = QPushButton("Reset Filters")
        self.reset_filters_btn.clicked.connect(self.reset_filters)
        self.reset_filters_btn.setStyleSheet("padding: 8px 16px;")
        button_layout.addWidget(self.reset_filters_btn)
        
        layout.addLayout(button_layout)
        
        info_label = QLabel('Showing all transactions where this account is involved. Click checkbox to confirm transaction.')
        info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px; background-color: #f0f0f0;')
        layout.addWidget(info_label)
        
        self.table = QTableWidget()
        
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Category', 'Payee', 
            'Other Account', 'Notes', 'Transaction Amount', 'Running Balance',
            'Confirmed', 'Delete'
        ])
        
        # Use Excel-Style Header
        self.header_view = ExcelHeaderView(self.table)
        self.table.setHorizontalHeader(self.header_view)
        
        # Hide Vertical Header
        self.table.verticalHeader().setVisible(False)
        
        # Configure Column Types
        self.header_view.set_column_types({
            0: 'date',
            6: 'number',
            7: 'number'
        })
        
        # Disable Filters
        self.header_view.set_filter_enabled(7, False) # Running Balance
        self.header_view.set_filter_enabled(8, False) # Confirmed
        self.header_view.set_filter_enabled(9, False) # Delete
        
        # Header Tooltips
        
        # Header Tooltips
        header_tooltips = [
            "Transaction Date",
            "Type (Income/Expense/Transfer)",
            "Budget Category",
            "Payer/Payee",
            "Counterparty Account (for Transfers)",
            "Additional Notes",
            "Amount affecting this account",
            "Account Balance after this transaction",
            "Verify this transaction against your real bank statement.\n(Optional - for your own tracking)",
            "Delete Transaction"
        ]
        for col, tooltip in enumerate(header_tooltips):
            item = self.table.horizontalHeaderItem(col)
            if item: item.setToolTip(tooltip)
        
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
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 9pt;
            }
        """)
        
        self.table.verticalHeader().hide()
        
        # Manually manage column widths
        self.table.setColumnWidth(0, 120) # Date (Increased to show full date + button)
        self.table.setColumnWidth(4, 150) # Other Account (Increased width)
        self.table.setColumnWidth(5, 150) # Notes
        self.table.setColumnWidth(8, 80)
        self.table.setColumnWidth(9, 70)
        
        header = self.table.horizontalHeader()
        content_columns = [1, 2, 3, 5, 6, 7] # Adjusted for Notes at 5
        for col in content_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        fixed_columns = [0, 4, 8, 9] # Fixed widths for Date, Other Account, Confirmed, Delete
        for col in fixed_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        
        self.table.verticalHeader().setDefaultSectionSize(35)
        
        # Delegates
        self.date_delegate = DateDelegate(self.table)
        self.table.setItemDelegateForColumn(0, self.date_delegate)
        
        self.category_delegate = ComboBoxDelegate(self.table, self.get_category_options)
        self.table.setItemDelegateForColumn(2, self.category_delegate)
        # Note: 'Other Account' (4) editing is complex (could be payee or transfer account), for now maybe leave as text or simple combo?
        # User asked for 'size of account' not enough, so resizing handles that.
        # But 'modify function doesnt work everywhere'.
        # Let's enable editing for basic fields first.
        
        layout.addWidget(self.table)

        
        self.status_label = QLabel('Select an account to view transactions')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        self.set_current_month_year()
        
        if self.account_combo.count() > 0:
            self.account_combo.setCurrentIndex(0)
            self.on_account_changed(0)
    
    def populate_accounts_combo(self):
        try:
            accounts = self.budget_app.get_all_accounts()
            all_transactions = self.budget_app.get_all_transactions()
            
            account_transaction_count = {}
            for account in accounts:
                if account.id == 0:
                    continue
                count = 0
                for trans in all_transactions:
                    if (trans.account_id == account.id or 
                        trans.to_account_id == account.id):
                        count += 1
                account_transaction_count[account.id] = count
            
            filtered_accounts = [acc for acc in accounts if acc.id != 0 and account_transaction_count.get(acc.id, 0) > 0]
            sorted_accounts = sorted(filtered_accounts, 
                                   key=lambda x: account_transaction_count.get(x.id, 0), 
                                   reverse=True)
            
            for account in sorted_accounts:
                transaction_count = account_transaction_count.get(account.id, 0)
                display_text = f"{account.account} {account.currency} ({transaction_count})"
                self.account_combo.addItem(display_text, account.id)
                
        except Exception as e:
            print(f"Error populating accounts combo: {e}")
            accounts = self.budget_app.get_all_accounts()
            filtered_accounts = [acc for acc in accounts if acc.id != 0]
            for account in filtered_accounts:
                display_text = f"{account.account} {account.currency}"
                self.account_combo.addItem(display_text, account.id)
    
    def populate_years(self):
        current_year = datetime.datetime.now().year
        years = list(range(current_year - 5, current_year + 2))
        self.year_combo.addItems([str(year) for year in years])
    
    def populate_months(self):
        # Add 'All' option first
        self.month_combo.addItem('All')
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        self.month_combo.addItems(months)
    
    def set_current_month_year(self):
        now = datetime.datetime.now()
        current_year = str(now.year)
        
        # Set current year
        index = self.year_combo.findText(current_year)
        if index >= 0:
            self.year_combo.setCurrentIndex(index)
        
        # Set month to 'All' to show full year
        self.month_combo.setCurrentIndex(0)  # 'All' is at index 0
    
    def format_swiss_number(self, number):
        try:
            is_negative = number < 0
            abs_number = abs(number)
            
            integer_part = int(abs_number)
            decimal_part = round(abs_number - integer_part, 2)
            
            integer_str = f"{integer_part:,}".replace(",", "'")
            
            decimal_str = f"{decimal_part:.2f}".split('.')[1]
            
            formatted = f"{integer_str}.{decimal_str}"
            
            if is_negative:
                formatted = f"-{formatted}"
                
            return formatted
        except (ValueError, TypeError):
            return "0.00"
    
    def get_account_name_by_id(self, account_id):
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account.account
        return ""
    
    def get_account_currency_by_id(self, account_id):
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account.currency or ""
        return ""
    
    def get_current_account_currency(self):
        account_id = self.selected_account_id
        if account_id:
            return self.get_account_currency_by_id(account_id)
        return ""
    
    def on_account_changed(self, index):
        if index >= 0:
            self.selected_account_id = self.account_combo.currentData()
            self.load_account_data()
    
    def calculate_running_balance_history(self):
        if not self.selected_account_id or not self.all_transactions_for_account:
            return {}
        
        sorted_transactions = sorted(self.all_transactions_for_account, key=lambda x: (x.date, x.id))
        
        running_balance = 0.0
        balance_history = {}
        
        for trans in sorted_transactions:
            if trans.type == 'income' and trans.account_id == self.selected_account_id:
                transaction_amount = float(trans.amount or 0)
                running_balance += transaction_amount
                
            elif trans.type == 'expense' and trans.account_id == self.selected_account_id:
                transaction_amount = float(trans.amount or 0)
                running_balance -= transaction_amount
                
            elif trans.type == 'transfer':
                if trans.account_id == self.selected_account_id:
                    transaction_amount = float(trans.amount or 0)
                    running_balance -= transaction_amount
                elif trans.to_account_id == self.selected_account_id:
                    transaction_amount = float(trans.to_amount or 0)
                    running_balance += transaction_amount
            
            balance_history[trans.id] = running_balance
        
        return balance_history
    
    def load_account_data(self):
        if not self.selected_account_id:
            return
            
        try:
            account_id = self.selected_account_id
            
            all_transactions = self.budget_app.get_all_transactions()
            
            self.all_transactions_for_account = []
            for trans in all_transactions:
                if (trans.account_id == account_id or 
                    trans.to_account_id == account_id):
                    self.all_transactions_for_account.append(trans)
            
            # Filter out ghost rows (must have date, id, type, and amount)
            # Ensure type is not empty string and amount is not empty string (if it's a string)
            valid_transactions = [
                t for t in self.all_transactions_for_account
                if t.date and str(t.date).strip() 
                   and t.id 
                   and t.type and str(t.type).strip() 
                   and t.amount is not None and str(t.amount).strip() != ""
            ]
            self.all_transactions_for_account = valid_transactions
            
            # Update date limits (placeholder for future use if needed)
            dates = [t.date for t in valid_transactions if t.date]
            if dates:
                pass
            
            self.running_balance_history = self.calculate_running_balance_history()
            
            # ExcelHeaderView populates dynamically
            
            self.apply_filters()
            
        except Exception as e:
            print(f"Error loading account data: {e}")
            import traceback
            traceback.print_exc()
            self.show_status('Error loading account data', error=True)
    
    def apply_filters(self):
        if not self.selected_account_id or not self.all_transactions_for_account:
            return
        
        selected_year = int(self.year_combo.currentText())
        selected_month_text = self.month_combo.currentText()
        
        transactions_to_display = []
        
        # If 'All' is selected, show all transactions for the year
        if selected_month_text == 'All':
            for trans in self.all_transactions_for_account:
                try:
                    if hasattr(trans, 'date') and trans.date:
                        trans_date = trans.date
                        if isinstance(trans_date, str):
                            trans_date = datetime.datetime.strptime(trans_date, '%Y-%m-%d').date()
                        
                        if trans_date.year == selected_year:
                            transactions_to_display.append(trans)
                except (ValueError, AttributeError) as e:
                    print(f"Error parsing date for transaction {trans.id}: {e}")
                    continue
            filter_info = f"All months {selected_year}"
        else:
            # Specific month selected (index is offset by 1 because 'All' is at index 0)
            selected_month = self.month_combo.currentIndex()
            
            for trans in self.all_transactions_for_account:
                try:
                    if hasattr(trans, 'date') and trans.date:
                        trans_date = trans.date
                        if isinstance(trans_date, str):
                            trans_date = datetime.datetime.strptime(trans_date, '%Y-%m-%d').date()
                        
                        if trans_date.year == selected_year and trans_date.month == selected_month:
                            transactions_to_display.append(trans)
                except (ValueError, AttributeError) as e:
                    print(f"Error parsing date for transaction {trans.id}: {e}")
                    continue
            
            filter_info = f"{selected_month_text} {selected_year}"
        
        transactions_to_display = sorted(transactions_to_display, key=lambda x: (x.date, x.id), reverse=True)
        
        transaction_history = []
        
        # Pre-fetch accounts for fast lookup
        accounts = self.budget_app.get_all_accounts()
        accounts_map = {acc.id: f'{acc.account}' for acc in accounts} # Only name needed here?
        # get_account_name_by_id returned account name only. Let's verify.
        # Line 279: return account.account
        # Yes, just account name.

        for trans in transactions_to_display:
            running_balance = self.running_balance_history.get(trans.id, 0.0)
            
            if trans.type == 'income' and trans.account_id == self.selected_account_id:
                transaction_amount = float(trans.amount or 0)
                effect = "+"
                effect = "+"
                other_account = "" # Only show for transfers
                
            elif trans.type == 'expense' and trans.account_id == self.selected_account_id:
                transaction_amount = float(trans.amount or 0)
                effect = "-"
                effect = "-"
                other_account = "" # Only show for transfers
                
            elif trans.type == 'transfer':
                if trans.account_id == self.selected_account_id:
                    transaction_amount = float(trans.amount or 0)
                    effect = "-"
                    other_account = accounts_map.get(trans.to_account_id, "")
                elif trans.to_account_id == self.selected_account_id:
                    transaction_amount = float(trans.to_amount or 0)
                    effect = "+"
                    other_account = accounts_map.get(trans.account_id, "")
                else:
                    continue
            else:
                continue
            
            transaction_history.append({
                'transaction': trans,
                'transaction_amount': transaction_amount,
                'effect': effect,
                'running_balance': running_balance,
                'other_account': other_account
            })
        
        self.populate_table(transaction_history)
        
        current_balance = 0.0
        if self.running_balance_history:
            last_transaction_id = list(self.running_balance_history.keys())[-1]
            current_balance = self.running_balance_history[last_transaction_id]
        
        currency = self.get_current_account_currency()
        balance_color = '#4CAF50' if current_balance >= 0 else '#f44336'
        
        if currency:
            balance_text = f'Current Balance: {currency} {self.format_swiss_number(current_balance)}'
        else:
            balance_text = f'Current Balance: {self.format_swiss_number(current_balance)}'
            
        self.current_balance_label.setText(balance_text)
        self.current_balance_label.setStyleSheet(f'font-weight: bold; font-size: 14px; color: {balance_color};')
        
        account_name = self.account_combo.currentText().split(' (')[0]
        self.show_status(f'Showing {len(transaction_history)} transactions for {account_name} ({filter_info})')
        
        self.update_confirm_all_button_state()
    
    def get_category_options(self):
        categories = self.budget_app.get_all_categories()
        return sorted([c.sub_category for c in categories])

    def on_cell_changed(self, row, column):
        try:
            item = self.table.item(row, column)
            if not item:
                return
            
            if row not in self.transaction_history_map:
                return
                
            trans = self.transaction_history_map[row]
            trans_id = trans.id
            new_value = item.text().strip()
            
            field = None
            
            if column == 0: # Date
                field = 'date'
                try:
                    datetime.datetime.strptime(new_value, '%Y-%m-%d')
                except ValueError:
                    self.show_status(f'Invalid date format: {new_value}. Use YYYY-MM-DD', error=True)
                    self.revert_cell(row, column, str(trans.date))
                    return
            
            elif column == 2: # Category
                field = 'sub_category'
                
            elif column == 3: # Payee
                field = 'payee'
            
            # Column 4 (Other Account) is read-only now, so no logic needed.
            
            elif column == 5: # Notes
                field = 'notes'

            elif column == 6: # Amount
                try:
                    # Remove currency symbols or thousand separators if any
                    clean_value = new_value.replace("'", "").replace("+", "").replace("CHF", "").strip()
                    amount = float(clean_value)
                    
                    # For updates, we usually just pass the positive amount for 'amount' field
                    # The logic for income/expense sign is handled by type.
                    field = 'amount'
                    new_value = abs(amount)
                        
                except ValueError:
                     self.show_status('Invalid amount', error=True)
                     # We can't easily get the original formatted string here without storing it, 
                     # but we can try to re-format the current trans amount
                     self.revert_cell(row, column, "?") 
                     self.refresh_data()
                     return

            if field:
                success = self.budget_app.update_transaction(trans_id, **{field: new_value})
                if success:
                    self.show_status(f'Updated transaction #{trans_id}')
                    self.refresh_data()
                    
                    if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                        self.parent_window.update_balance_display()
                else:
                    self.show_status(f'Error updating transaction #{trans_id}', error=True)
                    self.refresh_data()
                    
        except Exception as e:
            print(f"Error in on_cell_changed: {e}")
            self.show_status('Error updating transaction', error=True)

    def revert_cell(self, row, column, original_value):
        self.table.blockSignals(True)
        self.table.item(row, column).setText(original_value)
        self.table.blockSignals(False)

    def populate_table(self, transaction_history):
        self.table.blockSignals(True)
        
        # Robust filtering before population to prevent "holes"
        valid_history = []
        for data in transaction_history:
            trans = data['transaction']
            # Re-check validity just in case
            if (trans.date and str(trans.date).strip() and 
                trans.type and str(trans.type).strip() and
                data.get('transaction_amount') is not None): # Check processed amount too
                 valid_history.append(data)
                 
        self.table.setRowCount(0) # Force clear to prevent artifacts
        self.table.setRowCount(len(valid_history))
        self.table.setSortingEnabled(False)
        
        self.transaction_history_map = {} # Map row to transaction object for easy access
        
        for row, data in enumerate(valid_history):
            try:
                trans = data['transaction']
                self.transaction_history_map[row] = trans
                
                transaction_amount = data['transaction_amount']
                effect = data['effect']
                running_balance = data['running_balance']
                other_account = data['other_account']
                
                date_item = QTableWidgetItem(str(trans.date))
                self.table.setItem(row, 0, date_item)
                
                t_type = str(trans.type).capitalize() if trans.type else "Unknown"
                type_item = QTableWidgetItem(t_type)
                type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Type read-only
                self.table.setItem(row, 1, type_item)

                #Debug
                # print(f"Row {row}: {trans.date}, Type={trans.type}, Amt={transaction_amount}")
            
                category_item = QTableWidgetItem(trans.sub_category or "")
                if trans.type == 'transfer':
                    category_item.setFlags(category_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, category_item)
                
                payee_item = QTableWidgetItem(trans.payee or "")
                if trans.type == 'transfer':
                    payee_item.setFlags(payee_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, payee_item)
                
                other_acc_item = QTableWidgetItem(other_account)
                # Make Other Account read-only for ALL types to avoid confusion with Payee column
                other_acc_item.setFlags(other_acc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 4, other_acc_item)
                
                # Notes (Column 5)
                notes_item = QTableWidgetItem(trans.notes or "")
                self.table.setItem(row, 5, notes_item)
                
                formatted_amount = self.format_swiss_number(transaction_amount)
                trans_amount_text = f"{effect}{formatted_amount}"
                # Strip effect for editing? No, we better handle parsing
                 # Actually, amount should probably be editable too.
                trans_effect_item = NumericTableWidgetItem(trans_amount_text)
                if effect == "+":
                    trans_effect_item.setForeground(QColor(0, 128, 0))
                else:
                    trans_effect_item.setForeground(QColor(255, 0, 0))
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                trans_effect_item.setFont(font)
                self.table.setItem(row, 6, trans_effect_item)
                
                formatted_balance = self.format_swiss_number(abs(running_balance))
                balance_item = NumericTableWidgetItem(f"{running_balance:.2f}")
                if running_balance > 0:
                    balance_item.setForeground(QColor(0, 128, 0))
                elif running_balance < 0:
                    balance_item.setForeground(QColor(255, 0, 0))
                else:
                    balance_item.setForeground(QColor(0, 0, 0))
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                balance_item.setFont(font)
                balance_item.setFlags(balance_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Balance Read-only
                self.table.setItem(row, 7, balance_item)
                
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
                self.table.setCellWidget(row, 8, checkbox_widget)
                # Delete Button Frame
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
                
                self.table.setCellWidget(row, 9, action_widget)

            except Exception as e:
                print(f"Error populating row {row} (ID {trans.id}): {e}")
                # Continue to next row or partial row is fine (debug will show)
            
        # Ensure sorting is enabled after population
        self.table.setSortingEnabled(True)

        # Post-populate cleanup: Hide any rows that somehow remained empty
        rows_hidden = 0
        for r in range(self.table.rowCount()):
             item = self.table.item(r, 1) # Type column
             if not item or not item.text().strip() or item.text() == "Unknown":
                 self.table.setRowHidden(r, True)
                 rows_hidden += 1
        
        if rows_hidden > 0:
            pass # Silently cleaned up ghost rows
        
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()
        
        # Override specific widths
        self.table.setColumnWidth(0, max(150, self.table.columnWidth(0)))
        self.table.setColumnWidth(4, max(150, self.table.columnWidth(4)))
        self.table.setColumnWidth(8, 80)
        self.table.setColumnWidth(9, 70)
        
        if transaction_history:
            self.table.scrollToTop()
            
        # Autosize window width to show all columns properly
        # Calculate total width needed: sum of all column widths + margins
        total_width = self.table.horizontalHeader().length() + 50  # Add margin for scrollbar and padding
        
        # Get the parent window (could be the dialog itself or the main tabbed window)
        parent_window = self.window()
        if parent_window:
            # Ensure minimum width to display all columns
            min_width = total_width + 100  # Extra padding for window chrome
            if parent_window.width() < min_width:
                parent_window.resize(min_width, parent_window.height())



    def confirm_all_visible(self):
        try:
            unconfirmed_transactions = []
            
            for row in range(self.table.rowCount()):
                checkbox_widget = self.table.cellWidget(row, 7)
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
                
                self.refresh_data()
                
                if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()
                
                self.show_status(f'Successfully confirmed {confirmed_count} transactions!')
                
        except Exception as e:
            print(f"Error in confirm_all_visible: {e}")
            self.show_status('Error confirming transactions!', error=True)
    
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
    
    def update_confirm_all_button_state(self):
        has_unconfirmed = False
        all_confirmed = True
        
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 7)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    if not checkbox.isChecked():
                        has_unconfirmed = True
                        all_confirmed = False
                        break
        
        self.confirm_all_button.setEnabled(self.table.rowCount() > 0 and has_unconfirmed)
        
        self.all_confirmed_label.setVisible(self.table.rowCount() > 0 and all_confirmed)
    
    def reset_filters(self):
        if hasattr(self, 'header_view'):
            self.header_view.clear_filters()
            
    def on_delete_clicked(self):
        try:
            button = self.sender()
            trans_id = button.property('trans_id')
            
            reply = QMessageBox.question(
                self, 
                'Confirm Delete', 
                f'Delete transaction #{trans_id}?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.budget_app.delete_transaction(trans_id)
                self.show_status(f'Transaction #{trans_id} deleted!')
                self.refresh_data()
                
                if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()
                
        except Exception as e:
            print(f"Error in on_delete_clicked: {e}")
            self.show_status('Error deleting transaction!', error=True)
    
    def refresh_data(self):
        if self.selected_account_id:
            self.load_account_data()
            self.show_status('Data refreshed')
        else:
            self.show_status('Please select an account first')
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))