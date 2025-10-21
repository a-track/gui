"""
Dialog window for viewing all transactions.
SIMPLIFIED: Only shows transactions with confirmation and delete functionality.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QCheckBox, QHeaderView, QWidget, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor


class TransactionsDialog(QDialog):
    """Simplified dialog for viewing transactions with confirmation and delete."""
    
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle('All Transactions')
        self.setMinimumSize(1000, 500)
        
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel('Click checkbox to confirm/unconfirm transaction.')
        info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px;')
        layout.addWidget(info_label)
        
        # Table
        self.table = QTableWidget()
        self.table.verticalHeader().hide()
        
        # Columns with Actions for delete button
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Date', 'Type', 'Amount', 'Account', 'Payee', 
            'Category', 'Confirmed', 'Actions'
        ])
        
        # Make table read-only (no editing)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Improve table appearance
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
        
        # Get transactions and populate
        self.transactions = self.budget_app.get_all_transactions()
        self.populate_table()
        
        # Set column sizes
        self.table.setColumnWidth(0, 50)   # ID
        self.table.setColumnWidth(2, 80)   # Type
        self.table.setColumnWidth(3, 90)   # Amount
        self.table.setColumnWidth(7, 80)   # Confirmed
        self.table.setColumnWidth(8, 70)   # Actions
        
        # Make other columns resize to contents
        header = self.table.horizontalHeader()
        content_columns = [1, 4, 5, 6]
        for col in content_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        # Set row height
        self.table.verticalHeader().setDefaultSectionSize(35)
        
        layout.addWidget(self.table)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        layout.addWidget(self.status_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Refresh button
        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.refresh_table)
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
    
    def populate_table(self):
        """Populate the table with transaction data."""
        self.table.setRowCount(len(self.transactions))
        
        for row, trans in enumerate(self.transactions):
            # ID
            id_item = QTableWidgetItem(str(trans.id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            id_item.setBackground(QColor(240, 240, 240))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)
            
            # Date
            date_item = QTableWidgetItem(str(trans.date))
            self.table.setItem(row, 1, date_item)
            
            # Type
            type_item = QTableWidgetItem(trans.type)
            self.table.setItem(row, 2, type_item)
            
            # Amount
            if trans.type == 'transfer':
                amount_value = trans.from_amount if trans.from_amount else ""
            else:
                amount_value = trans.amount if trans.amount else ""
            
            amount_item = QTableWidgetItem(f"{amount_value:.2f}" if amount_value != "" else "")
            if amount_value:
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, amount_item)
            
            # Account
            if trans.type == 'transfer':
                account_name = self.get_account_name_by_id(trans.from_account_id)
            else:
                account_name = self.get_account_name_by_id(trans.account_id)
            account_item = QTableWidgetItem(account_name or "")
            self.table.setItem(row, 4, account_item)
            
            # Payee
            payee_item = QTableWidgetItem(trans.payee or "")
            self.table.setItem(row, 5, payee_item)
            
            # Category
            sub_category_item = QTableWidgetItem(trans.sub_category or "")
            self.table.setItem(row, 6, sub_category_item)
            
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
            
            # Action buttons - Modern X button (same as account perspective)
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
            
            # Set row background color based on type
            self.color_row_by_type(row, trans.type)
    
    def get_account_name_by_id(self, account_id):
        """Get account name by account ID."""
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account.account
        return ""
    
    def color_row_by_type(self, row, trans_type):
        """Set row background color based on transaction type."""
        color_map = {
            'income': QColor(230, 255, 230),    # Light green
            'expense': QColor(255, 230, 230),   # Light red
            'transfer': QColor(230, 230, 255)   # Light blue
        }
        
        if trans_type in color_map:
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(color_map[trans_type])
    
    def on_checkbox_changed(self, state):
        """Handle checkbox state changes."""
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
                self.refresh_table()
                
                if hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()
        except Exception as e:
            print(f"Error in on_delete_clicked: {e}")
            self.show_status('Error deleting transaction!', error=True)
    
    def refresh_table(self):
        """Refresh the table data."""
        self.transactions = self.budget_app.get_all_transactions()
        self.populate_table()
        self.show_status('Table refreshed!')
    
    def show_status(self, message, error=False):
        """Display a status message."""
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        # Clear after 5 seconds
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))