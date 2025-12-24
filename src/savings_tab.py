from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QComboBox, QToolTip)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QCursor
from custom_widgets import NoScrollComboBox

# Try importing Matplotlib
MATPLOTLIB_AVAILABLE = False
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
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
        # Fetch {month: net_amount}
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
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        if not MATPLOTLIB_AVAILABLE:
            error_label = QLabel("⚠️ Matplotlib is not installed.")
            layout.addWidget(error_label)
            return

        # Header Controls
        header_layout = QHBoxLayout()
        
        # Year Selector (Single year for bar chart clarity)
        header_layout.addWidget(QLabel("Year:"))
        self.year_combo = NoScrollComboBox()
        self.year_combo.setMinimumWidth(100)
        self.year_combo.currentIndexChanged.connect(self.refresh_graph)
        header_layout.addWidget(self.year_combo)
        
        # Refresh Button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setStyleSheet("padding: 5px 10px;")
        header_layout.addWidget(refresh_btn)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Loading Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)
        
        # Graph Area
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Tooltip connection
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)
        
    def populate_years(self):
        if not MATPLOTLIB_AVAILABLE: return
        
        years = self.budget_app.get_available_years()
        current_text = self.year_combo.currentText()
        
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        for year in years:
            self.year_combo.addItem(str(year), year)
        
        # Restore or default
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
        
        # Determine valid months range
        max_month = 12
        now = datetime.now()
        if self.current_year == now.year:
             max_month = now.month
             
        months = list(range(1, max_month + 1))
        all_month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month_labels = all_month_labels[:max_month]
        
        # Extract Income and Expense
        incomes = []
        expenses = [] # Will plot as negative
        net_savings = []
        cumulative_savings = []
        running_total = 0.0
        
        for m in months:
            val = data.get(m, {'income': 0.0, 'expense': 0.0})
            inc = val.get('income', 0.0)
            exp = val.get('expense', 0.0)
            incomes.append(inc)
            expenses.append(-exp) # Plot downward
            
            net = inc - exp
            net_savings.append(net)
            
            running_total += net
            cumulative_savings.append(running_total)

        # Plot Bars
        # Save bar containers for tooltip hit-testing
        self.bars_income = ax.bar(months, incomes, color='#4CAF50', label='Income', alpha=0.7)
        self.bars_expense = ax.bar(months, expenses, color='#F44336', label='Expenses', alpha=0.7)
        
        # Plot Accumulated Savings Line
        # Use a thicker line and markers to make it stand out
        ax.plot(months, cumulative_savings, color='#2196F3', marker='o', linewidth=2, label='Accumulated Savings')
        
        # Annotate Accumulated Savings
        for i, val in enumerate(cumulative_savings):
            # Annotate slightly above the point
            if i % 1 == 0: # Annotate every point? or skip if crowded? Let's try every point first.
                ax.annotate(f'{int(val):,}',
                            xy=(months[i], val),
                            xytext=(0, 5), # 5 points offset
                            textcoords="offset points",
                            ha='center', va='bottom',
                            color='#1565C0', fontsize=8, fontweight='bold')
        
        # Add Zero Value Line
        ax.axhline(0, color='black', linewidth=0.8)
        
        # Annotate Income and Expenses
        for i, (inc, exp) in enumerate(zip(incomes, expenses)):
            # Annotate Income (Positive)
            if abs(inc) > 1.0:
                ax.annotate(f'{int(inc):,}',
                            xy=(months[i], inc),
                            xytext=(0, 3), # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom',
                            color='#1B5E20', fontsize=8, fontweight='bold')
            
            # Annotate Expense (Negative)
            if abs(exp) > 1.0:
                ax.annotate(f'{int(abs(exp)):,}', # Show absolute value for readability? Or keep negative? Usually abs is cleaner if position implies sign. 
                            # User asked for "expense numbers", usually people want to see "500" expense, not "-500". 
                            # But bar is negative. Let's show absolute for clarity as requested "numbers".
                            xy=(months[i], exp),
                            xytext=(0, -3), # -3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='top',
                            color='#B71C1C', fontsize=8, fontweight='bold')

        ax.set_title(f'Monthly Cashflow ({self.current_year})')
        ax.set_ylabel('Amount (CHF)')
        ax.set_xticks(months)
        ax.set_xticklabels(month_labels)
        ax.grid(True, axis='y', linestyle=':', alpha=0.6)
        
        # Legend (Auto placement usually best, or upper left if positive bars dominate)
        ax.legend(loc='best')
        
        # Format Y axis
        ax.get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, p: format(int(x), ',')))
            
        self.figure.tight_layout()
        self.canvas.draw()

    def on_hover(self, event):
        """Handle mouse hover event for tooltips"""
        if event.inaxes != self.figure.axes[0]:
            return
            
        # Check Income Bars
        if self.bars_income:
            for i, bar in enumerate(self.bars_income):
                if bar.contains(event)[0]:
                    self.show_tooltip(event, i + 1, 'income')
                    return
        
        # Check Expense Bars
        if self.bars_expense:
            for i, bar in enumerate(self.bars_expense):
                if bar.contains(event)[0]:
                    self.show_tooltip(event, i + 1, 'expense')
                    return

    def show_tooltip(self, event, month, type_key):
        if not self.chart_data: return
        
        month_data = self.chart_data.get(month, {})
        if not month_data: return
        
        # Access details structure
        # New Structure: {'Category': {'total': x, 'subs': {'Sub': y}}}
        details = month_data.get('details', {}).get(type_key, {})
        
        if not details:
            QToolTip.showText(QCursor.pos(), "No details available")
            return
            
        # Sort by Category Total Amount descending
        sorted_cats = sorted(details.items(), key=lambda x: x[1]['total'], reverse=True)
        
        # Build tooltip text
        title = "Income" if type_key == 'income' else "Expenses"
        
        # Style: Bold Category, Indented Subcategories
        lines = []
        
        for cat_name, cat_data in sorted_cats:
            cat_total = cat_data['total']
            # Category Line (Bold)
            lines.append(f"<b>{cat_name}: {cat_total:,.2f}</b>")
            
            # Subcategories (Sorted Descending)
            subs = cat_data.get('subs', {})
            sorted_subs = sorted(subs.items(), key=lambda x: x[1], reverse=True)
            
            for sub_name, sub_val in sorted_subs:
                # Indent subcategories
                lines.append(f"&nbsp;&nbsp;{sub_name}: {sub_val:,.2f}")
            
        text = "<br>".join(lines)
        QToolTip.showText(QCursor.pos(), text)
