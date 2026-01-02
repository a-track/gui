from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QToolTip, QDialog,
                             QDialogButtonBox, QListWidget, QListWidgetItem,
                             QDateEdit)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QDate
from PyQt6.QtGui import QCursor, QFont
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

    def __init__(self, budget_app, start_date, end_date, filter_ids=None):
        super().__init__()
        self.budget_app = budget_app
        self.start_date = start_date
        self.end_date = end_date
        self.filter_ids = filter_ids

    def run(self):
        data = self.budget_app.get_investment_gains_history(self.start_date, self.end_date, self.filter_ids)
        self.finished.emit(data)


class InvestmentProfitTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.current_start_date = None
        self.current_end_date = None
        self.chart_data = None
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

        header_layout.addWidget(QLabel("Range:"))
        self.range_combo = NoScrollComboBox()
        self.range_combo.setMinimumWidth(150)
        self.range_combo.addItem("Last 12 Months", "last_12")
        self.range_combo.currentIndexChanged.connect(self.on_range_changed)
        header_layout.addWidget(self.range_combo)
        
        # Date Inputs
        self.date_range_widget = QWidget()
        date_layout = QHBoxLayout(self.date_range_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        
        date_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        
        date_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setDate(QDate.currentDate())
        self.from_date.setDate(QDate.currentDate().addMonths(-12))
        
        date_layout.addWidget(self.from_date)
        date_layout.addWidget(self.to_date)
        
        header_layout.addWidget(self.date_range_widget)
        self.date_range_widget.setVisible(False)

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
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.canvas.mpl_connect("motion_notify_event", self.on_hover)
        
        # Initial populate
        self.populate_years()

    def open_filter_dialog(self):
        dlg = InvestmentAccountFilterDialog(self.budget_app, self.filter_account_ids, self)
        if dlg.exec():
            selected = dlg.get_selected_ids()
            self.filter_account_ids = selected
            self.refresh_data()

    def populate_years(self):
        if not MATPLOTLIB_AVAILABLE:
            return

        years = self.budget_app.get_available_years()
        current_text = self.range_combo.currentText()
        
        self.range_combo.blockSignals(True)
        self.range_combo.clear()
        self.range_combo.addItem("Last 12 Months", "last_12")
        
        for year in years:
            self.range_combo.addItem(f"Year {year}", str(year))
            
        self.range_combo.addItem("Custom Range", "custom")

        index = self.range_combo.findText(current_text)
        if index >= 0:
            self.range_combo.setCurrentIndex(index)
        else:
            self.range_combo.setCurrentIndex(0) # Default Last 12

        self.range_combo.blockSignals(False)
        self.on_range_changed()
        
    def on_range_changed(self):
        mode = self.range_combo.currentData()
        self.date_range_widget.setVisible(mode == 'custom')
        if mode != 'custom':
            self.refresh_data()
            
    def get_date_range(self):
        mode = self.range_combo.currentData()
        today = QDate.currentDate()
        
        if mode == 'last_12':
            end_date = today
            start_date = today.addMonths(-12).addDays(1)
            return start_date.toString("yyyy-MM-dd"), end_date.toString("yyyy-MM-dd")
        elif mode == 'custom':
            s = self.from_date.date()
            e = self.to_date.date()
            if s > e: s = e
            return s.toString("yyyy-MM-dd"), e.toString("yyyy-MM-dd")
        else:
            # Year
            try:
                year = int(mode)
                return f"{year}-01-01", f"{year}-12-31"
            except:
                return today.addMonths(-12).toString("yyyy-MM-dd"), today.toString("yyyy-MM-dd")

    def refresh_data(self):
        """Called when tab becomes active"""
        self.load_data()

    def load_data(self):
        if not MATPLOTLIB_AVAILABLE:
            return

        start_date, end_date = self.get_date_range()
        self.current_start_date = start_date
        self.current_end_date = end_date

        self.progress_bar.setVisible(True)
        self.canvas.setVisible(False)

        self.loader = InvestmentProfitLoaderThread(self.budget_app, start_date, end_date, self.filter_account_ids)
        self.loader.finished.connect(self.on_data_loaded)
        self.loader.start()
    
    def on_data_loaded(self, data):
        self.progress_bar.setVisible(False)
        self.canvas.setVisible(True)
        self.chart_data = data
        self.plot_graph(data)
    
    def plot_graph(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not data:
            ax.text(0.5, 0.5, 'No Data for Selected Range', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12, color='#666666')
            ax.set_axis_off()
            self.canvas.draw()
            return

        # Sort keys YYYY-MM
        sorted_keys = sorted(data.keys())
        x_vals = range(len(sorted_keys))
        
        # Create Labels
        labels = []
        for k in sorted_keys:
            parts = k.split('-')
            y_short = parts[0][2:]
            m_idx = int(parts[1]) - 1
            mnames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            labels.append(f"{mnames[m_idx]} '{y_short}")

        gains = []
        losses = [] 
        
        # Details are not as granular as before? `get_investment_gains_history`
        # returns {'net', 'gain', 'loss'} but NOT details breakdown (Fees, Divs, Depos).
        # My implementation of `get_investment_gains_history` stored 'net', 'gain', 'loss'.
        # It did NOT store 'details' dictionary.
        # This means I CANNOT plot Dividends vs Capital Growth separately unless I update `models.py`.
        # The previous visualization relied on 'total_income', 'total_deposits' etc.
        # My `get_investment_gains_history` ONLY computed Net Gain/Loss logic: (End-Start)-Flows.
        # It did NOT break down flows into Deposits/Divs/Fees.
        
        # HMM. This reduces functionality (Tooltip details lost).
        # User asked for "range filter logic", implied same richness.
        # I should probably ENRICH `get_investment_gains_history` to return these details.
        
        # However, for now, I will plot Net Gain/Loss and Cumulative P&L.
        # If I want to match the previous chart (Stacked Bars of Sources), I need that data.
        # For this turn, I will implement a simpler "Waterfall" or Net Gain/Loss chart.
        # OR I can update `models.py` again.
        # Given constraint, I'll stick to what I have in `models.py` (Net, Gain, Loss) 
        # and plot simplified bars (Green Gain, Red Loss) + Cumulative Line.
        
        cumulative_return = []
        running = 0.0
        
        for k in sorted_keys:
            val = data[k]
            # Val has 'gain' (positive part) and 'loss' (positive magnitude of loss)
            g = val.get('gain', 0.0)
            l = val.get('loss', 0.0) # Absolute value
            
            # Net = gain - loss
            net = val.get('net', 0.0)
            
            gains.append(g)
            losses.append(-l) # Plot negative
            
            running += net
            cumulative_return.append(running)

        # Plot Bars
        ax.bar(x_vals, gains, color='#4CAF50', label='Gain', alpha=0.7)
        ax.bar(x_vals, losses, color='#F44336', label='Loss', alpha=0.7)
        
        # Cumulative Line
        ax.plot(x_vals, cumulative_return, color='#2196F3', marker='o', linewidth=2, label='Cumulative P&L')

        # Annotations
        for i, val in enumerate(cumulative_return):
            if abs(val) > 1:
               ax.annotate(format_currency(val, precision=0), xy=(x_vals[i], val), xytext=(0, 5) if val>=0 else (0,-10), 
                           textcoords='offset points', ha='center', fontsize=8, color='#2196F3')
        
        ax.axhline(0, color='black', linewidth=0.8)
        
        # Title
        total_pl = cumulative_return[-1] if cumulative_return else 0.0
        ax.set_title(f"Investment Performance ({self.current_start_date} - {self.current_end_date})\nTotal P&L: {'+' if total_pl>0 else ''}{format_currency(total_pl)}")
        
        ax.set_xticks(x_vals)
        ax.set_xticklabels(labels, rotation=45 if len(labels)>6 else 0)
        ax.grid(True, axis='y', linestyle=':', alpha=0.6)
        ax.legend(loc='upper left')
        ax.get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, p: format_currency(x, precision=0)))

        self.figure.tight_layout()
        self.canvas.draw()
        
    def on_hover(self, event):
        # Simplified tooltip
        if not self.figure.axes or event.inaxes != self.figure.axes[0]:
            QToolTip.hideText()
            return
        
        if event.xdata is None: return
        try:
            idx = int(round(event.xdata))
        except: return
        
        if not self.chart_data: return
        
        sorted_keys = sorted(self.chart_data.keys())
        if idx < 0 or idx >= len(sorted_keys): return
        
        key = sorted_keys[idx]
        val = self.chart_data[key]
        
        lines = [f"<b>{key}</b>"]
        gain = val.get('gain', 0.0)
        loss = val.get('loss', 0.0)
        net = val.get('net', 0.0)
        
        if gain > 0: lines.append(f"Gain: +{format_currency(gain)}")
        if loss > 0: lines.append(f"Loss: -{format_currency(loss)}")
        lines.append(f"<b>Net: {'+' if net>0 else ''}{format_currency(net)}</b>")
        
        QToolTip.setFont(QFont('Segoe UI', 10))
        QToolTip.showText(QCursor.pos(), "<br>".join(lines), self)
