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

            total_cost_basis = 0.0
            total_market_val = 0.0
            total_unrealized = 0.0
            total_income = 0.0
            total_fees = 0.0
            total_return_sum = 0.0

            total_income_breakdown = {}
            total_fees_breakdown = {}

            for acc in all_accounts:
                if not getattr(acc, 'is_investment', False):
                    continue
                if not getattr(acc, 'is_active', True):
                    continue

                acc_id = acc.id
                name = acc.account
                currency = acc.currency

                balance_data = balances.get(acc_id, {})
                cost_basis_native = balance_data.get('balance', 0.0)
                qty = balance_data.get('qty', 0.0)

                rate = rates.get(currency, 1.0)
                cost_basis_chf = cost_basis_native * rate

                market_val_native = cost_basis_native

                strategy = getattr(acc, 'valuation_strategy', 'Total Value')
                raw_val = self.budget_app.get_investment_valuation_for_date(
                    acc_id)

                if strategy == 'Price/Qty':
                    market_val_native = qty * raw_val
                elif raw_val > 0:
                    market_val_native = raw_val

                market_val_chf = market_val_native * rate

                income_data = dividends.get(
                    acc_id, {'total': 0.0, 'years': {}})
                income_chf = income_data['total']
                years_data = income_data['years']

                expense_data = expenses.get(
                    acc_id, {'total': 0.0, 'years': {}})
                fees_chf = expense_data['total']
                fees_years_data = expense_data['years']

                unrealized_pl_chf = market_val_chf - cost_basis_chf
                total_return_chf = unrealized_pl_chf + income_chf - fees_chf

                unrealized_pl_pct = 0.0
                if abs(cost_basis_chf) > 0.01:
                    unrealized_pl_pct = (
                        unrealized_pl_chf / abs(cost_basis_chf)) * 100

                total_return_pct = 0.0
                if abs(cost_basis_chf) > 0.01:
                    total_return_pct = (
                        total_return_chf / abs(cost_basis_chf)) * 100

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
                    'is_total': False
                }
                data.append(row)

                total_cost_basis += cost_basis_chf
                total_market_val += market_val_chf
                total_unrealized += unrealized_pl_chf
                total_income += income_chf
                total_fees += fees_chf
                total_return_sum += total_return_chf

                def aggregate_breakdown(source_years_data, target_total_dict):
                    for year, y_data in source_years_data.items():
                        if year not in target_total_dict:
                            target_total_dict[year] = {
                                'total': 0.0, 'breakdown': {}}

                        target_total_dict[year]['total'] += y_data['total']
                        for cat, val in y_data['breakdown'].items():
                            target_total_dict[year]['breakdown'][cat] = target_total_dict[year]['breakdown'].get(
                                cat, 0.0) + val

                aggregate_breakdown(years_data, total_income_breakdown)
                aggregate_breakdown(fees_years_data, total_fees_breakdown)

            total_unrealized_pct = 0.0
            if abs(total_cost_basis) > 0.01:
                total_unrealized_pct = (
                    total_unrealized / abs(total_cost_basis)) * 100

            total_return_pct = 0.0
            if abs(total_cost_basis) > 0.01:
                total_return_pct = (total_return_sum /
                                    abs(total_cost_basis)) * 100

            total_row = {
                'name': 'TOTAL',
                'currency': '',
                'qty': 0,
                'cost_basis': total_cost_basis,
                'market_value': total_market_val,
                'unrealized_pl': total_unrealized,
                'unrealized_pl_pct': total_unrealized_pct,
                'dividends': total_income,
                'income_breakdown': total_income_breakdown,
                'fees': total_fees,
                'fees_breakdown': total_fees_breakdown,
                'total_return': total_return_sum,
                'total_return_pct': total_return_pct,
                'is_total': True
            }

            if data:
                data.insert(0, total_row)

            self.finished.emit(data)

        except Exception as e:
            print(f"Error loading performance data: {e}")
            self.finished.emit([])


class InvestmentPerformanceTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.init_ui()
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

        info_label = QLabel(" All monetary values displayed in CHF")
        info_label.setStyleSheet(
            "color: #666; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(info_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Account", "Quantity", "Cost Basis", "Market Value",
            "Unrealized P&L", "Unrealized %",
            "Gains", "Fees",
            "Total Return", "Total Return %"
        ])

        self.header_view = ExcelHeaderView(self.table)
        self.table.setHorizontalHeader(self.header_view)

        self.table.setSortingEnabled(False)
        self.header_view.sectionClicked.connect(self.header_clicked)

        self.header_view.set_column_types({
            1: 'number', 2: 'number', 3: 'number', 4: 'number',
            5: 'number', 6: 'number', 7: 'number', 8: 'number', 9: 'number'
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
            7: 'fees', 8: 'total_return', 9: 'total_return_pct'
        }

        key_name = keys.get(column)
        if key_name:
            reverse = (order == Qt.SortOrder.DescendingOrder)

            data_to_sort.sort(key=lambda x: x.get(
                key_name, 0), reverse=reverse)

        self.current_data = [total_row] + data_to_sort
        self.populate_table(self.current_data)

    def populate_table(self, data):
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
                if is_pct:
                    text = f"{val:+.2f}%"
                else:
                    text = f"{val:,.2f}"

                if col == 1 and is_total:
                    text = ""

                item = NumericTableWidgetItem(text)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                if is_total:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)

                if col in [4, 5, 8, 9]:
                    if val > 0:
                        item.setForeground(QColor("#2e7d32"))
                    elif val < 0:
                        item.setForeground(QColor("#c62828"))

                if breakdown_dict:

                    sorted_years = sorted(
                        breakdown_dict.items(), key=lambda x: x[0], reverse=True)
                    tooltip_lines = []

                    for year, year_data in sorted_years:

                        cats = year_data.get('breakdown', {})
                        sorted_cats = sorted(
                            cats.items(), key=lambda x: x[1], reverse=True)
                        for cat, amt in sorted_cats:
                            tooltip_lines.append(f"{year} {cat}: {amt:,.2f}")

                    tooltip = "\n".join(tooltip_lines).strip()
                    item.setToolTip(tooltip)

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
            if row['dividends'] > 0:
                self.table.item(r, 6).setForeground(QColor("#2e7d32"))

            set_num(7, row['fees'], breakdown_dict=row.get('fees_breakdown'))
            if row['fees'] > 0:
                self.table.item(r, 7).setForeground(QColor("#c62828"))

            set_num(8, row['total_return'])
            set_num(9, row['total_return_pct'], is_pct=True)

        self.table.resizeColumnsToContents()

        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            current_width = header.sectionSize(i)
            header.resizeSection(i, current_width + 25)
