"""
Dialog window for viewing and editing all transactions.
UPDATED: For new database schema with accounts, categories, and proper transaction types.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QCheckBox, QHeaderView, QWidget,
                             QComboBox, QLineEdit, QDateEdit)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QFont
from delegates import ComboBoxDelegate


class TransactionsDialog(QDialog):
    """Dialog for viewing and managing all transactions with new schema."""
    
    def __init__(self, budget_app, parent=None):
        try:
            print("  TransactionsDialog.__init__ starting...")
            super().__init__(parent)
            print("  super().__init__ completed")
            
            self.budget_app = budget_app
            self.parent_window = parent
            
            # Simple window flags
            self.setWindowFlags(Qt.WindowType.Window)
            
            self.setWindowTitle('All Transactions')
            self.setMinimumSize(1400, 600)
            
            print("  Creating layout...")
            layout = QVBoxLayout()
            
            # Info label
            info_label = QLabel('Tip: Double-click cells to edit. Click checkbox to confirm transaction.')
            info_label.setStyleSheet('color: #666; font-style: italic; padding: 5px;')
            layout.addWidget(info_label)
            
            # Table
            print("  Creating table...")
            self.table = QTableWidget()
            
            # HIDE ROW NUMBERS
            self.table.verticalHeader().hide()
            
            self.table.setColumnCount(13)  # Reduced from 14 to 13
            self.table.setHorizontalHeaderLabels([
                'ID', 'Date', 'Type', 'Amount', 'From Account', 'Payee', 
                'Sub Category', 'To Account', 'To Amount', 'Qty', 
                'Notes', 'Confirmed', 'Actions'
            ])
            
            # Make columns editable
            self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
            
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
            
            # Set up delegates
            print("  Setting up delegates...")
            self.setup_delegates()
            
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
            
            # Set up resizable columns - CHANGED TO RESIZE TO CONTENTS
            print("  Setting up auto-sized columns...")
            header = self.table.horizontalHeader()
            
            # Set initial resize modes - most columns resize to contents
            self.table.setColumnWidth(0, 50)   # ID - fixed small
            self.table.setColumnWidth(11, 80)  # Confirmed - fixed
            self.table.setColumnWidth(12, 70)  # Actions - fixed
            
            # Make content-based columns resize to contents
            content_based_columns = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            for col in content_based_columns:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            
            # Make fixed columns interactive
            fixed_columns = [0, 11, 12]
            for col in fixed_columns:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            
            # Set row height for better appearance
            self.table.verticalHeader().setDefaultSectionSize(35)
            
            # Allow horizontal scrolling if needed
            self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
            
            layout.addWidget(self.table)
            
            # Status label
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
    
    def setup_delegates(self):
        """Set up delegates for different columns."""
        # Type delegate
        self.type_delegate = ComboBoxDelegate(['income', 'expense', 'transfer'], self)
        self.table.setItemDelegateForColumn(2, self.type_delegate)
    
        # Account delegate - show name + ID, sorted by ID
        accounts = self.budget_app.get_all_accounts()
        # Sort accounts by ID
        accounts_sorted = sorted(accounts, key=lambda x: x.id)
        account_display_names = [f"{acc.account} ({acc.id})" for acc in accounts_sorted]
        self.account_delegate = ComboBoxDelegate(account_display_names, self)
        self.table.setItemDelegateForColumn(4, self.account_delegate)
        self.table.setItemDelegateForColumn(7, self.account_delegate)
    
        # Category delegate
        categories = self.budget_app.get_all_categories()
        sub_category_names = [cat.sub_category for cat in categories]
        self.category_delegate = ComboBoxDelegate(sub_category_names, self)
        self.table.setItemDelegateForColumn(6, self.category_delegate)

    def get_account_id_from_display(self, display_text):
        """Extract account ID from display text like 'Account Name (123)'"""
        import re
        match = re.search(r'\((\d+)\)$', display_text)
        return int(match.group(1)) if match else None

    def get_display_text_by_id(self, account_id):
        """Get display text for account ID"""
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return f"{account.account} {account.currency} ({account.id})"
        return ""

    def get_account_id_by_name(self, account_name):
        """Get account ID by account name."""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.account == account_name:
                return account.id
        return None
    
    def get_account_name_by_id(self, account_id):
        """Get account name by account ID."""
        if account_id is None:
            return ""
        accounts = self.budget_app.get_all_accounts()
        for account in accounts:
            if account.id == account_id:
                return account.account
        return ""
    
    def populate_table(self):
        """Populate the table with transaction data."""
        try:
            print(f"    populate_table: Setting row count to {len(self.transactions)}")
            
            # Block signals to prevent updates during population
            self.table.blockSignals(True)
            
            self.table.setRowCount(len(self.transactions))
            
            print("    populate_table: Starting to populate rows...")
            for row, trans in enumerate(self.transactions):
                print(f"    populate_table: Processing row {row}, transaction ID {trans.id}")
                
                # ID (read-only)
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
                
                # Amount (for income/expense/transfer) - COMBINED COLUMN
                # For income/expense: use amount
                # For transfer: use from_amount
                if trans.type == 'transfer':
                    amount_value = trans.from_amount if trans.from_amount else ""
                else:
                    amount_value = trans.amount if trans.amount else ""
                
                amount_item = QTableWidgetItem(f"{amount_value:.2f}" if amount_value != "" else "")
                if amount_value:
                    amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 3, amount_item)
                
                # From Account (for income/expense/transfer)
                # For transfers, this should be from_account_id
                if trans.type == 'transfer':
                    account_display = self.get_display_text_by_id(trans.from_account_id)
                else:
                    account_display = self.get_display_text_by_id(trans.account_id)
                account_item = QTableWidgetItem(account_display)
                self.table.setItem(row, 4, account_item)
                
                # Payee
                payee_item = QTableWidgetItem(trans.payee or "")
                self.table.setItem(row, 5, payee_item)
                
                # Sub Category (for income/expense)
                sub_category_item = QTableWidgetItem(trans.sub_category or "")
                self.table.setItem(row, 6, sub_category_item)
                
                # To Account (for transfers only)
                to_account_display = self.get_display_text_by_id(trans.to_account_id)
                to_account_item = QTableWidgetItem(to_account_display or "")
                self.table.setItem(row, 7, to_account_item)
                
                # To Amount (for transfers only)
                to_amount = trans.to_amount if trans.to_amount else ""
                to_amount_item = QTableWidgetItem(f"{to_amount:.2f}" if to_amount != "" else "")
                if to_amount:
                    to_amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 8, to_amount_item)
                
                # Qty (for transfers)
                qty_item = QTableWidgetItem(f"{trans.qty:.4f}" if trans.qty else "")
                if trans.qty:
                    qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 9, qty_item)
                
                # Notes
                notes_item = QTableWidgetItem(trans.notes or "")
                self.table.setItem(row, 10, notes_item)
                
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
                self.table.setCellWidget(row, 11, checkbox_widget)
                
                # Action buttons - PROPERLY SIZED Modern X button
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(1, 1, 1, 1)  # Minimal margins
                action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                delete_btn = QPushButton('✕')  # Modern X symbol
                delete_btn.setFixedSize(22, 22)  # Even smaller to ensure no cutting
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
                
                self.table.setCellWidget(row, 12, action_widget)
                
                # Set row background color based on type
                self.color_row_by_type(row, trans.type)
                
                print(f"    populate_table: Row {row} completed")
            
            # Unblock signals
            self.table.blockSignals(False)
            
            # Auto-resize columns to content after population
            self.table.resizeColumnsToContents()
            
            # Set minimum widths for certain columns to prevent them from being too small
            self.table.setColumnWidth(0, max(50, self.table.columnWidth(0)))  # ID
            self.table.setColumnWidth(2, max(80, self.table.columnWidth(2)))  # Type
            self.table.setColumnWidth(3, max(90, self.table.columnWidth(3)))  # Amount
            self.table.setColumnWidth(11, max(80, self.table.columnWidth(11)))  # Confirmed
            self.table.setColumnWidth(12, max(70, self.table.columnWidth(12)))  # Actions
            
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
    
    def close_and_update(self):
        """Close dialog and update parent window balance."""
        if hasattr(self.parent_window, 'update_balance_display'):
            self.parent_window.update_balance_display()
        self.close()
    
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
            import traceback
            traceback.print_exc()
    
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
            import traceback
            traceback.print_exc()
    
    def on_cell_changed(self, row, column):
        """Handle cell edit events."""
        # Ignore if signals are blocked
        if self.table.signalsBlocked():
            return

        try:
            # Get transaction ID
            trans_id = int(self.table.item(row, 0).text())

            # Get current transaction type
            current_type = self.table.item(row, 2).text().lower()

            # Collect all field values
            field_values = {}

            # Common fields
            date = self.table.item(row, 1).text()
            trans_type = self.table.item(row, 2).text().lower()
            notes = self.table.item(row, 10).text()  # Updated column index

            field_values['date'] = date
            field_values['type'] = trans_type
            field_values['notes'] = notes

            # Type-specific fields
            if trans_type == 'income':
                # Validate and get income fields
                try:
                    amount = float(self.table.item(row, 3).text() or 0)
                    if amount <= 0:
                        raise ValueError("Amount must be positive")
                    field_values['amount'] = amount
                except (ValueError, TypeError):
                    self.show_status('Invalid amount for income!', error=True)
                    self.refresh_table()
                    return

                account_display = self.table.item(row, 4).text()
                account_id = self.get_account_id_from_display(account_display)
                if not account_id:
                    self.show_status('Invalid account!', error=True)
                    self.refresh_table()
                    return
                field_values['account_id'] = account_id

                field_values['payee'] = self.table.item(row, 5).text()
                field_values['sub_category'] = self.table.item(row, 6).text()

                # Clear transfer-specific fields
                field_values['from_account_id'] = None
                field_values['to_account_id'] = None
                field_values['from_amount'] = None
                field_values['to_amount'] = None
                field_values['qty'] = None

            elif trans_type == 'expense':
                # Validate and get expense fields
                try:
                    amount = float(self.table.item(row, 3).text() or 0)
                    if amount <= 0:
                        raise ValueError("Amount must be positive")
                    field_values['amount'] = amount
                except (ValueError, TypeError):
                    self.show_status('Invalid amount for expense!', error=True)
                    self.refresh_table()
                    return

                account_display = self.table.item(row, 4).text()
                account_id = self.get_account_id_from_display(account_display)
                if not account_id:
                    self.show_status('Invalid account!', error=True)
                    self.refresh_table()
                    return
                field_values['account_id'] = account_id

                field_values['payee'] = self.table.item(row, 5).text()
                field_values['sub_category'] = self.table.item(row, 6).text()

                # Clear transfer-specific fields
                field_values['from_account_id'] = None
                field_values['to_account_id'] = None
                field_values['from_amount'] = None
                field_values['to_amount'] = None
                field_values['qty'] = None

            elif trans_type == 'transfer':
                # Validate and get transfer fields
                from_account_display = self.table.item(row, 4).text()
                from_account_id = self.get_account_id_from_display(from_account_display)
                if not from_account_id:
                    self.show_status('Invalid from account!', error=True)
                    self.refresh_table()
                    return
                field_values['from_account_id'] = from_account_id

                to_account_display = self.table.item(row, 7).text()
                to_account_id = self.get_account_id_from_display(to_account_display)
                if not to_account_id:
                    self.show_status('Invalid to account!', error=True)
                    self.refresh_table()
                    return
                field_values['to_account_id'] = to_account_id

                if from_account_id == to_account_id:
                    self.show_status('Cannot transfer to the same account!', error=True)
                    self.refresh_table()
                    return

                try:
                    from_amount = float(self.table.item(row, 3).text() or 0)  # Now using column 3
                    if from_amount <= 0:
                        raise ValueError("From amount must be positive")
                    field_values['from_amount'] = from_amount
                except (ValueError, TypeError):
                    self.show_status('Invalid from amount!', error=True)
                    self.refresh_table()
                    return

                try:
                    to_amount_text = self.table.item(row, 8).text()
                    to_amount = float(to_amount_text) if to_amount_text else from_amount
                    if to_amount <= 0:
                        raise ValueError("To amount must be positive")
                    field_values['to_amount'] = to_amount
                except (ValueError, TypeError):
                    self.show_status('Invalid to amount!', error=True)
                    self.refresh_table()
                    return

                try:
                    qty_text = self.table.item(row, 9).text()
                    field_values['qty'] = float(qty_text) if qty_text else None
                except ValueError:
                    self.show_status('Invalid quantity!', error=True)
                    self.refresh_table()
                    return

                # Clear income/expense specific fields
                field_values['amount'] = None
                field_values['account_id'] = None
                field_values['payee'] = None
                field_values['sub_category'] = None
                field_values['invest_account_id'] = None

            # Get confirmed status
            checkbox_widget = self.table.cellWidget(row, 11)  # Updated column index
            checkbox = checkbox_widget.findChild(QCheckBox)
            field_values['confirmed'] = checkbox.isChecked()

            # Update in database
            success = self.budget_app.update_transaction(trans_id, **field_values)

            if success:
                self.show_status('Transaction updated successfully!')

                # If type changed, refresh the row to show/hide appropriate columns
                if column == 2 and current_type != trans_type:
                    self.refresh_table()
                else:
                    # Just update the row color
                    self.color_row_by_type(row, trans_type)

                if hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()
            else:
                self.show_status('Error updating transaction!', error=True)
                self.refresh_table()

        except Exception as e:
            print(f"Error in on_cell_changed: {e}")
            import traceback
            traceback.print_exc()
            self.show_status('Error updating transaction!', error=True)
            self.refresh_table()

    def refresh_table(self):
        """Refresh the table data."""
        self.table.blockSignals(True)
        self.transactions = self.budget_app.get_all_transactions()
        self.populate_table()
        self.table.blockSignals(False)
        self.show_status('Table refreshed!')
    
    def show_status(self, message, error=False):
        """Display a status message."""
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        # Clear after 3 seconds
        QTimer.singleShot(3000, lambda: self.status_label.setText(''))