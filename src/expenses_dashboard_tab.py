from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QDialog, QDialogButtonBox, QTreeWidget,
                             QTreeWidgetItem, QTreeWidgetItemIterator)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import datetime
import math
from custom_widgets import NoScrollComboBox


class CategoryFilterDialog(QDialog):
    def __init__(self, budget_app, selected_ids=None, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.selected_ids = set(selected_ids) if selected_ids else set()
        self.setWindowTitle("Filter Categories")
        self.setMinimumSize(400, 500)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.tree)

        self.populate_tree()

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        filter_actions = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(self.select_all)
        btn_none = QPushButton("Select None")
        btn_none.clicked.connect(self.select_none)
        filter_actions.addWidget(btn_all)
        filter_actions.addWidget(btn_none)
        filter_actions.addStretch()

        layout.addLayout(filter_actions)
        layout.addWidget(btn_box)

    def populate_tree(self):
        categories = self.budget_app.get_all_categories()

        grouped = {}

        for cat in categories:

            if cat.category_type != 'Expense':
                continue

            main = cat.category
            if main not in grouped:
                grouped[main] = []
            grouped[main].append(cat)

        block = self.tree.blockSignals(True)

        for main_name, cats in sorted(grouped.items()):
            parent_item = QTreeWidgetItem(self.tree)
            parent_item.setText(0, main_name)
            parent_item.setFlags(parent_item.flags(
            ) | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

            all_checked = True
            any_checked = False

            for cat in cats:
                child = QTreeWidgetItem(parent_item)
                child.setText(0, cat.sub_category)
                child.setData(0, Qt.ItemDataRole.UserRole, cat.id)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)

                if not self.selected_ids or cat.id in self.selected_ids:
                    child.setCheckState(0, Qt.CheckState.Checked)
                    any_checked = True
                else:
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    all_checked = False

            if not self.selected_ids:
                parent_item.setCheckState(0, Qt.CheckState.Checked)
            elif all_checked:
                parent_item.setCheckState(0, Qt.CheckState.Checked)
            elif any_checked:
                parent_item.setCheckState(0, Qt.CheckState.PartiallyChecked)
            else:
                parent_item.setCheckState(0, Qt.CheckState.Unchecked)

        self.tree.expandAll()
        self.tree.blockSignals(block)

    def on_item_changed(self, item, column):

        pass

    def get_selected_ids(self):
        selected = []

        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            cat_id = item.data(0, Qt.ItemDataRole.UserRole)
            if cat_id and item.checkState(0) == Qt.CheckState.Checked:
                selected.append(cat_id)
            iterator += 1
        return selected

    def select_all(self):
        self.set_all_checkstate(Qt.CheckState.Checked)

    def select_none(self):
        self.set_all_checkstate(Qt.CheckState.Unchecked)

    def set_all_checkstate(self, state):
        self.tree.blockSignals(True)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setCheckState(0, state)

            for j in range(item.childCount()):
                item.child(j).setCheckState(0, state)
        self.tree.blockSignals(False)


try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class DashboardLoaderThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, budget_app, year, month, filter_ids=None):
        super().__init__()
        self.budget_app = budget_app
        self.year = year
        self.month = month
        self.filter_ids = filter_ids

    def run(self):
        try:

            breakdown = self.budget_app.get_expenses_breakdown(
                self.year, self.month, self.filter_ids)

            trend_data = self.budget_app.get_monthly_expense_trend(
                self.year, self.month, self.filter_ids)

            top_payees = self.budget_app.get_top_payees(
                self.year, self.month, limit=10, category_ids=self.filter_ids)

            total_expense = sum(cat['total'] for cat in breakdown.values())

            data = {
                'breakdown': breakdown,
                'trend': trend_data,
                'top_payees': top_payees,
                'total_expense': total_expense,
                'year': self.year,
                'month': self.month
            }
            self.finished.emit(data)
        except Exception as e:
            print(f"Error in dashboard loader: {e}")
            self.finished.emit({})


