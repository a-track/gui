from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QWidget, QLineEdit, QMessageBox,
                             QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtGui import QColor, QFont
import datetime
from utils import safe_eval_math
from transactions_dialog import NumericTableWidgetItem
from custom_widgets import NoScrollComboBox


class BudgetDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)

        self.budget_app = budget_app
        self.parent_window = parent

        self.setWindowTitle('Monthly Budget vs Expenses')
        self.setMinimumSize(1000, 600)

        layout = QVBoxLayout()

        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel('Year:'))
        self.year_combo = NoScrollComboBox()
        current_year = datetime.datetime.now().year
        for year in range(current_year - 2, current_year + 1):
            self.year_combo.addItem(str(year))
        self.year_combo.setCurrentText(str(current_year))
        self.year_combo.currentTextChanged.connect(self.load_budget_data)
        period_layout.addWidget(self.year_combo)

        period_layout.addWidget(QLabel('Month:'))
        self.month_combo = NoScrollComboBox()
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
        for i, month in enumerate(months, 1):
            self.month_combo.addItem(month, i)

        current_month = datetime.datetime.now().month
        self.month_combo.setCurrentIndex(current_month - 1)
        self.month_combo.currentTextChanged.connect(self.load_budget_data)
        period_layout.addWidget(self.month_combo)

        period_layout.addStretch()
        layout.addLayout(period_layout)

        self.summary_label = QLabel('')
        self.summary_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.summary_label)

        self.income_summary_label = QLabel('')
        self.income_summary_label.setStyleSheet(
            'color: #4CAF50; padding: 5px;')
        layout.addWidget(self.income_summary_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ['Category', 'Sub Category', 'Monthly Budget', 'Current Month Expenses', 'Remaining', 'Usage %'])

        header_tooltips = [
            "Main Category",
            "Sub Category",
            "Target Monthly Limit",
            "Actual Spending this Month",
            "Budget - Expenses (Green = Under, Red = Over)",
            "Percentage of budget used"
        ]
        for col, tooltip in enumerate(header_tooltips):
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tooltip)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #b3d9ff;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 9pt;
            }
        """)

        self.table.verticalHeader().hide()

        header = self.table.horizontalHeader()
        for col in range(6):
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents)

        self.table.verticalHeader().setDefaultSectionSize(35)
        layout.addWidget(self.table)

        set_budgets_btn = QPushButton('Set Monthly Budgets')
        set_budgets_btn.clicked.connect(self.show_set_budgets_dialog)
        set_budgets_btn.setStyleSheet(
            'background-color: #2196F3; color: white; padding: 10px; font-size: 14px;')
        layout.addWidget(set_budgets_btn)

        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        self.load_budget_data()

    def get_selected_period(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentData()
        return year, month

    def load_budget_data(self):
        try:
            year, month = self.get_selected_period()

            monthly_budgets = self.budget_app.get_all_budgets()

            current_expenses = self.budget_app.get_budget_vs_expenses(
                year, month)

            income_by_category = self.get_income_by_category(year, month)

            total_budget = 0.0
            total_actual = 0.0
            total_remaining = 0.0
            total_income = sum(income_by_category.values())

            categories = self.budget_app.get_all_categories()
            category_map = {
                cat.sub_category: cat.category for cat in categories}

            category_data = {}
            category_totals = {}

            for sub_category, budget_amount in monthly_budgets.items():
                category = category_map.get(sub_category, 'Other')
                actual_data = current_expenses.get(sub_category, {})
                actual_amount = actual_data.get('actual', 0.0)
                remaining = budget_amount - actual_amount

                if category not in category_data:
                    category_data[category] = []
                    category_totals[category] = {
                        'budget': 0.0,
                        'actual': 0.0,
                        'remaining': 0.0
                    }

                category_data[category].append({
                    'sub_category': sub_category,
                    'budget': budget_amount,
                    'actual': actual_amount,
                    'remaining': remaining,
                    'percentage': (actual_amount / budget_amount * 100) if budget_amount > 0 else 0
                })

                category_totals[category]['budget'] += budget_amount
                category_totals[category]['actual'] += actual_amount
                category_totals[category]['remaining'] += remaining

                total_budget += budget_amount
                total_actual += actual_amount
                total_remaining += remaining

            for sub_category, data in current_expenses.items():
                if sub_category not in monthly_budgets:
                    category = category_map.get(sub_category, 'Other')
                    actual_amount = data.get('actual', 0.0)

                    if category not in category_data:
                        category_data[category] = []
                        category_totals[category] = {
                            'budget': 0.0,
                            'actual': 0.0,
                            'remaining': 0.0
                        }

                    category_data[category].append({
                        'sub_category': sub_category,
                        'budget': 0.0,
                        'actual': actual_amount,
                        'remaining': -actual_amount,
                        'percentage': 0.0
                    })

                    category_totals[category]['actual'] += actual_amount
                    category_totals[category]['remaining'] -= actual_amount

                    total_actual += actual_amount
                    total_remaining -= actual_amount

            month_name = self.month_combo.currentText()
            summary_text = f"Selected Period ({month_name} {year}) - Budget: {total_budget:.2f} | Expenses: {total_actual:.2f} | Remaining: {total_remaining:.2f}"
            self.summary_label.setText(summary_text)

            income_text = "Monthly Income: "
            if income_by_category:
                income_parts = []
                for category, amount in income_by_category.items():
                    if amount > 0:
                        income_parts.append(f"{category}: {amount:.2f}")
                income_text += " | ".join(income_parts)
                income_text += f" | Total: {total_income:.2f}"
            else:
                income_text += "No income recorded"
            self.income_summary_label.setText(income_text)

            self.populate_table_grouped(category_data, category_totals)

            self.show_status(f'Loaded budget data for {month_name} {year}')

        except Exception as e:
            print(f"Error loading budget data: {e}")
            self.show_status('Error loading budget data', error=True)

    def get_income_by_category(self, year, month):
        """Get income transactions grouped by category for the given month"""
        income_by_category = {}
        all_transactions = self.budget_app.get_all_transactions()

        for trans in all_transactions:
            if trans.type == 'income' and trans.date:
                try:
                    trans_date = trans.date
                    if isinstance(trans_date, str):
                        trans_date = datetime.datetime.strptime(
                            trans_date, '%Y-%m-%d').date()

                    if trans_date.year == year and trans_date.month == month:
                        category = trans.sub_category or 'Uncategorized'
                        amount = float(trans.amount or 0)
                        if category in income_by_category:
                            income_by_category[category] += amount
                        else:
                            income_by_category[category] = amount
                except (ValueError, AttributeError):
                    continue

        return income_by_category

    def populate_table_grouped(self, category_data, category_totals):
        total_rows = 0
        for category, items in category_data.items():
            total_rows += 1 + len(items) + 1

        self.table.setRowCount(total_rows)

        current_row = 0

        sorted_categories = sorted(category_data.keys())

        for category in sorted_categories:
            items = category_data[category]
            totals = category_totals.get(
                category, {'budget': 0, 'actual': 0, 'remaining': 0})

            category_item = QTableWidgetItem(category)
            category_item.setBackground(QColor(240, 240, 240))
            category_item.setBackground(QColor(240, 240, 240))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            category_item.setFont(font)
            self.table.setItem(current_row, 0, category_item)

            self.table.setSpan(current_row, 0, 1, 6)

            current_row += 1

            sorted_items = sorted(items, key=lambda x: x['sub_category'])

            for item in sorted_items:
                sub_category_item = QTableWidgetItem(
                    f"  {item['sub_category']}")
                self.table.setItem(current_row, 1, sub_category_item)

                budget_item = NumericTableWidgetItem(f"{item['budget']:.2f}")
                budget_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(current_row, 2, budget_item)

                actual_item = NumericTableWidgetItem(f"{item['actual']:.2f}")
                actual_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(current_row, 3, actual_item)

                remaining = item['remaining']
                remaining_item = NumericTableWidgetItem(f"{remaining:.2f}")
                remaining_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                remaining_item.setFont(font)

                if remaining >= 0:
                    remaining_item.setForeground(QColor(0, 128, 0))
                else:
                    remaining_item.setForeground(QColor(255, 0, 0))

                self.table.setItem(current_row, 4, remaining_item)

                percentage = item['percentage']
                percentage_item = NumericTableWidgetItem(f"{percentage:.1f}%")
                percentage_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                percentage_item.setFont(font)

                if percentage <= 75:
                    percentage_item.setForeground(QColor(0, 128, 0))
                elif percentage <= 90:
                    percentage_item.setForeground(QColor(255, 165, 0))
                else:
                    percentage_item.setForeground(QColor(255, 0, 0))

                self.table.setItem(current_row, 5, percentage_item)

                current_row += 1

            total_budget = totals['budget']
            total_actual = totals['actual']
            total_remaining = totals['remaining']
            total_percentage = (total_actual / total_budget *
                                100) if total_budget > 0 else 0

            total_budget_item = NumericTableWidgetItem(f"{total_budget:.2f}")
            total_budget_item.setBackground(QColor(220, 220, 220))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            total_budget_item.setFont(font)
            total_budget_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(current_row, 2, total_budget_item)

            total_actual_item = NumericTableWidgetItem(f"{total_actual:.2f}")
            total_actual_item.setBackground(QColor(220, 220, 220))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            total_actual_item.setFont(font)
            total_actual_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(current_row, 3, total_actual_item)

            total_remaining_item = QTableWidgetItem(f"{total_remaining:.2f}")
            total_remaining_item.setBackground(QColor(220, 220, 220))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            total_remaining_item.setFont(font)
            total_remaining_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if total_remaining >= 0:
                total_remaining_item.setForeground(QColor(0, 128, 0))
            else:
                total_remaining_item.setForeground(QColor(255, 0, 0))

            self.table.setItem(current_row, 4, total_remaining_item)

            total_percentage_item = QTableWidgetItem(
                f"{total_percentage:.1f}%")
            total_percentage_item.setBackground(QColor(220, 220, 220))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            total_percentage_item.setFont(font)
            total_percentage_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if total_percentage <= 75:
                total_percentage_item.setForeground(QColor(0, 128, 0))
            elif total_percentage <= 90:
                total_percentage_item.setForeground(QColor(255, 165, 0))
            else:
                total_percentage_item.setForeground(QColor(255, 0, 0))

            self.table.setItem(current_row, 5, total_percentage_item)

            current_row += 1

        self.table.resizeColumnsToContents()

        total_width = self.table.horizontalHeader().length() + 80
        if total_width > self.width():
            self.resize(total_width, self.height())

    def show_set_budgets_dialog(self):
        dialog = SetMonthlyBudgetsDialog(self.budget_app, self)
        if dialog.exec():
            self.load_budget_data()

    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet(
                'color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')

        QTimer.singleShot(5000, lambda: self.status_label.setText(''))


class SetMonthlyBudgetsDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)

        self.budget_app = budget_app
        self.parent_window = parent

        self.setWindowTitle('Set Monthly Budgets')
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()

        info_label = QLabel(
            'Set monthly budgets for each subcategory. These budgets will apply to all months.')
        info_label.setStyleSheet('color: #666; padding: 10px;')
        layout.addWidget(info_label)

        self.sub_category_widgets = []

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        categories = self.budget_app.get_all_categories()
        sub_categories_by_category = {}

        for category in categories:
            if category.category not in sub_categories_by_category:
                sub_categories_by_category[category.category] = []
            sub_categories_by_category[category.category].append(
                category.sub_category)

        current_budgets = self.budget_app.get_all_budgets()

        for category_name, sub_categories in sub_categories_by_category.items():
            category_header = QLabel(category_name)
            category_header.setStyleSheet(
                'font-weight: bold; background: #f0f0f0; padding: 8px; margin-top: 5px;')
            scroll_layout.addWidget(category_header)

            for sub_category in sorted(sub_categories):
                sub_layout = QHBoxLayout()

                sub_label = QLabel(sub_category)
                sub_label.setMinimumWidth(150)
                sub_layout.addWidget(sub_label)

                amount_input_layout = QHBoxLayout()
                amount_input_layout.addWidget(QLabel('CHF'))

                amount_input = QLineEdit()
                amount_input.setPlaceholderText('0.00')
                amount_input.setMaximumWidth(100)

                current_budget = current_budgets.get(sub_category, 0.0)
                if current_budget > 0:
                    amount_input.setText(f"{current_budget:.2f}")
                else:
                    amount_input.setText('0.00')

                amount_input.textChanged.connect(
                    lambda text, amt_input=amount_input: self.validate_amount_input(text, amt_input))
                amount_input_layout.addWidget(amount_input)

                sub_layout.addLayout(amount_input_layout)
                sub_layout.addStretch()

                scroll_layout.addLayout(sub_layout)

                self.sub_category_widgets.append({
                    'sub_category': sub_category,
                    'amount_input': amount_input
                })

        scroll_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setMinimumHeight(300)
        layout.addWidget(scroll_area)

        button_layout = QHBoxLayout()

        apply_btn = QPushButton('Save Monthly Budgets')
        apply_btn.clicked.connect(self.save_budgets)
        apply_btn.setStyleSheet(
            'background-color: #4CAF50; color: white; padding: 8px;')
        button_layout.addWidget(apply_btn)

        clear_btn = QPushButton('Clear All Budgets')
        clear_btn.clicked.connect(self.clear_budgets)
        clear_btn.setStyleSheet(
            'background-color: #f44336; color: white; padding: 8px;')
        button_layout.addWidget(clear_btn)

        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(
            'background-color: #666; color: white; padding: 8px;')
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def validate_amount_input(self, text, amount_input):
        if text == '':
            return

        allowed_chars = set('0123456789+-*/.() ')
        if not set(text).issubset(allowed_chars):
            cursor_pos = amount_input.cursorPosition()
            amount_input.setText(text[:-1])
            amount_input.setCursorPosition(max(0, cursor_pos - 1))

    def save_budgets(self):
        try:
            budgets_to_save = []

            for widget_info in self.sub_category_widgets:
                amount_text = widget_info['amount_input'].text()
                if amount_text.strip():
                    try:
                        amount = safe_eval_math(amount_text)
                        if amount >= 0:
                            budgets_to_save.append({
                                'sub_category': widget_info['sub_category'],
                                'amount': amount
                            })
                    except ValueError:
                        continue

            if not budgets_to_save:
                QMessageBox.warning(
                    self, 'Warning', 'No budget amounts specified')
                return

            success_count = 0
            for budget_info in budgets_to_save:
                sub_category = budget_info['sub_category']
                amount = budget_info['amount']

                success = self.budget_app.add_or_update_budget(
                    sub_category, amount)
                if success:
                    success_count += 1

            QMessageBox.information(
                self,
                'Success',
                f'Monthly budgets saved successfully!\n\n'
                f'Saved {success_count} budgets.\n\n'
                f'These budgets will apply to all months.'
            )
            self.accept()

        except Exception as e:
            print(f"Error saving budgets: {e}")
            QMessageBox.critical(
                self, 'Error', f'Error saving budgets: {str(e)}')

    def clear_budgets(self):
        reply = QMessageBox.question(
            self,
            'Confirm Clear',
            'Clear all monthly budgets?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for widget_info in self.sub_category_widgets:
                widget_info['amount_input'].setText('0.00')
