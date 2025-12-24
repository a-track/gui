from PyQt6.QtWidgets import QWidget, QVBoxLayout
from balance_dialog import BalanceLoaderThread
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QProgressBar, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from excel_filter import ExcelHeaderView
from transactions_dialog import NumericTableWidgetItem, TOTAL_ROW_ROLE, StringTableWidgetItem

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
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Header
        header_layout = QHBoxLayout()
        balance_label = QLabel('Account Balances')
        balance_label.setStyleSheet('font-weight: bold; font-size: 18px; margin-bottom: 10px;')
        header_layout.addWidget(balance_label)
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet("padding: 5px 10px;")
        header_layout.addWidget(refresh_btn)
        
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
                font-size: 10pt;
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
                font-size: 10pt;
            }
        """)
        self.balance_table.verticalHeader().hide()
        
        content_layout.addWidget(self.balance_table)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
        content_layout.addWidget(self.status_label)
        
        layout.addWidget(content_widget)
        
        # Load initial data
        self.refresh_data()
    
    def refresh_data(self):
        """Reload balance data"""
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
        # 1. Group balances by Account Name
        # grouped_data = { 'AccountName': { 'CHF': val, 'USD': val, 'total_chf': val } }
        
        all_accounts = self.budget_app.get_all_accounts()
        # Filter out ignored accounts
        valid_accounts = [acc for acc in all_accounts if acc.id != 0 and getattr(acc, 'show_in_balance', True)]
        
        current_rates = self.budget_app.get_exchange_rates_map()
        
        grouped_data = {}
        all_currencies = set()
        
        for acc in valid_accounts:
            acc_data = balances.get(acc.id)
            if not acc_data: continue
            
            name = acc.account
            currency = acc.currency
            
            if name not in grouped_data:
                grouped_data[name] = {'total_chf': 0.0, 'currencies': {}, 'tooltips': {}}
            
            # Calculate Value (Market or Balance)
            invested_amount = acc_data['balance'] # This is the transactional balance (Cost Basis)
            qty = acc_data.get('qty', 0.0)
            
            market_val = invested_amount
            tooltip_msg = None

            if getattr(acc, 'is_investment', False):
                raw_val = self.budget_app.get_investment_valuation_for_date(acc.id)
                strategy = getattr(acc, 'valuation_strategy', 'Total Value')
                
                if strategy == 'Price/Qty':
                    market_val = qty * raw_val
                    
                    # Performance Calculation
                    performance = market_val - invested_amount
                    perf_percent = 0.0
                    if invested_amount != 0:
                        perf_percent = (performance / abs(invested_amount)) * 100
                    
                    sign = "+" if performance >= 0 else ""
                    
                    tooltip_msg = (
                        f"{acc.account}:\n"
                        f"{qty:,.4f} units @ {raw_val:,.2f} = {market_val:,.2f} {currency}\n"
                        f"Invested Amount: {invested_amount:,.2f} {currency}\n"
                        f"Performance: {sign}{performance:,.2f} {currency} ({sign}{perf_percent:.2f}%)"
                    )
                elif raw_val > 0:
                    market_val = raw_val
                    tooltip_msg = f"{acc.account}: Manual Valuation = {market_val:,.2f} {currency}"
            
            if currency not in grouped_data[name]['currencies']:
                 grouped_data[name]['currencies'][currency] = 0.0
                 grouped_data[name]['tooltips'][currency] = []
            
            grouped_data[name]['currencies'][currency] += market_val
            if tooltip_msg:
                grouped_data[name]['tooltips'][currency].append(tooltip_msg)

            all_currencies.add(currency)
            
            # Add to Total CHF
            rate = current_rates.get(currency, 1.0)
            grouped_data[name]['total_chf'] += (market_val * rate)

        # Calculate global total per currency for sorting columns
        currency_totals_chf = {}
        for name, data in grouped_data.items():
            for curr, val in data['currencies'].items():
                 rate = current_rates.get(curr, 1.0)
                 chf_val = val * rate
                 currency_totals_chf[curr] = currency_totals_chf.get(curr, 0.0) + chf_val

        # Sort currencies by Total Value in CHF (Descending)
        sorted_currencies = sorted(list(all_currencies), key=lambda c: currency_totals_chf.get(c, 0.0), reverse=True)
        headers = ["Account"] + sorted_currencies + ["Total (CHF)"]
        
        # 2. Setup Table
        self.balance_table.setSortingEnabled(False)
        self.balance_table.clear()
        self.balance_table.setColumnCount(len(headers))
        self.balance_table.setHorizontalHeaderLabels(headers)
        
        # Excel Header
        self.header_view = ExcelHeaderView(self.balance_table)
        self.balance_table.setHorizontalHeader(self.header_view)
        
        col_types = {0: 'text'}
        for i in range(1, len(headers)):
            col_types[i] = 'number'
        self.header_view.set_column_types(col_types)
        
        self.balance_table.verticalHeader().hide()
        self.balance_table.horizontalHeader().setVisible(True)
        
        # Tooltips
        for col, title in enumerate(headers):
            item = self.balance_table.horizontalHeaderItem(col)
            if item:
                if title == "Account": item.setToolTip("Account Name (Grouped)")
                elif title == "Total (CHF)": item.setToolTip("Total value in CHF")
                else: item.setToolTip(f"Total value in {title}")

        # Sort by Total CHF Descending
        sorted_names = sorted(grouped_data.keys(), key=lambda x: grouped_data[x]['total_chf'], reverse=True)
        total_rows = len(sorted_names) + 1 # + Total Row
        self.balance_table.setRowCount(total_rows)

        font = self.balance_table.font()
        bold_font = QFont(font); bold_font.setBold(True)

        # 3. Fill Data Rows (index 1 to N, reserve 0 for Total)
        col_grand_totals = {c: 0.0 for c in sorted_currencies}
        final_grand_chf = 0.0
        
        for r, name in enumerate(sorted_names):
            row_idx = r + 1 # Start from 1
            data = grouped_data[name]
            
            # Name
            self.balance_table.setItem(row_idx, 0, StringTableWidgetItem(name))
            
            # Currencies
            for c, curr in enumerate(sorted_currencies):
                val = data['currencies'].get(curr, 0.0)
                if val != 0:
                    formatted = f"{val:,.2f} {curr}"
                    item = NumericTableWidgetItem(formatted)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    if val < 0: item.setForeground(QColor("red"))
                    
                    # Set Tooltips
                    tooltips = data['tooltips'].get(curr, [])
                    if tooltips:
                        item.setToolTip("\n".join(tooltips))
                        
                    self.balance_table.setItem(row_idx, c+1, item)
                    
                    col_grand_totals[curr] += val
            
            # Total CHF
            tot_chf = data['total_chf']
            t_item = NumericTableWidgetItem(f"{tot_chf:,.2f} CHF")
            
            # Set FX Tooltips (Detailed Breakdown)
            fx_breakdown = []
            for curr in sorted_currencies:
                val = data['currencies'].get(curr, 0.0)
                if val != 0 and curr != 'CHF':
                    rate = current_rates.get(curr, 1.0)
                    chf_val = val * rate
                    fx_breakdown.append(f"{val:,.2f} {curr} = {chf_val:,.2f} CHF (Rate: {rate:.4f})")
            
            if fx_breakdown:
                t_item.setToolTip("\n".join(fx_breakdown))
                
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if tot_chf < 0: t_item.setForeground(QColor("red"))
            self.balance_table.setItem(row_idx, len(headers)-1, t_item)
            
            final_grand_chf += tot_chf
 
        # 4. Fill Total Row (at index 0)
        l_item = StringTableWidgetItem("Total")
        l_item.setData(TOTAL_ROW_ROLE, True)
        l_item.setFont(bold_font)
        self.balance_table.setItem(0, 0, l_item)
        
        for c, curr in enumerate(sorted_currencies):
             val = col_grand_totals[curr]
             item = NumericTableWidgetItem(f"{val:,.2f} {curr}")
             item.setData(TOTAL_ROW_ROLE, True)
             item.setFont(bold_font)
             item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
             if val < 0: item.setForeground(QColor("red"))
             self.balance_table.setItem(0, c+1, item)
        
        tot_item = NumericTableWidgetItem(f"{final_grand_chf:,.2f} CHF")
        tot_item.setData(TOTAL_ROW_ROLE, True)
        tot_item.setFont(bold_font)
        tot_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if final_grand_chf < 0: tot_item.setForeground(QColor("red"))
        self.balance_table.setItem(0, len(headers)-1, tot_item)
        
        # Ensure sorting is enabled
        self.balance_table.setSortingEnabled(True)

        self.balance_table.blockSignals(False)
        self.balance_table.setSortingEnabled(True)
        
        # Enforce Default Sort: Total CHF (Last Column) Descending
        self.balance_table.sortItems(len(headers)-1, Qt.SortOrder.DescendingOrder)
        
        self.balance_table.resizeColumnsToContents()
        
        for col in range(self.balance_table.columnCount()):
            current_width = self.balance_table.columnWidth(col)
            self.balance_table.setColumnWidth(col, current_width + 20)

    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px; font-weight: bold;')
