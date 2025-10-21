import sys
import duckdb
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QComboBox, QRadioButton, QButtonGroup, QTableWidget,
                             QTableWidgetItem, QMessageBox, QDialog, QCheckBox,
                             QHeaderView, QStyledItemDelegate)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class Transaction:
    def __init__(self, trans_id: int, date: str, type: str, amount: float, 
                 category: str, account: str, description: str = "", 
                 to_account: str = None, confirmed: bool = False):
        self.id = trans_id
        self.date = date
        self.type = type
        self.amount = amount
        self.category = category
        self.account = account
        self.description = description
        self.to_account = to_account
        self.confirmed = confirmed

class BudgetApp:
    def __init__(self, db_path='budget.duckdb'):
        self.db_path = db_path
        self.accounts = ['Cash', 'Checking', 'Savings', 'Credit Card']
        self.expense_categories = ['Food', 'Transportation', 'Housing', 'Entertainment', 
                                   'Utilities', 'Healthcare', 'Shopping', 'Other']
        self.income_categories = ['Salary', 'Freelance', 'Investment', 'Gift', 'Other']
        self.init_database()

    def _get_connection(self):
        return duckdb.connect(self.db_path)

    def init_database(self):
        conn = self._get_connection()
        try:
            # Check if table exists using DuckDB syntax
            result = conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name='transactions'
            """).fetchone()
            
            # Only create if it doesn't exist
            if not result:
                conn.execute("""
                    CREATE TABLE transactions (
                        id INTEGER PRIMARY KEY,
                        date DATE NOT NULL,
                        type VARCHAR NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        category VARCHAR NOT NULL,
                        account VARCHAR NOT NULL,
                        description TEXT,
                        to_account VARCHAR,
                        confirmed BOOLEAN DEFAULT FALSE
                    )
                """)
                conn.commit()
            else:
                # Check if to_account and confirmed columns exist, add if they don't
                columns = conn.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name='transactions'
                """).fetchall()
                column_names = [col[0] for col in columns]
                
                if 'to_account' not in column_names:
                    conn.execute("ALTER TABLE transactions ADD COLUMN to_account VARCHAR")
                    conn.commit()
                
                if 'confirmed' not in column_names:
                    conn.execute("ALTER TABLE transactions ADD COLUMN confirmed BOOLEAN DEFAULT FALSE")
                    conn.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

    def _get_next_id(self) -> int:
        conn = self._get_connection()
        try:
            result = conn.execute("SELECT MAX(id) FROM transactions").fetchone()
            return 1 if result[0] is None else result[0] + 1
        finally:
            conn.close()

    def add_transaction(self, trans_type: str, amount: float, category: str, 
                       account: str, description: str = "", to_account: str = None):
        date = datetime.now().strftime("%Y-%m-%d")
        trans_id = self._get_next_id()
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO transactions (id, date, type, amount, category, account, description, to_account, confirmed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, FALSE)
            """, [trans_id, date, trans_type, amount, category, account, description, to_account])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding transaction: {e}")
            return False
        finally:
            conn.close()

    def get_all_transactions(self):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT id, date, type, amount, category, account, description, to_account, confirmed
                FROM transactions 
                ORDER BY date DESC, id DESC
            """).fetchall()
            return [Transaction(*row) for row in result]
        except Exception as e:
            print(f"Error getting transactions: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            conn.close()

    def update_transaction(self, trans_id: int, trans_type: str, amount: float, 
                          category: str, account: str, description: str = "", 
                          to_account: str = None, confirmed: bool = False):
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE transactions 
                SET type = ?, amount = ?, category = ?, account = ?, description = ?, to_account = ?, confirmed = ?
                WHERE id = ?
            """, [trans_type, amount, category, account, description, to_account, confirmed, trans_id])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating transaction: {e}")
            return False
        finally:
            conn.close()

    def delete_transaction(self, trans_id: int):
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM transactions WHERE id = ?", [trans_id])
            conn.commit()
        finally:
            conn.close()

    def toggle_confirmation(self, trans_id: int):
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE transactions 
                SET confirmed = NOT confirmed
                WHERE id = ?
            """, [trans_id])
            conn.commit()
        finally:
            conn.close()

    def get_balance_summary(self):
        """Get balance summary for all accounts"""
        conn = self._get_connection()
        try:
            balances = {}
            for account in self.accounts:
                balances[account] = 0.0
            
            transactions = self.get_all_transactions()
            for trans in transactions:
                # Convert amount to float to avoid Decimal type issues
                amount = float(trans.amount)
                
                if trans.type == 'income':
                    balances[trans.account] += amount
                elif trans.type == 'expense':
                    balances[trans.account] -= amount
                elif trans.type == 'transfer':
                    balances[trans.account] -= amount
                    if trans.to_account:
                        balances[trans.to_account] += amount
            
            return balances
        finally:
            conn.close()

class ComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.ItemDataRole.EditRole)
        if value:
            idx = editor.findText(str(value))
            if idx >= 0:
                editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
    
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class TransactionsDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        try:
            print("  TransactionsDialog.__init__ starting...")
            super().__init__(parent)
            print("  super().__init__ completed")
            
            self.budget_app = budget_app
            self.parent_window = parent
            
            # Simple window flags - removed WindowStaysOnTopHint for better compatibility
            self.setWindowFlags(Qt.WindowType.Window)
            
            self.setWindowTitle('All Transactions')
            self.setMinimumSize(1200, 500)
            
            print("  Creating layout...")
            layout = QVBoxLayout()
            
            # Info label
            info_label = QLabel('Tip: Double-click any cell to edit. Click checkbox to confirm transaction.')
            info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px;')
            layout.addWidget(info_label)
            
            # Table
            print("  Creating table...")
            self.table = QTableWidget()
            self.table.setColumnCount(10)
            self.table.setHorizontalHeaderLabels(['ID', 'Date', 'Type', 'Amount', 'Category', 
                                                   'From Account', 'To Account', 'Description', 
                                                   'Confirmed', 'Actions'])
            
            # Make columns editable
            self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
            
            # Set up delegates for dropdown columns
            print("  Setting up delegates...")
            self.type_delegate = ComboBoxDelegate(['Income', 'Expense', 'Transfer'], self)
            self.table.setItemDelegateForColumn(2, self.type_delegate)
            
            self.account_delegate = ComboBoxDelegate(self.budget_app.accounts, self)
            self.table.setItemDelegateForColumn(5, self.account_delegate)
            self.table.setItemDelegateForColumn(6, self.account_delegate)
            
            # Get transactions and populate
            print("  Getting transactions...")
            self.transactions = self.budget_app.get_all_transactions()
            print(f"  Got {len(self.transactions)} transactions")
            
            # Connect cell changed signal
            print("  Connecting signals...")
            self.table.cellChanged.connect(self.on_cell_changed)
            
            print("  Populating table...")
            self.populate_table()
            print("  Table populated")
            
            # Resize columns
            print("  Resizing columns...")
            header = self.table.horizontalHeader()
            for i in range(self.table.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Description column
            
            layout.addWidget(self.table)
            
            # Status bar
            print("  Creating status label...")
            self.status_label = QLabel('')
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
            layout.addWidget(self.status_label)
            
            # Button layout
            print("  Creating buttons...")
            button_layout = QHBoxLayout()
            
            # Refresh button
            refresh_btn = QPushButton('Refresh')
            refresh_btn.clicked.connect(self.refresh_table)
            refresh_btn.setStyleSheet('background-color: #FF9800; color: white; padding: 8px;')
            button_layout.addWidget(refresh_btn)
            
            button_layout.addStretch()
            
            # Close button
            close_btn = QPushButton('Close')
            close_btn.clicked.connect(self.close_and_update)
            close_btn.setStyleSheet('background-color: #2196F3; color: white; padding: 8px;')
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            print("  Setting layout...")
            self.setLayout(layout)
            print("  TransactionsDialog.__init__ completed successfully!")
            
        except Exception as e:
            print("\n" + "="*60)
            print("ERROR IN TransactionsDialog.__init__:")
            print("="*60)
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print("="*60)
            raise
    
    def populate_table(self):
        try:
            print(f"    populate_table: Setting row count to {len(self.transactions)}")
            self.table.setRowCount(len(self.transactions))
            
            # Temporarily disconnect signal to avoid triggering during population
            print("    populate_table: Disconnecting cellChanged signal")
            try:
                self.table.cellChanged.disconnect()
            except:
                pass
            
            print("    populate_table: Starting to populate rows...")
            for row, trans in enumerate(self.transactions):
                print(f"    populate_table: Processing row {row}, transaction ID {trans.id}")
                
                # ID (read-only)
                id_item = QTableWidgetItem(str(trans.id))
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                id_item.setBackground(QColor(240, 240, 240))
                self.table.setItem(row, 0, id_item)
                
                # Date (read-only for now)
                date_item = QTableWidgetItem(str(trans.date))
                date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                date_item.setBackground(QColor(240, 240, 240))
                self.table.setItem(row, 1, date_item)
                
                # Type
                type_item = QTableWidgetItem(trans.type.capitalize())
                self.table.setItem(row, 2, type_item)
                
                # Amount
                amount_item = QTableWidgetItem(f"{trans.amount:.2f}")
                self.table.setItem(row, 3, amount_item)
                
                # Category
                category_item = QTableWidgetItem(trans.category)
                self.table.setItem(row, 4, category_item)
                
                # From Account
                account_item = QTableWidgetItem(trans.account)
                self.table.setItem(row, 5, account_item)
                
                # To Account - make read-only for non-transfer transactions
                to_account_item = QTableWidgetItem(trans.to_account or "")
                if trans.type.lower() != 'transfer':
                    # Make read-only with gray background for income/expense
                    to_account_item.setFlags(to_account_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    to_account_item.setBackground(QColor(240, 240, 240))
                    to_account_item.setForeground(QColor(150, 150, 150))
                self.table.setItem(row, 6, to_account_item)
                
                # Description
                desc_item = QTableWidgetItem(trans.description or "")
                self.table.setItem(row, 7, desc_item)
                
                print(f"    populate_table: Creating checkbox for row {row}")
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
                self.table.setCellWidget(row, 8, checkbox_widget)
                
                print(f"    populate_table: Creating action buttons for row {row}")
                # Action buttons widget
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(4, 4, 4, 4)
                
                delete_btn = QPushButton('Delete')
                delete_btn.setStyleSheet('background-color: #f44336; color: white; padding: 4px 12px;')
                delete_btn.setProperty('trans_id', trans.id)
                delete_btn.clicked.connect(self.on_delete_clicked)
                
                action_layout.addWidget(delete_btn)
                action_layout.addStretch()
                action_widget.setLayout(action_layout)
                
                self.table.setCellWidget(row, 9, action_widget)
                print(f"    populate_table: Row {row} completed")
            
            # Reconnect signal
            print("    populate_table: Reconnecting cellChanged signal")
            self.table.cellChanged.connect(self.on_cell_changed)
            print("    populate_table: COMPLETED SUCCESSFULLY")
            
        except Exception as e:
            print("\n" + "="*60)
            print("ERROR IN populate_table:")
            print("="*60)
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print("="*60)
            raise
    
    def close_and_update(self):
        """Close dialog and update parent window balance"""
        if hasattr(self.parent_window, 'update_balance_display'):
            self.parent_window.update_balance_display()
        self.close()
    
    def on_checkbox_changed(self, state):
        """Handle checkbox state changes"""
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
            import traceback
            traceback.print_exc()
    
    def on_delete_clicked(self):
        """Handle delete button clicks"""
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
                
                # Update parent window if it has a refresh method
                if hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()
        except Exception as e:
            print(f"Error in on_delete_clicked: {e}")
            import traceback
            traceback.print_exc()
    
    def on_cell_changed(self, row, column):
        # Get transaction ID
        trans_id = int(self.table.item(row, 0).text())
        
        # Get transaction type
        trans_type = self.table.item(row, 2).text().lower()
        
        # Validate account changes - ensure they're from the valid list
        if column == 5:  # From Account column
            account = self.table.item(row, 5).text()
            if account not in self.budget_app.accounts:
                self.show_status(f'Invalid account! Must be one of: {", ".join(self.budget_app.accounts)}', error=True)
                self.refresh_table()
                return
        
        if column == 6:  # To Account column
            # Only allow editing To Account for transfers
            if trans_type != 'transfer':
                self.show_status('To Account can only be set for Transfer transactions!', error=True)
                self.refresh_table()
                return
            
            to_account = self.table.item(row, 6).text()
            if to_account and to_account not in self.budget_app.accounts:
                self.show_status(f'Invalid account! Must be one of: {", ".join(self.budget_app.accounts)}', error=True)
                self.refresh_table()
                return
        
        # Get all current values
        try:
            amount = float(self.table.item(row, 3).text())
        except ValueError:
            self.show_status('Invalid amount! Please enter a number.', error=True)
            self.refresh_table()
            return
        
        if amount <= 0:
            self.show_status('Amount must be greater than 0!', error=True)
            self.refresh_table()
            return
        
        category = self.table.item(row, 4).text()
        account = self.table.item(row, 5).text()
        to_account_text = self.table.item(row, 6).text()
        
        # Only set to_account if it's a transfer and the field is not empty
        if trans_type == 'transfer':
            to_account = to_account_text if to_account_text else None
            if to_account and account == to_account:
                self.show_status('Cannot transfer to the same account!', error=True)
                self.refresh_table()
                return
        else:
            to_account = None
        
        description = self.table.item(row, 7).text()
        
        # Get confirmed status from checkbox
        checkbox_widget = self.table.cellWidget(row, 8)
        checkbox = checkbox_widget.findChild(QCheckBox)
        confirmed = checkbox.isChecked()
        
        # Update in database
        success = self.budget_app.update_transaction(
            trans_id, trans_type, amount, category, account, description, to_account, confirmed
        )
        
        if success:
            self.show_status('Transaction updated successfully!')
            
            # Refresh the row to apply read-only status if type changed
            if column == 2:  # Type column changed
                self.refresh_table()
            
            # Update parent window if it has a refresh method
            if hasattr(self.parent_window, 'update_balance_display'):
                self.parent_window.update_balance_display()
        else:
            self.show_status('Error updating transaction!', error=True)
    
    def refresh_table(self):
        self.transactions = self.budget_app.get_all_transactions()
        self.populate_table()
        self.show_status('Table refreshed!')
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        # Clear after 3 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.status_label.setText(''))

class BudgetTrackerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.budget_app = BudgetApp()
        self.init_ui()
        self.update_balance_display()

    def init_ui(self):
        self.setWindowTitle('Budget Tracker')
        self.setMinimumSize(600, 700)
        
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
        
        subtitle = QLabel('Manage your income, expenses, and transfers easily!')
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        main_layout.addWidget(subtitle)
        
        main_layout.addSpacing(20)
        
        # Balance summary section
        balance_label = QLabel('Account Balances:')
        balance_label.setStyleSheet('font-weight: bold; font-size: 14px;')
        main_layout.addWidget(balance_label)
        
        self.balance_display = QLabel()
        self.balance_display.setStyleSheet('background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;')
        main_layout.addWidget(self.balance_display)
        
        main_layout.addSpacing(20)
        
        # Transaction type
        type_label = QLabel('Transaction Type:')
        main_layout.addWidget(type_label)
        
        type_layout = QHBoxLayout()
        self.income_radio = QRadioButton('Income')
        self.expense_radio = QRadioButton('Expense')
        self.transfer_radio = QRadioButton('Transfer')
        self.income_radio.setChecked(True)
        
        self.type_group = QButtonGroup()
        self.type_group.addButton(self.income_radio)
        self.type_group.addButton(self.expense_radio)
        self.type_group.addButton(self.transfer_radio)
        
        type_layout.addWidget(self.income_radio)
        type_layout.addWidget(self.expense_radio)
        type_layout.addWidget(self.transfer_radio)
        type_layout.addStretch()
        main_layout.addLayout(type_layout)
        
        # Amount
        amount_label = QLabel('Amount:')
        main_layout.addWidget(amount_label)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText('Enter amount')
        main_layout.addWidget(self.amount_input)
        
        # Category
        self.category_label = QLabel('Category:')
        main_layout.addWidget(self.category_label)
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.budget_app.income_categories)
        main_layout.addWidget(self.category_combo)
        
        # From Account
        from_account_label = QLabel('From Account:')
        main_layout.addWidget(from_account_label)
        self.account_combo = QComboBox()
        self.account_combo.addItems(self.budget_app.accounts)
        main_layout.addWidget(self.account_combo)
        
        # To Account (for transfers)
        self.to_account_label = QLabel('To Account:')
        main_layout.addWidget(self.to_account_label)
        self.to_account_combo = QComboBox()
        self.to_account_combo.addItems(self.budget_app.accounts)
        main_layout.addWidget(self.to_account_combo)
        
        # Update UI when transaction type changes
        self.income_radio.toggled.connect(self.update_ui_for_type)
        self.expense_radio.toggled.connect(self.update_ui_for_type)
        self.transfer_radio.toggled.connect(self.update_ui_for_type)
        self.update_ui_for_type()
        
        # Description
        description_label = QLabel('Description (optional):')
        main_layout.addWidget(description_label)
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText('Enter description')
        main_layout.addWidget(self.description_input)
        
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
        
        main_layout.addLayout(button_layout)
        main_layout.addStretch()

    def update_balance_display(self):
        """Update the balance display with current account balances"""
        balances = self.budget_app.get_balance_summary()
        
        balance_text = ""
        total = 0.0
        for account, balance in balances.items():
            balance_text += f"{account:20s}: ${balance:>10.2f}\n"
            total += balance
        
        balance_text += "-" * 35 + "\n"
        balance_text += f"{'Total':20s}: ${total:>10.2f}"
        
        self.balance_display.setText(balance_text)

    def update_ui_for_type(self):
        is_transfer = self.transfer_radio.isChecked()
        
        # Show/hide category for transfers
        self.category_label.setVisible(not is_transfer)
        self.category_combo.setVisible(not is_transfer)
        
        # Show/hide to_account for transfers
        self.to_account_label.setVisible(is_transfer)
        self.to_account_combo.setVisible(is_transfer)
        
        # Update categories
        if not is_transfer:
            self.category_combo.clear()
            if self.income_radio.isChecked():
                self.category_combo.addItems(self.budget_app.income_categories)
            else:
                self.category_combo.addItems(self.budget_app.expense_categories)

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
        
        # Get values based on transaction type
        if self.transfer_radio.isChecked():
            trans_type = 'transfer'
            category = 'Transfer'
            account = self.account_combo.currentText()
            to_account = self.to_account_combo.currentText()
            
            if account == to_account:
                self.show_status('Cannot transfer to the same account', error=True)
                return
        else:
            trans_type = 'income' if self.income_radio.isChecked() else 'expense'
            category = self.category_combo.currentText()
            account = self.account_combo.currentText()
            to_account = None
        
        description = self.description_input.text()
        
        # Add to database
        success = self.budget_app.add_transaction(trans_type, amount, category, account, description, to_account)
        
        if success:
            self.show_status('Transaction added successfully! ✓')
            # Clear form
            self.amount_input.clear()
            self.description_input.clear()
            self.category_combo.setCurrentIndex(0)
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
        
        # Clear after 3 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.status_label.setText(''))

    def view_transactions(self):
        """Open the transactions dialog as a non-modal window"""
        try:
            # Check if dialog already exists and is visible
            if hasattr(self, 'transactions_dialog') and self.transactions_dialog is not None:
                try:
                    if self.transactions_dialog.isVisible():
                        print("Dialog already open, bringing to front...")
                        self.transactions_dialog.raise_()
                        self.transactions_dialog.activateWindow()
                        return
                except:
                    pass
            
            print("Creating TransactionsDialog...")
            dialog = TransactionsDialog(self.budget_app, self)
            print("Dialog created successfully")
            
            # Keep a reference to prevent garbage collection
            self.transactions_dialog = dialog
            
            print("Calling dialog.show()...")
            # Use show() instead of exec() - non-modal approach
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            print("Dialog.show() completed - Dialog should now be visible!")
            
        except Exception as e:
            print("\n" + "="*60)
            print("ERROR IN view_transactions:")
            print("="*60)
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print("="*60)
            QMessageBox.critical(self, 'Error', f'Error opening transactions view:\n{str(e)}')
            self.show_status('Error opening transactions view', error=True)

def main():
    # Catch any uncaught exceptions
    def exception_hook(exctype, value, tb):
        print("\n" + "="*60)
        print("UNCAUGHT EXCEPTION - APP CRASHED:")
        print("="*60)
        print(f"Type: {exctype.__name__}")
        print(f"Value: {value}")
        print("\nTraceback:")
        import traceback
        traceback.print_tb(tb)
        print("="*60)
    
    sys.excepthook = exception_hook
    
    try:
        app = QApplication(sys.argv)
        window = BudgetTrackerWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print("\n" + "="*60)
        print("EXCEPTION IN MAIN:")
        print("="*60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("="*60)

if __name__ == '__main__':
    main()