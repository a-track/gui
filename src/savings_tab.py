from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QToolTip)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QCursor
from custom_widgets import NoScrollComboBox


MATPLOTLIB_AVAILABLE = False
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class SavingsLoaderThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, budget_app, year):
        super().__init__()
        self.budget_app = budget_app
        self.year = year

    def run(self):

        data = self.budget_app.get_monthly_cashflow(self.year)
        self.finished.emit(data)


class SavingsTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.current_year = None
        self.chart_data = None
        self.bars_income = None
        self.bars_expense = None
        self.bars_invested = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        if not MATPLOTLIB_AVAILABLE:
            error_label = QLabel("⚠️ Matplotlib is not installed.")
            layout.addWidget(error_label)
            return

        header_layout = QHBoxLayout()

        header_layout.addWidget(QLabel("Year:"))
        self.year_combo = NoScrollComboBox()
        self.year_combo.setMinimumWidth(100)
        self.year_combo.currentIndexChanged.connect(self.refresh_graph)
        header_layout.addWidget(self.year_combo)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setStyleSheet("padding: 5px 10px;")
        header_layout.addWidget(refresh_btn)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def populate_years(self):
        if not MATPLOTLIB_AVAILABLE:
            return

        years = self.budget_app.get_available_years()
        current_text = self.year_combo.currentText()

        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        for year in years:
            self.year_combo.addItem(str(year), year)

        index = self.year_combo.findText(current_text)
        if index >= 0:
            self.year_combo.setCurrentIndex(index)
        elif years:
            self.year_combo.setCurrentIndex(0)

        self.year_combo.blockSignals(False)

    def refresh_data(self):
        """Called when tab becomes active"""
        self.populate_years()
        self.load_data()

    def load_data(self):
        if not MATPLOTLIB_AVAILABLE or self.year_combo.count() == 0:
            return

        year = self.year_combo.currentData()
        self.current_year = year

        self.progress_bar.setVisible(True)
        self.canvas.setVisible(False)

        self.loader = SavingsLoaderThread(self.budget_app, year)
        self.loader.finished.connect(self.on_data_loaded)
        self.loader.start()

    def refresh_graph(self):
        self.load_data()

    def on_data_loaded(self, data):
        self.progress_bar.setVisible(False)
        self.canvas.setVisible(True)
        self.chart_data = data
        self.plot_graph(data)

    def plot_graph(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        max_month = 12
        now = datetime.now()
        if self.current_year == now.year:
            max_month = now.month

        months = list(range(1, max_month + 1))
        all_month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
                            'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month_labels = all_month_labels[:max_month]

        incomes = []
        expenses = []
        monthly_invested = []
        
        cumulative_savings = []
        cumulative_invested = []
        
        running_savings = 0.0
        running_invested = 0.0

        for m in months:
            val = data.get(m, {'income': 0.0, 'expense': 0.0, 'invested': 0.0})
            inc = val.get('income', 0.0)
            exp = val.get('expense', 0.0)
            inv = val.get('invested', 0.0)
            
            incomes.append(inc)
            expenses.append(-exp)
            monthly_invested.append(inv)

            net = inc - exp
            # net_savings.append(net) # Not directly used for plotting, but for cumulative

            running_savings += net
            cumulative_savings.append(running_savings)
            
            running_invested += inv
            cumulative_invested.append(running_invested)

        # Calculate YTD Totals
        tot_inc = sum(incomes)
        tot_exp = sum([abs(x) for x in expenses])
        tot_net = tot_inc - tot_exp
        tot_inv = sum(monthly_invested)
        tot_saved = tot_net - tot_inv

        # 1. Cash Bars (Standard)
        self.bars_income = ax.bar(
            months, incomes, color='#4CAF50', label='Income', alpha=0.7)
        self.bars_expense = ax.bar(
            months, expenses, color='#F44336', label='Expenses', alpha=0.7)
            
        # 2. Cumulative Lines
        ax.plot(months, cumulative_savings, color='#2196F3',
                marker='o', linewidth=2, label='Accumulated Savings')
                
        ax.plot(months, cumulative_invested, color='#7B1FA2',
                marker='s', linewidth=2, label='Accumulated Invested')

        # Annotations (Savings Line)
        for i, val in enumerate(cumulative_savings):
            if i % 1 == 0:
                ax.annotate(f'{int(val):,}',
                            xy=(months[i], val),
                            xytext=(0, 5),
                            textcoords="offset points",
                            ha='center', va='bottom',
                            color='#1565C0', fontsize=8, fontweight='bold')

        # Annotations (Invested Line)
        for i, val in enumerate(cumulative_invested):
            if i % 1 == 0:
                ax.annotate(f'{int(val):,}',
                            xy=(months[i], val),
                            xytext=(0, -10),
                            textcoords="offset points",
                            ha='center', va='top',
                            color='#6A1B9A', fontsize=8, fontweight='bold')

        ax.axhline(0, color='black', linewidth=0.8)

        # Annotate Bars
        for i in range(len(months)):
            inc = incomes[i]
            exp = expenses[i]

            # Income Annotation
            if abs(inc) > 1.0:
                ax.annotate(f'{int(inc):,}',
                            xy=(months[i], inc/2),
                            ha='center', va='center',
                            color='white', fontsize=7, fontweight='bold')

            # Expense Annotation
            if abs(exp) > 1.0:
                 ax.annotate(f'{int(abs(exp)):,}',
                            xy=(months[i], exp/2),
                            ha='center', va='center',
                            color='white', fontsize=7, fontweight='bold')
        
        title_text = f'Monthly Cashflow ({self.current_year})'
        subtitle_text = (f"Inc: {tot_inc:,.0f} | Exp: {tot_exp:,.0f} | "
                         f"Net: {tot_net:,.0f} | Inv: {tot_inv:,.0f} | Saved: {tot_saved:,.0f}")
        
        ax.set_title(f"{title_text}\n{subtitle_text}", fontsize=10)
        ax.set_ylabel('Amount (CHF)')
        ax.set_xticks(months)
        ax.set_xticklabels(month_labels)
        ax.grid(True, axis='y', linestyle=':', alpha=0.6)

        # Legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='best')

        ax.get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, p: format(int(x), ',')))

        self.figure.tight_layout()
        self.canvas.draw()

    def on_hover(self, event):
        """Handle mouse hover event for tooltips"""
        if event.inaxes != self.figure.axes[0]:
            return

        checks = [
            (self.bars_income, 'income'),
            (self.bars_expense, 'expense')
        ]

        for bar_container, type_key in checks:
            if bar_container:
                for i, bar in enumerate(bar_container):
                    if bar.contains(event)[0]:
                        self.show_tooltip(event, i + 1, type_key)
                        return

    def show_tooltip(self, event, month, type_key):
        if not self.chart_data:
            return

        month_data = self.chart_data.get(month, {})
        if not month_data:
            return
            
        if type_key == 'invested':
            val = month_data.get('invested', 0.0)
            text = f"Net Invested: {val:,.2f}"
            QToolTip.showText(QCursor.pos(), text)
            return

        details = month_data.get('details', {}).get(type_key, {})

        if not details:
            QToolTip.showText(QCursor.pos(), "No details available")
            return

        sorted_cats = sorted(
            details.items(), key=lambda x: x[1]['total'], reverse=True)

        lines = []

        for cat_name, cat_data in sorted_cats:
            cat_total = cat_data['total']

            lines.append(f"<b>{cat_name}: {cat_total:,.2f}</b>")

            subs = cat_data.get('subs', {})
            sorted_subs = sorted(
                subs.items(), key=lambda x: x[1], reverse=True)

            for sub_name, sub_val in sorted_subs:

                lines.append(f"&nbsp;&nbsp;{sub_name}: {sub_val:,.2f}")

        text = "<br>".join(lines)
        QToolTip.showText(QCursor.pos(), text)
