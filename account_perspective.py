from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QComboBox, QHeaderView, QWidget, QCheckBox,
                             QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import datetime


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
        
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel('Select Account:'))
        
        self.account_combo = QComboBox()
        accounts = self.budget_app.get_all_accounts()
        accounts_sorted = sorted(accounts, key=lambda x: x.id)
        for account in accounts_sorted:
            display_text = f"{account.account} {account.currency}"
            self.account_combo.addItem(display_text, account.id)
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        account_layout.addWidget(self.account_combo)
        
        account_layout.addStretch()
        
        self.current_balance_label = QLabel('Current Balance: 0.00')
        self.current_balance_label.setStyleSheet('font-weight: bold; font-size: 14px; color: #4CAF50;')
        account_layout.addWidget(self.current_balance_label)
        
        layout.addLayout(account_layout)
        
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel('Year:'))
        self.year_combo = QComboBox()
        self.populate_years()
        self.year_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.year_combo)
        
        filter_layout.addWidget(QLabel('Month:'))
        self.month_combo = QComboBox()
        self.populate_months()
        self.month_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.month_combo)
        
        filter_layout.addStretch()
        
        self.show_all_checkbox = QCheckBox('Show All Transactions')
        self.show_all_checkbox.stateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.show_all_checkbox)
        
        layout.addLayout(filter_layout)
        
        info_label = QLabel('Showing all transactions where this account is involved. Click checkbox to confirm transaction.')
        info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px; background-color: #f0f0f0;')
        layout.addWidget(info_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Category', 'Payee', 
            'Other Account', 'Transaction Amount', 'Running Balance',
            'Confirmed', 'Actions'
        ])
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
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
        
        self.table.verticalHeader().hide()
        
        header = self.table.horizontalHeader()
        self.table.setColumnWidth(7, 80)
        self.table.setColumnWidth(8, 70)
        
        content_based_columns = [0, 1, 2, 3, 4, 5, 6]
        for col in content_based_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        fixed_columns = [7, 8]
        for col in fixed_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        
        self.table.verticalHeader().setDefaultSectionSize(35)
        
        layout.addWidget(self.table)
        
        self.status_label = QLabel('Select an account to view transactions')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        self.set_current_month_year()
        
        if accounts:
            self.account_combo.setCurrentIndex(0)
            self.on_account_changed(0)
    
    def populate_years(self):
        current_year = datetime.datetime.now().year
        years = list(range(current_year - 5, current_year + 2))
        self.year_combo.addItems([str(year) for year in years])
    
    def populate_months(self):
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        self.month_combo.addItems(months)
    
    def set_current_month_year(self):
        now = datetime.datetime.now()
        current_year = str(now.year)
        current_month = now.strftime('%B')
        
        index = self.year_combo.findText(current_year)
        if index >= 0:
            self.year_combo.setCurrentIndex(index)
        
        index = self.month_combo.findText(current_month)
        if index >= 0:
            self.month_combo.setCurrentIndex(index)
    
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
            
            self.running_balance_history = self.calculate_running_balance_history()
            
            self.apply_filters()
            
        except Exception as e:
            print(f"Error loading account data: {e}")
            import traceback
            traceback.print_exc()
            self.show_status('Error loading account data', error=True)
    
    def apply_filters(self):
        if not self.selected_account_id or not self.all_transactions_for_account:
            return
        
        if self.show_all_checkbox.isChecked():
            transactions_to_display = self.all_transactions_for_account
            filter_info = "all transactions"
        else:
            selected_year = int(self.year_combo.currentText())
            selected_month = self.month_combo.currentIndex() + 1
            
            transactions_to_display = []
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
            
            month_name = self.month_combo.currentText()
            filter_info = f"{month_name} {selected_year}"
        
        transactions_to_display.sort(key=lambda x: (x.date, x.id))
        
        transaction_history = []
        
        for trans in transactions_to_display:
            running_balance = self.running_balance_history.get(trans.id, 0.0)
            
            if trans.type == 'income' and trans.account_id == self.selected_account_id:
                transaction_amount = float(trans.amount or 0)
                effect = "+"
                other_account = trans.payee or "Income"
                
            elif trans.type == 'expense' and trans.account_id == self.selected_account_id:
                transaction_amount = float(trans.amount or 0)
                effect = "-"
                other_account = trans.payee or "Expense"
                
            elif trans.type == 'transfer':
                if trans.account_id == self.selected_account_id:
                    transaction_amount = float(trans.amount or 0)
                    effect = "-"
                    other_account = self.get_account_name_by_id(trans.to_account_id)
                elif trans.to_account_id == self.selected_account_id:
                    transaction_amount = float(trans.to_amount or 0)
                    effect = "+"
                    other_account = self.get_account_name_by_id(trans.account_id)
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
        
        account_name = self.account_combo.currentText()
        self.show_status(f'Showing {len(transaction_history)} transactions for {account_name} ({filter_info})')
        
    def populate_table(self, transaction_history):
        self.table.setRowCount(len(transaction_history))
        
        for row, data in enumerate(transaction_history):
            trans = data['transaction']
            transaction_amount = data['transaction_amount']
            effect = data['effect']
            running_balance = data['running_balance']
            other_account = data['other_account']
            
            date_item = QTableWidgetItem(str(trans.date))
            self.table.setItem(row, 0, date_item)
            
            type_item = QTableWidgetItem(trans.type.capitalize())
            self.table.setItem(row, 1, type_item)
            
            category_item = QTableWidgetItem(trans.sub_category or "")
            self.table.setItem(row, 2, category_item)
            
            payee_item = QTableWidgetItem(trans.payee or "")
            self.table.setItem(row, 3, payee_item)
            
            other_acc_item = QTableWidgetItem(other_account)
            self.table.setItem(row, 4, other_acc_item)
            
            formatted_amount = self.format_swiss_number(transaction_amount)
            trans_amount_text = f"{effect}{formatted_amount}"
            trans_effect_item = QTableWidgetItem(trans_amount_text)
            if effect == "+":
                trans_effect_item.setForeground(QColor(0, 128, 0))
            else:
                trans_effect_item.setForeground(QColor(255, 0, 0))
            trans_effect_item.setFont(QFont("", weight=QFont.Weight.Bold))
            self.table.setItem(row, 5, trans_effect_item)
            
            formatted_balance = self.format_swiss_number(running_balance)
            balance_item = QTableWidgetItem(formatted_balance)
            if running_balance >= 0:
                balance_item.setForeground(QColor(0, 128, 0))
            else:
                balance_item.setForeground(QColor(255, 0, 0))
            balance_item.setFont(QFont("", weight=QFont.Weight.Bold))
            self.table.setItem(row, 6, balance_item)
            
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
        
        self.table.resizeColumnsToContents()
        
        self.table.setColumnWidth(1, max(80, self.table.columnWidth(1)))
        self.table.setColumnWidth(5, max(130, self.table.columnWidth(5)))
        self.table.setColumnWidth(6, max(130, self.table.columnWidth(6)))
        self.table.setColumnWidth(7, max(80, self.table.columnWidth(7)))
        self.table.setColumnWidth(8, max(70, self.table.columnWidth(8)))
        
        if transaction_history:
            self.table.scrollToBottom()
    
    def on_checkbox_changed(self, state):
        try:
            checkbox = self.sender()
            trans_id = checkbox.property('trans_id')
            self.budget_app.toggle_confirmation(trans_id)
            self.show_status(f'Transaction #{trans_id} confirmation toggled!')
            
            if hasattr(self.parent_window, 'update_balance_display'):
                self.parent_window.update_balance_display()
        except Exception as e:
            print(f"Error in on_checkbox_changed: {e}")
            self.show_status('Error updating confirmation!', error=True)
    
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
                
                if hasattr(self.parent_window, 'update_balance_display'):
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