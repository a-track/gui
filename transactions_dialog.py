"""
Optimized dialog for viewing transactions with month/year filtering.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QCheckBox, QHeaderView, QWidget, QMessageBox,
                             QProgressBar, QComboBox)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import datetime

class TransactionLoaderThread(QThread):
    """Thread for loading transactions in background"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(int)
    
    def __init__(self, budget_app):
        super().__init__()
        self.budget_app = budget_app
    
    def run(self):
        try:
            # Get all transactions
            all_transactions = self.budget_app.get_all_transactions()
            self.finished.emit(all_transactions)
        except Exception as e:
            print(f"Error loading transactions: {e}")
            self.finished.emit([])

class TransactionsDialog(QDialog):
    """Optimized dialog for viewing transactions with month/year filtering."""
    
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        self.all_transactions = []
        self.filtered_transactions = []
        
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle('All Transactions')
        self.setMinimumSize(1000, 600)
        
        layout = QVBoxLayout()
        
        # Filter controls
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
        
        layout.addLayout(filter_layout)
        
        # Info label
        self.info_label = QLabel('Loading transactions...')
        self.info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px;')
        layout.addWidget(self.info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
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
        refresh_btn.clicked.connect(self.load_transactions)
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
        
        # Set current month/year as default
        self.set_current_month_year()
        
        # Load transactions
        self.load_transactions()
    
    def populate_years(self):
        """Populate years combo box with recent years"""
        current_year = datetime.datetime.now().year
        years = list(range(current_year - 5, current_year + 2))
        self.year_combo.addItems([str(year) for year in years])
    
    def populate_months(self):
        """Populate months combo box"""
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        self.month_combo.addItems(months)
    
    def set_current_month_year(self):
        """Set filters to current month and year"""
        now = datetime.datetime.now()
        current_year = str(now.year)
        current_month = now.strftime('%B')  # Full month name
        
        # Set year
        index = self.year_combo.findText(current_year)
        if index >= 0:
            self.year_combo.setCurrentIndex(index)
        
        # Set month
        index = self.month_combo.findText(current_month)
        if index >= 0:
            self.month_combo.setCurrentIndex(index)
    
    def load_transactions(self):
        """Load all transactions"""
        self.progress_bar.setVisible(True)
        self.info_label.setText('Loading transactions...')
        
        # Load in background thread
        self.loader_thread = TransactionLoaderThread(self.budget_app)
        self.loader_thread.finished.connect(self.on_transactions_loaded)
        self.loader_thread.start()
    
    def on_transactions_loaded(self, transactions):
        """Handle loaded transactions"""
        self.progress_bar.setVisible(False)
        self.all_transactions = transactions
        
        # Apply initial filters
        self.apply_filters()
    
    def apply_filters(self):
        """Apply year/month filters to transactions"""
        if not self.all_transactions:
            return
        
        # Filter by selected year and month
        selected_year = int(self.year_combo.currentText())
        selected_month = self.month_combo.currentIndex() + 1  # 1-12
        
        self.filtered_transactions = []
        for trans in self.all_transactions:
            try:
                # Parse transaction date
                if hasattr(trans, 'date') and trans.date:
                    trans_date = trans.date
                    if isinstance(trans_date, str):
                        # If date is string, parse it
                        trans_date = datetime.datetime.strptime(trans_date, '%Y-%m-%d').date()
                    
                    if trans_date.year == selected_year and trans_date.month == selected_month:
                        self.filtered_transactions.append(trans)
            except (ValueError, AttributeError) as e:
                print(f"Error parsing date for transaction {trans.id}: {e}")
                continue
        
        month_name = self.month_combo.currentText()
        self.info_label.setText(
            f'Showing {len(self.filtered_transactions)} transactions for {month_name} {selected_year}'
        )
        
        self.populate_table()
    
    def populate_table(self):
        """Populate table with filtered transactions"""
        self.table.setRowCount(len(self.filtered_transactions))
        
        for row, trans in enumerate(self.filtered_transactions):
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
            type_item = QTableWidgetItem(str.title(trans.type))
            self.table.setItem(row, 2, type_item)
            
            # Amount
            if trans.type == 'transfer':
                amount_value = trans.amount if trans.amount else ""
            else:
                amount_value = trans.amount if trans.amount else ""
            
            amount_item = QTableWidgetItem(f"{amount_value:.2f}" if amount_value != "" else "")
            if amount_value:
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, amount_item)
            
            # Account
            if trans.type == 'transfer':
                account_name = self.get_account_name_by_id(trans.account_id)
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
            
            # Set row background color based on type
            self.color_row_by_type(row, trans.type)
    
    def get_account_name_by_id(self, account_id):
        """Get account name by account ID."""
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return f'{account.account} {account.currency}'
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
        self.load_transactions()
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