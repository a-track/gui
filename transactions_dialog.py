from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QCheckBox, QHeaderView, QWidget, QMessageBox,
                             QProgressBar, QComboBox, QStyledItemDelegate)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import datetime
from delegates import ComboBoxDelegate, DateDelegate
from utils import safe_eval_math

class TransactionLoaderThread(QThread):
    finished = pyqtSignal(list)
    progress = pyqtSignal(int)
    
    def __init__(self, budget_app):
        super().__init__()
        self.budget_app = budget_app
    
    def run(self):
        try:
            all_transactions = self.budget_app.get_all_transactions()
            self.finished.emit(all_transactions)
        except Exception as e:
            print(f"Error loading transactions: {e}")
            self.finished.emit([])

class TransactionsDialog(QDialog):
    
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        self.all_transactions = []
        self.filtered_transactions = []
        
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle('View All Transactions')
        self.setMinimumSize(1000, 600)
        
        layout = QVBoxLayout()
        
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
        
        self.info_label = QLabel('Loading transactions...')
        self.info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px;')
        layout.addWidget(self.info_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.table = QTableWidget()
        self.table.verticalHeader().hide()
        
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Date', 'Type', 'Amount', 'Account', 'Account To', 'Payee', 
            'Category', 'Confirmed', 'Actions'
        ])
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)
        
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
        
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 120) # Date
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 150) # Account From
        self.table.setColumnWidth(5, 150) # Account To
        self.table.setColumnWidth(8, 80) # Confirmed
        self.table.setColumnWidth(9, 70) # Actions
        
        header = self.table.horizontalHeader()
        content_columns = [6, 7] # Payee, Category
        for col in content_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.verticalHeader().setDefaultSectionSize(35)
        
        # Set Delegates
        self.date_delegate = DateDelegate(self.table)
        self.table.setItemDelegateForColumn(1, self.date_delegate)

        self.account_delegate = ComboBoxDelegate(self.table, self.get_account_options)
        self.table.setItemDelegateForColumn(4, self.account_delegate)
        self.table.setItemDelegateForColumn(5, self.account_delegate) # Also for Account To
        
        self.category_delegate = ComboBoxDelegate(self.table, self.get_category_options)
        self.table.setItemDelegateForColumn(7, self.category_delegate) # Verify index
        
        layout.addWidget(self.table)
        
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        self.set_current_month_year()
        
        self.load_transactions()
    
    def get_account_options(self):
        accounts = self.budget_app.get_all_accounts()
        return [f"{a.account} {a.currency}" for a in accounts if getattr(a, 'is_active', True)] # Intentionally similar to display format
    
    def get_category_options(self):
        categories = self.budget_app.get_all_categories()
        # Return sub_category
        return sorted([c.sub_category for c in categories])
    
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
    
    def load_transactions(self):
        self.progress_bar.setVisible(True)
        self.info_label.setText('Loading transactions...')
        
        self.loader_thread = TransactionLoaderThread(self.budget_app)
        self.loader_thread.finished.connect(self.on_transactions_loaded)
        self.loader_thread.start()
    
    def on_transactions_loaded(self, transactions):
        self.progress_bar.setVisible(False)
        self.all_transactions = transactions
        
        self.apply_filters()
    
    def apply_filters(self):
        if not self.all_transactions:
            return
        
        selected_year = int(self.year_combo.currentText())
        selected_month = self.month_combo.currentIndex() + 1
        
        self.filtered_transactions = []
        for trans in self.all_transactions:
            try:
                if hasattr(trans, 'date') and trans.date:
                    trans_date = trans.date
                    if isinstance(trans_date, str):
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
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.filtered_transactions))
        
        for row, trans in enumerate(self.filtered_transactions):
            id_item = QTableWidgetItem(str(trans.id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            id_item.setBackground(QColor(240, 240, 240))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)
            
            date_item = QTableWidgetItem(str(trans.date))
            self.table.setItem(row, 1, date_item)
            
            type_item = QTableWidgetItem(str.title(trans.type))
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Type read-only for now
            self.table.setItem(row, 2, type_item)
            
            if trans.type == 'transfer':
                amount_value = trans.amount if trans.amount else ""
            else:
                amount_value = trans.amount
            
            amount_item = QTableWidgetItem(f"{amount_value:.2f}" if amount_value != "" else "")
            if amount_value:
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, amount_item)
            
            if trans.type == 'transfer':
                account_name = self.get_account_name_by_id(trans.account_id)
            else:
                account_name = self.get_account_name_by_id(trans.account_id)
            
            account_item = QTableWidgetItem(account_name or "")
            self.table.setItem(row, 4, account_item)

            # Account To (Column 5)
            if trans.type == 'transfer':
                to_account_name = self.get_account_name_by_id(trans.to_account_id)
            else:
                to_account_name = ""
            
            to_account_item = QTableWidgetItem(to_account_name)
            if trans.type != 'transfer':
                to_account_item.setFlags(to_account_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                to_account_item.setBackground(QColor(245, 245, 245)) # Grey out
            self.table.setItem(row, 5, to_account_item)
            
            payee_item = QTableWidgetItem(trans.payee or "")
            if trans.type == 'transfer':
                payee_item.setFlags(payee_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 6, payee_item)
            
            sub_category_item = QTableWidgetItem(trans.sub_category or "")
            if trans.type == 'transfer':
                sub_category_item.setFlags(sub_category_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 7, sub_category_item)
            
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
            
            self.color_row_by_type(row, trans.type)
        self.table.blockSignals(False)

    def on_cell_changed(self, row, column):
        try:
            item = self.table.item(row, column)
            if not item:
                return
                
            trans_id_item = self.table.item(row, 0)
            if not trans_id_item:
                return
                
            trans_id = int(trans_id_item.text())
            new_value = item.text().strip()
            
            # Map column to db field
            # 1: Date, 3: Amount, 4: Account, 5: Account To, 6: Payee, 7: Sub Category
            field = None
            
            if column == 1: # Date
                field = 'date'
                try:
                    datetime.datetime.strptime(new_value, '%Y-%m-%d')
                except ValueError:
                    self.show_status(f'Invalid date format: {new_value}. Use YYYY-MM-DD', error=True)
                    self.revert_cell(row, column)
                    return
            elif column == 3: # Amount
                field = 'amount'
                try:
                    new_value = safe_eval_math(new_value)
                except ValueError:
                    self.show_status('Invalid amount expression', error=True)
                    self.revert_cell(row, column)
                    return
            elif column == 4: # Account From
                field = 'account_id'
                account_id = self.budget_app.get_account_id_from_name_currency(new_value)
                if account_id is None:
                    self.show_status(f'Account "{new_value}" not found.', error=True)
                    self.revert_cell(row, column)
                    return
                new_value = account_id
            elif column == 5: # Account To (Transfer only)
                field = 'to_account_id'
                account_id = self.budget_app.get_account_id_from_name_currency(new_value)
                if account_id is None:
                    self.show_status(f'Account "{new_value}" not found.', error=True)
                    self.revert_cell(row, column)
                    return
                new_value = account_id
            elif column == 6: # Payee
                field = 'payee'
            elif column == 7: # Category (Sub Category in DB)
                field = 'sub_category'
            
            if field:
                success = self.budget_app.update_transaction(trans_id, **{field: new_value})
                if success:
                    self.show_status(f'Updated transaction #{trans_id}')
                    # Update local model
                    trans = self.filtered_transactions[row]
                    setattr(trans, field, new_value)
                else:
                    self.show_status(f'Error updating transaction #{trans_id}', error=True)
                    self.revert_cell(row, column)
                    
        except Exception as e:
            print(f"Error in on_cell_changed: {e}")
            self.show_status('Error updating transaction', error=True)
            self.revert_cell(row, column)

    def revert_cell(self, row, column):
        """Revert cell to value from local model"""
        try:
            self.table.blockSignals(True)
            trans = self.filtered_transactions[row]
            
            value = ""
            value = ""
            if column == 1:
                value = str(trans.date)
            elif column == 3:
                value = f"{trans.amount:.2f}" if trans.amount else ""
            elif column == 4:
                value = self.get_account_name_by_id(trans.account_id)
            elif column == 5:
                value = self.get_account_name_by_id(trans.to_account_id)
            elif column == 6:
                value = trans.payee or ""
            elif column == 7:
                value = trans.sub_category or ""
                
            self.table.item(row, column).setText(value)
        except Exception as e:
            print(f"Error reverting cell: {e}")
        finally:
            self.table.blockSignals(False)
    
    def get_account_name_by_id(self, account_id):
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return f'{account.account} {account.currency}'
        return ""
    
    def color_row_by_type(self, row, trans_type):
        color_map = {
            'income': QColor(230, 255, 230),
            'expense': QColor(255, 230, 230),
            'transfer': QColor(230, 230, 255)
        }
        
        if trans_type in color_map:
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(color_map[trans_type])
    
    def on_checkbox_changed(self, state):
        try:
            checkbox = self.sender()
            trans_id = checkbox.property('trans_id')
            self.budget_app.toggle_confirmation(trans_id)
            self.show_status(f'Transaction #{trans_id} confirmation toggled!')
            
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
                self.refresh_table()
                
        except Exception as e:
            print(f"Error in on_delete_clicked: {e}")
            self.show_status('Error deleting transaction!', error=True)
    
    def refresh_table(self):
        self.load_transactions()
        self.show_status('Table refreshed!')
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))