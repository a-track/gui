import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QComboBox, QRadioButton, QButtonGroup, QMessageBox,
                             QDateEdit, QGroupBox, QScrollArea, QProgressBar, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal

from models import BudgetApp
from transactions_dialog import TransactionsDialog
from account_perspective import AccountPerspectiveDialog
from accounts_dialog import AccountsDialog
from categories_dialog import CategoriesDialog
from budget_dialog import BudgetDialog

class BalanceLoaderThread(QThread):
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
        self.transaction_counts = self.budget_app.get_transaction_counts()  # Add this line
        self.init_ui()
        self.load_balances_async()

    def init_ui(self):
        self.setWindowTitle('Budget Tracker')
        self.setMinimumSize(950, 800)
        
        # Create a scroll area for the entire window
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create central widget that will hold all content
        central_widget = QWidget()
        self.setCentralWidget(scroll_area)
        scroll_area.setWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Balance section with proper spacing
        balance_header_layout = QHBoxLayout()
        balance_label = QLabel('Account Balances')
        balance_label.setStyleSheet('font-weight: bold; font-size: 16px; margin-bottom: 10px;')
        
        refresh_btn = QPushButton('Refresh Balances')
        refresh_btn.clicked.connect(self.load_balances_async)
        refresh_btn.setStyleSheet('background-color: #607D8B; color: white; padding: 5px; font-size: 12px;')
        refresh_btn.setMaximumWidth(120)
        
        balance_header_layout.addWidget(balance_label)
        balance_header_layout.addStretch()
        balance_header_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(balance_header_layout)
        
        # Balance display with proper spacing
        balance_scroll_area = QScrollArea()
        balance_scroll_area.setWidgetResizable(True)
        balance_scroll_area.setMinimumHeight(200)  # Increased minimum height
        balance_scroll_area.setMaximumHeight(400)  # Increased maximum height
        balance_scroll_area.setStyleSheet('border: 1px solid #cccccc; border-radius: 5px; margin-bottom: 20px;')
        
        balance_widget = QWidget()
        self.balance_layout = QVBoxLayout(balance_widget)
        
        self.balance_display = QLabel('Loading balances...')
        self.balance_display.setStyleSheet('''
            background-color: #f5f5f5; 
            padding: 20px;  /* Increased padding */
            border-radius: 5px; 
            font-family: "Courier New", monospace; 
            font-size: 13px;
            line-height: 1.4;
        ''')
        self.balance_display.setWordWrap(False)
        self.balance_layout.addWidget(self.balance_display)
        
        balance_scroll_area.setWidget(balance_widget)
        main_layout.addWidget(balance_scroll_area)
        
        main_layout.addSpacing(20)
        
        # Transaction form with same header style as Account Balances
        form_group = QGroupBox('Add Transaction')
        form_group.setStyleSheet('''
            QGroupBox { 
                font-weight: bold; 
                font-size: 16px; 
                margin-top: 10px; 
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        ''')
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)  # Add spacing between form elements
        
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
        
        self.starting_balance_layout = QHBoxLayout()
        self.starting_balance_checkbox = QCheckBox('This is a starting balance transaction')
        self.starting_balance_checkbox.toggled.connect(self.update_ui_for_type)
        self.starting_balance_layout.addWidget(self.starting_balance_checkbox)
        self.starting_balance_layout.addStretch()
        form_layout.addLayout(self.starting_balance_layout)
        
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel('Date:'))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        date_layout.addWidget(self.date_input)
        date_layout.addStretch()
        form_layout.addLayout(date_layout)
        
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel('Amount:'))
        
        self.from_amount_currency_label = QLabel('CHF')
        self.from_amount_currency_label.setStyleSheet('font-weight: bold; color: #666; min-width: 40px;')
        amount_layout.addWidget(self.from_amount_currency_label)
        
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText('Enter amount')
        amount_layout.addWidget(self.amount_input)
        
        amount_layout.addStretch()
        form_layout.addLayout(amount_layout)
        
        self.from_account_layout = QHBoxLayout()
        self.from_account_layout.addWidget(QLabel('Account:'))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(250)
        self.update_account_combo()
        self.from_account_layout.addWidget(self.account_combo)
        self.from_account_layout.addStretch()
        form_layout.addLayout(self.from_account_layout)
        
        self.parent_category_layout = QHBoxLayout()
        self.parent_category_layout.addWidget(QLabel('Category:'))
        self.parent_category_combo = QComboBox()
        self.parent_category_combo.setMinimumWidth(200)
        self.parent_category_combo.currentTextChanged.connect(self.on_parent_category_changed)
        self.parent_category_layout.addWidget(self.parent_category_combo)
        self.parent_category_layout.addStretch()
        form_layout.addLayout(self.parent_category_layout)
        
        self.sub_category_layout = QHBoxLayout()
        self.sub_category_layout.addWidget(QLabel('Sub Category:'))
        self.sub_category_combo = QComboBox()
        self.sub_category_combo.setMinimumWidth(200)
        self.sub_category_layout.addWidget(self.sub_category_combo)
        self.sub_category_layout.addStretch()
        form_layout.addLayout(self.sub_category_layout)
        
        self.to_account_layout = QHBoxLayout()
        self.to_account_layout.addWidget(QLabel('To Account:'))
        self.to_account_combo = QComboBox()
        self.to_account_combo.setMinimumWidth(250)
        self.update_to_account_combo()
        self.to_account_layout.addWidget(self.to_account_combo)
        self.to_account_layout.addStretch()
        form_layout.addLayout(self.to_account_layout)
        
        self.to_amount_layout = QHBoxLayout()
        self.to_amount_layout.addWidget(QLabel('To Amount:'))
        
        self.to_amount_currency_label = QLabel('')
        self.to_amount_currency_label.setStyleSheet('font-weight: bold; color: #666; min-width: 40px;')
        self.to_amount_layout.addWidget(self.to_amount_currency_label)
        
        self.to_amount_input = QLineEdit()
        self.to_amount_input.setPlaceholderText('Receiving amount (for different currency)')
        self.to_amount_input.setMinimumWidth(150)
        self.to_amount_layout.addWidget(self.to_amount_input)
        
        self.exchange_rate_label = QLabel('Exchange Rate: 1.0000')
        self.exchange_rate_label.setStyleSheet('color: #666; font-style: italic; min-width: 150px;')
        self.exchange_rate_label.setMinimumWidth(150)
        self.to_amount_layout.addWidget(self.exchange_rate_label)
        
        self.to_amount_layout.addStretch()
        form_layout.addLayout(self.to_amount_layout)

        self.qty_layout = QHBoxLayout()
        self.qty_layout.addWidget(QLabel('Quantity:'))
        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText('Optional - for investment transfers')
        self.qty_input.setMinimumWidth(150)
        self.qty_layout.addWidget(self.qty_input)
        self.qty_layout.addStretch()
        form_layout.addLayout(self.qty_layout)

        
        self.payee_layout = QHBoxLayout()
        self.payee_layout.addWidget(QLabel('Payee:'))
        
        self.payee_input = QComboBox()
        self.payee_input.setEditable(True)  
        self.payee_input.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.payee_input.setPlaceholderText('Optional - select or type new')
        self.update_payee_combo()
        
        self.payee_layout.addWidget(self.payee_input)
        self.payee_layout.addStretch()
        form_layout.addLayout(self.payee_layout)
        
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel('Notes:'))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText('Optional notes')
        notes_layout.addWidget(self.notes_input)
        notes_layout.addStretch()
        form_layout.addLayout(notes_layout)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        self.income_radio.toggled.connect(self.update_ui_for_type)
        self.expense_radio.toggled.connect(self.update_ui_for_type)
        self.transfer_radio.toggled.connect(self.update_ui_for_type)
        
        self.account_combo.currentIndexChanged.connect(self.on_accounts_changed)
        self.to_account_combo.currentIndexChanged.connect(self.on_accounts_changed)
        
        self.update_ui_for_type()
        
        main_layout.addSpacing(20)
        
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
        main_layout.addWidget(self.status_label)
        
        # All 6 buttons in one row with vertical alignment
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)  # Space between buttons
        
        add_btn = QPushButton('Add Transaction')
        add_btn.clicked.connect(self.add_transaction)
        add_btn.setStyleSheet('''
            QPushButton {
                background-color: #2196F3; 
                color: white; 
                padding: 12px 8px; 
                font-size: 14px; 
                border: none; 
                border-radius: 4px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        ''')
        add_btn.setMinimumWidth(140)
        buttons_layout.addWidget(add_btn)
        
        budget_btn = QPushButton('Budget vs Expenses')
        budget_btn.clicked.connect(self.view_budget)
        budget_btn.setStyleSheet('''
            QPushButton {
                background-color: #FF5722; 
                color: white; 
                padding: 12px 8px; 
                font-size: 14px; 
                border: none; 
                border-radius: 4px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        ''')
        budget_btn.setMinimumWidth(140)
        buttons_layout.addWidget(budget_btn)
        
        view_btn = QPushButton('View All Transactions')
        view_btn.clicked.connect(self.view_transactions)
        view_btn.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                padding: 12px 8px; 
                font-size: 14px; 
                border: none; 
                border-radius: 4px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        ''')
        view_btn.setMinimumWidth(140)
        buttons_layout.addWidget(view_btn)

        account_view_btn = QPushButton('Account Perspective')
        account_view_btn.clicked.connect(self.view_account_perspective)
        account_view_btn.setStyleSheet('''
            QPushButton {
                background-color: #9C27B0; 
                color: white; 
                padding: 12px 8px; 
                font-size: 14px; 
                border: none; 
                border-radius: 4px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        ''')
        account_view_btn.setMinimumWidth(140)
        buttons_layout.addWidget(account_view_btn)

        accounts_btn = QPushButton('Manage Accounts')
        accounts_btn.clicked.connect(self.manage_accounts)
        accounts_btn.setStyleSheet('''
            QPushButton {
                background-color: #FF9800; 
                color: white; 
                padding: 12px 8px; 
                font-size: 14px; 
                border: none; 
                border-radius: 4px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        ''')
        accounts_btn.setMinimumWidth(140)
        buttons_layout.addWidget(accounts_btn)

        categories_btn = QPushButton('Manage Categories')
        categories_btn.clicked.connect(self.manage_categories)
        categories_btn.setStyleSheet('''
            QPushButton {
                background-color: #795548; 
                color: white; 
                padding: 12px 8px; 
                font-size: 14px; 
                border: none; 
                border-radius: 4px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #5D4037;
            }
        ''')
        categories_btn.setMinimumWidth(140)
        buttons_layout.addWidget(categories_btn)
        
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        # Add stretch at the bottom for better spacing
        main_layout.addStretch(1)
        
        # Auto-size the window to fit content
        self.adjustSize()

    # ... (rest of the methods remain exactly the same as in the previous version)
    # All other methods (load_balances_async, update_balance_display_with_data, etc.)
    # remain completely unchanged from the previous version

    def load_balances_async(self):
        self.balance_display.setText('Loading balances...')
        
        self.balance_loader = BalanceLoaderThread(self.budget_app)
        self.balance_loader.finished.connect(self.on_balances_loaded)
        self.balance_loader.error.connect(self.on_balances_error)
        self.balance_loader.start()

    def on_balances_loaded(self, balances):
        self.update_balance_display_with_data(balances)

    def on_balances_error(self, error_message):
        self.balance_display.setText(f'Error loading balances: {error_message}')

    def update_balance_display_with_data(self, balances):
        transaction_counts = {}
        all_accounts = self.budget_app.get_all_accounts()
        for account in all_accounts:
            count = self.budget_app.count_transactions_for_account(account.id)
            transaction_counts[account.id] = count
        
        account_groups = {}
        for account_id, data in balances.items():
            if abs(data['balance']) < 0.001:
                continue
                
            account_obj = self.get_account_by_id(account_id)

            if account_obj:
                if account_obj.id == 0:
                    continue
                show_in_balance = getattr(account_obj, 'show_in_balance', True)
                if not show_in_balance:
                    continue
                
            account_name = data['account_name']
            
            if account_name not in account_groups:
                account_groups[account_name] = []
            
            count = transaction_counts.get(account_id, 0)
            account_groups[account_name].append((account_id, data, count))
                
          
        
        group_transaction_counts = {}
        for account_name, accounts in account_groups.items():
            total_count = sum(count for _, _, count in accounts)
            group_transaction_counts[account_name] = total_count
        
        currency_totals = {}
        for account_name, accounts in account_groups.items():
            for account_id, data, count in accounts:
                currency = self.get_currency_for_account(account_id)
                balance = data['balance']
                if currency in currency_totals:
                    currency_totals[currency] += abs(balance)
                else:
                    currency_totals[currency] = abs(balance)
        
        all_currencies = sorted(currency_totals.keys(), key=lambda x: currency_totals[x], reverse=True)
        
        sorted_account_groups = sorted(account_groups.items(), 
                                    key=lambda x: group_transaction_counts[x[0]], 
                                    reverse=True)
        
        account_col_width = 35
        currency_col_width = 15
        
        balance_text = ""
        
        header = f"{'Account':{account_col_width}}"
        for currency in all_currencies:
            header += f"{currency:>{currency_col_width}}"
        balance_text += header + "\n"
        balance_text += "-" * (account_col_width + len(all_currencies) * currency_col_width) + "\n"
        
        total_by_currency = {currency: 0.0 for currency in all_currencies}
        for account_name, accounts in sorted_account_groups:
            group_balances = {currency: 0.0 for currency in all_currencies}
            for account_id, data, count in accounts:
                currency = self.get_currency_for_account(account_id)
                group_balances[currency] += data['balance']
            
            line = f"{account_name:{account_col_width}}"
            for currency in all_currencies:
                balance = group_balances[currency]
                if abs(balance) >= 0.001:
                    line += f"{balance:>{currency_col_width}.2f}"
                    total_by_currency[currency] += balance
                else:
                    line += f"{'':>{currency_col_width}}"
            balance_text += line + "\n"
        
        balance_text += "-" * (account_col_width + len(all_currencies) * currency_col_width) + "\n"
        total_line = f"{'Total':{account_col_width}}"
        for currency in all_currencies:
            total_line += f"{total_by_currency[currency]:>{currency_col_width}.2f}"
        balance_text += total_line
        
        self.balance_display.setText(balance_text)

    def update_account_combo(self):
        self.account_combo.clear()
        accounts = self.budget_app.get_all_accounts()
        
        # Sort accounts by transaction count (most used first)
        accounts_sorted = sorted(accounts, 
                               key=lambda x: self.transaction_counts['accounts'].get(x.id, 0), 
                               reverse=True)
        
        for account in accounts_sorted:
            if account.id == 0:
                continue
            display_text = f"{account.account} ({account.currency})"
            self.account_combo.addItem(display_text, account.id)
        self.account_combo.adjustSize()
    
    def update_to_account_combo(self):
        self.to_account_combo.clear()
        accounts = self.budget_app.get_all_accounts()
        
        # Sort accounts by transaction count (most used first)
        accounts_sorted = sorted(accounts, 
                               key=lambda x: self.transaction_counts['accounts'].get(x.id, 0), 
                               reverse=True)
        
        for account in accounts_sorted:
            if account.id == 0:
                continue
            display_text = f"{account.account} ({account.currency})"
            self.to_account_combo.addItem(display_text, account.id)
        self.to_account_combo.adjustSize()
    
    def update_payee_combo(self):
        """Update payee dropdown with most used payees first"""
        payee_counts = self.transaction_counts['payees']
        
        # Sort payees by count (most used first)
        sorted_payees = sorted(payee_counts.items(), key=lambda x: x[1], reverse=True)
        
        current_text = self.payee_input.currentText()
        self.payee_input.clear()
        
        # Add most used payees
        for payee, count in sorted_payees:
            self.payee_input.addItem(payee)
        
        # Set current text back if it exists
        index = self.payee_input.findText(current_text)
        if index >= 0:
            self.payee_input.setCurrentIndex(index)
        elif current_text:
            self.payee_input.setCurrentText(current_text)
    
    def on_accounts_changed(self):
        self.update_currency_labels()
        self.update_transfer_ui_based_on_currencies()
    
    def update_currency_labels(self):
        from_account_id = self.account_combo.currentData()
        to_account_id = self.to_account_combo.currentData()
        
        is_starting_balance = self.starting_balance_checkbox.isChecked()
        
        if is_starting_balance:
            currency = self.get_currency_for_account(to_account_id) if to_account_id else 'CHF'
            self.from_amount_currency_label.setText(currency)
        else:
            from_currency = self.get_currency_for_account(from_account_id) if from_account_id else 'CHF'
            self.from_amount_currency_label.setText(from_currency)
        
        to_currency = self.get_currency_for_account(to_account_id) if to_account_id else ''
        self.to_amount_currency_label.setText(to_currency)
    
    def update_transfer_ui_based_on_currencies(self):
        if not self.transfer_radio.isChecked() or self.starting_balance_checkbox.isChecked():
            return
            
        from_account_id = self.account_combo.currentData()
        to_account_id = self.to_account_combo.currentData()
        
        if from_account_id and to_account_id:
            from_currency = self.get_currency_for_account(from_account_id)
            to_currency = self.get_currency_for_account(to_account_id)
            
            different_currencies = from_currency != to_currency
            
            self.to_amount_layout.itemAt(0).widget().setVisible(different_currencies)
            self.to_amount_currency_label.setVisible(different_currencies)
            self.to_amount_input.setVisible(different_currencies)
            self.exchange_rate_label.setVisible(different_currencies)
            
            if not different_currencies:
                self.to_amount_input.clear()
                self.exchange_rate_label.setText('Exchange Rate: 1.0000')
    
    def update_ui_for_type(self):
        is_transfer = self.transfer_radio.isChecked()
        is_income = self.income_radio.isChecked()
        is_starting_balance = self.starting_balance_checkbox.isChecked()
        
        self.starting_balance_layout.itemAt(0).widget().setVisible(is_transfer)
        
        self.parent_category_layout.itemAt(0).widget().setVisible(not is_transfer and not is_starting_balance)
        self.parent_category_combo.setVisible(not is_transfer and not is_starting_balance)
        self.sub_category_layout.itemAt(0).widget().setVisible(not is_transfer and not is_starting_balance)
        self.sub_category_combo.setVisible(not is_transfer and not is_starting_balance)
        
        payee_visible = not is_transfer and not is_starting_balance
        self.payee_layout.itemAt(0).widget().setVisible(payee_visible)
        self.payee_input.setVisible(payee_visible)
        
        self.to_account_layout.itemAt(0).widget().setVisible(is_transfer or is_starting_balance)
        self.to_account_combo.setVisible(is_transfer or is_starting_balance)
        
        from_account_visible = not is_starting_balance
        self.from_account_layout.itemAt(0).widget().setVisible(from_account_visible)
        self.account_combo.setVisible(from_account_visible)
        
        self.from_amount_currency_label.setVisible(True)
        self.to_amount_currency_label.setVisible(is_transfer and not is_starting_balance)
        
        # Show quantity field only for transfers (not starting balance)
        self.qty_layout.itemAt(0).widget().setVisible(is_transfer and not is_starting_balance)
        self.qty_input.setVisible(is_transfer and not is_starting_balance)
        
        if is_transfer and not is_starting_balance:
            self.update_transfer_ui_based_on_currencies()
            self.amount_input.textChanged.connect(self.calculate_exchange_rate)
            self.to_amount_input.textChanged.connect(self.calculate_exchange_rate_from_to)
        else:
            try:
                self.amount_input.textChanged.disconnect(self.calculate_exchange_rate)
            except:
                pass
            try:
                self.to_amount_input.textChanged.disconnect(self.calculate_exchange_rate_from_to)
            except:
                pass
            
            self.to_amount_layout.itemAt(0).widget().setVisible(False)
            self.to_amount_currency_label.setVisible(False)
            self.to_amount_input.setVisible(False)
            self.exchange_rate_label.setVisible(False)
        
        if not is_transfer and not is_starting_balance:
            trans_type = 'income' if is_income else 'expense'
            self.update_parent_categories(trans_type)
        
        if is_starting_balance:
            self.to_account_layout.itemAt(0).widget().setText('Account:')
            self.amount_input.setPlaceholderText('Starting balance amount')
        else:
            self.to_account_layout.itemAt(0).widget().setText('To Account:')
            self.amount_input.setPlaceholderText('Enter amount')
        
        self.update_currency_labels()

    def calculate_exchange_rate(self):
        try:
            from_amount = float(self.amount_input.text())
            to_amount_text = self.to_amount_input.text().strip()
            
            if to_amount_text and float(to_amount_text) > 0:
                to_amount = float(to_amount_text)
                if from_amount > 0:
                    exchange_rate = to_amount / from_amount
                    self.exchange_rate_label.setText(f'Exchange Rate: {exchange_rate:.4f}')
            elif from_amount > 0:
                self.exchange_rate_label.setText('Exchange Rate: 1.0000')
                self.to_amount_input.setText(str(from_amount))
        except (ValueError, ZeroDivisionError):
            self.exchange_rate_label.setText('Exchange Rate: -')

    def calculate_exchange_rate_from_to(self):
        try:
            to_amount = float(self.to_amount_input.text())
            from_amount_text = self.amount_input.text().strip()
            
            if from_amount_text and float(from_amount_text) > 0:
                from_amount = float(from_amount_text)
                if to_amount > 0:
                    exchange_rate = to_amount / from_amount
                    self.exchange_rate_label.setText(f'Exchange Rate: {exchange_rate:.4f}')
        except (ValueError, ZeroDivisionError):
            self.exchange_rate_label.setText('Exchange Rate: -')

    def update_parent_categories(self, trans_type):
        self.parent_category_combo.clear()
        categories = self.budget_app.get_all_categories()
        
        parent_categories = set()
        category_counts = {}
        
        for category in categories:
            if trans_type == 'income':
                if category.category.lower() == 'income':
                    parent_categories.add(category.category)
                    # Get count for this parent category (sum of all subcategories)
                    count = sum(self.transaction_counts['categories'].get(sub.sub_category, 0) 
                               for sub in categories if sub.category == category.category)
                    category_counts[category.category] = count
            else:
                if category.category.lower() != 'income':
                    parent_categories.add(category.category)
                    # Get count for this parent category (sum of all subcategories)
                    count = sum(self.transaction_counts['categories'].get(sub.sub_category, 0) 
                               for sub in categories if sub.category == category.category)
                    category_counts[category.category] = count
        
        # Sort parent categories by count (most used first)
        sorted_parents = sorted(list(parent_categories), 
                              key=lambda x: category_counts.get(x, 0), 
                              reverse=True)
        
        for parent in sorted_parents:
            self.parent_category_combo.addItem(parent)
        
        self.parent_category_combo.adjustSize()
        
        if self.parent_category_combo.count() > 0:
            self.parent_category_combo.setCurrentIndex(0)
            self.update_sub_categories()

    def on_parent_category_changed(self, parent_category):
        self.update_sub_categories()

    def update_sub_categories(self):
        self.sub_category_combo.clear()
        
        parent_category = self.parent_category_combo.currentText()
        if not parent_category:
            return
            
        categories = self.budget_app.get_all_categories()
        
        sub_categories = []
        for category in categories:
            if category.category == parent_category:
                count = self.transaction_counts['categories'].get(category.sub_category, 0)
                sub_categories.append((category.sub_category, count))
        
        # Sort subcategories by count (most used first)
        sorted_subs = sorted(sub_categories, key=lambda x: x[1], reverse=True)
        
        for sub, count in sorted_subs:
            self.sub_category_combo.addItem(sub)
        
        self.sub_category_combo.adjustSize()
        
        if self.sub_category_combo.count() > 0:
            self.sub_category_combo.setCurrentIndex(0)

    def get_currency_for_account(self, account_id):
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account.currency
        return 'CHF'

    def get_account_by_id(self, account_id):
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account
        return None

    def add_transaction(self):
        try:
            amount = float(self.amount_input.text())
            if amount <= 0:
                self.show_status('Amount must be greater than 0', error=True)
                return
        except ValueError:
            self.show_status('Please enter a valid number', error=True)
            return
        
        date = self.date_input.date().toString("yyyy-MM-dd")
        account_id = self.account_combo.currentData()
        payee = self.payee_input.currentText().strip()
        notes = self.notes_input.text().strip()
        
        # Get quantity if provided (for transfers)
        qty_text = self.qty_input.text().strip()
        qty = None
        if qty_text:
            try:
                qty = float(qty_text)
            except ValueError:
                self.show_status('Please enter a valid number for quantity', error=True)
                return
        
        is_starting_balance = self.starting_balance_checkbox.isChecked()
        
        if is_starting_balance:
            to_account_id = self.to_account_combo.currentData()
            
            from_account_id = 0
            from_amount = amount
            to_amount = amount
            
            success = self.budget_app.add_transfer(
                date=date,
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                from_amount=from_amount,
                to_amount=to_amount,
                notes=notes
            )
            
        elif self.transfer_radio.isChecked():
            to_account_id = self.to_account_combo.currentData()
            
            if account_id == to_account_id:
                self.show_status('Cannot transfer to the same account', error=True)
                return
            
            from_currency = self.get_currency_for_account(account_id)
            to_currency = self.get_currency_for_account(to_account_id)
            
            if from_currency == to_currency:
                to_amount = amount
            else:
                to_amount_text = self.to_amount_input.text().strip()
                if to_amount_text:
                    try:
                        to_amount = float(to_amount_text)
                    except ValueError:
                        self.show_status('Please enter a valid number for To Amount', error=True)
                        return
                else:
                    to_amount = amount
            
            success = self.budget_app.add_transfer(
                date=date,
                from_account_id=account_id,
                to_account_id=to_account_id,
                from_amount=amount,
                to_amount=to_amount,
                qty=qty,  # Add quantity parameter
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
            
        else:
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
            self.amount_input.clear()
            self.to_amount_input.clear()
            self.qty_input.clear()  # Clear quantity field
            self.payee_input.setCurrentText('')
            self.notes_input.clear()
            self.account_combo.setCurrentIndex(0)
            self.to_account_combo.setCurrentIndex(0)
            self.starting_balance_checkbox.setChecked(False)
            
            # Refresh transaction counts and dropdowns after adding transaction
            self.transaction_counts = self.budget_app.get_transaction_counts()
            self.update_payee_combo()
        else:
            self.show_status('Error adding transaction', error=True)

    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
        
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))

    def view_transactions(self):
        try:
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

    def view_budget(self):
        try:
            if hasattr(self, 'budget_dialog') and self.budget_dialog is not None:
                try:
                    if self.budget_dialog.isVisible():
                        self.budget_dialog.raise_()
                        self.budget_dialog.activateWindow()
                        return
                except:
                    pass
            
            dialog = BudgetDialog(self.budget_app, self)
            self.budget_dialog = dialog
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            
        except Exception as e:
            print(f"Error in view_budget: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, 'Error', f'Error opening budget view:\n{str(e)}')
            self.show_status('Error opening budget view', error=True)

    def manage_accounts(self):
        dialog = AccountsDialog(self.budget_app, self)
        dialog.exec()
        self.update_account_combo()
        self.update_to_account_combo()

    def manage_categories(self):
        dialog = CategoriesDialog(self.budget_app, self)
        dialog.exec()
        self.transaction_counts = self.budget_app.get_transaction_counts()  # Refresh counts
        self.update_ui_for_type()

    def update_balance_display(self):
        self.load_balances_async()