class KPICard(QFrame):
    def __init__(self, title, value, subtitle="", color="#333", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            KPICard {{
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }}
            QLabel {{ border: none; }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #666; font-size: 14px; font-weight: bold;")
        layout.addWidget(title_lbl)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            f"color: {color}; font-size: 24px; font-weight: bold;")
        layout.addWidget(value_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color: #999; font-size: 12px;")
            layout.addWidget(sub_lbl)

        layout.addStretch()
        self.setLayout(layout)


class ExpensesDashboardTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app

        today = datetime.date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.filter_category_ids = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setLayout(main_layout)

        if not MATPLOTLIB_AVAILABLE:
            main_layout.addWidget(
                QLabel("Matplotlib is required for this dashboard."))
            return

        header_layout = QHBoxLayout()

        title = QLabel("Expenses Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        header_layout.addWidget(QLabel("Year:"))
        self.year_combo = NoScrollComboBox()
        self.populate_years()
        self.year_combo.currentTextChanged.connect(self.on_filter_changed)
        header_layout.addWidget(self.year_combo)

        header_layout.addWidget(QLabel("Month:"))
        self.month_combo = NoScrollComboBox()

        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        self.month_combo.addItems(months)

        self.month_combo.setCurrentIndex(self.current_month - 1)
        self.month_combo.currentIndexChanged.connect(self.on_filter_changed)
        header_layout.addWidget(self.month_combo)

        btn_filter = QPushButton("Filter Categories")
        btn_filter.clicked.connect(self.open_filter_dialog)
        header_layout.addWidget(btn_filter)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(btn_refresh)

        main_layout.addLayout(header_layout)

        self.kpi_layout = QHBoxLayout()
        self.kpi_total = KPICard("Total Expenses", "CHF 0.00", color="#D32F2F")
        self.kpi_avg = KPICard(
            "12-Month Average", "CHF 0.00", "Based on trailing 12m", color="#1976D2")
        self.kpi_top = KPICard("Top Category", "None",
                               "CHF 0.00", color="#388E3C")

        self.kpi_layout.addWidget(self.kpi_total)
        self.kpi_layout.addWidget(self.kpi_avg)
        self.kpi_layout.addWidget(self.kpi_top)

        main_layout.addLayout(self.kpi_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        self.fig_pie = Figure(figsize=(6, 6), dpi=100)
        self.canvas_pie = FigureCanvas(self.fig_pie)
        self.frame_pie = self.wrap_chart("Category Breakdown", self.canvas_pie)
        content_layout.addWidget(self.frame_pie, stretch=3)

        right_col = QVBoxLayout()
        right_col.setSpacing(20)

        self.fig_line = Figure(figsize=(5, 3), dpi=100)
        self.canvas_line = FigureCanvas(self.fig_line)
        self.frame_line = self.wrap_chart("12-Month Trend", self.canvas_line)
        right_col.addWidget(self.frame_line, stretch=2)

        self.fig_bar = Figure(figsize=(5, 4), dpi=100)
        self.canvas_bar = FigureCanvas(self.fig_bar)
        self.frame_bar = self.wrap_chart("Top Payees", self.canvas_bar)
        right_col.addWidget(self.frame_bar, stretch=3)

        content_layout.addLayout(right_col, stretch=2)

        main_layout.addLayout(content_layout, stretch=1)

        self.load_data()

    def wrap_chart(self, title_text, widget):
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: white; border-radius: 8px; border: 1px solid #e0e0e0;")
        layout = QVBoxLayout()
        title = QLabel(title_text)
        title.setStyleSheet(
            "font-weight: bold; font-size: 14px; border: none; padding-bottom: 5px;")
        layout.addWidget(title)
        layout.addWidget(widget)
        frame.setLayout(layout)
        return frame

    def populate_years(self):
        years = self.budget_app.get_available_years()
        if not years:
            years = [self.current_year]

        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        self.year_combo.addItems([str(y) for y in years])
        self.year_combo.setCurrentText(str(self.current_year))
        self.year_combo.blockSignals(False)

    def on_filter_changed(self):
        try:
            self.current_year = int(self.year_combo.currentText())

            self.current_month = self.month_combo.currentIndex() + 1
            self.load_data()
        except:
            pass

    def open_filter_dialog(self):
        dlg = CategoryFilterDialog(
            self.budget_app, self.filter_category_ids, self)
        if dlg.exec():
            self.filter_category_ids = dlg.get_selected_ids()

            if not self.filter_category_ids:

                pass
            self.load_data()

    def load_data(self):
        if not MATPLOTLIB_AVAILABLE:
            return

        self.loader = DashboardLoaderThread(
            self.budget_app, self.current_year, self.current_month, self.filter_category_ids)
        self.loader.finished.connect(self.update_dashboard)
        self.loader.start()

    def update_dashboard(self, data):
        if not data:
            return

        self.update_kpis(data)
        self.plot_pie(data['breakdown'])
        self.plot_line(data['trend'])
        self.plot_bar(data['top_payees'])

    def update_kpis(self, data):
        total = data['total_expense']
        self.kpi_total.findChildren(QLabel)[1].setText(f"CHF {total:,.2f}")

        trend = data['trend']
        if trend:
            total_trend = sum(t['amount'] for t in trend)
            avg = total_trend / len(trend)
            self.kpi_avg.findChildren(QLabel)[1].setText(f"CHF {avg:,.2f}")
        else:
            self.kpi_avg.findChildren(QLabel)[1].setText("CHF 0.00")

        breakdown = data['breakdown']
        if breakdown:

            top_cat = max(breakdown.items(), key=lambda x: x[1]['total'])
            name = top_cat[0]
            val = top_cat[1]['total']
            self.kpi_top.findChildren(QLabel)[1].setText(name)
            self.kpi_top.findChildren(QLabel)[2].setText(f"CHF {val:,.2f}")
        else:
            self.kpi_top.findChildren(QLabel)[1].setText("None")
            self.kpi_top.findChildren(QLabel)[2].setText("CHF 0.00")

    def plot_pie(self, breakdown):
        self.fig_pie.clear()

        if not breakdown:
            self.canvas_pie.draw()
            return

        sorted_items = sorted(
            breakdown.items(), key=lambda x: x[1]['total'], reverse=True)

        tooltip_texts = []

        filtered_sizes = []
        filtered_labels = []

        for k, v in sorted_items:
            val = v['total']

            if val is None or not math.isfinite(val):
                val = 0.0

            if val <= 0:
                continue

            filtered_sizes.append(val)
            filtered_labels.append(k)

            subs = sorted(v['subs'].items(),
                          key=lambda x: x[1], reverse=True)[:3]
            sub_text = "\n".join([f" - {sn}: {sv:,.2f}" for sn, sv in subs])
            text = f"{k}: CHF {val:,.2f}\n{sub_text}"
            tooltip_texts.append(text)

        if not filtered_sizes:
            self.canvas_pie.draw()
            return

        sizes = filtered_sizes
        labels = filtered_labels

        ax = self.fig_pie.add_subplot(111)
        wedges, texts, autotexts = ax.pie(sizes, labels=None, autopct='%1.1f%%',
                                          startangle=90, pctdistance=0.85,
                                          textprops={'fontsize': 9})

        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        self.fig_pie.gca().add_artist(centre_circle)
        ax.axis('equal')

        def on_hover(event):
            found = False
            for i, w in enumerate(wedges):
                if w.contains_point([event.x, event.y]):
                    self.canvas_pie.setToolTip(tooltip_texts[i])
                    found = True
                    break
            if not found:
                self.canvas_pie.setToolTip("")

        self.canvas_pie.mpl_connect('motion_notify_event', on_hover)

        ax.legend(wedges, labels, loc="center", bbox_to_anchor=(
            0.5, -0.1), ncol=3, frameon=False, fontsize='small')

        self.fig_pie.tight_layout()
        self.canvas_pie.draw()

    def plot_line(self, trend_data):
        self.fig_line.clear()
        if not trend_data:
            self.canvas_line.draw()
            return

        ax = self.fig_line.add_subplot(111)

        months = [t['month_str'] for t in trend_data]

        values = []
        for t in trend_data:
            val = t['amount']
            if val is None or not math.isfinite(val):
                val = 0.0
            values.append(val)

        x_indices = range(len(months))

        line, = ax.plot(x_indices, values, marker='o',
                        color='#1976D2', linewidth=2)
        ax.fill_between(x_indices, values, color='#1976D2', alpha=0.1)

        ax.set_xticks(x_indices)
        ax.set_xticklabels(months, rotation=45, ha='right', fontsize=9)
        ax.grid(True, linestyle=':', alpha=0.6)

        ax.get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, p: format(int(x), ',')))

        def on_hover(event):
            if event.inaxes == ax:
                cont, ind = line.contains(event)
                if cont:
                    idx = ind['ind'][0]
                    val = values[idx]
                    mon = months[idx]
                    self.canvas_line.setToolTip(f"{mon}: CHF {val:,.2f}")
                    return
            self.canvas_line.setToolTip("")

        self.canvas_line.mpl_connect('motion_notify_event', on_hover)

        self.fig_line.tight_layout()
        self.canvas_line.draw()

    def plot_bar(self, payees_list):
        self.fig_bar.clear()

        months_names = ["", "Jan", "Feb", "Mar", "Apr", "May",
                        "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        if 1 <= self.current_month <= 12:
            m_name = months_names[self.current_month]
            self.frame_bar.findChild(QLabel).setText(
                f"Top Payees ({m_name} {self.current_year})")

        if not payees_list:
            self.canvas_bar.draw()
            return

        ax = self.fig_bar.add_subplot(111)
        payees_list.reverse()

        names = [str(p['payee']) for p in payees_list]

        values = []
        for p in payees_list:
            val = p['amount']
            if val is None or not math.isfinite(val):
                val = 0.0
            values.append(val)

        bars = ax.barh(names, values, color='#43A047')

        max_val = max(values) if values else 0.0

        if not math.isfinite(max_val) or max_val <= 0:
            max_val = 100.0

        ax.set_xlim(0, max_val * 1.25)

        for bar in bars:
            width = bar.get_width()

            x_pos = width + (max_val * 0.02)
            ax.text(x_pos, bar.get_y() + bar.get_height()/2,
                    f'{width:,.2f}',
                    ha='left', va='center', fontweight='bold', color='#333', fontsize=9)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.set_xticks([])

        ax.grid(axis='x', linestyle=':', alpha=0.3)

        self.fig_bar.tight_layout()
        self.canvas_bar.draw()
