"""
Main window for the Budget Tracker application.
Optimized for performance with large datasets.
"""
import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QComboBox, QRadioButton, QButtonGroup, QMessageBox,
                             QDateEdit, QGroupBox, QScrollArea, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from models import BudgetApp
from transactions_dialog import TransactionsDialog
from account_perspective import AccountPerspectiveDialog
from accounts_dialog import AccountsDialog
from categories_dialog import CategoriesDialog

class BalanceLoaderThread(QThread):
    """Thread for loading balance data in background"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, budget_app):
        super().__init__()
        self.budget_app = budget_app
    
    def run(self):
        try:
            balances = self.budget_app.get_balance_summary()
            self.finished.emit(balances)
        except Exception as e:
            self.error.emit(str(e))

class BudgetTrackerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.budget_app = BudgetApp()
        self.balance_loader = None
        self.init_ui()
        self.load_balances_async()

    def init_ui(self):
        self.setWindowTitle('Budget Tracker')
        self.setMinimumSize(1000, 800)
        self.resize(1200, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Title
        title = QLabel('Budget Tracker')
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet('color: #2196F3;')
        main_layout.addWidget(title)
        
        main_layout.addSpacing(20)
        
        # Balance summary section
        balance_label = QLabel('Account Balances')
        balance_label.setStyleSheet('font-weight: bold; font-size: 14px;')
        main_layout.addWidget(balance_label)
        
        # Progress bar for initial loading
        self.loading_progress = QProgressBar()
        self.loading_progress.setVisible(False)
        self.loading_progress.setRange(0, 0)  # Indeterminate progress
        main_layout.addWidget(self.loading_progress)
        
        # Create scroll area for balance display
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(400)
        scroll_area.setStyleSheet('border: 1px solid #cccccc; border-radius: 5px;')
        
        # Balance display widget
        balance_widget = QWidget()
        self.balance_layout = QVBoxLayout(balance_widget)
        
        self.balance_display = QLabel('Loading balances...')
        self.balance_display.setStyleSheet('background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: "Courier New", monospace; font-size: 12px;')
        self.balance_display.setWordWrap(False)
        self.balance_layout.addWidget(self.balance_display)
        
        scroll_area.setWidget(balance_widget)
        main_layout.addWidget(scroll_area)
        
        main_layout.addSpacing(20)
        
        # Transaction Form Group
        form_group = QGroupBox('Add Transaction')
        form_group.setStyleSheet('QGroupBox { font-weight: bold}')
        form_layout = QVBoxLayout()
        
        # Transaction type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel('Transaction Type:'))
        self.expense_radio = QRadioButton('Expense')
        self.income_radio = QRadioButton('Income')
        self.transfer_radio = QRadioButton('Transfer')
        self.expense_radio.setChecked(True)
        
        self.type_group = QButtonGroup()
        self.type_group.addButton(self.income_radio)
        self.type_group.addButton(self.expense_radio)
        self.type_group.addButton(self.transfer_radio)
        
        type_layout.addWidget(self.income_radio)
        type_layout.addWidget(self.expense_radio)
        type_layout.addWidget(self.transfer_radio)
        type_layout.addStretch()
        form_layout.addLayout(type_layout)
        
        # Date
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel('Date:'))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        date_layout.addWidget(self.date_input)
        date_layout.addStretch()
        form_layout.addLayout(date_layout)
        
        # Amount
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel('Amount:'))
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText('Enter amount')
        amount_layout.addWidget(self.amount_input)
        amount_layout.addStretch()
        form_layout.addLayout(amount_layout)
        
        # Account
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel('Account:'))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(200)
        self.update_account_combo()
        account_layout.addWidget(self.account_combo)
        account_layout.addStretch()
        form_layout.addLayout(account_layout)
        
        # Parent Category (for income/expense)
        self.parent_category_layout = QHBoxLayout()
        self.parent_category_layout.addWidget(QLabel('Category:'))
        self.parent_category_combo = QComboBox()
        self.parent_category_combo.setMinimumWidth(200)
        self.parent_category_combo.currentTextChanged.connect(self.on_parent_category_changed)
        self.parent_category_layout.addWidget(self.parent_category_combo)
        self.parent_category_layout.addStretch()
        form_layout.addLayout(self.parent_category_layout)
        
        # Sub Category (for income/expense)
        self.sub_category_layout = QHBoxLayout()
        self.sub_category_layout.addWidget(QLabel('Sub Category:'))
        self.sub_category_combo = QComboBox()
        self.sub_category_combo.setMinimumWidth(200)
        self.sub_category_layout.addWidget(self.sub_category_combo)
        self.sub_category_layout.addStretch()
        form_layout.addLayout(self.sub_category_layout)
        
        # To Account (for transfers)
        self.to_account_layout = QHBoxLayout()
        self.to_account_layout.addWidget(QLabel('To Account:'))
        self.to_account_combo = QComboBox()
        self.to_account_combo.setMinimumWidth(200)
        self.update_to_account_combo()
        self.to_account_layout.addWidget(self.to_account_combo)
        self.to_account_layout.addStretch()
        form_layout.addLayout(self.to_account_layout)
        
        # Payee
        payee_layout = QHBoxLayout()
        payee_layout.addWidget(QLabel('Payee:'))
        self.payee_input = QLineEdit()
        self.payee_input.setPlaceholderText('Optional')
        payee_layout.addWidget(self.payee_input)
        payee_layout.addStretch()
        form_layout.addLayout(payee_layout)
        
        # Notes
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel('Notes:'))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText('Optional notes')
        notes_layout.addWidget(self.notes_input)
        notes_layout.addStretch()
        form_layout.addLayout(notes_layout)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # Update UI when transaction type changes
        self.income_radio.toggled.connect(self.update_ui_for_type)
        self.expense_radio.toggled.connect(self.update_ui_for_type)
        self.transfer_radio.toggled.connect(self.update_ui_for_type)
        self.update_ui_for_type()
        
        main_layout.addSpacing(20)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
        main_layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton('Add Transaction')
        add_btn.clicked.connect(self.add_transaction)
        add_btn.setStyleSheet('background-color: #2196F3; color: white; padding: 10px; font-size: 14px;')
        button_layout.addWidget(add_btn)
        
        view_btn = QPushButton('View All Transactions')
        view_btn.clicked.connect(self.view_transactions)
        view_btn.setStyleSheet('background-color: #4CAF50; color: white; padding: 10px; font-size: 14px;')
        button_layout.addWidget(view_btn)

        account_view_btn = QPushButton('Account Perspective')
        account_view_btn.clicked.connect(self.view_account_perspective)
        account_view_btn.setStyleSheet('background-color: #9C27B0; color: white; padding: 10px; font-size: 14px;')
        button_layout.addWidget(account_view_btn)
        
        main_layout.addLayout(button_layout)

        # Management buttons
        management_layout = QHBoxLayout()
        
        accounts_btn = QPushButton('Manage Accounts')
        accounts_btn.clicked.connect(self.manage_accounts)
        accounts_btn.setStyleSheet('background-color: #FF9800; color: white; padding: 10px; font-size: 14px;')
        management_layout.addWidget(accounts_btn)
        
        categories_btn = QPushButton('Manage Categories')
        categories_btn.clicked.connect(self.manage_categories)
        categories_btn.setStyleSheet('background-color: #795548; color: white; padding: 10px; font-size: 14px;')
        management_layout.addWidget(categories_btn)
        
        main_layout.addLayout(management_layout)
        main_layout.addStretch()

    def load_balances_async(self):
        """Load balances in background thread to keep UI responsive"""
        self.loading_progress.setVisible(True)
        self.balance_display.setText('Loading balances...')
        
        self.balance_loader = BalanceLoaderThread(self.budget_app)
        self.balance_loader.finished.connect(self.on_balances_loaded)
        self.balance_loader.error.connect(self.on_balances_error)
        self.balance_loader.start()

    def on_balances_loaded(self, balances):
        """Handle completed balance loading"""
        self.loading_progress.setVisible(False)
        self.update_balance_display_with_data(balances)

    def on_balances_error(self, error_message):
        """Handle balance loading error"""
        self.loading_progress.setVisible(False)
        self.balance_display.setText(f'Error loading balances: {error_message}')

    def update_balance_display_with_data(self, balances):
        """Update balance display with pre-loaded data, sorted by transaction count"""
        # Get transaction counts for all accounts
        transaction_counts = {}
        all_accounts = self.budget_app.get_all_accounts()
        for account in all_accounts:
            # Count transactions for this account
            count = self.budget_app.count_transactions_for_account(account.id)
            transaction_counts[account.id] = count
        
        # Group accounts by name (ignoring currency suffix)
        account_groups = {}
        for account_id, data in balances.items():
            # Skip accounts with zero balance
            if data['balance'] == 0:
                continue
                
            account_type = data['type']
            if account_type in ['Cash', 'Bank', 'Credit']:
                # Extract base account name (remove currency suffix)
                account_name = data['account_name']
                base_name = account_name.rsplit(' ', 1)[0]  # Remove last word (currency)
                
                if base_name not in account_groups:
                    account_groups[base_name] = []
                
                # Store account data along with transaction count
                count = transaction_counts.get(account_id, 0)
                account_groups[base_name].append((account_id, data, count))
        
        # Calculate total transaction count per account group
        group_transaction_counts = {}
        for base_name, accounts in account_groups.items():
            total_count = sum(count for _, _, count in accounts)
            group_transaction_counts[base_name] = total_count
        
        # Get all unique currencies from all accounts and calculate totals
        currency_totals = {}
        for base_name, accounts in account_groups.items():
            for account_id, data, count in accounts:
                currency = self.get_currency_for_account(account_id)
                balance = data['balance']
                if currency in currency_totals:
                    currency_totals[currency] += abs(balance)
                else:
                    currency_totals[currency] = abs(balance)
        
        # Sort currencies by total amount in descending order
        all_currencies = sorted(currency_totals.keys(), key=lambda x: currency_totals[x], reverse=True)
        
        # Sort account groups by transaction count (descending)
        sorted_account_groups = sorted(account_groups.items(), 
                                    key=lambda x: group_transaction_counts[x[0]], 
                                    reverse=True)
        
        # Calculate column widths
        account_col_width = 35
        currency_col_width = 15
        
        # Build the display text
        balance_text = ""
        
        # Header
        header = f"{'Account':{account_col_width}}"
        for currency in all_currencies:
            header += f"{currency:>{currency_col_width}}"
        balance_text += header + "\n"
        balance_text += "-" * (account_col_width + len(all_currencies) * currency_col_width) + "\n"
        
        # Display one line per account group, sorted by transaction count
        total_by_currency = {currency: 0.0 for currency in all_currencies}
        for base_name, accounts in sorted_account_groups:
            # Calculate balances per currency for this account group
            group_balances = {currency: 0.0 for currency in all_currencies}
            for account_id, data, count in accounts:
                currency = self.get_currency_for_account(account_id)
                group_balances[currency] += data['balance']
            
            # Display one line for the account group
            line = f"{base_name:{account_col_width}}"
            for currency in all_currencies:
                balance = group_balances[currency]
                if balance != 0:
                    line += f"{balance:>{currency_col_width}.2f}"
                    total_by_currency[currency] += balance
                else:
                    line += f"{'':>{currency_col_width}}"
            balance_text += line + "\n"
        
        # Totals
        balance_text += "-" * (account_col_width + len(all_currencies) * currency_col_width) + "\n"
        total_line = f"{'Total':{account_col_width}}"
        for currency in all_currencies:
            total_line += f"{total_by_currency[currency]:>{currency_col_width}.2f}"
        balance_text += total_line
        
        self.balance_display.setText(balance_text)

    def update_account_combo(self):
        self.account_combo.clear()
        accounts = self.budget_app.get_all_accounts()
        # Sort accounts by ID
        accounts_sorted = sorted(accounts, key=lambda x: x.id)
        for account in accounts_sorted:
            display_text = f"{account.account} {account.currency}"
            self.account_combo.addItem(display_text, account.id)
        # Adjust size after adding items
        self.account_combo.adjustSize()
    
    def update_to_account_combo(self):
        self.to_account_combo.clear()
        accounts = self.budget_app.get_all_accounts()
        # Sort accounts by ID
        accounts_sorted = sorted(accounts, key=lambda x: x.id)
        for account in accounts_sorted:
            display_text = f"{account.account} {account.currency}"
            self.to_account_combo.addItem(display_text, account.id)
        # Adjust size after adding items
        self.to_account_combo.adjustSize()
    
    def update_ui_for_type(self):
        is_transfer = self.transfer_radio.isChecked()
        is_income = self.income_radio.isChecked()
        
        # Show/hide category sections for transfers
        self.parent_category_layout.itemAt(0).widget().setVisible(not is_transfer)
        self.parent_category_combo.setVisible(not is_transfer)
        self.sub_category_layout.itemAt(0).widget().setVisible(not is_transfer)
        self.sub_category_combo.setVisible(not is_transfer)
        
        # Show/hide to_account for transfers
        self.to_account_layout.itemAt(0).widget().setVisible(is_transfer)
        self.to_account_combo.setVisible(is_transfer)
        
        # Update categories based on type
        if not is_transfer:
            trans_type = 'income' if is_income else 'expense'
            self.update_parent_categories(trans_type)

    def update_parent_categories(self, trans_type):
        """Update parent categories based on transaction type"""
        self.parent_category_combo.clear()
        categories = self.budget_app.get_all_categories()
        
        # Get unique parent categories
        parent_categories = set()
        for category in categories:
            if trans_type == 'income':
                # For income, only show 'Income' parent category
                if category.category.lower() == 'income':
                    parent_categories.add(category.category)
            else:
                # For expense, show all except 'Income'
                if category.category.lower() != 'income':
                    parent_categories.add(category.category)
        
        # Add to combo box
        for parent in sorted(list(parent_categories)):
            self.parent_category_combo.addItem(parent)
        
        # Adjust size after adding items
        self.parent_category_combo.adjustSize()
        
        # Auto-select first item and update subcategories
        if self.parent_category_combo.count() > 0:
            self.parent_category_combo.setCurrentIndex(0)
            self.update_sub_categories()

    def on_parent_category_changed(self, parent_category):
        """Handle parent category selection change"""
        self.update_sub_categories()

    def update_sub_categories(self):
        """Update subcategories based on selected parent category"""
        self.sub_category_combo.clear()
        
        parent_category = self.parent_category_combo.currentText()
        if not parent_category:
            return
            
        categories = self.budget_app.get_all_categories()
        
        # Filter subcategories by selected parent category
        sub_categories = []
        for category in categories:
            if category.category == parent_category:
                sub_categories.append(category.sub_category)
        
        # Add to combo box
        for sub in sorted(sub_categories):
            self.sub_category_combo.addItem(sub)
        
        # Adjust size after adding items
        self.sub_category_combo.adjustSize()
        
        # Auto-select first item if available
        if self.sub_category_combo.count() > 0:
            self.sub_category_combo.setCurrentIndex(0)

    def get_currency_for_account(self, account_id):
        """Get currency for a specific account ID"""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account.currency
        return 'CHF'  # Default

    def add_transaction(self):
        # Validate amount
        try:
            amount = float(self.amount_input.text())
            if amount <= 0:
                self.show_status('Amount must be greater than 0', error=True)
                return
        except ValueError:
            self.show_status('Please enter a valid number', error=True)
            return
        
        # Get common values
        date = self.date_input.date().toString("yyyy-MM-dd")
        account_id = self.account_combo.currentData()
        payee = self.payee_input.text().strip()
        notes = self.notes_input.text().strip()
        
        # Add transaction based on type
        if self.transfer_radio.isChecked():
            to_account_id = self.to_account_combo.currentData()
            
            if account_id == to_account_id:
                self.show_status('Cannot transfer to the same account', error=True)
                return
            
            success = self.budget_app.add_transfer(
                date=date,
                from_account_id=account_id,
                to_account_id=to_account_id,
                from_amount=amount,
                notes=notes
            )
            
        elif self.income_radio.isChecked():
            sub_category = self.sub_category_combo.currentText()
            
            success = self.budget_app.add_income(
                date=date,
                amount=amount,
                account_id=account_id,
                payee=payee,
                sub_category=sub_category,
                notes=notes
            )
            
        else:  # Expense
            sub_category = self.sub_category_combo.currentText()
            
            success = self.budget_app.add_expense(
                date=date,
                amount=amount,
                account_id=account_id,
                sub_category=sub_category,
                payee=payee,
                notes=notes
            )
        
        if success:
            self.show_status('Transaction added successfully! ✓')
            # Clear form
            self.amount_input.clear()
            self.payee_input.clear()
            self.notes_input.clear()
            self.account_combo.setCurrentIndex(0)
            self.to_account_combo.setCurrentIndex(0)
            
            # Update balance display
            self.update_balance_display()
        else:
            self.show_status('Error adding transaction', error=True)

    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
        
        # Clear after 5 seconds
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))

    def view_transactions(self):
        """Open the transactions dialog as a non-modal window"""
        try:
            # Check if dialog already exists and is visible
            if hasattr(self, 'transactions_dialog') and self.transactions_dialog is not None:
                try:
                    if self.transactions_dialog.isVisible():
                        self.transactions_dialog.raise_()
                        self.transactions_dialog.activateWindow()
                        return
                except:
                    pass
            
            dialog = TransactionsDialog(self.budget_app, self)
            self.transactions_dialog = dialog
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            
        except Exception as e:
            print(f"Error in view_transactions: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, 'Error', f'Error opening transactions view:\n{str(e)}')
            self.show_status('Error opening transactions view', error=True)

    def view_account_perspective(self):
        """Open the account perspective dialog."""
        try:
            if hasattr(self, 'account_perspective_dialog') and self.account_perspective_dialog is not None:
                try:
                    if self.account_perspective_dialog.isVisible():
                        self.account_perspective_dialog.raise_()
                        self.account_perspective_dialog.activateWindow()
                        return
                except:
                    pass
            
            dialog = AccountPerspectiveDialog(self.budget_app, self)
            self.account_perspective_dialog = dialog
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            
        except Exception as e:
            print(f"Error in view_account_perspective: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, 'Error', f'Error opening account perspective:\n{str(e)}')
            self.show_status('Error opening account perspective', error=True)

    def manage_accounts(self):
        """Open the accounts management dialog."""
        dialog = AccountsDialog(self.budget_app, self)
        dialog.exec()
        # Refresh account combos after dialog closes
        self.update_account_combo()
        self.update_to_account_combo()
        self.update_balance_display()

    def manage_categories(self):
        """Open the categories management dialog."""
        dialog = CategoriesDialog(self.budget_app, self)
        dialog.exec()
        # Refresh category combo after dialog closes
        self.update_ui_for_type()

    def update_balance_display(self):
        """Public method to update balance display (triggers async loading)"""
        self.load_balances_async()