from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QToolTip, QDateEdit, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, QDate
from PyQt6.QtGui import QCursor
from custom_widgets import NoScrollComboBox
from utils import format_currency


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

    def __init__(self, budget_app, start_date, end_date):
        super().__init__()
        self.budget_app = budget_app
        self.start_date = start_date
        self.end_date = end_date

    def run(self):
        data = self.budget_app.get_cashflow_data(self.start_date, self.end_date)
        self.finished.emit(data)


class SavingsTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.current_start_date = None
        self.current_end_date = None
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

        header_layout.addWidget(QLabel("Range:"))
        self.range_combo = NoScrollComboBox()
        self.range_combo.setMinimumWidth(150)
        self.range_combo.addItem("Last 12 Months", "last_12")
        self.range_combo.currentIndexChanged.connect(self.on_range_changed)
        header_layout.addWidget(self.range_combo)

        # Custom Date Range Inputs (Hidden by default)
        self.date_range_widget = QWidget()
        date_layout = QHBoxLayout(self.date_range_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        
        date_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setDate(QDate.currentDate().addYears(-1))
        date_layout.addWidget(self.from_date)

        date_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setDate(QDate.currentDate())
        date_layout.addWidget(self.to_date)

        header_layout.addWidget(self.date_range_widget)
        self.date_range_widget.setVisible(False)

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
        # Add years to the combo box after "Last 12 Months"
        if not MATPLOTLIB_AVAILABLE:
            return

        years = self.budget_app.get_available_years()
        current_text = self.range_combo.currentText()
        
        self.range_combo.blockSignals(True)
        
        # Keep "Last 12 Months" and "Custom"
        # Re-populate years in between
        
        # Clear specific year items if any (simplified: rebuild all)
        self.range_combo.clear()
        self.range_combo.addItem("Last 12 Months", "last_12")
        
        for year in years:
            self.range_combo.addItem(f"Year {year}", str(year))
            
        self.range_combo.addItem("Custom Range", "custom")

        # Restore selection if possible
        index = self.range_combo.findText(current_text)
        if index >= 0:
            self.range_combo.setCurrentIndex(index)
        else:
            self.range_combo.setCurrentIndex(0) # Default to Last 12 Months

        self.range_combo.blockSignals(False)
        self.on_range_changed() # Update visibility

    def refresh_data(self):
        """Called when tab becomes active"""
        self.populate_years()
        self.load_data()

    def load_data(self):
        if not MATPLOTLIB_AVAILABLE or self.year_combo.count() == 0:
            return

    def on_range_changed(self):
        mode = self.range_combo.currentData()
        self.date_range_widget.setVisible(mode == 'custom')
        if mode != 'custom':
            self.load_data()

    def get_date_range(self):
        mode = self.range_combo.currentData()
        today = QDate.currentDate()
        
        if mode == 'last_12':
            end_date = today
            start_date = today.addMonths(-11).addDays(-(today.day() - 1)) # Start of that month
            return start_date.toString("yyyy-MM-dd"), end_date.toString("yyyy-MM-dd")
            
        elif mode == 'custom':
            return self.from_date.date().toString("yyyy-MM-dd"), self.to_date.date().toString("yyyy-MM-dd")
            
        else:
            # Specific Year
            try:
                year = int(mode)
                return f"{year}-01-01", f"{year}-12-31"
            except:
                return today.toString("yyyy-MM-dd"), today.toString("yyyy-MM-dd")

    def load_data(self):
        if not MATPLOTLIB_AVAILABLE:
            return

        start_str, end_str = self.get_date_range()
        
        if start_str > end_str:
             QMessageBox.warning(self, "Invalid Range", "Start Date cannot be after End Date.")
             return

        self.current_start_date = start_str
        self.current_end_date = end_str

        self.progress_bar.setVisible(True)
        self.canvas.setVisible(False)

        if hasattr(self, 'loader') and self.loader is not None:
            if self.loader.isRunning():
                self.loader.quit()
                self.loader.wait()
        
        self.loader = SavingsLoaderThread(self.budget_app, start_str, end_str)
        self.loader.finished.connect(self.on_data_loaded)
        self.loader.start()

    def closeEvent(self, event):
        if hasattr(self, 'loader') and self.loader is not None and self.loader.isRunning():
            self.loader.quit()
            self.loader.wait()
        super().closeEvent(event)

    def refresh_graph(self):
        # Triggered by combo change (handled by on_range_changed)
        pass

    def on_data_loaded(self, data):
        self.progress_bar.setVisible(False)
        self.canvas.setVisible(True)
        self.chart_data = data
        self.plot_graph(data)

    def plot_graph(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        month_keys = sorted(data.keys())
        
        # If no data, show at least current month
        if not month_keys:
             month_keys = [datetime.now().strftime("%Y-%m")]
        
        months_x = range(len(month_keys))
        
        # Format labels: "2025-01" -> "Jan '25" or "Jan" if all same year
        labels = []
        for k in month_keys:
            try:
                dt = datetime.strptime(k, "%Y-%m")
                labels.append(dt.strftime("%b '%y"))
            except:
                labels.append(k)

        incomes = []
        expenses = []
        monthly_invested = []
        
        cumulative_savings = []
        cumulative_invested = []
        
        running_savings = 0.0
        running_invested = 0.0

        for mk in month_keys:
            val = data.get(mk, {'income': 0.0, 'expense': 0.0, 'invested': 0.0})
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
            months_x, incomes, color='#4CAF50', label='Income', alpha=0.7)
        self.bars_expense = ax.bar(
            months_x, expenses, color='#F44336', label='Expenses', alpha=0.7)
            
        # 2. Cumulative Lines
        ax.plot(months_x, cumulative_savings, color='#2196F3',
                marker='o', linewidth=2, label='Accumulated Savings')
                
        ax.plot(months_x, cumulative_invested, color='#7B1FA2',
                marker='s', linewidth=2, label='Accumulated Invested')

        # Annotations (Savings Line)
        for i, val in enumerate(cumulative_savings):
            # Show every point if <= 12 months, else sparser
            step = 1 if len(month_keys) <= 12 else 2
            if i % step == 0:
                ax.annotate(format_currency(val, precision=0),
                            xy=(months_x[i], val),
                            xytext=(0, 5),
                            textcoords="offset points",
                            ha='center', va='bottom',
                            color='#1565C0', fontsize=8, fontweight='bold')

        # Annotations (Invested Line)
        for i, val in enumerate(cumulative_invested):
            step = 1 if len(month_keys) <= 12 else 2
            if i % step == 0:
                ax.annotate(format_currency(val, precision=0),
                            xy=(months_x[i], val),
                            xytext=(0, -10),
                            textcoords="offset points",
                            ha='center', va='top',
                            color='#6A1B9A', fontsize=8, fontweight='bold')

        ax.axhline(0, color='black', linewidth=0.8)

        # Annotate Bars
        for i in range(len(months_x)):
            inc = incomes[i]
            exp = expenses[i]

            # Income Annotation
            if abs(inc) > 1.0:
                ax.annotate(format_currency(inc, precision=0),
                            xy=(months_x[i], inc/2),
                            ha='center', va='center',
                            color='white', fontsize=7, fontweight='bold')

            # Expense Annotation
            if abs(exp) > 1.0:
                 ax.annotate(format_currency(abs(exp), precision=0),
                            xy=(months_x[i], exp/2),
                            ha='center', va='center',
                            color='white', fontsize=7, fontweight='bold')
        
        title_text = f'Monthly Cashflow ({self.current_start_date} to {self.current_end_date})'
        subtitle_text = (f"Inc: {format_currency(tot_inc, precision=0)} | Exp: {format_currency(tot_exp, precision=0)} | "
                         f"Net: {format_currency(tot_net, precision=0)} | Inv: {format_currency(tot_inv, precision=0)} | Saved: {format_currency(tot_saved, precision=0)}")
        
        ax.set_title(f"{title_text}\n{subtitle_text}", fontsize=10)
        ax.set_ylabel('Amount (CHF)')
        ax.set_xticks(months_x)
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 6 else 0)
        ax.grid(True, axis='y', linestyle=':', alpha=0.6)

        # Legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='best')

        ax.get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, p: format_currency(x, precision=0)))

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

    def show_tooltip(self, event, idx, type_key):
        if not self.chart_data:
            return

        # Map index back to key
        sorted_keys = sorted(self.chart_data.keys())
        if idx < 1 or idx > len(sorted_keys):
            return
            
        key = sorted_keys[idx-1]
        month_data = self.chart_data.get(key, {})
        if not month_data:
            return
            
        if type_key == 'invested':
            val = month_data.get('invested', 0.0)
            text = f"Net Invested: {format_currency(val)}"
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

            lines.append(f"<b>{cat_name}: {format_currency(cat_total)}</b>")

            subs = cat_data.get('subs', {})
            sorted_subs = sorted(
                subs.items(), key=lambda x: x[1], reverse=True)

            for sub_name, sub_val in sorted_subs:

                lines.append(f"&nbsp;&nbsp;{sub_name}: {format_currency(sub_val)}")

        text = "<br>".join(lines)
        QToolTip.showText(QCursor.pos(), text)
