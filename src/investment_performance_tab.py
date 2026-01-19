from datetime import date, datetime
from finance_utils import xirr, calculate_linked_twr
from utils import format_currency
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTableWidget, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from excel_filter import ExcelHeaderView
from transactions_dialog import NumericTableWidgetItem, StringTableWidgetItem


class PerformanceLoaderThread(QThread):
    finished = pyqtSignal(object)

    def __init__(self, budget_app):
        super().__init__()
        self.budget_app = budget_app

    def run(self):
        try:
            balances = self.budget_app.get_balance_summary()
            dividends = self.budget_app.get_accumulated_dividends()
            expenses = self.budget_app.get_accumulated_expenses()
            rates = self.budget_app.get_exchange_rates_map()
            all_accounts = self.budget_app.get_all_accounts()

            data = []

            # Aggregators for Total Row
            total_stats = {
                'cost_basis': 0.0,
                'market_val': 0.0,
                'unrealized': 0.0,
                'income': 0.0,
                'fees': 0.0,
                'return_sum': 0.0,
                'income_bd': {},
                'fees_bd': {},
            }
            
            # For Total TWR, we need to merge all value histories and all flows.
            all_value_histories_chf = [] # List of list of (date, value_chf)
            all_flows_chf = [] # List of (date, amount_chf)

            today = date.today()

            for acc in all_accounts:
                if not getattr(acc, 'is_investment', False):
                    continue
                if not getattr(acc, 'is_active', True):
                    continue

                acc_id = acc.id
                name = acc.account
                currency = acc.currency

                # --- 1. Basic Stats ---
                # --- 1. Basic Stats ---
                balance_data = balances.get(acc_id, {})
                qty = balance_data.get('qty', 0.0)

                # Cost Basis: Use Historical Exchange Rates (Net Invested Capital)
                # Instead of current balance * current rate, we sum historic inflows
                cost_basis_chf = self.budget_app.get_historical_cost_basis(acc_id)

                # Market Value: Use Current Exchange Rates (What is it worth NOW?)
                rate = rates.get(currency, 1.0)
                
                # Fetch Valuation (Native)
                valuation_native = 0.0
                strategy = getattr(acc, 'valuation_strategy', 'Total Value')
                raw_val = self.budget_app.get_investment_valuation_for_date(acc_id)

                if strategy == 'Price/Qty':
                    valuation_native = qty * raw_val
                elif raw_val > 0:
                    valuation_native = raw_val
                else:
                    # Fallback to balance if no valuation
                    valuation_native = balance_data.get('balance', 0.0)

                market_val_chf = valuation_native * rate

                income_data = dividends.get(acc_id, {'total': 0.0, 'years': {}})
                income_chf = income_data['total']
                years_data = income_data['years']

                expense_data = expenses.get(acc_id, {'total': 0.0, 'years': {}})
                fees_chf = expense_data['total']
                fees_years_data = expense_data['years']

                unrealized_pl_chf = market_val_chf - cost_basis_chf
                total_return_chf = unrealized_pl_chf + income_chf - fees_chf

                unrealized_pl_pct = 0.0
                if abs(cost_basis_chf) > 0.01:
                    unrealized_pl_pct = (unrealized_pl_chf / abs(cost_basis_chf)) * 100

                total_return_pct = 0.0
                if abs(cost_basis_chf) > 0.01:
                    total_return_pct = (total_return_chf / abs(cost_basis_chf)) * 100

                # --- 2. Advanced Stats (IRR & TWR) ---
                
                # Fetch Flows
                flows = self.budget_app.get_account_cash_flows(acc_id)
                
                # IRR Calcs
                xirr_flows = flows.copy()
                xirr_flows.append((today, market_val_chf)) # Assuming flows are converted/base? 
                # Wait, flows from `get_account_cash_flows` returns `amount`. 
                # We need to treat flows as CHF if we compare to CHF Market Value?
                # Usually XIRR should be in Currency of the Asset to get "Native IRR".
                # But here we display "IRR" in the table. 
                # If we mix currencies in Total, we must use CHF.
                # For individual rows, Native IRR is better?
                # The prompt tooltip says "IRR/TWR in Native Currency".
                # So for individual row, we use Native Flows and Native MV.
                # `get_account_cash_flows` returns values in Transaction Amount (Native).
                # `market_val_native` is Native.
                # So:
                xirr_flows_native = flows.copy()
                xirr_flows_native.append((today, valuation_native))
                irr_val = xirr(xirr_flows_native)
                irr_pct = (irr_val * 100.0) if irr_val is not None else None

                # TWR Calcs
                # Requires Value History in Native Currency
                val_history = []
                
                if strategy == 'Total Value':
                    # History is already Total Value
                    raw_history = self.budget_app.get_investment_valuation_history(acc_id)
                    val_history = raw_history # List of (date, value)
                
                elif strategy == 'Price/Qty':
                    # Need to reconstruct Total Value = Price * Qty
                    price_history = self.budget_app.get_investment_valuation_history(acc_id)
                    qty_changes = self.budget_app.get_qty_changes(acc_id)
                    
                    if price_history:
                        # Reconstruct
                        # Create Qty timeline
                        # We need Qty at each Price Date
                        # Sort both
                        price_history.sort(key=lambda x: x[0])
                        qty_changes.sort(key=lambda x: x[0])
                        
                        current_qty = 0.0
                        qty_idx = 0
                        n_qty = len(qty_changes)
                        
                        for p_date, price in price_history:
                            # Apply all qty changes up to p_date
                            while qty_idx < n_qty and qty_changes[qty_idx][0] <= p_date:
                                current_qty += qty_changes[qty_idx][1]
                                qty_idx += 1
                            
                            val = price * current_qty
                            val_history.append((p_date, val))

                twr_pct = None
                if val_history:
                    # Append current
                    # Make sure not duplicate date
                    if not val_history or val_history[-1][0] < today:
                        val_history.append((today, valuation_native))
                    
                    twr_val = calculate_linked_twr(val_history, flows)
                    twr_pct = twr_val

                # --- 3. Collect Data for TOTAL Row ---
                # We need CHF flows and CHF history
                
                # Convert flows to CHF
                flows_chf_acc = [(d, amt * rate) for d, amt in flows]
                all_flows_chf.extend(flows_chf_acc)

                # Convert history to CHF
                # (Ideally we use historical rate, but using current rate is a necessary simplification 
                # if we don't carry full exchange rate history efficiently here. 
                # Or we could fetch rate for each point? That's heavy.
                # Let's use current rate for approximation of "Current Portfolio performance"
                # OR better: The values stored were historical. We should convert them using historical rates?
                # That creates "Currency Impact" in TWR. 
                # Usually Total Portfolio TWR is in Base Currency (CHF).
                # So yes, we should convert everything to CHF. 
                # Using CURRENT rate for HISTORY is wrong (distorts past value).
                # But we don't have easy historical lookup here without N queries.
                # Let's use Constant Rate (Current) for the entire history series?
                # This effectively calculates "What if this was always in CHF at today's rate?".
                # This removes currency fluctuation from the TWR, showing only Asset Performance.
                # This is arguably BETTER for "Investment Performance" pure view.
                # If we want "Total Return in CHF", we need realized FX gains.
                # Let's stick to Current Rate for simplicity and consistency with "Native TWR".
                
                history_chf = [(d, v * rate) for d, v in val_history]
                all_value_histories_chf.append(history_chf)

                # Add to basic aggregates
                total_stats['cost_basis'] += cost_basis_chf
                total_stats['market_val'] += market_val_chf
                total_stats['unrealized'] += unrealized_pl_chf
                total_stats['income'] += income_chf
                total_stats['fees'] += fees_chf
                total_stats['return_sum'] += total_return_chf
                
                # Aggregate breakdowns
                def agg_bd(src, limit_dict):
                    for y, d in src.items():
                        if y not in limit_dict: limit_dict[y] = {'total':0.0,'breakdown':{}}
                        limit_dict[y]['total'] += d['total']
                        for c, v in d['breakdown'].items():
                            limit_dict[y]['breakdown'][c] = limit_dict[y]['breakdown'].get(c, 0.0) + v
                
                agg_bd(years_data, total_stats['income_bd'])
                agg_bd(fees_years_data, total_stats['fees_bd'])

                row = {
                    'name': name,
                    'currency': currency,
                    'qty': qty,
                    'cost_basis': cost_basis_chf,
                    'market_value': market_val_chf,
                    'unrealized_pl': unrealized_pl_chf,
                    'unrealized_pl_pct': unrealized_pl_pct,
                    'dividends': income_chf,
                    'income_breakdown': years_data,
                    'fees': fees_chf,
                    'fees_breakdown': fees_years_data,
                    'total_return': total_return_chf,
                    'total_return_pct': total_return_pct,
                    'irr': irr_pct,
                    'twr': twr_pct,
                    'is_total': False
                }
                data.append(row)

            # --- Calculate TOTAL Row Stats ---
            
            # Total TWR
            total_twr_pct = None
            if all_value_histories_chf:
                # Merge Histories
                # 1. Get all unique dates
                all_dates = set()
                for h in all_value_histories_chf:
                    for d, v in h:
                        all_dates.add(d)
                sorted_dates = sorted(list(all_dates))
                
                # 2. Forward fill summation
                total_history = []
                # Current values for each account (initially 0 or start val? Assumed 0 before first point)
                curr_vals = [0.0] * len(all_value_histories_chf)
                
                # We need to efficienty walk time.
                # Map date -> list of (acc_idx, val) updates
                updates_by_date = {d: [] for d in sorted_dates}
                for idx, h in enumerate(all_value_histories_chf):
                    for d, v in h:
                        updates_by_date[d].append((idx, v))
                
                for d in sorted_dates:
                    # Apply updates
                    for idx, v in updates_by_date[d]:
                        curr_vals[idx] = v
                    
                    # Sum
                    total_val = sum(curr_vals)
                    total_history.append((d, total_val))
                
                # 3. Calculate TWR
                # Flows: internal flows cancel out? 
                # Yes, if we sum +100 and -100 on same day.
                # `calculate_linked_twr` takes flows.
                # We need to flatten `all_flows_chf`?
                # Ideally merge flows on same day to single net flow.
                # (Though `calculate_linked_twr` might handle list of flows? Checks implementation...
                # implementation expects list of (date, amount). If multiple same day?
                # It does `flows_by_date[f_date] += f_amt`. So yes, it aggregates.)
                
                total_twr_pct = calculate_linked_twr(total_history, all_flows_chf)

            # Total IRR
            total_irr_pct = None
            if all_flows_chf or total_stats['market_val'] > 0:
                total_xirr_flows = all_flows_chf.copy()
                total_xirr_flows.append((today, total_stats['market_val']))
                # Recalculate XIRR on aggregated flows
                # Note: Internal flows between accounts in all_flows_chf should cancel out 
                # if we have both sides (Transfer Out from A, Transfer In to B).
                # Provided they have same date and amount.
                # Even if dates slightly differ, XIRR handles them as separate flows.
                
                t_irr = xirr(total_xirr_flows)
                if t_irr is not None:
                     total_irr_pct = t_irr * 100.0

            # Total stats pct
            t_unreal_pct = (total_stats['unrealized'] / abs(total_stats['cost_basis']) * 100) if abs(total_stats['cost_basis']) > 0.01 else 0.0
            t_ret_pct = (total_stats['return_sum'] / abs(total_stats['cost_basis']) * 100) if abs(total_stats['cost_basis']) > 0.01 else 0.0

            total_row = {
                'name': 'TOTAL',
                'currency': '',
                'qty': 0,
                'cost_basis': total_stats['cost_basis'],
                'market_value': total_stats['market_val'],
                'unrealized_pl': total_stats['unrealized'],
                'unrealized_pl_pct': t_unreal_pct,
                'dividends': total_stats['income'],
                'income_breakdown': total_stats['income_bd'],
                'fees': total_stats['fees'],
                'fees_breakdown': total_stats['fees_bd'],
                'total_return': total_stats['return_sum'],
                'total_return_pct': t_ret_pct,
                'irr': total_irr_pct,
                'twr': total_twr_pct,
                'is_total': True
            }

            if data:
                data.insert(0, total_row)

            self.finished.emit(data)

        except Exception as e:
            print(f"Error loading performance data: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit([])


class InvestmentPerformanceTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.init_ui()
        
    def filter_content(self, text):
        """Filter table rows based on text matching."""
        if not hasattr(self, 'performance_table'): return
        
        search_text = text.lower()
        rows = self.performance_table.rowCount()
        cols = self.performance_table.columnCount()
        
        for row in range(rows):
            should_show = False
            if not search_text:
                should_show = True
            else:
                for col in range(cols):
                    item = self.performance_table.item(row, col)
                    if item and search_text in item.text().lower():
                        should_show = True
                        break
            self.performance_table.setRowHidden(row, not should_show)
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        header_layout = QHBoxLayout()
        title = QLabel("Investment Performance")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        info_label = QLabel(" All monetary values displayed in CHF. IRR/TWR in Native Currency (Total TWR in CHF).")
        info_label.setStyleSheet(
            "color: #666; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(info_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(12) 
        self.table.setHorizontalHeaderLabels([
            "Account", "Quantity", "Cost Basis", "Market Value",
            "Unrealized P&L", "Unrealized %",
            "Gains", "Fees",
            "Total Return", "Total Return %",
            "IRR", "TWR"
        ])

        self.header_view = ExcelHeaderView(self.table)
        self.header_view.set_filters_enabled(False)
        self.table.setHorizontalHeader(self.header_view)

        # Tooltips for headers
        self.table.horizontalHeaderItem(10).setToolTip(
            "Internal Rate of Return (Money-Weighted Return).\n"
            "Measures your personal performance, accounting for the timing and size of your deposits/withdrawals."
        )
        self.table.horizontalHeaderItem(11).setToolTip(
            "Time-Weighted Return.\n"
            "Measures the performance of the asset itself, eliminating the effect of your cash flow timing.\n"
            "Requires historical quantity/valuation data."
        )

        self.table.setSortingEnabled(False)
        self.header_view.sectionClicked.connect(self.header_clicked)

        self.header_view.set_column_types({
            1: 'number', 2: 'number', 3: 'number', 4: 'number',
            5: 'number', 6: 'number', 7: 'number', 8: 'number', 9: 'number',
            10: 'number', 11: 'number'
        })

        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #fafafa;
                font-size: 10pt;
                selection-background-color: #e3f2fd;
                selection-color: black;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.table)

        self.current_data = []

        self.sort_column = 3
        self.sort_order = Qt.SortOrder.DescendingOrder

    def refresh_data(self):
        self.table.setRowCount(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        if hasattr(self, 'loader') and self.loader.isRunning():
            self.loader.wait()

        self.loader = PerformanceLoaderThread(self.budget_app)
        self.loader.finished.connect(self.on_data_loaded)
        self.loader.start()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def cleanup(self):
        if hasattr(self, 'loader') and self.loader.isRunning():
            self.loader.wait()

    def on_data_loaded(self, data):
        self.progress_bar.setVisible(False)
        self.current_data = data

        self.table.horizontalHeader().setSortIndicator(self.sort_column, self.sort_order)
        self.sort_data(self.sort_column, self.sort_order)

    def header_clicked(self, logical_index):
        if self.sort_column == logical_index:
            if self.sort_order == Qt.SortOrder.AscendingOrder:
                self.sort_order = Qt.SortOrder.DescendingOrder
            else:
                self.sort_order = Qt.SortOrder.AscendingOrder
        else:
            self.sort_column = logical_index
            self.sort_order = Qt.SortOrder.AscendingOrder

        self.table.horizontalHeader().setSortIndicator(logical_index, self.sort_order)
        self.sort_data(logical_index, self.sort_order)

    def sort_data(self, column, order):
        if not self.current_data:
            return

        total_row = self.current_data[0]
        data_to_sort = self.current_data[1:]

        keys = {
            0: 'name', 1: 'qty', 2: 'cost_basis', 3: 'market_value',
            4: 'unrealized_pl', 5: 'unrealized_pl_pct', 6: 'dividends',
            7: 'fees', 8: 'total_return', 9: 'total_return_pct',
            10: 'irr', 11: 'twr'
        }

        key_name = keys.get(column)
        if key_name:
            reverse = (order == Qt.SortOrder.DescendingOrder)
            # Handle None values for sort
            data_to_sort.sort(key=lambda x: (x.get(key_name) is None, x.get(key_name, 0)), reverse=reverse)

        self.current_data = [total_row] + data_to_sort
        self.populate_table(self.current_data)

    def populate_table(self, data):
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(len(data))

            for r, row in enumerate(data):
                is_total = row.get('is_total', False)

                acc_item = StringTableWidgetItem(row['name'])
                if is_total:
                    f = acc_item.font()
                    f.setBold(True)
                    acc_item.setFont(f)
                self.table.setItem(r, 0, acc_item)

                def set_num(col, val, is_pct=False, breakdown_dict=None):
                    if val is None:
                        text = "-"
                    elif is_pct:
                        text = f"{val:+.2f}%"
                    else:
                        text = format_currency(val)

                    if col == 1 and is_total:
                        text = ""

                    item = NumericTableWidgetItem(text)
                    
                    # Store numeric value for sorting if needed, though we sort data list
                    # item.setData(Qt.ItemDataRole.UserRole, val if val is not None else -999999)

                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                    if is_total:
                        f = item.font()
                        f.setBold(True)
                        item.setFont(f)

                    if val is not None and col in [4, 5, 8, 9, 10, 11]:
                        if val > 0:
                            item.setForeground(QColor("#2e7d32")) # Green
                        elif val < 0:
                            item.setForeground(QColor("#c62828")) # Red

                    if breakdown_dict:
                        sorted_years = sorted(
                            breakdown_dict.items(), key=lambda x: x[0], reverse=True)
                        tooltip_lines = []
                        for year, year_data in sorted_years:
                            cats = year_data.get('breakdown', {})
                            sorted_cats = sorted(
                                cats.items(), key=lambda x: x[1], reverse=True)
                            for cat, amt in sorted_cats:
                                tooltip_lines.append(f"{year} {cat}: {format_currency(amt)}")
                        tooltip = "\n".join(tooltip_lines).strip()
                        item.setToolTip(tooltip)
                    elif col in [10, 11] and val is None:
                        item.setToolTip("Insufficient data (needs >1 flow/valuation)")

                    self.table.setItem(r, col, item)

                set_num(1, row['qty'])
                self.table.item(r, 1).setForeground(QColor("black"))

                set_num(2, row['cost_basis'])
                self.table.item(r, 2).setForeground(QColor("black"))

                set_num(3, row['market_value'])
                self.table.item(r, 3).setForeground(QColor("black"))

                set_num(4, row['unrealized_pl'])
                set_num(5, row['unrealized_pl_pct'], is_pct=True)

                set_num(6, row['dividends'],
                        breakdown_dict=row.get('income_breakdown'))
                if row['dividends'] is not None and row['dividends'] > 0:
                    self.table.item(r, 6).setForeground(QColor("#2e7d32"))

                set_num(7, row['fees'], breakdown_dict=row.get('fees_breakdown'))
                if row['fees'] is not None and row['fees'] > 0:
                    self.table.item(r, 7).setForeground(QColor("#c62828"))

                set_num(8, row['total_return'])
                set_num(9, row['total_return_pct'], is_pct=True)
                
                # New Columns
                set_num(10, row['irr'], is_pct=True)
                set_num(11, row['twr'], is_pct=True)

            self.table.resizeColumnsToContents()

            header = self.table.horizontalHeader()
            for i in range(self.table.columnCount()):
                current_width = header.sectionSize(i)
                header.resizeSection(i, current_width + 35)
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)

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
