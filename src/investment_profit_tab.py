from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QToolTip, QDialog,
                             QDialogButtonBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QCursor, QFont
from custom_widgets import NoScrollComboBox

MATPLOTLIB_AVAILABLE = False
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class InvestmentAccountFilterDialog(QDialog):
    def __init__(self, budget_app, selected_ids=None, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.selected_ids = set(selected_ids) if selected_ids else set()
        self.setWindowTitle("Filter Investment Accounts")
        self.setMinimumSize(300, 400)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.populate_list()

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        btns_layout = QHBoxLayout()
        all_btn = QPushButton("Select All")
        all_btn.clicked.connect(self.select_all)
        none_btn = QPushButton("Select None")
        none_btn.clicked.connect(self.select_none)
        btns_layout.addWidget(all_btn)
        btns_layout.addWidget(none_btn)
        layout.addLayout(btns_layout)

        layout.addWidget(btn_box)

    def populate_list(self):
        accounts = self.budget_app.get_all_accounts()
        # Filter for investment accounts only
        inv_accounts = [acc for acc in accounts if getattr(acc, 'is_investment', False)]
        
        for acc in inv_accounts:
            item = QListWidgetItem(f"{acc.account} ({acc.currency})")
            item.setData(Qt.ItemDataRole.UserRole, acc.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            if not self.selected_ids or acc.id in self.selected_ids:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            
            self.list_widget.addItem(item)
            
    def get_selected_ids(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected

    def select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def select_none(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)


class InvestmentProfitLoaderThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, budget_app, year, filter_ids=None):
        super().__init__()
        self.budget_app = budget_app
        self.year = year
        self.filter_ids = filter_ids

    def run(self):
        data = self.budget_app.get_monthly_investment_gains(self.year, self.filter_ids)
        self.finished.emit(data)


class InvestmentProfitTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.current_year = None
        self.chart_data = None
        self.bars_gains = None
        self.bars_losses = None
        self.filter_account_ids = None # None means all
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if self.chart_data is None:
            self.refresh_data()

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

        filter_btn = QPushButton("Filter Accounts")
        filter_btn.clicked.connect(self.open_filter_dialog)
        header_layout.addWidget(filter_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet("padding: 5px 10px;")
        header_layout.addWidget(refresh_btn)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def open_filter_dialog(self):
        dlg = InvestmentAccountFilterDialog(self.budget_app, self.filter_account_ids, self)
        if dlg.exec():
            selected = dlg.get_selected_ids()
            # If all are selected, or none (which implies all?), we can optimize or just update
            # Logic: If user selects None, maybe show none? Or show all? Usually empty means empty.
            self.filter_account_ids = selected
            self.refresh_data()

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
            now_year = str(datetime.now().year)
            idx = self.year_combo.findText(now_year)
            if idx >= 0:
                self.year_combo.setCurrentIndex(idx)
            else:
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

        self.loader = InvestmentProfitLoaderThread(self.budget_app, year, self.filter_account_ids)
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

        if not data:
            ax.text(0.5, 0.5, 'No Data for Selected Accounts/Year', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12, color='#666666')
            ax.set_axis_off()
            self.canvas.draw()
            return

        max_month = 12
        now = datetime.now()
        if self.current_year == now.year:
            max_month = now.month

        months = list(range(1, max_month + 1))
        all_month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
                            'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month_labels = all_month_labels[:max_month]

        gains = []
        losses = []  # stored as negative numbers
        income_list = []
        expense_list = [] # stored as positive usually, but we plot as negative or subtraction?
        # Expense is positive in result, we want to plot downwards.
        
        deposits_list = []
        withdrawals_list = [] # stored as positive in result, we plot downwards.
        
        cumulative_return = []
        cumulative_net_flows = []
        
        running_return = 0.0
        running_flow_total = 0.0

        for m in months:
            val = data.get(m, {})
            # Price P&L
            g = val.get('total_gain', 0.0)
            l = val.get('total_loss', 0.0)
            
            # Income/Expense (Dividends/Fees)
            inc = val.get('total_income', 0.0)
            exp = val.get('total_expense', 0.0)
            
            # Capital Flows
            dep = val.get('total_deposits', 0.0)
            wdr = val.get('total_withdrawals', 0.0) # Positive value
            
            gains.append(g)
            losses.append(l)
            income_list.append(inc)
            # We plot expenses downwards
            expense_list.append(-exp) 
            deposits_list.append(dep)
            withdrawals_list.append(-wdr) 
            
            # Blue Line: Total Return (Price P&L + Net Income)
            # Net Income = inc - exp
            # Price P&L = g + l (l is negative)
            # Total Return for month = (g + l) + (inc - exp)
            monthly_return = (g + l) + (inc - exp)
            running_return += monthly_return
            
            # Purple Line: Net Invested Capital (Deposits - Withdrawals)
            # Net Flow = dep - wdr
            running_flow_total += (dep - wdr)
            
            cumulative_return.append(running_return)
            cumulative_net_flows.append(running_flow_total)

        # Plot Stacked Bars
        # Order: 
        # Positive: Gains -> Income -> Deposits
        # Negative: Losses -> Expenses -> Withdrawals
        
        # 1. Price Gains (Green)
        self.bars_gains = ax.bar(months, gains, color='#4CAF50', label='Market Gains', alpha=0.7)
        
        # 2. Income/Dividends (Orange) on top of Gains
        self.bars_income = ax.bar(months, income_list, bottom=gains, color='#FF9800', label='Dividends/Fees', alpha=0.8)
        
        # Calculate bottom for Deposits (Gains + Income)
        bottom_deposits = [g + i for g, i in zip(gains, income_list)]
        
        # 3. Deposits (Light Blue) on top of (Gains + Income)
        self.bars_inflows = ax.bar(months, deposits_list, bottom=bottom_deposits, color='#29B6F6', label='Deposits/Withdrawals', alpha=0.7)
        
        # Negative Side
        # 1. Price Losses (Red)
        self.bars_losses = ax.bar(months, losses, color='#F44336', label='Market Losses', alpha=0.7)
        
        # 2. Expenses/Fees (Orange - Same as Divs) below Losses
        # Note: losses are negative, expense_list is negative.
        self.bars_expense = ax.bar(months, expense_list, bottom=losses, color='#FF9800', label='_nolegend_', alpha=0.8)
        
        # Calculate bottom for Withdrawals (Losses + Expenses)
        bottom_withdrawals = [l + e for l, e in zip(losses, expense_list)]
        
        # 3. Withdrawals (Light Blue) below (Losses + Expenses)
        self.bars_outflows = ax.bar(months, withdrawals_list, bottom=bottom_withdrawals, color='#29B6F6', label='_nolegend_', alpha=0.7)
        # Lines
        ax.plot(months, cumulative_return, color='#2196F3',
                marker='o', linewidth=2, label='Market P&L (Total Return)')
                
        # ax.plot(months, cumulative_net_flows, color='#9C27B0',
        #         marker='s', linewidth=2, label='Net Invested Capital')

        # Annotate Blue Line (Market Performance - Total Return)
        for i, val in enumerate(cumulative_return):
            if abs(val) > 1:
                ax.annotate(f'{int(val):,}', xy=(months[i], val), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=8, color='#2196F3')

        # Annotate Purple Line (Net Invested Capital)
        # for i, val in enumerate(cumulative_net_flows):
        #     if abs(val) > 1:
        #         ax.annotate(f'{int(val):,}', xy=(months[i], val), xytext=(0, -10), textcoords='offset points', ha='center', fontsize=8, color='#9C27B0')

        ax.axhline(0, color='black', linewidth=0.8)

        # Calculate YTD Totals
        ytd_gains = sum(gains)
        ytd_divs = sum(income_list)
        ytd_losses = sum(losses)
        ytd_fees = sum(expense_list) # already negative
        ytd_return = cumulative_return[-1] if cumulative_return else 0.0
        
        ytd_net_price = ytd_gains + ytd_losses
        ytd_net_flows = sum(deposits_list) + sum(withdrawals_list)

        # Format Header Title
        title_text = f'Investment Performance ({self.current_year})'
        subtitle_text = (f"Total Return: {ytd_return:+,.0f} | "
                         f"Net Price Gains: {ytd_net_price:+,.0f} | "
                         f"Divs: {ytd_divs:+,.0f} | Fees: {ytd_fees:+,.0f} | "
                         f"Net Deposits: {ytd_net_flows:+,.0f}")
        
        ax.set_title(f"{title_text}\n{subtitle_text}", fontsize=10)
        
        ax.set_ylabel('Profit/Loss (CHF)')
        ax.set_xticks(months)
        ax.set_xticklabels(month_labels)
        ax.grid(True, axis='y', linestyle=':', alpha=0.6)

        # Force legend location to ensure visibility
        ax.legend(loc='upper left')
        ax.get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, p: format(int(x), ',')))

        self.figure.tight_layout()
        self.canvas.draw()

    val = None # Placeholder if needed
    
    def on_hover(self, event):
        if not self.figure.axes or event.inaxes != self.figure.axes[0]:
            # Clear tooltip if moved out of axes
            if getattr(self, 'last_tooltip_state', None) is not None:
                self.last_tooltip_state = None
                QToolTip.hideText()
            return
            
        # Position-Based Tooltip Logic
        if event.xdata is None or event.ydata is None:
            return
            
        try:
            # Round xdata to nearest integer to get month index (1-based)
            month = int(round(event.xdata))
        except (ValueError, TypeError):
            return
        
        # Check bounds
        max_month = len(self.chart_data) if self.chart_data else 12
        if month < 1 or month > max_month:
            return
            
        # Determine Positive/Negative Zone
        zone = 'combined_positive' if event.ydata >= 0 else 'combined_negative'
        
        # State Check (Debounce)
        current_state = (month, zone)
        if getattr(self, 'last_tooltip_state', None) == current_state:
            return
            
        self.last_tooltip_state = current_state
        self.show_tooltip(event, month, zone)

    def show_tooltip(self, event, month, category):
        if not self.chart_data:
            return

        month_data = self.chart_data.get(month, {})
        details = month_data.get('details', {})
        flow_details = details.get('flows', {})
        
        lines = []

        if category == 'combined_positive':
            # Gather all positive components: Market Gains, Dividends, Deposits
            
            # 1. Deposits
            deposits = {k:v for k,v in flow_details.items() if v > 0}
            
            # 2. Dividends (Detailed)
            income_details = details.get('income', {})
            total_income = month_data.get('total_income', 0.0)
            
            # 3. Market Gains
            gains = details.get('gains', {})
            
            # Build list
            has_content = False
            
            if deposits:
                lines.append("<b>— Deposits —</b>")
                for k,v in sorted(deposits.items(), key=lambda x: abs(x[1]), reverse=True):
                    lines.append(f"{k}: {v:+,.2f}")
                has_content = True
                
            if income_details:
                if has_content: lines.append("")
                lines.append("<b>— Dividends —</b>")
                for k,v in sorted(income_details.items(), key=lambda x: abs(x[1]), reverse=True):
                    lines.append(f"{k}: {v:+,.2f}")
                has_content = True
            elif abs(total_income) > 0.01:
                if has_content: lines.append("")
                lines.append("<b>— Dividends —</b>")
                lines.append(f"Total: {total_income:+,.2f}")
                has_content = True
                
            if gains:
                if has_content: lines.append("")
                lines.append("<b>— Price Gains —</b>")
                for k,v in sorted(gains.items(), key=lambda x: abs(x[1]), reverse=True):
                    lines.append(f"{k}: {v:+,.2f}")

        elif category == 'combined_negative':
            # Gather all negative components: Market Losses, Fees, Withdrawals
            
            # 1. Withdrawals
            withdrawals = {k:v for k,v in flow_details.items() if v < 0}
            
            # 2. Fees (Detailed)
            expense_details = details.get('expense', {})
            total_expense = month_data.get('total_expense', 0.0)
            
            # 3. Market Losses
            losses = details.get('losses', {})
            
            has_content = False
            
            if withdrawals:
                lines.append("<b>— Withdrawals —</b>")
                for k,v in sorted(withdrawals.items(), key=lambda x: abs(x[1]), reverse=True):
                    lines.append(f"{k}: {v:+,.2f}")
                has_content = True
                
            if expense_details:
                if has_content: lines.append("")
                lines.append("<b>— Fees/Taxes —</b>")
                for k,v in sorted(expense_details.items(), key=lambda x: abs(x[1]), reverse=True):
                    # Expense details are stored positive, display as negative
                    lines.append(f"{k}: {-v:+,.2f}")
                has_content = True
            elif abs(total_expense) > 0.01:
                if has_content: lines.append("")
                lines.append("<b>— Fees/Taxes —</b>")
                lines.append(f"Total: {-total_expense:+,.2f}")
                has_content = True
                
            if losses:
                if has_content: lines.append("")
                lines.append("<b>— Price Losses —</b>")
                for k,v in sorted(losses.items(), key=lambda x: abs(x[1]), reverse=True):
                    lines.append(f"{k}: {v:+,.2f}")

        if lines:
            QToolTip.setFont(QFont('Segoe UI', 10))
            QToolTip.showText(QCursor.pos(), "<br>".join(lines), self)
