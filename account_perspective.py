"""
Account Perspective - Show transaction history and running balance for a specific account.
SIMPLIFIED: Read-only view with delete and confirm functionality.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QComboBox, QHeaderView, QWidget, QCheckBox,
                             QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


class AccountPerspectiveDialog(QDialog):
    """Dialog for viewing transaction history and running balance for a specific account."""
    
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        self.selected_account_id = None
        
        self.setWindowTitle('Account Transactions & Balance History')
        self.setMinimumSize(1200, 600)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel('Account Transactions & Balance History')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet('color: #2196F3; padding: 10px;')
        layout.addWidget(title)
        
        # Account selection
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel('Select Account:'))
        
        self.account_combo = QComboBox()
        accounts = self.budget_app.get_all_accounts()
        # Sort accounts by ID
        accounts_sorted = sorted(accounts, key=lambda x: x.id)
        for account in accounts_sorted:
            # Display as "Account Name Currency (Account ID)"
            display_text = f"{account.account} {account.currency}"
            self.account_combo.addItem(display_text, account.id)  # Store account ID as data
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        account_layout.addWidget(self.account_combo)
        
        account_layout.addStretch()
        
        # Current balance display
        self.current_balance_label = QLabel('Current Balance: 0.00')
        self.current_balance_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #4CAF50;')
        account_layout.addWidget(self.current_balance_label)
        
        layout.addLayout(account_layout)
        
        # Info label
        info_label = QLabel('Showing all transactions where this account is involved. Click checkbox to confirm transaction.')
        info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px; background-color: #f0f0f0;')
        layout.addWidget(info_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Category', 'Payee', 
            'Other Account', 'Transaction Amount', 'Running Balance',
            'Confirmed', 'Actions'
        ])
        
        # Make table read-only (no editing)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Style the table
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
        
        # Hide row numbers
        self.table.verticalHeader().hide()
        
        # Set initial column widths
        header = self.table.horizontalHeader()
        self.table.setColumnWidth(7, 80)   # Confirmed
        self.table.setColumnWidth(8, 70)   # Actions
        
        # Make columns resizable and set most to auto-size
        content_based_columns = [0, 1, 2, 3, 4, 5, 6]
        for col in content_based_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        # Fixed columns
        fixed_columns = [7, 8]
        for col in fixed_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        
        # Set row height
        self.table.verticalHeader().setDefaultSectionSize(35)
        
        layout.addWidget(self.table)
        
        # Status bar
        self.status_label = QLabel('Select an account to view transactions')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Refresh button
        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet('background-color: #FF9800; color: white; padding: 8px;')
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        
        # Close button
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet('background-color: #2196F3; color: white; padding: 8px;')
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Auto-select first account and load data
        if accounts:
            self.account_combo.setCurrentIndex(0)
            self.on_account_changed(0)
    
    def format_swiss_number(self, number):
        """Format number in Swiss format: 2'005.50 instead of 2,005.50"""
        try:
            # Handle negative numbers
            is_negative = number < 0
            abs_number = abs(number)
            
            # Split into integer and decimal parts
            integer_part = int(abs_number)
            decimal_part = round(abs_number - integer_part, 2)
            
            # Format integer part with apostrophes as thousand separators
            integer_str = f"{integer_part:,}".replace(",", "'")
            
            # Format decimal part to always have 2 digits
            decimal_str = f"{decimal_part:.2f}".split('.')[1]
            
            # Combine parts
            formatted = f"{integer_str}.{decimal_str}"
            
            # Add negative sign if needed
            if is_negative:
                formatted = f"-{formatted}"
                
            return formatted
        except (ValueError, TypeError):
            return "0.00"
    
    def get_account_name_by_id(self, account_id):
        """Get account name by account ID."""
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account.account
        return ""
    
    def get_account_currency_by_id(self, account_id):
        """Get account currency by account ID."""
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account.currency or ""
        return ""
    
    def get_current_account_currency(self):
        """Get currency for currently selected account."""
        account_id = self.selected_account_id
        if account_id:
            return self.get_account_currency_by_id(account_id)
        return ""
    
    def on_account_changed(self, index):
        """Handle account selection change."""
        if index >= 0:
            # Get the account ID from the combo box data
            self.selected_account_id = self.account_combo.currentData()
            self.load_account_data()
    
    def load_account_data(self):
        """Load and display transactions for the selected account."""
        if not self.selected_account_id:
            return
            
        try:
            # Get account ID
            account_id = self.selected_account_id
            
            # Get all transactions
            all_transactions = self.budget_app.get_all_transactions()
            
            # Filter transactions for this account
            account_transactions = []
            for trans in all_transactions:
                # Check if this transaction involves the selected account
                if (trans.account_id == account_id or 
                    trans.from_account_id == account_id or 
                    trans.to_account_id == account_id):
                    account_transactions.append(trans)
            
            # Sort by date (oldest first for running balance calculation)
            account_transactions.sort(key=lambda x: (x.date, x.id))
            
            # Calculate running balance
            running_balance = 0.0
            transaction_history = []
            
            for trans in account_transactions:
                # Determine transaction effect on this account
                if trans.type == 'income' and trans.account_id == account_id:
                    # Income into this account
                    transaction_amount = float(trans.amount or 0)
                    running_balance += transaction_amount
                    effect = "+"
                    other_account = trans.payee or "Income"
                    
                elif trans.type == 'expense' and trans.account_id == account_id:
                    # Expense from this account
                    transaction_amount = float(trans.amount or 0)
                    running_balance -= transaction_amount
                    effect = "-"
                    other_account = trans.payee or "Expense"
                    
                elif trans.type == 'transfer':
                    if trans.from_account_id == account_id:
                        # Transfer out of this account
                        transaction_amount = float(trans.from_amount or 0)
                        running_balance -= transaction_amount
                        effect = "-"
                        other_account = self.get_account_name_by_id(trans.to_account_id)
                    elif trans.to_account_id == account_id:
                        # Transfer into this account
                        transaction_amount = float(trans.to_amount or 0)
                        running_balance += transaction_amount
                        effect = "+"
                        other_account = self.get_account_name_by_id(trans.from_account_id)
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
            
            # Populate table
            self.populate_table(transaction_history)
            
            # Update current balance display with currency
            current_balance = running_balance
            currency = self.get_current_account_currency()
            balance_color = '#4CAF50' if current_balance >= 0 else '#f44336'
            
            if currency:
                balance_text = f'Current Balance: {currency} {self.format_swiss_number(current_balance)}'
            else:
                balance_text = f'Current Balance: {self.format_swiss_number(current_balance)}'
                
            self.current_balance_label.setText(balance_text)
            self.current_balance_label.setStyleSheet(f'font-weight: bold; font-size: 14px; color: {balance_color};')
            
            # Update status
            account_name = self.account_combo.currentText()
            self.show_status(f'Showing {len(transaction_history)} transactions for {account_name}')
            
        except Exception as e:
            print(f"Error loading account data: {e}")
            import traceback
            traceback.print_exc()
            self.show_status('Error loading account data', error=True)
    
    def populate_table(self, transaction_history):
        """Populate the table with transaction history and running balance."""
        self.table.setRowCount(len(transaction_history))
        
        for row, data in enumerate(transaction_history):
            trans = data['transaction']
            transaction_amount = data['transaction_amount']
            effect = data['effect']
            running_balance = data['running_balance']
            other_account = data['other_account']
            
            # Date
            date_item = QTableWidgetItem(str(trans.date))
            self.table.setItem(row, 0, date_item)
            
            # Type
            type_item = QTableWidgetItem(trans.type.capitalize())
            self.table.setItem(row, 1, type_item)
            
            # Category
            category_item = QTableWidgetItem(trans.sub_category or "")
            self.table.setItem(row, 2, category_item)
            
            # Payee
            payee_item = QTableWidgetItem(trans.payee or "")
            self.table.setItem(row, 3, payee_item)
            
            # Other Account
            other_acc_item = QTableWidgetItem(other_account)
            self.table.setItem(row, 4, other_acc_item)
            
            # Transaction Amount (effect on this account)
            formatted_amount = self.format_swiss_number(transaction_amount)
            trans_amount_text = f"{effect}{formatted_amount}"
            trans_effect_item = QTableWidgetItem(trans_amount_text)
            if effect == "+":
                trans_effect_item.setForeground(QColor(0, 128, 0))  # Green for positive
            else:
                trans_effect_item.setForeground(QColor(255, 0, 0))  # Red for negative
            trans_effect_item.setFont(QFont("", weight=QFont.Weight.Bold))
            self.table.setItem(row, 5, trans_effect_item)
            
            # Running Balance
            formatted_balance = self.format_swiss_number(running_balance)
            balance_item = QTableWidgetItem(formatted_balance)
            if running_balance >= 0:
                balance_item.setForeground(QColor(0, 128, 0))  # Green for positive
            else:
                balance_item.setForeground(QColor(255, 0, 0))  # Red for negative
            balance_item.setFont(QFont("", weight=QFont.Weight.Bold))
            self.table.setItem(row, 6, balance_item)
            
            # Confirmed checkbox
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
            self.table.setCellWidget(row, 7, checkbox_widget)
            
            # Action buttons - Modern X button
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
            
            self.table.setCellWidget(row, 8, action_widget)
        
        # Auto-resize columns to content after population
        self.table.resizeColumnsToContents()
        
        # Set minimum widths for certain columns to prevent them from being too small
        self.table.setColumnWidth(1, max(80, self.table.columnWidth(1)))   # Type
        self.table.setColumnWidth(5, max(130, self.table.columnWidth(5)))  # Transaction Amount
        self.table.setColumnWidth(6, max(130, self.table.columnWidth(6)))  # Running Balance
        self.table.setColumnWidth(7, max(80, self.table.columnWidth(7)))   # Confirmed
        self.table.setColumnWidth(8, max(70, self.table.columnWidth(8)))   # Actions
        
        # Scroll to bottom to see most recent transactions
        if transaction_history:
            self.table.scrollToBottom()
    
    def on_checkbox_changed(self, state):
        """Handle checkbox state changes."""
        try:
            checkbox = self.sender()
            trans_id = checkbox.property('trans_id')
            self.budget_app.toggle_confirmation(trans_id)
            self.show_status(f'Transaction #{trans_id} confirmation toggled!')
            
            # Update parent window if it has a refresh method
            if hasattr(self.parent_window, 'update_balance_display'):
                self.parent_window.update_balance_display()
        except Exception as e:
            print(f"Error in on_checkbox_changed: {e}")
            self.show_status('Error updating confirmation!', error=True)
    
    def on_delete_clicked(self):
        """Handle delete button clicks."""
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
                
                # Update parent window if it has a refresh method
                if hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()
        except Exception as e:
            print(f"Error in on_delete_clicked: {e}")
            self.show_status('Error deleting transaction!', error=True)
    
    def refresh_data(self):
        """Refresh the account data."""
        if self.selected_account_id:
            self.load_account_data()
            self.show_status('Data refreshed')
        else:
            self.show_status('Please select an account first')
    
    def show_status(self, message, error=False):
        """Display a status message."""
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        # Clear after 5 seconds
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))