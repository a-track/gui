

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QDateEdit)
from PyQt6.QtCore import Qt, QDate
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


class ReportTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        if not MATPLOTLIB_AVAILABLE:
            error_label = QLabel("⚠️ Matplotlib is not installed.")
            error_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #f44336;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addStretch()
            layout.addWidget(error_label)
            layout.addStretch()
            return

        header_layout = QHBoxLayout()

        header_layout.addWidget(QLabel("Range:"))
        self.range_combo = NoScrollComboBox()
        self.range_combo.setMinimumWidth(150)
        self.range_combo.addItem("Last 12 Months", "last_12")
        self.range_combo.currentIndexChanged.connect(self.on_range_changed)
        header_layout.addWidget(self.range_combo)

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

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet("padding: 5px 10px;")
        header_layout.addWidget(refresh_btn)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        self.populate_years()
        self.refresh_data()

    def populate_years(self):
        """Populate year range combo"""
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
            self.range_combo.setCurrentIndex(0)

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
            try:
                year = int(mode)
                return f"{year}-01-01", f"{year}-12-31"
            except:
                return today.addMonths(-12).toString("yyyy-MM-dd"), today.toString("yyyy-MM-dd")

    def refresh_data(self):
        start_date, end_date = self.get_date_range()
        self.load_data(start_date, end_date)

    def load_data(self, start_date, end_date):
        if not MATPLOTLIB_AVAILABLE:
            return

        self.canvas.setVisible(True)
        self.message_label.hide()

        try:
            data = self.budget_app.get_net_worth_history(start_date, end_date)
            self.plot_graph(data, start_date, end_date)
        except Exception as e:
            print(f"Error loading report: {e}")
            self.message_label.setText(f"Error: {e}")
            self.message_label.show()
            self.canvas.hide()

    def plot_graph(self, data, start_date, end_date):
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        sorted_keys = sorted(data.keys())
        if not sorted_keys:
            self.message_label.setText("No data for selected range")
            self.message_label.show()
            self.canvas.hide()
            return
            
        x_vals = range(len(sorted_keys))
        y_vals = [data[k] for k in sorted_keys]
        
        line = ax.plot(x_vals, y_vals, marker='o', linewidth=2, color='#2196F3', label='Net Worth')
        
        ax.fill_between(x_vals, y_vals, color='#2196F3', alpha=0.1)

        if y_vals:
            last_val = y_vals[-1]
            last_x = x_vals[-1]
            ax.annotate(f'{format_currency(last_val)}', xy=(last_x, last_val),
                        xytext=(5, 5), textcoords='offset points',
                        color='#2196F3', fontweight='bold')

        ax.set_title(f'Balance Evolution ({start_date} to {end_date})')
        ax.set_ylabel('Net Worth (CHF)')
        
        labels = []
        for k in sorted_keys:
            parts = k.split('-')
            year_short = parts[0][2:]
            month_idx = int(parts[1]) - 1
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            labels.append(f"{month_names[month_idx]} '{year_short}")
            
        ax.set_xticks(x_vals)
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 6 else 0)
        
        ax.grid(True, linestyle=':', alpha=0.6)
        
        ax.get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, p: format(int(x), ",").replace(",", "'"))) 

        self.figure.tight_layout()
        self.canvas.draw()
