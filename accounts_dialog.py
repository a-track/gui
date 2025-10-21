"""
Account Management Dialog
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QLineEdit, QComboBox,
                             QCheckBox, QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


class AccountsDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.parent_window = parent
        
        self.setWindowTitle('Manage Accounts')
        self.setMinimumSize(1000, 500)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel('Account Management')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet('color: #2196F3; padding: 10px;')
        layout.addWidget(title)
        
        # Add new account section
        new_account_layout = QHBoxLayout()
        
        new_account_layout.addWidget(QLabel('Account Name:'))
        self.account_name_input = QLineEdit()
        self.account_name_input.setPlaceholderText('Enter account name')
        new_account_layout.addWidget(self.account_name_input)
        
        new_account_layout.addWidget(QLabel('Type:'))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['Cash', 'Bank', 'Credit', 'Share', 'ETF', 'Fonds', '3a', 'Other'])
        new_account_layout.addWidget(self.type_combo)
        
        new_account_layout.addWidget(QLabel('Company:'))
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText('Optional')
        new_account_layout.addWidget(self.company_input)
        
        new_account_layout.addWidget(QLabel('Currency:'))
        self.currency_input = QLineEdit()
        self.currency_input.setText('CHF')
        self.currency_input.setMaximumWidth(80)
        new_account_layout.addWidget(self.currency_input)
        
        self.is_investment_check = QCheckBox('Investment Account')
        new_account_layout.addWidget(self.is_investment_check)
        
        add_btn = QPushButton('Add Account')
        add_btn.clicked.connect(self.add_account)
        add_btn.setStyleSheet('background-color: #4CAF50; color: white; padding: 5px;')
        new_account_layout.addWidget(add_btn)
        
        layout.addLayout(new_account_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['ID', 'Account Name', 'Type', 'Company', 'Currency', 'Actions'])
        
        # Make table read-only
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Style the table to match transactions dialog
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
        self.table.setColumnWidth(5, 70)   # Actions - fixed small width
        
        # Make content-based columns resize to contents
        content_based_columns = [0, 1, 2, 3, 4]
        for col in content_based_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        # Actions column stays interactive
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        
        # Set row height
        self.table.verticalHeader().setDefaultSectionSize(35)
        
        layout.addWidget(self.table)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.load_accounts)
        refresh_btn.setStyleSheet('background-color: #FF9800; color: white; padding: 8px;')
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet('background-color: #2196F3; color: white; padding: 8px;')
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.load_accounts()
    
    def load_accounts(self):
        try:
            accounts = self.budget_app.get_all_accounts()
            # Sort accounts by ID
            accounts_sorted = sorted(accounts, key=lambda x: x.id)
            self.table.setRowCount(len(accounts_sorted))
            
            for row, account in enumerate(accounts_sorted):
                # ID
                id_item = QTableWidgetItem(str(account.id))
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                id_item.setBackground(QColor(240, 240, 240))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, id_item)
                
                # Account Name
                name_item = QTableWidgetItem(account.account)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only
                self.table.setItem(row, 1, name_item)
                
                # Type
                type_item = QTableWidgetItem(account.type)
                type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only
                self.table.setItem(row, 2, type_item)
                
                # Company
                company_item = QTableWidgetItem(account.company or '')
                company_item.setFlags(company_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only
                self.table.setItem(row, 3, company_item)
                
                # Currency
                currency_item = QTableWidgetItem(account.currency)
                currency_item.setFlags(currency_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only
                self.table.setItem(row, 4, currency_item)
                
                # Actions - Modern X button
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(1, 1, 1, 1)  # Minimal margins
                action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                delete_btn = QPushButton('✕')  # Modern X symbol
                delete_btn.setFixedSize(22, 22)  # Small size to fit nicely
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
                delete_btn.setProperty('account_id', account.id)
                delete_btn.clicked.connect(self.delete_account)
                delete_btn.setToolTip('Delete account')
                
                action_layout.addWidget(delete_btn)
                action_widget.setLayout(action_layout)
                
                self.table.setCellWidget(row, 5, action_widget)
            
            # Auto-resize columns to content after population
            self.table.resizeColumnsToContents()
            
            # Set minimum widths for certain columns to prevent them from being too small
            self.table.setColumnWidth(0, max(50, self.table.columnWidth(0)))   # ID
            self.table.setColumnWidth(2, max(80, self.table.columnWidth(2)))   # Type
            self.table.setColumnWidth(4, max(80, self.table.columnWidth(4)))   # Currency
            self.table.setColumnWidth(5, max(70, self.table.columnWidth(5)))   # Actions
            
            self.show_status(f'Loaded {len(accounts)} accounts')
            
        except Exception as e:
            print(f"Error loading accounts: {e}")
            self.show_status('Error loading accounts', error=True)
    
    def add_account(self):
        account_name = self.account_name_input.text().strip()
        if not account_name:
            self.show_status('Please enter an account name', error=True)
            return
        
        account_type = self.type_combo.currentText()
        company = self.company_input.text().strip() or None
        currency = self.currency_input.text().strip()
        is_investment = self.is_investment_check.isChecked()
        
        success = self.budget_app.add_account(account_name, account_type, company, currency, is_investment)
        
        if success:
            self.show_status('Account added successfully!')
            self.account_name_input.clear()
            self.company_input.clear()
            self.currency_input.setText('CHF')
            self.is_investment_check.setChecked(False)
            self.load_accounts()
            
            # Update parent window if needed
            if hasattr(self.parent_window, 'update_balance_display'):
                self.parent_window.update_balance_display()
        else:
            self.show_status('Error adding account', error=True)
    
    def delete_account(self):
        try:
            button = self.sender()
            account_id = button.property('account_id')
            
            reply = QMessageBox.question(
                self, 
                'Confirm Delete', 
                f'Delete this account?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success, message = self.budget_app.delete_account(account_id)
                if success:
                    self.show_status('Account deleted successfully!')
                    self.load_accounts()
                    
                    # Update parent window if needed
                    if hasattr(self.parent_window, 'update_balance_display'):
                        self.parent_window.update_balance_display()
                else:
                    self.show_status(f'Error: {message}', error=True)
                    
        except Exception as e:
            print(f"Error deleting account: {e}")
            self.show_status('Error deleting account', error=True)
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))