from PyQt6.QtWidgets import QWidget, QVBoxLayout
from balance_dialog import BalanceDialog


class BalanceTab(QWidget):
    """Tab widget for viewing account balances"""
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.parent_window = parent
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Create the balance dialog content (without the dialog wrapper)
        from balance_dialog import BalanceLoaderThread
        from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, 
                                     QTableWidget, QProgressBar, QTableWidgetItem)
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont, QColor
        
        self.balance_loader = None
        
        content_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        balance_label = QLabel('Account Balances')
        balance_label.setStyleSheet('font-weight: bold; font-size: 18px; margin-bottom: 10px;')
        header_layout.addWidget(balance_label)
        header_layout.addStretch()
        
        content_layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        content_layout.addWidget(self.progress_bar)
        
        # Balance Table
        self.balance_table = QTableWidget()
        self.balance_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.balance_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.balance_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.balance_table.setAlternatingRowColors(True)
        self.balance_table.setShowGrid(False)
        self.balance_table.setStyleSheet("""
            QTableWidget {
                background-color: #fcfcfc;
                alternate-background-color: #f2f2f2;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border: none;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #d0d0d0;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        self.balance_table.verticalHeader().hide()
        
        content_layout.addWidget(self.balance_table)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
        content_layout.addWidget(self.status_label)
        
        layout.addLayout(content_layout)
        
        # Load initial data
        self.refresh_data()
    
    def refresh_data(self):
        """Reload balance data"""
        from balance_dialog import BalanceLoaderThread
        from PyQt6.QtWidgets import QTableWidgetItem
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor
        
        self.balance_table.clear()
        self.balance_table.setRowCount(1)
        self.balance_table.setColumnCount(1)
        item = QTableWidgetItem('Loading balances...')
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.balance_table.setItem(0, 0, item)
        self.balance_table.horizontalHeader().setVisible(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.balance_loader = BalanceLoaderThread(self.budget_app)
        self.balance_loader.finished.connect(self.on_balances_loaded)
        self.balance_loader.error.connect(self.on_balances_error)
        self.balance_loader.start()
    
    def on_balances_loaded(self, balances):
        self.progress_bar.setVisible(False)
        self.update_balance_display_with_data(balances)
        self.show_status('Balances loaded successfully')
    
    def on_balances_error(self, error_message):
        from PyQt6.QtWidgets import QTableWidgetItem
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor
        
        self.progress_bar.setVisible(False)
        self.balance_table.clear()
        self.balance_table.setRowCount(1)
        self.balance_table.setColumnCount(1)
        item = QTableWidgetItem(f'Error loading balances: {error_message}')
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor('red'))
        self.balance_table.setItem(0, 0, item)
        self.show_status(f'Error: {error_message}', error=True)
    
    def update_balance_display_with_data(self, balances):
        from PyQt6.QtWidgets import QTableWidgetItem
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont, QColor
        
        # Pre-fetch accounts
        all_accounts = self.budget_app.get_all_accounts()
        accounts_map = {acc.id: acc for acc in all_accounts}
        currency_map = {acc.id: acc.currency for acc in all_accounts}
        
        account_groups = {}
        for account_id, data in balances.items():
            if abs(data['balance']) < 0.001:
                continue
                
            account_obj = accounts_map.get(account_id)
            if account_obj:
                if account_obj.id == 0:
                    continue
                show_in_balance = getattr(account_obj, 'show_in_balance', True)
                if not show_in_balance:
                    continue
                
            account_name = data['account_name']
            if account_name not in account_groups:
                account_groups[account_name] = []
            
            count = data.get('count', 0)
            account_groups[account_name].append((account_id, data, count))
        
        group_transaction_counts = {}
        for account_name, accounts in account_groups.items():
            total_count = sum(count for _, _, count in accounts)
            group_transaction_counts[account_name] = total_count
        
        currency_totals = {}
        for account_name, accounts in account_groups.items():
            for account_id, data, count in accounts:
                currency = currency_map.get(account_id, 'CHF')
                balance = data['balance']
                if currency in currency_totals:
                    currency_totals[currency] += abs(balance)
                else:
                    currency_totals[currency] = abs(balance)
        
        all_currencies = sorted(currency_totals.keys(), key=lambda x: currency_totals[x], reverse=True)
        sorted_account_groups = sorted(account_groups.items(), 
                                    key=lambda x: group_transaction_counts[x[0]], 
                                    reverse=True)
        
        # Setup Table
        self.balance_table.blockSignals(True)
        self.balance_table.clear()
        self.balance_table.setColumnCount(len(all_currencies) + 1)
        self.balance_table.setHorizontalHeaderLabels(['Account'] + all_currencies)
        self.balance_table.horizontalHeader().setVisible(True)
        
        row_count = len(sorted_account_groups) + 1
        self.balance_table.setRowCount(row_count)
        
        current_row = 0
        total_by_currency = {currency: 0.0 for currency in all_currencies}
        
        font = self.balance_table.font()
        bold_font = QFont(font)
        bold_font.setBold(True)
        
        # Fill Account Rows
        for account_name, accounts in sorted_account_groups:
            name_item = QTableWidgetItem(account_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.balance_table.setItem(current_row, 0, name_item)
            
            group_balances = {currency: 0.0 for currency in all_currencies}
            for account_id, data, count in accounts:
                currency = currency_map.get(account_id, 'CHF')
                group_balances[currency] += data['balance']
            
            for col_idx, currency in enumerate(all_currencies):
                balance = group_balances[currency]
                if abs(balance) >= 0.001:
                    formatted_balance = self.format_with_thousand_separators(balance)
                    balance_item = QTableWidgetItem(formatted_balance)
                    balance_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    
                    if balance < 0:
                         balance_item.setForeground(QColor(255, 0, 0))
                    
                    self.balance_table.setItem(current_row, col_idx + 1, balance_item)
                    total_by_currency[currency] += balance
            
            current_row += 1
        
        # Fill Total Row
        total_label_item = QTableWidgetItem("Total")
        total_label_item.setFont(bold_font)
        total_label_item.setFlags(total_label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.balance_table.setItem(current_row, 0, total_label_item)
        
        for col_idx, currency in enumerate(all_currencies):
             formatted_total = self.format_with_thousand_separators(total_by_currency[currency])
             total_item = QTableWidgetItem(formatted_total)
             total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
             total_item.setFont(bold_font)
             
             if total_by_currency[currency] < 0:
                  total_item.setForeground(QColor(255, 0, 0))
             
             self.balance_table.setItem(current_row, col_idx + 1, total_item)
             
        self.balance_table.blockSignals(False)
        
        # Autosize
        self.balance_table.resizeColumnsToContents()
        self.balance_table.resizeRowsToContents()
        
        for col in range(self.balance_table.columnCount()):
            current_width = self.balance_table.columnWidth(col)
            self.balance_table.setColumnWidth(col, current_width + 20)
    
    def format_with_thousand_separators(self, number):
        """Format number with thousand separators and 2 decimal places"""
        return f"{number:,.2f}"
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
