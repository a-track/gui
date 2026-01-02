
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QDateEdit)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from custom_widgets import NoScrollComboBox
from excel_filter import ExcelHeaderView
from transactions_dialog import NumericTableWidgetItem, TOTAL_ROW_ROLE, StringTableWidgetItem
from utils import format_currency


class BalanceTab(QWidget):
    """Tab widget for viewing account balances"""

    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.parent_window = parent
        self.init_ui()

    def showEvent(self, event):
        self.populate_years()
        super().showEvent(event)

    def init_ui(self):


        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        header_layout = QHBoxLayout()
        balance_label = QLabel('Account Balances')
        balance_label.setStyleSheet(
            'font-weight: bold; font-size: 18px; margin-bottom: 10px;')
        header_layout.addWidget(balance_label)
        header_layout.addStretch()

        header_layout.addWidget(QLabel("Range:"))
        self.range_combo = NoScrollComboBox()
        self.range_combo.setMinimumWidth(150)
        self.range_combo.addItem("Current (All Time)", "last_12") # Reusing 'last_12' as 'Current' logic (Today)
        self.range_combo.currentIndexChanged.connect(self.on_range_changed)
        header_layout.addWidget(self.range_combo)

        # Custom Date Range Inputs (Hidden by default, used for 'Custom' or specific year end)
        self.date_range_widget = QWidget()
        date_layout = QHBoxLayout(self.date_range_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        
        # Balance only cares about "As Of", typically End Date.
        # But for consistency with savings tab UI, we keep the widgets, but mainly use 'To' date.
        
        date_layout.addWidget(QLabel("As Of:")) # Changed label to be clearer for Balance
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setDate(QDate.currentDate())
        date_layout.addWidget(self.to_date)

        header_layout.addWidget(self.date_range_widget)
        self.date_range_widget.setVisible(False)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet("padding: 5px 10px;")
        header_layout.addWidget(refresh_btn)

        content_layout.addLayout(header_layout)



        self.balance_table = QTableWidget()
        self.balance_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.balance_table.setSelectionMode(
            QTableWidget.SelectionMode.NoSelection)
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

        self.status_label = QLabel('')
        self.status_label.setStyleSheet(
            'color: #4CAF50; padding: 5px; font-weight: bold;')
        content_layout.addWidget(self.status_label)

        layout.addWidget(content_widget)

        self.populate_years()
        self.refresh_data()

    def populate_years(self):
        years = self.budget_app.get_available_years()
        current_text = self.range_combo.currentText()
        
        self.range_combo.blockSignals(True)
        self.range_combo.clear()
        self.range_combo.addItem("Current (All Time)", "last_12")
        
        for year in years:
            self.range_combo.addItem(f"Year {year}", str(year))
            
        self.range_combo.addItem("Custom", "custom")

        index = self.range_combo.findText(current_text)
        if index >= 0:
            self.range_combo.setCurrentIndex(index)
        else:
            self.range_combo.setCurrentIndex(0)

        self.range_combo.blockSignals(False)
        self.on_range_changed()

    def on_range_changed(self):
        mode = self.range_combo.currentData()
        self.date_range_widget.setVisible(mode == 'custom')
        if mode != 'custom':
            self.refresh_data()
            
    def filter_content(self, text):
        """Filter table rows based on text matching."""
        search_text = text.lower()
        rows = self.balance_table.rowCount()
        cols = self.balance_table.columnCount()
        
        for row in range(rows):
            should_show = False
            if not search_text:
                should_show = True
            else:
                for col in range(cols):
                    item = self.balance_table.item(row, col)
                    # Skip widget checks if they complicate logic, just check text
                    if item and search_text in item.text().lower():
                        should_show = True
                        break
            
            self.balance_table.setRowHidden(row, not should_show)

    def get_end_date(self):
        mode = self.range_combo.currentData()
        today = QDate.currentDate()
        
        if mode == 'last_12':
            # "Current" balance is effectively today (or all time)
            return None # None means no filter (all time)
            
        elif mode == 'custom':
            return self.to_date.date().toString("yyyy-MM-dd")
            
        else:
            # Specific Year
            try:
                year = int(mode)
                return f"{year}-12-31"
            except:
                return None

    def refresh_data(self):
        """Reload balance data synchronously"""
        try:
            target_date = self.get_end_date()
            balances = self.budget_app.get_balance_summary(target_date)
            self.update_balance_display_with_data(balances, target_date)
            
            status_msg = 'Balances loaded successfully'
            if target_date:
                status_msg += f" (As of {target_date})"
            self.show_status(status_msg)
        except Exception as e:
            self.balance_table.clear()
            self.balance_table.setRowCount(1)
            self.balance_table.setColumnCount(1)
            item = QTableWidgetItem(f'Error loading balances: {e}')
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor('red'))
            self.balance_table.setItem(0, 0, item)
            self.show_status(f'Error: {e}', error=True)

    def update_balance_display_with_data(self, balances, target_date=None):

        all_accounts = self.budget_app.get_all_accounts()

        valid_accounts = [acc for acc in all_accounts if acc.id !=
                          0 and getattr(acc, 'show_in_balance', True)]

        current_rates = self.budget_app.get_exchange_rates_map()

        grouped_data = {}
        all_currencies = set()

        for acc in valid_accounts:
            acc_data = balances.get(acc.id)
            if not acc_data:
                continue

            name = acc.account
            currency = acc.currency

            if name not in grouped_data:
                grouped_data[name] = {'total_chf': 0.0,
                                      'currencies': {}, 'tooltips': {}}

            invested_amount = acc_data['balance']
            qty = acc_data.get('qty', 0.0)

            market_val = invested_amount
            tooltip_msg = None

            if getattr(acc, 'is_investment', False):
                raw_val = self.budget_app.get_investment_valuation_for_date(
                    acc.id, target_date)
                strategy = getattr(acc, 'valuation_strategy', 'Total Value')

                if strategy == 'Price/Qty':
                    market_val = qty * raw_val

                    performance = market_val - invested_amount
                    perf_percent = 0.0
                    if invested_amount != 0:
                        perf_percent = (
                            performance / abs(invested_amount)) * 100

                    sign = "+" if performance >= 0 else ""

                    tooltip_msg = (
                        f"{acc.account}:\n"
                        f"{format_currency(qty, precision=4)} units @ {format_currency(raw_val)} = {format_currency(market_val)} {currency}\n"
                        f"Invested Amount: {format_currency(invested_amount)} {currency}\n"
                        f"Performance: {sign}{format_currency(performance)} {currency} ({sign}{perf_percent:.2f}%)"
                    )
                elif raw_val > 0:
                    market_val = raw_val
                    tooltip_msg = f"{acc.account}: Manual Valuation = {format_currency(market_val)} {currency}"

            if currency not in grouped_data[name]['currencies']:
                grouped_data[name]['currencies'][currency] = 0.0
                grouped_data[name]['tooltips'][currency] = []

            grouped_data[name]['currencies'][currency] += market_val
            if tooltip_msg:
                grouped_data[name]['tooltips'][currency].append(tooltip_msg)

            all_currencies.add(currency)

            rate = current_rates.get(currency, 1.0)
            grouped_data[name]['total_chf'] += (market_val * rate)

        currency_totals_chf = {}
        for name, data in grouped_data.items():
            for curr, val in data['currencies'].items():
                rate = current_rates.get(curr, 1.0)
                chf_val = val * rate
                currency_totals_chf[curr] = currency_totals_chf.get(
                    curr, 0.0) + chf_val

        sorted_currencies = sorted(list(
            all_currencies), key=lambda c: currency_totals_chf.get(c, 0.0), reverse=True)
        headers = ["Account"] + sorted_currencies + ["Total (CHF)"]

        self.balance_table.setUpdatesEnabled(False)
        self.balance_table.setSortingEnabled(False)
        self.balance_table.blockSignals(True)
        try:
            self.balance_table.clear()
            self.balance_table.setColumnCount(len(headers))
            self.balance_table.setHorizontalHeaderLabels(headers)

            self.header_view = ExcelHeaderView(self.balance_table)
            self.balance_table.setHorizontalHeader(self.header_view)

            col_types = {0: 'text'}
            for i in range(1, len(headers)):
                col_types[i] = 'number'
            self.header_view.set_column_types(col_types)

            self.balance_table.verticalHeader().hide()
            self.balance_table.horizontalHeader().setVisible(True)

            for col, title in enumerate(headers):
                item = self.balance_table.horizontalHeaderItem(col)
                if item:
                    if title == "Account":
                        item.setToolTip("Account Name (Grouped)")
                    elif title == "Total (CHF)":
                        item.setToolTip("Total value in CHF")
                    else:
                        item.setToolTip(f"Total value in {title}")

            sorted_names = sorted(
                grouped_data.keys(), key=lambda x: grouped_data[x]['total_chf'], reverse=True)
            total_rows = len(sorted_names) + 1
            self.balance_table.setRowCount(total_rows)

            font = self.balance_table.font()
            bold_font = QFont(font)
            bold_font.setBold(True)

            col_grand_totals = {c: 0.0 for c in sorted_currencies}
            final_grand_chf = 0.0

            for r, name in enumerate(sorted_names):
                row_idx = r + 1
                data = grouped_data[name]

                self.balance_table.setItem(row_idx, 0, StringTableWidgetItem(name))

                for c, curr in enumerate(sorted_currencies):
                    val = data['currencies'].get(curr, 0.0)
                    if abs(val) >= 0.001: # Changed 'balance' to 'val'
                        formatted_balance = format_currency(val) # Changed 'balance' to 'val'
                        item = NumericTableWidgetItem(f"{formatted_balance} {curr}") # Changed 'balance_item' to 'item' and added currency
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        if val < 0:
                            item.setForeground(QColor("red"))

                        tooltips = data['tooltips'].get(curr, [])
                        if tooltips:
                            item.setToolTip("\n".join(tooltips))

                        self.balance_table.setItem(row_idx, c+1, item)

                        col_grand_totals[curr] += val

                tot_chf = data['total_chf']
                t_item = NumericTableWidgetItem(f"{format_currency(tot_chf)} CHF")

                fx_breakdown = []
                for curr in sorted_currencies:
                    val = data['currencies'].get(curr, 0.0)
                    if val != 0 and curr != 'CHF':
                        rate = current_rates.get(curr, 1.0)
                        chf_val = val * rate
                        fx_breakdown.append(
                            f"{format_currency(val)} {curr} = {format_currency(chf_val)} CHF (Rate: {rate:.4f})")

                if fx_breakdown:
                    t_item.setToolTip("\n".join(fx_breakdown))

                t_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if tot_chf < 0:
                    t_item.setForeground(QColor("red"))
                self.balance_table.setItem(row_idx, len(headers)-1, t_item)

                final_grand_chf += tot_chf

            l_item = StringTableWidgetItem("Total")
            l_item.setData(TOTAL_ROW_ROLE, True)
            l_item.setFont(bold_font)
            self.balance_table.setItem(0, 0, l_item)

            # Re-calculating total_by_currency based on col_grand_totals
            total_by_currency = col_grand_totals
            
            for c, curr in enumerate(sorted_currencies): # Iterating through sorted_currencies to match column order
                val = total_by_currency[curr]
                item = NumericTableWidgetItem(f"{format_currency(val)} {curr}") # Corrected to use 'val' and 'curr'
                item.setData(TOTAL_ROW_ROLE, True)
                item.setFont(bold_font)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if val < 0:
                    item.setForeground(QColor("red"))
                self.balance_table.setItem(0, c+1, item)

            tot_item = NumericTableWidgetItem(f"{format_currency(final_grand_chf)} CHF")
            tot_item.setData(TOTAL_ROW_ROLE, True)
            tot_item.setFont(bold_font)
            tot_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if final_grand_chf < 0:
                tot_item.setForeground(QColor("red"))
            self.balance_table.setItem(0, len(headers)-1, tot_item)

            self.balance_table.sortItems(
                len(headers)-1, Qt.SortOrder.DescendingOrder)

            self.balance_table.resizeColumnsToContents()

            for col in range(self.balance_table.columnCount()):
                current_width = self.balance_table.columnWidth(col)
                self.balance_table.setColumnWidth(col, current_width + 20)
        finally:
            self.balance_table.blockSignals(False)
            self.balance_table.setSortingEnabled(True)
            self.balance_table.setUpdatesEnabled(True)

    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet(
                'color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet(
                'color: #4CAF50; padding: 5px; font-weight: bold;')
