
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMenu, QToolButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction


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
        self.selected_years = set()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        if not MATPLOTLIB_AVAILABLE:
            error_label = QLabel("⚠️ Matplotlib is not installed.")
            error_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #f44336;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            hint_label = QLabel("Please run: pip install matplotlib")
            hint_label.setStyleSheet("font-size: 14px; color: #666;")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            layout.addStretch()
            layout.addWidget(error_label)
            layout.addWidget(hint_label)
            layout.addStretch()
            return

        header_layout = QHBoxLayout()

        self.year_btn = QToolButton()
        self.year_btn.setText("Select Years 📅")
        self.year_btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup)
        self.year_menu = QMenu(self)
        self.year_btn.setMenu(self.year_menu)

        self.year_btn.setStyleSheet("""
            QToolButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f0f0f0;
            }
            QToolButton:hover { background-color: #e0e0e0; }
            QToolButton::menu-indicator { image: none; }
        """)
        header_layout.addWidget(self.year_btn)



        header_layout.addStretch()
        layout.addLayout(header_layout)



        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.message_label)

    def populate_years(self):
        if not MATPLOTLIB_AVAILABLE:
            return

        years = self.budget_app.get_available_years()
        self.year_menu.clear()

        if not years:
            self.year_btn.setEnabled(False)
            return

        self.year_btn.setEnabled(True)

        if not self.selected_years and years:
            self.selected_years.add(years[0])

        for year in years:
            action = QAction(str(year), self)
            action.setCheckable(True)
            action.setChecked(year in self.selected_years)
            action.triggered.connect(
                lambda checked, y=year: self.toggle_year(y, checked))
            self.year_menu.addAction(action)

    def toggle_year(self, year, checked):
        if checked:
            self.selected_years.add(year)
        else:
            self.selected_years.discard(year)
        self.load_data()

    def refresh_data(self):
        """Called when tab becomes active or user clicks Refresh"""
        self.populate_years()
        self.load_data()

    def load_data(self):
        if not MATPLOTLIB_AVAILABLE:
            return

        if not self.selected_years:
            self.figure.clear()
            self.canvas.draw()
            return

        sorted_years = sorted(list(self.selected_years))

        self.canvas.setVisible(True)
        self.message_label.hide()

        try:
            data = {}
            for year in sorted_years:
                data[year] = self.budget_app.get_monthly_balances(year)
            
            self.plot_graph(data)
        except Exception as e:
            print(f"Error loading report: {e}")

    def plot_graph(self, data):
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        months = range(1, 13)
        month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
                        'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        import datetime
        current_date = datetime.date.today()
        current_year = current_date.year
        current_month = current_date.month

        for year in sorted(data.keys()):
            year_data = data_to_list(data[year])
            
            x_vals = list(months)
            y_vals = year_data

            if year == current_year:
                x_vals = x_vals[:current_month]
                y_vals = y_vals[:current_month]
            elif year > current_year:
                continue

            line = ax.plot(x_vals, y_vals, marker='o',
                           linewidth=2, label=str(year))

            if y_vals:
                last_val = y_vals[-1]
                last_x = x_vals[-1]
                
                if last_val > 0:
                    color = line[0].get_color()
                    ax.annotate(f'{last_val:,.0f}', xy=(last_x, last_val),
                                xytext=(5, 0), textcoords='offset points',
                                color=color, fontweight='bold')

        ax.set_title('Balance Evolution')
        ax.set_ylabel('Net Worth (CHF)')
        ax.set_xticks(months)
        ax.set_xticklabels(month_labels)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend()

        ax.get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, p: format(int(x), ',')))

        self.figure.tight_layout()
        self.canvas.draw()


def data_to_list(data_dict):
    """Convert dict {1: val, ...} to list [val, ...] sorted by key"""
    return [data_dict.get(m, 0.0) for m in range(1, 13)]
