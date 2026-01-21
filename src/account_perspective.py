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
from custom_widgets import NoScrollComboBox, CheckableComboBox
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

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 10)

        acc_widget = QWidget()
        acc_widget.setStyleSheet(".QWidget { background-color: #f5f5f5; border-radius: 6px; border: 1px solid #e0e0e0; }")
        acc_layout = QHBoxLayout(acc_widget)
        acc_layout.setContentsMargins(10, 5, 10, 5)
        
        lbl_acc = QLabel('Account:')
        lbl_acc.setStyleSheet("font-weight: bold; color: #333;")
        acc_layout.addWidget(lbl_acc)

        self.account_combo = NoScrollComboBox()
        self.account_combo.setMinimumWidth(250)
        self.populate_accounts_combo()
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        acc_layout.addWidget(self.account_combo)
        
        top_bar.addWidget(acc_widget)
        top_bar.addStretch()

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
        p_lbl.setStyleSheet("color: #666; font-size: 11px; text-transform: uppercase;")
        p_layout.addWidget(p_lbl)

        self.period_balance_label = QLabel("0.00")
        self.period_balance_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        p_layout.addWidget(self.period_balance_label)
        balance_layout.addLayout(p_layout)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.VLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        line1.setStyleSheet("color: #e0e0e0;")
        balance_layout.addWidget(line1)

        ps_layout = QVBoxLayout()
        ps_lbl = QLabel("Period Start")
        ps_lbl.setStyleSheet("color: #666; font-size: 11px; text-transform: uppercase;")
        ps_layout.addWidget(ps_lbl)

        self.period_start_label = QLabel("0.00")
        self.period_start_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        ps_layout.addWidget(self.period_start_label)
        balance_layout.addLayout(ps_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #e0e0e0;")
        balance_layout.addWidget(line)

        t_layout = QVBoxLayout()
        t_lbl = QLabel("Total Balance")
        t_lbl.setStyleSheet("color: #666; font-size: 11px; text-transform: uppercase;")
        t_layout.addWidget(t_lbl)

        self.current_balance_label = QLabel("0.00")
        self.current_balance_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2e7d32;")
        t_layout.addWidget(self.current_balance_label)
        balance_layout.addLayout(t_layout)

        top_bar.addWidget(balance_widget)
        layout.addLayout(top_bar)

        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(0, 0, 0, 10)

        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        filter_layout.addWidget(QLabel('Year:'))
        self.year_combo = NoScrollComboBox()
        self.year_combo.setFixedWidth(80)
        self.populate_years()
        self.year_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.year_combo)

        filter_layout.addSpacing(10)

        filter_layout.addWidget(QLabel('Month:'))
        self.month_combo = CheckableComboBox()
        self.month_combo.setMinimumWidth(120)
        self.populate_months()
        self.month_combo.model().dataChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.month_combo)

        filter_layout.addSpacing(10)

        self.show_all_dates_checkbox = QCheckBox("Show All Dates")
        self.show_all_dates_checkbox.setChecked(False)
        self.show_all_dates_checkbox.toggled.connect(self.on_show_all_dates_toggled)
        filter_layout.addWidget(self.show_all_dates_checkbox)

        action_bar.addWidget(filter_widget)
        action_bar.addStretch()

        self.confirm_all_button = QPushButton('Confirm All Visible Transactions')
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
        action_bar.addWidget(self.confirm_all_button)

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
        action_bar.addWidget(self.all_confirmed_label)

        action_bar.addSpacing(10)

        layout.addLayout(action_bar)

        info_label = QLabel(
            )
        info_label.setStyleSheet(
            )
        layout.addWidget(info_label)

        self.table = QTableWidget()

        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            , 'Type', 'Category', 'Payee',
            , 'Notes', 'Transaction Amount', 'Running Balance',
            , 'Delete'
        ])

        self.header_view = ExcelHeaderView(self.table)
        self.header_view.set_filters_enabled(False)
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
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            
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
        
        self._updating_month_selection = False
        self.month_combo.model().dataChanged.connect(self.on_month_data_changed)

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
                                 0 and account_transaction_count.get(acc.id, 0) > 0 and getattr(acc, 'is_active', True)]
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
            filtered_accounts = [acc for acc in accounts if acc.id != 0 and getattr(acc, 'is_active', True)]
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
            , 'February', 'March', 'April', 'May', 'June',
            , 'August', 'September', 'October', 'November', 'December'
        ]
        self.month_combo.addItems(months)
        
        self.month_combo.update_display_text()

    def set_current_month_year(self):
        now = datetime.datetime.now()
        current_year = str(now.year)

        index = self.year_combo.findText(current_year)
        if index >= 0:
            self.year_combo.setCurrentIndex(index)

        current_month = now.month
        model = self.month_combo.model()
        model.blockSignals(True)
        for i in range(model.rowCount()):
             model.item(i).setCheckState(Qt.CheckState.Unchecked)
        
        if 1 <= current_month < model.rowCount():
             model.item(current_month).setCheckState(Qt.CheckState.Checked)
             
        model.blockSignals(False)
        self.month_combo.update_display_text()

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
            
            self.all_transactions_for_account, self.running_balance_history =                self.budget_app.get_account_transactions_with_balance(account_id)

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

    def on_month_data_changed(self, topLeft, bottomRight, roles=None):
        if self._updating_month_selection:
            return
            
        if roles and Qt.ItemDataRole.CheckStateRole not in roles:
            pass

        model = self.month_combo.model()
        row = topLeft.row()
        item = model.item(row)
        
        self._updating_month_selection = True
        try:
            if row == 0:
                new_state = item.checkState()
                for i in range(1, model.rowCount()):
                    model.item(i).setCheckState(new_state)
            else:
                all_checked = True
                for i in range(1, model.rowCount()):
                    if model.item(i).checkState() != Qt.CheckState.Checked:
                        all_checked = False
                        break
                
                model.item(0).setCheckState(Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked)
        finally:
            self._updating_month_selection = False
            self.month_combo.update_display_text()
            self.apply_filters()

    def apply_filters(self):
        if not self.selected_account_id or not self.all_transactions_for_account:
            return

        show_all_dates = self.show_all_dates_checkbox.isChecked()
        selected_year = int(self.year_combo.currentText())

        transactions_to_display = []

        checked_indices = self.month_combo.get_checked_indices() 
        
        selected_months_0based = [] 
        
        for idx in checked_indices:
            if idx == 0: continue
            selected_months_0based.append(idx - 1)
        
        transactions_to_display = []

        if show_all_dates:
            for trans in self.all_transactions_for_account:
                if hasattr(trans, 'date') and trans.date:
                    transactions_to_display.append(trans)
            filter_info = "All Dates"

        elif len(selected_months_0based) == 12 or not selected_months_0based:
            for trans in self.all_transactions_for_account:
                try:
                    if hasattr(trans, 'date') and trans.date:
                        trans_date = trans.date
                        if isinstance(trans_date, str):
                            trans_date = datetime.datetime.strptime(
                                trans_date, '%Y-%m-%d').date()

                        if trans_date.year == selected_year:
                            transactions_to_display.append(trans)
                except (ValueError, AttributeError):
                    continue
            filter_info = f"All months {selected_year}"
        else:
            selected_month_names = []
            for idx in selected_months_0based:
                 target_month = idx + 1
                 selected_month_names.append(datetime.date(1900, target_month, 1).strftime('%b'))

            filter_info = f"{', '.join(selected_month_names)} {selected_year}"

            for trans in self.all_transactions_for_account:
                try:
                    if hasattr(trans, 'date') and trans.date:
                        trans_date = trans.date
                        if isinstance(trans_date, str):
                            trans_date = datetime.datetime.strptime(
                                trans_date, '%Y-%m-%d').date()

                        if trans_date.year == selected_year:
                             if (trans_date.month - 1) in selected_months_0based:
                                 transactions_to_display.append(trans)
                except (ValueError, AttributeError):
                    continue

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
                : trans,
                : transaction_amount,
                : effect,
                : running_balance,
                : other_account
            })

        self.populate_table(transaction_history)

        total_balance = 0.0
        if self.running_balance_history:
            last_transaction_id = list(self.running_balance_history.keys())[0]
            total_balance = self.running_balance_history[last_transaction_id]

        period_start_date = None
        if not show_all_dates:
             if len(selected_months_0based) == 12 or not selected_months_0based:
                 period_start_date = datetime.date(selected_year, 1, 1)
             elif selected_months_0based:
                 min_idx = min(selected_months_0based)
                 period_start_date = datetime.date(selected_year, min_idx + 1, 1)
        
        period_start_balance = 0.0
        if period_start_date:
            candidates_start = []
            for t in self.all_transactions_for_account:
                 if not (t.date and t.type and t.amount is not None): continue
                 t_date = t.date
                 if isinstance(t_date, str):
                     try: t_date = datetime.datetime.strptime(t_date, '%Y-%m-%d').date()
                     except: continue
                 
                 if t_date < period_start_date:
                     candidates_start.append(t)
            
            if candidates_start:
                candidates_start.sort(key=lambda x: (x.date, x.id), reverse=True)
                period_start_balance = self.running_balance_history.get(candidates_start[0].id, 0.0)

        period_end_balance = 0.0
        if transaction_history:
            period_end_balance = transaction_history[0]['running_balance']
        else:
            if len(selected_months_0based) == 12 or not selected_months_0based:
                period_end_date = datetime.date(selected_year, 12, 31)
            elif selected_months_0based:
                max_idx = max(selected_months_0based)
                next_month = datetime.date(selected_year + 1, 1, 1) if max_idx == 11 else datetime.date(selected_year, max_idx + 2, 1)
                period_end_date = next_month - datetime.timedelta(days=1)
            else:
                 period_end_date = None

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
        start_color = '#333333'
        start_color = '#2e7d32' if period_start_balance >= 0 else '#c62828'

        if currency:
            total_val = f"{currency} {format_currency(total_balance)}"
            period_val = f"{currency} {format_currency(period_end_balance)}"
            start_val = f"{currency} {format_currency(period_start_balance)}"
        else:
            total_val = format_currency(total_balance)
            period_val = format_currency(period_end_balance)
            start_val = format_currency(period_start_balance)

        self.current_balance_label.setText(f'Total Balance: {total_val}')
        self.current_balance_label.setStyleSheet(
            f'font-weight: bold; font-size: 14px; color: {total_color};')

        self.period_balance_label.setText(f'Period End: {period_val}')
        self.period_balance_label.setStyleSheet(
            f'font-weight: bold; font-size: 14px; color: {period_color};')
            
        self.period_start_label.setText(f'Period Start: {start_val}')
        self.period_start_label.setStyleSheet(
            f'font-weight: bold; font-size: 14px; color: {start_color};')

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

            if column == 8:
                return

            trans_id_item = self.table.item(row, 0)
            if not trans_id_item: return
            
            trans_id = trans_id_item.data(Qt.ItemDataRole.UserRole)
            
            if trans_id is None:
                 if row in self.transaction_history_map:
                    trans_id = self.transaction_history_map[row].id
            
            if trans_id is None: return
            
            trans = getattr(self, 'trans_id_map', {}).get(trans_id)
            if not trans:
                trans = next((t for t in self.all_transactions_for_account if t.id == trans_id), None)
            
            if not trans: return

            if hasattr(trans, 'confirmed') and trans.confirmed:
                self.show_status("Cannot edit confirmed transaction", error=True)
                QMessageBox.warning(self, "Transaction Confirmed",
                                    
                                    )
                self.revert_cell(row, column, item.text()) 
                self.refresh_data()
                return

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
                        , "").replace("CHF", "").strip()
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
        self.trans_id_map = {}
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        
        try:
            self.table.setRowCount(len(transaction_history))
            
            for row, data in enumerate(transaction_history):
                trans = data['transaction']
                self.transaction_history_map[row] = trans
                self.trans_id_map[trans.id] = trans
                
                transaction_amount = data['transaction_amount']
                effect = data['effect']
                running_balance = data['running_balance']
                other_account = data['other_account']

                date_item = QTableWidgetItem(str(trans.date))
                date_item.setData(Qt.ItemDataRole.UserRole, trans.id)
                date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, date_item)

                type_item = QTableWidgetItem(str(trans.type).capitalize())
                type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, 1, type_item)

                cat_item = QTableWidgetItem(trans.sub_category or "")
                cat_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, cat_item)

                payee_item = QTableWidgetItem(trans.payee or "")
                payee_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, payee_item)

                other_item = QTableWidgetItem(other_account)
                other_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, 4, other_item)

                note_item = QTableWidgetItem(trans.notes or "")
                note_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 5, note_item)

                amount_str = f"{effect}{format_currency(abs(transaction_amount))}"
                amt_item = NumericTableWidgetItem(amount_str)
                amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if effect == '+':
                    amt_item.setForeground(QColor("#2e7d32"))
                else:
                    amt_item.setForeground(QColor("#c62828"))
                self.table.setItem(row, 6, amt_item)

                bal_item = NumericTableWidgetItem(format_currency(running_balance))
                bal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                bal_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, 7, bal_item)

                chk_widget = QWidget()
                chk_layout = QHBoxLayout()
                chk_layout.setContentsMargins(0, 0, 0, 0)
                chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chk = QCheckBox()
                chk.setChecked(trans.confirmed)
                chk.setProperty('trans_id', trans.id)
                chk.clicked.connect(self.on_checkbox_changed) 
                chk_layout.addWidget(chk)
                chk_widget.setLayout(chk_layout)
                self.table.setCellWidget(row, 8, chk_widget)

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
            
            header = self.table.horizontalHeader()
            for i in range(self.table.columnCount()):
                current_width = header.sectionSize(i)
                header.resizeSection(i, current_width + 25)
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
                    )
                return

            reply = QMessageBox.question(
                self,
                ,
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
            
            if hasattr(self, 'trans_id_map') and trans_id in self.trans_id_map:
                 self.trans_id_map[trans_id].confirmed = checkbox.isChecked()

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

            trans = getattr(self, 'trans_id_map', {}).get(trans_id)
            if not trans:
                 trans = next((t for t in self.all_transactions_for_account if t.id == trans_id), None)
            
            if trans and hasattr(trans, 'confirmed') and trans.confirmed:
                self.show_status("Cannot delete confirmed transaction", error=True)
                QMessageBox.warning(self, "Transaction Confirmed",
                                    
                                    )
                return

            reply = QMessageBox.question(
                self,
                ,
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
                )
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')

        QTimer.singleShot(5000, lambda: self.status_label.setText(''))

    def filter_content(self, text):
        
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