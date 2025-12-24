import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QComboBox, 
                             QRadioButton, QButtonGroup, QDateEdit, QGroupBox,
                             QScrollArea, QCheckBox, QTabWidget, QMessageBox,
                             QMenu)
from PyQt6.QtCore import Qt, QDate, QSettings, QEvent
from PyQt6.QtGui import QFont, QIcon, QAction
from investment_tab import InvestmentTab

from models import BudgetApp
from models import BudgetApp
from utils import safe_eval_math, resource_path
from models import BudgetApp
from utils import safe_eval_math, resource_path
from custom_widgets import NoScrollComboBox
from expenses_dashboard_tab import ExpensesDashboardTab


class BudgetTrackerWindow(QMainWindow):
    def __init__(self, db_path=None):
        super().__init__()
        self.db_path = db_path
        self.budget_app = BudgetApp(db_path)
        self.transaction_counts = self.budget_app.get_transaction_counts()
        self.init_ui()
    
    def init_ui(self):
        title = 'Budget Tracker 3.8'
        if self.db_path:
            title += f' - [{self.db_path}]'
        self.setWindowTitle(title)

        self.setMinimumSize(800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        central_widget.setLayout(main_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(False) # Ensure styling looks right
        self.tab_widget.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.tabBar().customContextMenuRequested.connect(self.show_tab_context_menu)
        
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 12px;
                margin-right: 2px;
                font-size: 12px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom-color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e8e8e8;
            }
        """)
        
        # -- Tab Definitions --
        # We store definitions to allow restoring order/visibility
        # Format: key -> (widget, title, tooltip)
        self.tab_defs = {}
        
        # New Keys to force order reset
        self.tab_defs['add_transaction'] = self.create_add_transaction_tab()
        self.tab_defs['overview'] = self.create_balance_tab()
        self.tab_defs['expenses_dashboard'] = self.create_expenses_dashboard_tab()
        self.tab_defs['transactions'] = self.create_transactions_tab()
        self.tab_defs['account_entries'] = self.create_account_perspective_tab()
        self.tab_defs['budget'] = self.create_budget_tab()
        self.tab_defs['balance_report'] = self.create_report_tab()  # Was Report
        self.tab_defs['cash_flow'] = self.create_savings_tab()  # Was Savings
        self.tab_defs['investments'] = self.create_investment_tab()
        self.tab_defs['performance'] = self.create_investment_performance_tab()
        self.tab_defs['currencies'] = self.create_exchange_rates_tab()
        self.tab_defs['manage_accounts'] = self.create_accounts_tab()
        self.tab_defs['manage_categories'] = self.create_categories_tab()
        self.tab_defs['data_management'] = self.create_data_management_tab()
        
        # Restore State (add tabs in saved order)
        self.restore_state()
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        main_layout.addWidget(self.tab_widget)

    def show_tab_context_menu(self, point):
        menu = QMenu(self)
        
        # "Show/Hide Tabs" Section
        label_action = QAction("Visible Tabs:", self)
        label_action.setEnabled(False)
        menu.addAction(label_action)
        menu.addSeparator()
        
        # Get currently visible keys based on widgets
        visible_widgets = [self.tab_widget.widget(i) for i in range(self.tab_widget.count())]
        
        # Create a checkbox action for EVERY tab definition
        # Use default order for the menu list
        default_order = ['add_transaction', 'overview', 'expenses_dashboard', 'performance', 'transactions', 'account_entries', 'budget', 
                         'balance_report', 'cash_flow', 'investments', 'currencies', 
                         'manage_accounts', 'manage_categories', 'data_management']
                         
        for key in default_order:
            if key not in self.tab_defs: continue
            
            widget, title, tip = self.tab_defs[key]
            is_visible = widget in visible_widgets
            
            action = QAction(title, self)
            action.setCheckable(True)
            action.setChecked(is_visible)
            # Use closure to capture key
            action.triggered.connect(lambda checked, k=key: self.toggle_tab(k, checked))
            menu.addAction(action)
            
        menu.exec(self.tab_widget.tabBar().mapToGlobal(point))

    def toggle_tab(self, key, checked):
        if key not in self.tab_defs: return
        widget, title, tip = self.tab_defs[key]
        
        if checked:
            # Show (Append to end because restoring position is hard with movability)
            if self.tab_widget.indexOf(widget) == -1:
                self.tab_widget.addTab(widget, title)
                self.tab_widget.setTabToolTip(self.tab_widget.count()-1, tip)
        else:
            # Hide
            idx = self.tab_widget.indexOf(widget)
            if idx != -1:
                self.tab_widget.removeTab(idx)

    def restore_state(self):
        settings = QSettings("BudgetTracker", "MainWindow")
        
        # Restore Geometry
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore Tab Order/Visibility
        # Default order if nothing saved
        default_order = ['add_transaction', 'overview', 'expenses_dashboard', 'performance', 'transactions', 'account_entries', 'budget', 
                         'balance_report', 'cash_flow', 'investments', 'currencies', 
                         'manage_accounts', 'manage_categories', 'data_management']
                         
        saved_order = settings.value("tab_order", default_order)
        # Ensure it's a list (PyQt6 sometimes returns different types if single item)
        if not isinstance(saved_order, list):
             saved_order = default_order

        # 1. Add tabs in saved order
        for key in saved_order:
            if key in self.tab_defs:
                widget, title, tip = self.tab_defs[key]
                # Avoid duplicates
                if self.tab_widget.indexOf(widget) == -1:
                     self.tab_widget.addTab(widget, title)
                     self.tab_widget.setTabToolTip(self.tab_widget.count()-1, tip)
        
        # 2. Add any new tabs that weren't in saved order (e.g. upgrades)
        # We append them at the end
        for key in default_order:
            if key in self.tab_defs:
                widget, title, tip = self.tab_defs[key]
                if self.tab_widget.indexOf(widget) == -1:
                    # Check if it was explicitly hidden?
                    # For simplicity, if not in saved order, we assume it's NEW and show it.
                    # Use a separate "hidden_tabs" list if we want to distinguish "hidden" from "new".
                    # But "tab_order" usually contains only visible tabs.
                    # Let's check "all_known_tabs" setting to mitigate reappearing closed tabs?
                    # For now, simple: Append missing tabs.
                     self.tab_widget.addTab(widget, title)
                     self.tab_widget.setTabToolTip(self.tab_widget.count()-1, tip)

    def save_state(self):
        settings = QSettings("BudgetTracker", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        
        # Save visible tabs order
        current_order = []
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            # Find key for this widget
            for key, (w, t, tip) in self.tab_defs.items():
                if w == widget:
                    current_order.append(key)
                    break
        
        settings.setValue("tab_order", current_order)

    def closeEvent(self, event):
        """Cleanup when window is closed"""
        self.save_state()
        try:
            if hasattr(self, 'budget_app'):
                self.budget_app.close()
        except:
            pass
        event.accept()
    
    def create_add_transaction_tab(self):
        """Create the Add Transaction tab"""
        tab = QWidget()
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        tab_layout = QVBoxLayout()
        tab.setLayout(tab_layout)
        tab_layout.addWidget(scroll_area)
        
        main_layout = QVBoxLayout()
        content_widget.setLayout(main_layout)
        
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
        form_layout.setSpacing(10)
        
        # Transaction Type
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
        
        self.income_radio.setToolTip("Money entering your accounts (e.g. Salary)")
        self.expense_radio.setToolTip("Money leaving your accounts (e.g. Rent, Food)")
        self.transfer_radio.setToolTip("Money moving between your accounts")
        type_layout.addStretch()
        form_layout.addLayout(type_layout)
        
        # Starting Balance Checkbox
        self.starting_balance_layout = QHBoxLayout()
        self.starting_balance_checkbox = QCheckBox('This is a starting balance transaction')
        self.starting_balance_checkbox.setToolTip("Use this for the very first transaction of an account to set its initial value.")
        self.starting_balance_checkbox.toggled.connect(self.update_ui_for_type)
        self.starting_balance_layout.addWidget(self.starting_balance_checkbox)
        self.starting_balance_layout.addStretch()
        form_layout.addLayout(self.starting_balance_layout)
        
        # Date
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel('Date:'))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        date_layout.addWidget(self.date_input)
        date_layout.addStretch()
        form_layout.addLayout(date_layout)
        
        # From Account
        self.from_account_layout = QHBoxLayout()
        self.from_account_layout.addWidget(QLabel('Account:'))
        self.account_combo = NoScrollComboBox()
        self.account_combo.setMinimumWidth(250)
        self.update_account_combo()
        self.from_account_layout.addWidget(self.account_combo)
        self.from_account_layout.addStretch()
        form_layout.addLayout(self.from_account_layout)
        
        # To Account
        self.to_account_layout = QHBoxLayout()
        self.to_account_layout.addWidget(QLabel('To Account:'))
        self.to_account_combo = NoScrollComboBox()
        self.to_account_combo.setMinimumWidth(250)
        self.update_to_account_combo()
        self.to_account_layout.addWidget(self.to_account_combo)
        self.to_account_layout.addStretch()
        form_layout.addLayout(self.to_account_layout)
        
        # Payee
        self.payee_layout = QHBoxLayout()
        self.payee_layout.addWidget(QLabel('Payee:'))
        self.payee_input = NoScrollComboBox()
        self.payee_input.setEditable(True)
        self.payee_input.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.payee_input.setPlaceholderText('Optional - select or type new')
        self.update_payee_combo()
        self.payee_layout.addWidget(self.payee_input)
        self.payee_layout.addStretch()
        form_layout.addLayout(self.payee_layout)
        
        # Category
        self.parent_category_layout = QHBoxLayout()
        self.parent_category_layout.addWidget(QLabel('Category:'))
        self.parent_category_combo = NoScrollComboBox()
        self.parent_category_combo.setMinimumWidth(200)
        self.parent_category_combo.currentTextChanged.connect(self.on_parent_category_changed)
        self.parent_category_layout.addWidget(self.parent_category_combo)
        self.parent_category_layout.addStretch()
        form_layout.addLayout(self.parent_category_layout)
        
        # Sub Category
        self.sub_category_layout = QHBoxLayout()
        self.sub_category_layout.addWidget(QLabel('Sub Category:'))
        self.sub_category_combo = NoScrollComboBox()
        self.sub_category_combo.setMinimumWidth(200)
        self.sub_category_layout.addWidget(self.sub_category_combo)
        self.sub_category_layout.addStretch()
        form_layout.addLayout(self.sub_category_layout)
        
        # Investment Account (Optional, for Income)
        self.invest_account_layout = QHBoxLayout()
        self.invest_account_layout.addWidget(QLabel('Investment Account:'))
        self.invest_account_combo = NoScrollComboBox()
        self.invest_account_combo.setMinimumWidth(250)
        self.invest_account_combo.setPlaceholderText('Optional - select if dividend')
        self.update_invest_account_combo()
        self.invest_account_layout.addWidget(self.invest_account_combo)
        self.invest_account_layout.addStretch()
        form_layout.addLayout(self.invest_account_layout)

        # Amount
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel('Amount:'))
        self.from_amount_currency_label = QLabel('CHF')
        self.from_amount_currency_label.setStyleSheet('font-weight: bold; color: #666; min-width: 40px;')
        amount_layout.addWidget(self.from_amount_currency_label)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText('Enter amount')
        self.amount_input.setMaximumWidth(150)
        self.amount_input.textChanged.connect(self.update_amount_preview)
        amount_layout.addWidget(self.amount_input)
        
        self.amount_preview_label = QLabel('')
        self.amount_preview_label.setStyleSheet('color: #2196F3; font-style: italic; font-weight: bold; margin-left: 10px;')
        amount_layout.addWidget(self.amount_preview_label)
        
        amount_layout.addStretch()
        form_layout.addLayout(amount_layout)
        
        # To Amount
        self.to_amount_layout = QHBoxLayout()
        self.to_amount_layout.addWidget(QLabel('To Amount:'))
        self.to_amount_currency_label = QLabel('')
        self.to_amount_currency_label.setStyleSheet('font-weight: bold; color: #666; min-width: 40px;')
        self.to_amount_layout.addWidget(self.to_amount_currency_label)
        self.to_amount_input = QLineEdit()
        self.to_amount_input.setPlaceholderText('Receiving amount')
        self.to_amount_input.setToolTip("Amount received in the destination account. Only needed if the currency is different.")
        self.to_amount_input.setMaximumWidth(150)
        self.to_amount_layout.addWidget(self.to_amount_input)
        self.exchange_rate_label = QLabel('Exchange Rate: 1.0000')
        self.exchange_rate_label.setStyleSheet('color: #666; font-style: italic; min-width: 150px;')
        self.exchange_rate_label.setMinimumWidth(150)
        self.to_amount_layout.addWidget(self.exchange_rate_label)
        self.to_amount_layout.addStretch()
        form_layout.addLayout(self.to_amount_layout)
        
        # Quantity
        self.qty_layout = QHBoxLayout()
        self.qty_layout.addWidget(QLabel('Quantity:'))
        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText('Optional - for investment transfers')
        self.qty_input.setToolTip("Number of shares or units. Used for Investment Accounts.")
        self.qty_input.setMaximumWidth(250)
        self.qty_layout.addWidget(self.qty_input)
        self.qty_layout.addStretch()
        form_layout.addLayout(self.qty_layout)
        
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
        
        # Connect signals
        self.income_radio.toggled.connect(self.update_ui_for_type)
        self.expense_radio.toggled.connect(self.update_ui_for_type)
        self.transfer_radio.toggled.connect(self.update_ui_for_type)
        self.account_combo.currentIndexChanged.connect(self.on_accounts_changed)
        self.to_account_combo.currentIndexChanged.connect(self.on_accounts_changed)
        
        self.update_ui_for_type()
        
        main_layout.addSpacing(20)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
        main_layout.addWidget(self.status_label)
        
        # Add Transaction button
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
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
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch(1)
        
        self.add_transaction_tab_widget = tab
        return tab, "➕ Add Transaction", "Create new Income, Expense, or Transfer transactions."

    def update_amount_preview(self, text):
        """Update amount preview with calculated math result"""
        if not text:
            self.amount_preview_label.setText('')
            return
            
        # Check if math operators are present
        if any(op in text for op in ['+', '-', '*', '/']):
            try:
                # Use utils.safe_eval_math
                val = safe_eval_math(text)
                self.amount_preview_label.setText(f"= {val:,.2f}")
            except:
                # Clear on valid error or incomplete expression
                self.amount_preview_label.setText('')
        else:
            self.amount_preview_label.setText('')
    
    def create_balance_tab(self):
        """Create the Balance tab - lazy loaded"""
        from balance_tab import BalanceTab
        self.balance_tab_widget = BalanceTab(self.budget_app, self)
        return self.balance_tab_widget, "💰 Overview", "Overview of account balances, investment values, and net worth."

    
    def create_transactions_tab(self):
        """Create the Transactions tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # Import and embed transactions dialog content
        from transactions_dialog import TransactionsDialog
        self.transactions_dialog_ref = TransactionsDialog(self.budget_app, self)
        
        # Extract the dialog's layout content
        dialog_layout = self.transactions_dialog_ref.layout()
        if dialog_layout:
            while dialog_layout.count():
                item = dialog_layout.takeAt(0)
                if item.widget():
                    layout.addWidget(item.widget())
                elif item.layout():
                    layout.addLayout(item.layout())
        
        self.transactions_tab_widget = tab
        return tab, "📋 Transactions", "View, edit, filter, and delete past transactions."
        
    def create_account_perspective_tab(self):
        """Create the Account Perspective tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        from account_perspective import AccountPerspectiveDialog
        self.account_perspective_dialog_ref = AccountPerspectiveDialog(self.budget_app, self)
        
        dialog_layout = self.account_perspective_dialog_ref.layout()
        if dialog_layout:
            while dialog_layout.count():
                item = dialog_layout.takeAt(0)
                if item.widget():
                    layout.addWidget(item.widget())
                elif item.layout():
                    layout.addLayout(item.layout())
        
        self.account_perspective_tab_widget = tab
        return tab, "📑 Account Entries", "Detailed analysis of transactions for a specific account."
    
    def create_budget_tab(self):
        """Create the Budget tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        from budget_dialog import BudgetDialog
        self.budget_dialog_ref = BudgetDialog(self.budget_app, self)
        
        dialog_layout = self.budget_dialog_ref.layout()
        if dialog_layout:
            while dialog_layout.count():
                item = dialog_layout.takeAt(0)
                if item.widget():
                    layout.addWidget(item.widget())
                elif item.layout():
                    layout.addLayout(item.layout())
        
        self.budget_tab_widget = tab
        return tab, "💵 Budget", "Track spending against monthly budgets per category."
    
    def create_accounts_tab(self):
        """Create the Accounts tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        from accounts_dialog import AccountsDialog
        self.accounts_dialog_ref = AccountsDialog(self.budget_app, self)
        
        dialog_layout = self.accounts_dialog_ref.layout()
        if dialog_layout:
            while dialog_layout.count():
                item = dialog_layout.takeAt(0)
                if item.widget():
                    layout.addWidget(item.widget())
                elif item.layout():
                    layout.addLayout(item.layout())
        
        self.accounts_tab_widget = tab
        return tab, "🏦 Accounts", "Manage your bank and investment accounts."
    
    
    def create_expenses_dashboard_tab(self):
        tab = ExpensesDashboardTab(self.budget_app, self)
        return tab, "📊 Expenses", "Dashboard of Expenses and Spending Habits"

    def create_categories_tab(self):
        """Create the Categories tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        from categories_dialog import CategoriesDialog
        self.categories_dialog_ref = CategoriesDialog(self.budget_app, self)
        
        dialog_layout = self.categories_dialog_ref.layout()
        if dialog_layout:
            while dialog_layout.count():
                item = dialog_layout.takeAt(0)
                if item.widget():
                    layout.addWidget(item.widget())
                elif item.layout():
                    layout.addLayout(item.layout())
        
        self.categories_tab_widget = tab
        return tab, "📁 Categories", "Manage income and expense categories and sub-categories."
    
    def create_exchange_rates_tab(self):
        """Create the Exchange Rates tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        from exchange_rates_tab import ExchangeRatesTab
        self.exchange_rates_tab_ref = ExchangeRatesTab(self.budget_app, self)
        layout.addWidget(self.exchange_rates_tab_ref)
        self.exchange_rates_tab_widget = tab
        return tab, "💱 Currencies", "Manage historical exchange rates for multi-currency tracking."

    def create_data_management_tab(self):
        """Create the Data Management tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        from data_management_tab import DataManagementTab
        self.data_management_tab_ref = DataManagementTab(self.budget_app, self)
        layout.addWidget(self.data_management_tab_ref)
        self.data_tab_widget = tab
        return tab, "💾 Data", "Import/Export data and backup your database."
    
    def create_investment_tab(self):
        """Create the Investment tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        from investment_tab import InvestmentTab
        self.investment_tab_ref = InvestmentTab(self.budget_app, self)
        layout.addWidget(self.investment_tab_ref)
        self.investment_tab_widget = tab
        return tab, "📈 Investments", "Track historical prices and valuations for investment accounts."

    def create_investment_performance_tab(self):
        """Create the Investment Performance tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        from investment_performance_tab import InvestmentPerformanceTab
        self.investment_performance_tab_ref = InvestmentPerformanceTab(self.budget_app, self)
        layout.addWidget(self.investment_performance_tab_ref)
        self.investment_performance_tab_widget = tab
        return tab, "🚀 Performance", "Detailed investment performance metrics including dividends."

    def create_report_tab(self):
        """Create the Report tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        from report_tab import ReportTab
        self.report_tab_ref = ReportTab(self.budget_app, self)
        layout.addWidget(self.report_tab_ref)
        self.report_tab_widget = tab
        return tab, "📊 Balance", "Visualize balance evolution over time."

    def create_savings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        from savings_tab import SavingsTab
        self.savings_tab_ref = SavingsTab(self.budget_app, self)
        layout.addWidget(self.savings_tab_ref)
        self.savings_tab_widget = tab
        # Load initial data
        self.savings_tab_ref.refresh_data()
        return tab, "💸 Cash Flow", "Visualize monthly savings rate."
    
    def on_tab_changed(self, index):
        """Called when user switches tabs - Refactored for movability"""
        current_widget = self.tab_widget.widget(index)
        
        # Refresh data when switching to certain tabs based on Widget Identity
        if current_widget == self.balance_tab_widget:
            self.balance_tab_widget.refresh_data()
        elif hasattr(self, 'transactions_tab_widget') and current_widget == self.transactions_tab_widget:
            if hasattr(self, 'transactions_dialog_ref'):
                self.transactions_dialog_ref.load_transactions()
        elif hasattr(self, 'account_perspective_tab_widget') and current_widget == self.account_perspective_tab_widget:
            if hasattr(self, 'account_perspective_dialog_ref'):
                self.account_perspective_dialog_ref.refresh_data()
        elif hasattr(self, 'budget_tab_widget') and current_widget == self.budget_tab_widget:
            if hasattr(self, 'budget_dialog_ref'):
                self.budget_dialog_ref.load_budget_data()
        elif hasattr(self, 'accounts_tab_widget') and current_widget == self.accounts_tab_widget:
            if hasattr(self, 'accounts_dialog_ref'):
                self.accounts_dialog_ref.load_accounts()
        elif hasattr(self, 'categories_tab_widget') and current_widget == self.categories_tab_widget:
            if hasattr(self, 'categories_dialog_ref'):
                self.categories_dialog_ref.load_categories()
        elif hasattr(self, 'exchange_rates_tab_widget') and current_widget == self.exchange_rates_tab_widget:
            if hasattr(self, 'exchange_rates_tab_ref'):
                self.exchange_rates_tab_ref.refresh_data()
        elif hasattr(self, 'report_tab_widget') and current_widget == self.report_tab_widget:
            if hasattr(self, 'report_tab_ref'):
                self.report_tab_ref.refresh_data()
        elif hasattr(self, 'savings_tab_widget') and current_widget == self.savings_tab_widget:
            if hasattr(self, 'savings_tab_ref'):
                self.savings_tab_ref.refresh_data()
        elif hasattr(self, 'investment_performance_tab_widget') and current_widget == self.investment_performance_tab_widget:
            if hasattr(self, 'investment_performance_tab_ref'):
                self.investment_performance_tab_ref.refresh_data()

    
    # Include all the helper methods from the original main_window.py
    # (update_account_combo, update_payee_combo, add_transaction, etc.)
    
    def update_account_combo(self):
        self.account_combo.clear()
        accounts = self.budget_app.get_all_accounts()
        accounts_sorted = sorted(accounts, 
                               key=lambda x: self.transaction_counts['accounts'].get(x.id, 0), 
                               reverse=True)
        for account in accounts_sorted:
            if account.id == 0:
                continue
            if not getattr(account, 'is_active', True):
                continue
            display_text = f"{account.account} ({account.currency})"
            self.account_combo.addItem(display_text, account.id)
        self.account_combo.adjustSize()
    
    def update_to_account_combo(self):
        self.to_account_combo.clear()
        accounts = self.budget_app.get_all_accounts()
        accounts_sorted = sorted(accounts, 
                               key=lambda x: self.transaction_counts['accounts'].get(x.id, 0), 
                               reverse=True)
        for account in accounts_sorted:
            if account.id == 0:
                continue
            if not getattr(account, 'is_active', True):
                continue
            display_text = f"{account.account} ({account.currency})"
            self.to_account_combo.addItem(display_text, account.id)
        self.to_account_combo.adjustSize()
    
    def update_payee_combo(self):
        payee_counts = self.transaction_counts['payees']
        sorted_payees = sorted(payee_counts.items(), key=lambda x: x[1], reverse=True)
        current_text = self.payee_input.currentText()
        self.payee_input.clear()
        for payee, count in sorted_payees:
            self.payee_input.addItem(payee)
        index = self.payee_input.findText(current_text)
        if index >= 0:
            self.payee_input.setCurrentIndex(index)
        elif current_text:
            self.payee_input.setCurrentText(current_text)
            
    def update_invest_account_combo(self):
        self.invest_account_combo.clear()
        self.invest_account_combo.addItem("None", None)
        accounts = self.budget_app.get_all_accounts()
        # Filter for investment accounts
        invest_accounts = [acc for acc in accounts if getattr(acc, 'is_investment', False) and getattr(acc, 'is_active', True)]
        invest_accounts.sort(key=lambda x: x.account)
        
        for account in invest_accounts:
            display_text = f"{account.account} ({account.currency})"
            self.invest_account_combo.addItem(display_text, account.id)
    
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
        
        # Show/Hide Investment Account (Income Only)
        self.invest_account_layout.itemAt(0).widget().setVisible(is_income and not is_starting_balance)
        self.invest_account_combo.setVisible(is_income and not is_starting_balance)
        
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
            from_amount = safe_eval_math(self.amount_input.text())
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
            
            if from_amount_text:
                from_amount = safe_eval_math(from_amount_text)
                if to_amount > 0:
                    exchange_rate = to_amount / from_amount
                    self.exchange_rate_label.setText(f'Exchange Rate: {exchange_rate:.4f}')
        except (ValueError, ZeroDivisionError):
            self.exchange_rate_label.setText('Exchange Rate: -')
    
    def on_parent_category_changed(self, parent_category):
        self.update_sub_categories()
    
    def update_sub_categories(self):
        self.sub_category_combo.clear()
        parent_category = self.parent_category_combo.currentText()
        if not parent_category:
            return
            
        categories = self.budget_app.get_all_categories()
        is_income = self.income_radio.isChecked()
        expected_category_type = 'Income' if is_income else 'Expense'
        
        sub_categories = []
        for category in categories:
            if (category.category == parent_category and 
                category.category_type == expected_category_type):
                count = self.transaction_counts['categories'].get(category.sub_category, 0)
                sub_categories.append((category.sub_category, count))
        
        sorted_subs = sorted(sub_categories, key=lambda x: x[1], reverse=True)
        for sub, count in sorted_subs:
            self.sub_category_combo.addItem(sub)
        
        self.sub_category_combo.adjustSize()
        if self.sub_category_combo.count() > 0:
            self.sub_category_combo.setCurrentIndex(0)
    
    def update_parent_categories(self, trans_type):
        self.parent_category_combo.clear()
        categories = self.budget_app.get_all_categories()
        
        parent_categories = set()
        category_counts = {}
        expected_category_type = 'Income' if trans_type == 'income' else 'Expense'
        
        for category in categories:
            if category.category_type == expected_category_type:
                parent_categories.add(category.category)
                count = sum(self.transaction_counts['categories'].get(sub.sub_category, 0) 
                           for sub in categories if sub.category == category.category)
                category_counts[category.category] = count
        
        sorted_parents = sorted(list(parent_categories), 
                              key=lambda x: category_counts.get(x, 0), 
                              reverse=True)
        
        for parent in sorted_parents:
            self.parent_category_combo.addItem(parent)
        
        self.parent_category_combo.adjustSize()
        if self.parent_category_combo.count() > 0:
            self.parent_category_combo.setCurrentIndex(0)
            self.update_sub_categories()
    
    def get_currency_for_account(self, account_id):
        account = self.get_account_by_id(account_id)
        return account.currency if account else 'CHF'
    
    def get_account_by_id(self, account_id):
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account
        return None
    
    def add_transaction(self):
        try:
            amount = safe_eval_math(self.amount_input.text())
            if amount <= 0:
                self.show_status('Amount must be greater than 0', error=True)
                return
        except ValueError:
            self.show_status('Please enter a valid number or expression', error=True)
            return
        
        date = self.date_input.date().toString("yyyy-MM-dd")
        account_id = self.account_combo.currentData()
        payee = self.payee_input.currentText().strip()
        notes = self.notes_input.text().strip()
        
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
                qty=qty,
                notes=notes
            )
            
        elif self.income_radio.isChecked():
            sub_category = self.sub_category_combo.currentText()
            invest_account_id = self.invest_account_combo.currentData()
            # If default index 0 (which might be empty/None) is selected, currentData might be None or 0.
            # We want explicit None if nothing selected.
            if self.invest_account_combo.currentIndex() == -1:
                invest_account_id = None
                
            success = self.budget_app.add_income(
                date=date,
                amount=amount,
                account_id=account_id,
                payee=payee,
                sub_category=sub_category,
                notes=notes,
                invest_account_id=invest_account_id
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
            self.qty_input.clear()
            self.qty_input.clear()
            self.notes_input.clear()
            self.invest_account_combo.setCurrentIndex(0) # Reset to None
            self.starting_balance_checkbox.setChecked(False)
            self.transaction_counts = self.budget_app.get_transaction_counts()
            self.update_payee_combo()
            
            # Refresh other tabs
            if hasattr(self, 'balance_tab_widget'):
                self.balance_tab_widget.refresh_data()
        else:
            self.show_status('Error adding transaction', error=True)
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
