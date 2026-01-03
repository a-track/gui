from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QWidget, QCheckBox, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from excel_filter import ExcelHeaderView, BooleanTableWidgetItem
from transactions_dialog import NumericTableWidgetItem
from custom_widgets import NoScrollComboBox


class AccountsDialog(QDialog):
    def __init__(self, budget_app, parent_window=None):
        super().__init__(parent_window)
        self.budget_app = budget_app
        self.parent_window = parent_window
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle('Manage Accounts')
        self.setMinimumSize(1000, 500)

        layout = QVBoxLayout()

        new_account_layout = QHBoxLayout()

        new_account_layout.addWidget(QLabel('Name:'))
        self.account_name_input = QLineEdit()
        self.account_name_input.setPlaceholderText('Enter name')
        new_account_layout.addWidget(self.account_name_input)

        new_account_layout.addWidget(QLabel('Type:'))
        self.type_input = QLineEdit()
        self.type_input.setPlaceholderText('Enter type')
        new_account_layout.addWidget(self.type_input)

        new_account_layout.addWidget(QLabel('Company:'))
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText('Optional')
        new_account_layout.addWidget(self.company_input)

        new_account_layout.addWidget(QLabel('Cur:'))
        self.currency_input = QLineEdit()
        self.currency_input.setPlaceholderText('XXX')
        self.currency_input.setMaximumWidth(50)
        new_account_layout.addWidget(self.currency_input)

        self.is_investment_checkbox = QCheckBox('Invest?')
        self.is_investment_checkbox.toggled.connect(
            self.toggle_valuation_visibility)
        new_account_layout.addWidget(self.is_investment_checkbox)

        self.valuation_combo = NoScrollComboBox()
        self.valuation_combo.addItems(
            ['Total Value', 'Price/Qty', 'No Valuation'])
        self.valuation_combo.setVisible(False)
        self.valuation_combo.setToolTip("Valuation Strategy")
        new_account_layout.addWidget(self.valuation_combo)

        self.show_in_balance_checkbox = QCheckBox('Show')
        self.show_in_balance_checkbox.setChecked(True)
        self.show_in_balance_checkbox.setToolTip("Show in Balance")
        new_account_layout.addWidget(self.show_in_balance_checkbox)

        self.is_active_checkbox = QCheckBox('Active')
        self.is_active_checkbox.setChecked(True)
        new_account_layout.addWidget(self.is_active_checkbox)

        add_btn = QPushButton('Add')
        add_btn.clicked.connect(self.add_account)
        add_btn.setStyleSheet(
            'background-color: #4CAF50; color: white; padding: 5px 15px;')
        new_account_layout.addWidget(add_btn)

        layout.addLayout(new_account_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Account Name', 'Type', 'Company', 'Cur',
            'Show', 'Active', 'Investment', 'Valuation Method', 'Delete'
        ])

        header_tooltips = [
            "System ID",
            "Account Display Name",
            "Bank, Cash, Investment, etc.",
            "Institution Name",
            "Account Currency",
            "Show in Balance Tab?",
            "If checked, account appears in selection lists when adding transactions.",
            "Is Investment Account?",
            "Method for calculating value (Total Value / Price per Qty)",
            "Delete Account"
        ]
        for col, tooltip in enumerate(header_tooltips):
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tooltip)

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 9pt;
            }
        """)

        self.table.verticalHeader().hide()

        self.header_view = ExcelHeaderView(self.table)
        self.table.setHorizontalHeader(self.header_view)

        self.header_view.set_filter_enabled(9, False)

        self.header_view.set_column_types({
            0: 'number'
        })

        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Interactive)

        layout.addWidget(self.table)

        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        self.load_accounts()

    def toggle_valuation_visibility(self, checked):
        self.valuation_combo.setVisible(checked)

    def load_accounts(self):
        try:
            accounts = self.budget_app.get_all_accounts(show_inactive=True)

            accounts = [
                account for account in accounts
                if account.id != 0 and account.account and account.account.strip()
            ]
            accounts = sorted(accounts, key=lambda x: x.id)
            self.populate_table(accounts)
        except Exception as e:
            self.show_status(f'Error loading accounts: {e}', error=True)

    def populate_table(self, accounts):
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        try:
            self.table.setRowCount(0)

            valid_accounts = [
                a for a in accounts if a.id and a.account and str(a.account).strip()]

            self.table.setRowCount(len(valid_accounts))

            for row, account in enumerate(valid_accounts):
                try:

                    id_item = NumericTableWidgetItem(str(account.id))
                    # Allow editing ID
                    id_item.setFlags(id_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    id_item.setBackground(QColor(240, 240, 240))
                    id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    id_item.setToolTip("Double click to change ID")
                    self.table.setItem(row, 0, id_item)

                    self.table.setItem(row, 1, QTableWidgetItem(account.account))

                    self.table.setItem(row, 2, QTableWidgetItem(account.type))

                    self.table.setItem(
                        row, 3, QTableWidgetItem(account.company or ''))

                    self.table.setItem(row, 4, QTableWidgetItem(account.currency))

                    def create_checkbox_widget(checked, callback_name, prop_name):
                        widget = QWidget()
                        layout = QHBoxLayout()
                        layout.setContentsMargins(0, 0, 0, 0)
                        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        cb = QCheckBox()
                        cb.setChecked(checked)
                        cb.setProperty('account_id', account.id)
                        cb.toggled.connect(getattr(self, callback_name))
                        layout.addWidget(cb)
                        widget.setLayout(layout)
                        return widget

                    self.table.setItem(row, 5, BooleanTableWidgetItem(
                        "Yes" if getattr(account, 'show_in_balance', True) else "No"))
                    self.table.setCellWidget(row, 5, create_checkbox_widget(
                        getattr(account, 'show_in_balance',
                                True), 'toggle_show_in_balance', 'show_in_balance'
                    ))

                    self.table.setItem(row, 6, BooleanTableWidgetItem(
                        "Yes" if getattr(account, 'is_active', True) else "No"))
                    self.table.setCellWidget(row, 6, create_checkbox_widget(
                        getattr(account, 'is_active',
                                True), 'toggle_active', 'is_active'
                    ))

                    invest_widget = QWidget()
                    inv_layout = QHBoxLayout()
                    inv_layout.setContentsMargins(0, 0, 0, 0)
                    inv_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    inv_cb = QCheckBox()
                    inv_cb.setChecked(getattr(account, 'is_investment', False))
                    inv_cb.setProperty('account_id', account.id)

                    inv_cb.toggled.connect(self.toggle_investment)
                    inv_layout.addWidget(inv_cb)
                    invest_widget.setLayout(inv_layout)
                    self.table.setItem(row, 7, BooleanTableWidgetItem(
                        "Yes" if getattr(account, 'is_investment', False) else "No"))
                    self.table.setCellWidget(row, 7, invest_widget)

                    strat_widget = QWidget()
                    strat_layout = QHBoxLayout()
                    strat_layout.setContentsMargins(0, 0, 0, 0)
                    strat_combo = NoScrollComboBox()
                    strat_combo.addItems(
                        ['Total Value', 'Price/Qty', 'No Valuation'])

                    current_strat = getattr(
                        account, 'valuation_strategy', 'Total Value')
                    if not current_strat and getattr(account, 'is_investment', False):
                        current_strat = 'Total Value'
                    elif not current_strat:
                        current_strat = 'Total Value'

                    strat_combo.setCurrentText(current_strat)
                    strat_combo.setProperty('account_id', account.id)
                    strat_combo.currentIndexChanged.connect(
                        self.change_valuation_strategy)

                    strat_combo.setEnabled(
                        getattr(account, 'is_investment', False))

                    strat_layout.addWidget(strat_combo)
                    strat_widget.setLayout(strat_layout)
                    self.table.setItem(row, 8, QTableWidgetItem(current_strat))
                    self.table.setCellWidget(row, 8, strat_widget)

                    action_widget = QWidget()
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                    delete_btn = QPushButton('✕')
                    delete_btn.setFixedSize(20, 20)
                    delete_btn.setStyleSheet('''
                        QPushButton { background-color: #ff4444; color: white; border-radius: 10px; font-weight: bold; }
                        QPushButton:hover { background-color: #cc0000; }
                    ''')
                    delete_btn.setProperty('account_id', account.id)
                    delete_btn.clicked.connect(self.delete_account)

                    action_layout.addWidget(delete_btn)
                    action_widget.setLayout(action_layout)
                    self.table.setCellWidget(row, 9, action_widget)
                except Exception as e:
                    print(f"Error populating account row: {e}")

            self.table.resizeColumnsToContents()
            
            header = self.table.horizontalHeader()
            for i in range(self.table.columnCount()):
                current_width = header.sectionSize(i)
                header.resizeSection(i, current_width + 25)
        finally:
            self.table.blockSignals(False)
            self.table.setSortingEnabled(True)
            self.table.setUpdatesEnabled(True)
        self.show_status(f'Loaded {len(valid_accounts)} accounts')

    def on_cell_changed(self, row, column):
        try:

            if column not in [0, 1, 2, 3, 4]:
                return

            item = self.table.item(row, column)
            if not item:
                return

            # Special handling for ID change (Column 0)
            if column == 0:
                # We need the OLD ID to perform the update.
                # However, since the cell just changed, we can't easily get the old ID from the table directly
                # unless we stored it. But we can infer it if we assume the user didn't change sorting/filtering
                # concurrently.
                # BETTER APPROACH: Use the 'account_id' property we stored on widgtes in this row?
                # Actually, the buttons/checkboxes have the property.
                # Let's try to get it from the checkbox in column 5.
                checkbox_widget = self.table.cellWidget(row, 5)
                if not checkbox_widget:
                    return
                checkbox = checkbox_widget.findChild(QCheckBox)
                if not checkbox:
                    return
                
                old_id = checkbox.property('account_id')
                try:
                    new_id = int(item.text().strip())
                except ValueError:
                    self.show_status("Invalid ID format", error=True)
                except ValueError:
                    self.show_status("Invalid ID format", error=True)
                    QTimer.singleShot(0, self.load_accounts) # Revert
                    return
                
                if old_id == new_id:
                    return

                # Pre-check if ID exists to avoid unnecessary confirmation dialog
                existing_account = self.budget_app.get_account_by_id(new_id)
                if existing_account:
                    self.show_status(f"Account ID {new_id} already exists", error=True)
                    QMessageBox.warning(self, "ID Exists", f"Account ID {new_id} already exists.\nPlease choose a unique ID.")
                    self.show_status(f"Account ID {new_id} already exists", error=True)
                    QMessageBox.warning(self, "ID Exists", f"Account ID {new_id} already exists.\nPlease choose a unique ID.")
                    QTimer.singleShot(0, self.load_accounts) # Revert
                    return

                reply = QMessageBox.question(
                    self, 'Confirm ID Change', 
                    f'Are you sure you want to change Account ID from {old_id} to {new_id}?\n'
                    f'This will update all linked transactions.',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    success, msg = self.budget_app.update_account_id(old_id, new_id)
                    if success:
                        self.show_status(f'ID updated from {old_id} to {new_id}')
                    if success:
                        self.show_status(f'ID updated from {old_id} to {new_id}')
                        # Delay reload to avoid commitData warning since we are in the middle of editing
                        QTimer.singleShot(0, self.load_accounts) 
                        if hasattr(self.parent_window, 'refresh_global_state'):
                            self.parent_window.refresh_global_state()
                    else:
                        self.show_status(f'Error: {msg}', error=True)
                        QTimer.singleShot(0, self.load_accounts) # Revert
                else:
                    QTimer.singleShot(0, self.load_accounts) # Revert
                
                return

            id_item = self.table.item(row, 0)
            if not id_item:
                return

            account_id = int(id_item.text())
            new_value = item.text().strip()

            current_account = self.budget_app.get_account_by_id(account_id)
            if not current_account:
                return

            if column == 1:
                current_account.account = new_value
            elif column == 2:
                current_account.type = new_value
            elif column == 3:
                current_account.company = new_value
            elif column == 4:
                current_account.currency = new_value

            self.save_account_update(current_account)

        except Exception as e:
            self.show_status(f'Error updating account: {e}', error=True)

    def save_account_update(self, account):
        success = self.budget_app.update_account(
            account_id=account.id,
            account=account.account,
            type=account.type,
            company=account.company,
            currency=account.currency,
            is_investment=getattr(account, 'is_investment', False),
            valuation_strategy=getattr(account, 'valuation_strategy', None)
        )
        if success:
            self.show_status('Account updated')
            if hasattr(self.parent_window, 'update_balance_display'):
                self.parent_window.update_balance_display()
            if hasattr(self.parent_window, 'refresh_global_state'):
                self.parent_window.refresh_global_state()
        else:
            self.show_status('Failed to update account', error=True)

    def toggle_show_in_balance(self, checked):
        sender = self.sender()
        if not sender:
            return
        self.budget_app.update_account_show_in_balance(
            sender.property('account_id'), checked)

        index = self.table.indexAt(sender.parentWidget().pos())
        if index.isValid():
            item = self.table.item(index.row(), 5)
            if item:
                item.setData(ExcelHeaderView.FILTER_DATA_ROLE,
                             "Yes" if checked else "No")
                item.setText("")

        self.show_status('Updated show in balance')

        if hasattr(self.parent_window, 'refresh_global_state'):
            self.parent_window.refresh_global_state()

    def toggle_active(self, checked):
        sender = self.sender()
        if not sender:
            return
        self.budget_app.update_account_active(
            sender.property('account_id'), checked)

        index = self.table.indexAt(sender.parentWidget().pos())
        if index.isValid():
            item = self.table.item(index.row(), 6)
            if item:
                item.setData(ExcelHeaderView.FILTER_DATA_ROLE,
                             "Yes" if checked else "No")
                item.setText("")

        self.show_status('Updated active status')

        if hasattr(self.parent_window, 'update_account_combo'):
            self.parent_window.update_account_combo()
            self.parent_window.update_to_account_combo()
        
        if hasattr(self.parent_window, 'refresh_global_state'):
            self.parent_window.refresh_global_state()

    def toggle_investment(self, checked):
        sender = self.sender()
        if not sender:
            return

        account_id = sender.property('account_id')

        index = self.table.indexAt(sender.parentWidget().pos())
        if not index.isValid():
            return
        row = index.row()

        account = self.budget_app.get_account_by_id(account_id)
        if account:
            account.is_investment = checked

            if checked and not account.valuation_strategy:
                account.valuation_strategy = 'Total Value'

            self.save_account_update(account)

            strat_widget = self.table.cellWidget(row, 8)
            if strat_widget:
                combo = strat_widget.findChild(QComboBox)
                if combo:
                    combo.setEnabled(checked)
                    if checked:
                        combo.setCurrentText(account.valuation_strategy)

            item_inv = self.table.item(row, 7)
            if item_inv:
                item_inv.setData(ExcelHeaderView.FILTER_DATA_ROLE,
                                 "Yes" if checked else "No")
                item_inv.setText("")

            item_strat = self.table.item(row, 8)
            if item_strat and checked:
                item_strat.setText(account.valuation_strategy)

    def change_valuation_strategy(self):
        sender = self.sender()
        if not sender:
            return

        account_id = sender.property('account_id')
        new_strat = sender.currentText()

        account = self.budget_app.get_account_by_id(account_id)
        if account:
            account.valuation_strategy = new_strat
            self.save_account_update(account)

            index = self.table.indexAt(sender.parentWidget().pos())
            if index.isValid():
                item = self.table.item(index.row(), 8)
                if item:
                    item.setText(new_strat)

    def add_account(self):
        account_name = self.account_name_input.text().strip()
        account_type = self.type_input.text().strip()
        currency = self.currency_input.text().strip()

        if not account_name or not currency or not account_type:
            self.show_status(
                'Name, Type and Currency are required', error=True)
            return

        company = self.company_input.text().strip() or None
        show_in = self.show_in_balance_checkbox.isChecked()
        is_active = self.is_active_checkbox.isChecked()
        is_invest = self.is_investment_checkbox.isChecked()
        valuation = self.valuation_combo.currentText() if is_invest else None

        success, msg = self.budget_app.add_account(
            account_name, account_type, company, currency,
            show_in, is_active, is_invest, valuation
        )

        if success:
            self.show_status('Account added!')
            self.account_name_input.clear()
            self.type_input.clear()
            self.company_input.clear()
            self.currency_input.clear()
            self.load_accounts()

            if hasattr(self.parent_window, 'update_account_combo'):
                self.parent_window.update_account_combo()
                self.parent_window.update_to_account_combo()
            
            if hasattr(self.parent_window, 'refresh_global_state'):
                self.parent_window.refresh_global_state()
        else:
            self.show_status(f'Error: {msg}', error=True)

    def delete_account(self):
        try:
            account_id = self.sender().property('account_id')
            reply = QMessageBox.question(self, 'Confirm Delete', 'Delete this account?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = self.budget_app.delete_account(account_id)
                if success:
                    self.show_status('Deleted')
                    self.load_accounts()
                    if hasattr(self.parent_window, 'refresh_global_state'):
                        self.parent_window.refresh_global_state()
                else:
                    self.show_status(f'Error: {msg}', error=True)
        except Exception as e:
            self.show_status(f'Error deleting: {e}', error=True)

    def show_status(self, message, error=False):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            'color: #f44336' if error else 'color: #4CAF50')
        QTimer.singleShot(3000, lambda: self.status_label.setText(''))

    def filter_content(self, text):
        """Filter table rows based on text matching."""
        if not hasattr(self, 'table'): return
        
        search_text = text.lower()
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        
        for row in range(rows):
            should_show = False
            if not search_text:
                should_show = True
            else:
                for col in range(cols):
                    item = self.table.item(row, col)
                    # Check standard items
                    if item and search_text in item.text().lower():
                        should_show = True
                        break
                    
                    # Check cell widgets (checkboxes, combos) if needed, or rely on underlying data
                    # For simple search, text check is usually enough if data is in items
            self.table.setRowHidden(row, not should_show)
