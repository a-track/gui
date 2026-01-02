from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QWidget, QCheckBox, QMessageBox,
                             QFrame)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import datetime


from delegates import ComboBoxDelegate, DateDelegate
import datetime
from excel_filter import ExcelHeaderView
from transactions_dialog import NumericTableWidgetItem
from custom_widgets import NoScrollComboBox
from utils import format_currency


class AccountPerspectiveDialog(QDialog):

    def __init__(self, budget_app, parent=None):
        super().__init__(parent)

        self.budget_app = budget_app
        self.parent_window = parent
        self.selected_account_id = None
        self.all_transactions_for_account = []
        self.filtered_transactions = []
        self.running_balance_history = {}
        self.transaction_history_map = {}

        self.setWindowTitle('Account Perspective')
        self.setMinimumSize(1200, 600)

        layout = QVBoxLayout()

        main_header = QHBoxLayout()
        main_header.setContentsMargins(0, 0, 0, 10)

        filter_widget = QWidget()
        filter_widget.setStyleSheet(
            ".QWidget { background-color: #f5f5f5; border-radius: 6px; border: 1px solid #e0e0e0; }")
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(10, 5, 10, 5)

        lbl_acc = QLabel('Account:')
        lbl_acc.setStyleSheet("font-weight: bold; color: #333;")
        filter_layout.addWidget(lbl_acc)

        self.account_combo = NoScrollComboBox()
        self.account_combo.setMinimumWidth(250)
        self.populate_accounts_combo()
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        filter_layout.addWidget(self.account_combo)

        filter_layout.addSpacing(15)

        filter_layout.addWidget(QLabel('Year:'))
        self.year_combo = NoScrollComboBox()
        self.year_combo.setFixedWidth(80)
        self.populate_years()
        self.year_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.year_combo)

        filter_layout.addWidget(QLabel('Month:'))
        self.month_combo = NoScrollComboBox()
        self.month_combo.setFixedWidth(100)
        self.populate_months()
        self.month_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.month_combo)

        filter_layout.addSpacing(15)

        self.show_all_dates_checkbox = QCheckBox("Show All Dates")
        self.show_all_dates_checkbox.setChecked(False)
        self.show_all_dates_checkbox.toggled.connect(
            self.on_show_all_dates_toggled)
        filter_layout.addWidget(self.show_all_dates_checkbox)

        main_header.addWidget(filter_widget)

        main_header.addStretch()

        balance_widget = QWidget()
        balance_widget.setStyleSheet("""
            .QWidget {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
        """)
        balance_layout = QHBoxLayout(balance_widget)
        balance_layout.setContentsMargins(15, 5, 15, 5)
        balance_layout.setSpacing(20)

        p_layout = QVBoxLayout()
        p_lbl = QLabel("Period End")
        p_lbl.setStyleSheet(
            "color: #666; font-size: 11px; text-transform: uppercase;")
        p_layout.addWidget(p_lbl)

        self.period_balance_label = QLabel("0.00")
        self.period_balance_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #333;")
        p_layout.addWidget(self.period_balance_label)
        balance_layout.addLayout(p_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #e0e0e0;")
        balance_layout.addWidget(line)

        t_layout = QVBoxLayout()
        t_lbl = QLabel("Total Balance")
        t_lbl.setStyleSheet(
            "color: #666; font-size: 11px; text-transform: uppercase;")
        t_layout.addWidget(t_lbl)

        self.current_balance_label = QLabel("0.00")
        self.current_balance_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #2e7d32;")
        t_layout.addWidget(self.current_balance_label)
        balance_layout.addLayout(t_layout)

        main_header.addWidget(balance_widget)

        layout.addLayout(main_header)

        button_layout = QHBoxLayout()

        self.confirm_all_button = QPushButton(
            'Confirm All Visible Transactions')
        self.confirm_all_button.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        ''')
        self.confirm_all_button.clicked.connect(self.confirm_all_visible)
        self.confirm_all_button.setEnabled(False)
        button_layout.addWidget(self.confirm_all_button)
        


        self.all_confirmed_label = QLabel('✓ All transactions confirmed')
        self.all_confirmed_label.setStyleSheet('''
            QLabel {
                color: #4CAF50;
                font-weight: bold;
                padding: 8px 16px;
                background-color: #f0f9f0;
                border: 1px solid #4CAF50;
                border-radius: 4px;
            }
        ''')
        self.all_confirmed_label.setVisible(False)
        button_layout.addWidget(self.all_confirmed_label)

        button_layout.addStretch()

        button_layout.addStretch()

        self.reset_filters_btn = QPushButton("Reset Filters")
        self.reset_filters_btn.clicked.connect(self.reset_filters)
        self.reset_filters_btn.setStyleSheet("padding: 8px 16px;")
        button_layout.addWidget(self.reset_filters_btn)

        layout.addLayout(button_layout)

        info_label = QLabel(
            'Showing all transactions where this account is involved. Click checkbox to confirm transaction.')
        info_label.setStyleSheet(
            'color: #666; font-style: italic; padding: 5px; background-color: #f0f0f0;')
        layout.addWidget(info_label)

        self.table = QTableWidget()

        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Category', 'Payee',
            'Other Account', 'Notes', 'Transaction Amount', 'Running Balance',
            'Confirmed', 'Delete'
        ])

        self.header_view = ExcelHeaderView(self.table)
        self.table.setHorizontalHeader(self.header_view)

        self.table.verticalHeader().setVisible(False)

        self.header_view.set_column_types({
            0: 'date',
            6: 'number',
            7: 'number'
        })

        self.header_view.set_filter_enabled(7, False)
        self.header_view.set_filter_enabled(8, False)
        self.header_view.set_filter_enabled(9, False)

        header_tooltips = [
            "Transaction Date",
            "Type (Income/Expense/Transfer)",
            "Budget Category",
            "Payer/Payee",
            "Transaction Date",
            "Type (Income/Expense/Transfer)",
            "Budget Category",
            "Payer/Payee",
            "Counterparty Account (for Transfers)",
            "Additional Notes",
            "Amount affecting this account",
            "Account Balance after this transaction",
            "Verify this transaction against your real bank statement.\n(Optional - for your own tracking)",
            "Delete Transaction"
        ]
        for col, tooltip in enumerate(header_tooltips):
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tooltip)

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)

        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                font-size: 9pt;
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
                font-size: 9pt;
            }
        """)

        self.table.verticalHeader().hide()

        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 150)
        self.table.setColumnWidth(8, 80)
        self.table.setColumnWidth(9, 70)

        header = self.table.horizontalHeader()
        content_columns = [1, 2, 3, 5, 6, 7]
        for col in content_columns:
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.Interactive)

        fixed_columns = [0, 4, 8, 9]
        for col in fixed_columns:
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.Interactive)

        self.table.verticalHeader().setDefaultSectionSize(35)

        self.date_delegate = DateDelegate(self.table)
        self.table.setItemDelegateForColumn(0, self.date_delegate)

        self.category_delegate = ComboBoxDelegate(
            self.table, self.get_category_options)
        self.table.setItemDelegateForColumn(2, self.category_delegate)

        layout.addWidget(self.table)

        self.status_label = QLabel('Select an account to view transactions')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        self.set_current_month_year()

        if self.account_combo.count() > 0:
            self.account_combo.setCurrentIndex(0)
            self.on_account_changed(0)

    def populate_accounts_combo(self):
        try:
            accounts = self.budget_app.get_all_accounts()
            all_transactions = self.budget_app.get_all_transactions()

            account_transaction_count = {}
            for account in accounts:
                if account.id == 0:
                    continue
                count = 0
                for trans in all_transactions:
                    if (trans.account_id == account.id or
                            trans.to_account_id == account.id):
                        count += 1
                account_transaction_count[account.id] = count

            filtered_accounts = [acc for acc in accounts if acc.id !=
                                 0 and account_transaction_count.get(acc.id, 0) > 0]
            sorted_accounts = sorted(filtered_accounts,
                                     key=lambda x: account_transaction_count.get(
                                         x.id, 0),
                                     reverse=True)

            for account in sorted_accounts:
                transaction_count = account_transaction_count.get(
                    account.id, 0)
                display_text = f"{account.account} {account.currency} ({transaction_count})"
                self.account_combo.addItem(display_text, account.id)

        except Exception as e:
            print(f"Error populating accounts combo: {e}")
            accounts = self.budget_app.get_all_accounts()
            filtered_accounts = [acc for acc in accounts if acc.id != 0]
            for account in filtered_accounts:
                display_text = f"{account.account} {account.currency}"
                self.account_combo.addItem(display_text, account.id)

    def populate_years(self):
        current_year = datetime.datetime.now().year
        years = list(range(current_year - 5, current_year + 2))
        self.year_combo.addItems([str(year) for year in years])

    def populate_months(self):

        self.month_combo.addItem('All')
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        self.month_combo.addItems(months)

    def set_current_month_year(self):
        now = datetime.datetime.now()
        current_year = str(now.year)

        index = self.year_combo.findText(current_year)
        if index >= 0:
            self.year_combo.setCurrentIndex(index)

        self.month_combo.setCurrentIndex(0)

    # Removed format_swiss_number, using utils.format_currency instead

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

    def load_account_data(self):
        if not self.selected_account_id:
            return

        try:
            account_id = self.selected_account_id
            
            # Optimized fetch with SQL window functions
            self.all_transactions_for_account, self.running_balance_history = \
                self.budget_app.get_account_transactions_with_balance(account_id)

            self.apply_filters()

        except Exception as e:
            print(f"Error loading account data: {e}")
            import traceback
            traceback.print_exc()
            self.show_status('Error loading account data', error=True)

    def on_show_all_dates_toggled(self, checked):
        self.year_combo.setEnabled(not checked)
        self.month_combo.setEnabled(not checked)
        self.apply_filters()

    def apply_filters(self):
        if not self.selected_account_id or not self.all_transactions_for_account:
            return

        show_all_dates = self.show_all_dates_checkbox.isChecked()
        selected_year = int(self.year_combo.currentText())
        selected_month_text = self.month_combo.currentText()

        transactions_to_display = []

        if show_all_dates:

            for trans in self.all_transactions_for_account:

                if hasattr(trans, 'date') and trans.date:
                    transactions_to_display.append(trans)
            filter_info = "All Dates"

        elif selected_month_text == 'All':
            for trans in self.all_transactions_for_account:
                try:
                    if hasattr(trans, 'date') and trans.date:
                        trans_date = trans.date
                        if isinstance(trans_date, str):
                            trans_date = datetime.datetime.strptime(
                                trans_date, '%Y-%m-%d').date()

                        if trans_date.year == selected_year:
                            transactions_to_display.append(trans)
                except (ValueError, AttributeError) as e:
                    continue
            filter_info = f"All months {selected_year}"
        else:
            selected_month = self.month_combo.currentIndex()
            for trans in self.all_transactions_for_account:
                try:
                    if hasattr(trans, 'date') and trans.date:
                        trans_date = trans.date
                        if isinstance(trans_date, str):
                            trans_date = datetime.datetime.strptime(
                                trans_date, '%Y-%m-%d').date()

                        if trans_date.year == selected_year and trans_date.month == selected_month:
                            transactions_to_display.append(trans)
                except (ValueError, AttributeError) as e:
                    continue

            filter_info = f"{selected_month_text} {selected_year}"

        transactions_to_display = sorted(
            transactions_to_display, key=lambda x: (x.date, x.id), reverse=True)

        transaction_history = []

        accounts = self.budget_app.get_all_accounts(show_inactive=True)
        accounts_map = {acc.id: f'{acc.account}' for acc in accounts}

        for trans in transactions_to_display:

            if not (trans.date and str(trans.date).strip() and
                    trans.type and str(trans.type).strip() and
                    trans.amount is not None):
                continue

            running_balance = self.running_balance_history.get(trans.id, 0.0)

            if trans.type == 'income' and trans.account_id == self.selected_account_id:
                transaction_amount = float(trans.amount or 0)
                effect = "+"
                other_account = ""

            elif trans.type == 'expense' and trans.account_id == self.selected_account_id:
                transaction_amount = float(trans.amount or 0)
                effect = "-"
                other_account = ""

            elif trans.type == 'transfer':
                if trans.account_id == self.selected_account_id:
                    transaction_amount = float(trans.amount or 0)
                    effect = "-"
                    other_account = accounts_map.get(trans.to_account_id, "")
                elif trans.to_account_id == self.selected_account_id:
                    transaction_amount = float(trans.to_amount or 0)
                    effect = "+"
                    other_account = accounts_map.get(trans.account_id, "")
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

        total_balance = 0.0
        if self.running_balance_history:
            last_transaction_id = list(self.running_balance_history.keys())[-1]
            total_balance = self.running_balance_history[last_transaction_id]

        period_end_balance = 0.0
        if transaction_history:

            period_end_balance = transaction_history[0]['running_balance']
        else:

            if selected_month_text == 'All':
                period_end_date = datetime.date(selected_year, 12, 31)
            else:
                selected_month = self.month_combo.currentIndex()
                next_month = datetime.date(
                    selected_year + 1, 1, 1) if selected_month == 12 else datetime.date(selected_year, selected_month + 1, 1)
                period_end_date = next_month - datetime.timedelta(days=1)

            candidates = []
            for t in self.all_transactions_for_account:

                if not (t.date and t.type and t.amount is not None):
                    continue

                t_date = t.date
                if isinstance(t_date, str):
                    try:
                        t_date = datetime.datetime.strptime(
                            t_date, '%Y-%m-%d').date()
                    except:
                        continue
                if t_date <= period_end_date:
                    candidates.append(t)

            if candidates:
                candidates.sort(key=lambda x: (x.date, x.id), reverse=True)
                period_end_balance = self.running_balance_history.get(
                    candidates[0].id, 0.0)

        currency = self.get_current_account_currency()

        total_color = '#4CAF50' if total_balance >= 0 else '#f44336'
        period_color = '#2e7d32' if period_end_balance >= 0 else '#c62828'

        if currency:
            total_val = f"{currency} {format_currency(total_balance)}"
            period_val = f"{currency} {format_currency(period_end_balance)}"
        else:
            total_val = format_currency(total_balance)
            period_val = format_currency(period_end_balance)

        self.current_balance_label.setText(f'Total Balance: {total_val}')
        self.current_balance_label.setStyleSheet(
            f'font-weight: bold; font-size: 14px; color: {total_color};')

        self.period_balance_label.setText(f'Period Balance: {period_val}')
        self.period_balance_label.setStyleSheet(
            f'font-weight: bold; font-size: 14px; color: {period_color};')

        account_name = self.account_combo.currentText().split(' (')[0]
        self.show_status(
            f'Showing {len(transaction_history)} transactions for {account_name} ({filter_info})')
        self.update_confirm_all_button_state()

    def get_category_options(self):
        categories = self.budget_app.get_all_categories()
        return sorted([c.sub_category for c in categories])

    def on_cell_changed(self, row, column):
        try:
            item = self.table.item(row, column)
            if not item:
                return

            if row not in self.transaction_history_map:
                return

            trans = self.transaction_history_map[row]
            trans_id = trans.id
            new_value = item.text().strip()

            field = None

            if column == 0:
                field = 'date'
                try:
                    datetime.datetime.strptime(new_value, '%Y-%m-%d')
                except ValueError:
                    self.show_status(
                        f'Invalid date format: {new_value}. Use YYYY-MM-DD', error=True)
                    self.revert_cell(row, column, str(trans.date))
                    return

            elif column == 2:
                # Resolve sub_category name to category_id
                categories = self.budget_app.get_all_categories()
                category_match = next((c for c in categories if c.sub_category == new_value), None)
                
                if category_match:
                    field = 'category_id'
                    new_value = category_match.id
                else:
                    self.show_status(f"Category '{new_value}' not found", error=True)
                    self.revert_cell(row, column, trans.sub_category or "")
                    return

            elif column == 3:
                field = 'payee'

            elif column == 5:
                field = 'notes'

            elif column == 6:
                try:

                    clean_value = new_value.replace("'", "").replace(
                        "+", "").replace("CHF", "").strip()
                    amount = float(clean_value)

                    field = 'amount'
                    new_value = abs(amount)

                except ValueError:
                    self.show_status('Invalid amount', error=True)
                    self.revert_cell(row, column, "?")
                    self.refresh_data()
                    return

            if field:
                success = self.budget_app.update_transaction(
                    trans_id, **{field: new_value})
                if success:
                    self.show_status(f'Updated transaction #{trans_id}')
                    self.refresh_data()

                    if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                        self.parent_window.update_balance_display()
                else:
                    self.show_status(
                        f'Error updating transaction #{trans_id}', error=True)
                    self.refresh_data()

        except Exception as e:
            print(f"Error in on_cell_changed: {e}")
            self.show_status('Error updating transaction', error=True)

    def revert_cell(self, row, column, original_value):
        self.table.blockSignals(True)
        self.table.item(row, column).setText(original_value)
        self.table.blockSignals(False)

    def populate_table(self, transaction_history):
        self.transaction_history_map = {}
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        
        try:
            self.table.setRowCount(len(transaction_history))
            
            for row, data in enumerate(transaction_history):
                trans = data['transaction']
                self.transaction_history_map[row] = trans
                transaction_amount = data['transaction_amount']
                effect = data['effect']
                running_balance = data['running_balance']
                other_account = data['other_account']

                # 0: Date
                date_item = QTableWidgetItem(str(trans.date))
                date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, date_item)

                # 1: Type
                type_item = QTableWidgetItem(str(trans.type).capitalize())
                type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, 1, type_item)

                # 2: Category
                cat_item = QTableWidgetItem(trans.sub_category or "")
                # Category typically editable
                cat_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, cat_item)

                # 3: Payee
                payee_item = QTableWidgetItem(trans.payee or "")
                payee_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, payee_item)

                # 4: Other Account
                other_item = QTableWidgetItem(other_account)
                other_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, 4, other_item)

                # 5: Notes
                note_item = QTableWidgetItem(trans.notes or "")
                note_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 5, note_item)

                # 6: Transaction Amount
                amount_str = f"{effect}{format_currency(abs(transaction_amount))}"
                amt_item = NumericTableWidgetItem(amount_str)
                amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if effect == '+':
                    amt_item.setForeground(QColor("#2e7d32")) # Green
                else:
                    amt_item.setForeground(QColor("#c62828")) # Red
                self.table.setItem(row, 6, amt_item)

                # 7: Running Balance
                bal_item = NumericTableWidgetItem(format_currency(running_balance))
                bal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                bal_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, 7, bal_item)

                # 8: Confirmed
                chk_widget = QWidget()
                chk_layout = QHBoxLayout()
                chk_layout.setContentsMargins(0, 0, 0, 0)
                chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chk = QCheckBox()
                chk.setChecked(trans.confirmed)
                chk.setProperty('trans_id', trans.id)
                # Note: on_checkbox_changed expects sender() to be the checkbox
                chk.clicked.connect(self.on_checkbox_changed) 
                chk_layout.addWidget(chk)
                chk_widget.setLayout(chk_layout)
                self.table.setCellWidget(row, 8, chk_widget)

                # 9: Delete
                del_widget = QWidget()
                del_layout = QHBoxLayout()
                del_layout.setContentsMargins(0, 0, 0, 0)
                del_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                del_btn = QPushButton("✕")
                del_btn.setFixedSize(20, 20)
                del_btn.setStyleSheet("""
                    QPushButton { background-color: #ff4444; color: white; border-radius: 10px; font-weight: bold; }
                    QPushButton:hover { background-color: #cc0000; }
                """)
                del_btn.setProperty('trans_id', trans.id)
                del_btn.clicked.connect(self.on_delete_clicked)
                del_layout.addWidget(del_btn)
                del_widget.setLayout(del_layout)
                self.table.setCellWidget(row, 9, del_widget)

            self.table.resizeColumnsToContents()
            self.table.setColumnWidth(0, max(150, self.table.columnWidth(0)))
            self.table.setColumnWidth(4, max(150, self.table.columnWidth(4)))
            self.table.setColumnWidth(8, 80)
            self.table.setColumnWidth(9, 70)

            if transaction_history:
                self.table.scrollToTop()

            total_width = self.table.horizontalHeader().length() + 50
            parent_window = self.window()
            if parent_window:
                min_width = total_width + 100
                if parent_window.width() < min_width:
                    parent_window.resize(min_width, parent_window.height())
        except Exception as e:
            print(f"Error populating table: {e}")
            self.show_status("Error displaying transactions", error=True)
        finally:
            self.table.blockSignals(False)
            self.table.setSortingEnabled(True)
            self.table.setUpdatesEnabled(True)
            self.update_confirm_all_button_state()

    def confirm_all_visible(self):
        try:
            unconfirmed_transactions = []

            for row in range(self.table.rowCount()):
                checkbox_widget = self.table.cellWidget(row, 8)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox and not checkbox.isChecked():
                        trans_id = checkbox.property('trans_id')
                        unconfirmed_transactions.append(trans_id)

            if not unconfirmed_transactions:
                self.show_status(
                    'All visible transactions are already confirmed!')
                return

            reply = QMessageBox.question(
                self,
                'Confirm All Transactions',
                f'Are you sure you want to confirm all {len(unconfirmed_transactions)} unconfirmed transactions?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                confirmed_count = 0
                for trans_id in unconfirmed_transactions:
                    try:
                        self.budget_app.toggle_confirmation(trans_id)
                        confirmed_count += 1
                    except Exception as e:
                        print(f"Error confirming transaction {trans_id}: {e}")

                self.refresh_data()

                if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                    self.parent_window.update_balance_display()

                self.show_status(
                    f'Successfully confirmed {confirmed_count} transactions!')

        except Exception as e:
            print(f"Error in confirm_all_visible: {e}")
            self.show_status('Error confirming transactions!', error=True)

    def on_checkbox_changed(self, state):
        try:
            checkbox = self.sender()
            trans_id = checkbox.property('trans_id')
            self.budget_app.toggle_confirmation(trans_id)
            self.show_status(f'Transaction #{trans_id} confirmation toggled!')

            if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
                self.parent_window.update_balance_display()

            self.update_confirm_all_button_state()

        except Exception as e:
            print(f"Error in on_checkbox_changed: {e}")
            self.show_status('Error updating confirmation!', error=True)

    def update_confirm_all_button_state(self):
        has_unconfirmed = False
        all_confirmed = True

        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 8)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    if not checkbox.isChecked():
                        has_unconfirmed = True
                        all_confirmed = False
                        break

        self.confirm_all_button.setEnabled(
            self.table.rowCount() > 0 and has_unconfirmed)

        self.all_confirmed_label.setVisible(
            self.table.rowCount() > 0 and all_confirmed)

    def reset_filters(self):
        if hasattr(self, 'header_view'):
            self.header_view.clear_filters()

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

                if self.parent_window and hasattr(self.parent_window, 'update_balance_display'):
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
            self.status_label.setStyleSheet(
                'color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')

        QTimer.singleShot(5000, lambda: self.status_label.setText(''))

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
                    if item and search_text in item.text().lower():
                        should_show = True
                        break
            self.table.setRowHidden(row, not should_show)
