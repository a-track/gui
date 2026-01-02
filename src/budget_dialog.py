from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QWidget, QLineEdit, QMessageBox,
                             QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtGui import QColor, QFont
import datetime
from utils import safe_eval_math, format_currency
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

        # --- Top Controls (Fixed) ---
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

        # --- Scrollable Content Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 10, 0) # Right margin for scrollbar

        self.summary_label = QLabel('')
        self.summary_label.setStyleSheet('color: #666; padding: 5px;')
        self.content_layout.addWidget(self.summary_label)

        # --- EXPENSES SECTION ---
        lbl_expenses = QLabel("Expenses")
        lbl_expenses.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; margin-top: 10px;")
        self.content_layout.addWidget(lbl_expenses)

        self.table_expenses = QTableWidget()
        self.setup_table(self.table_expenses)
        self.content_layout.addWidget(self.table_expenses)

        # --- INCOME SECTION ---
        lbl_income = QLabel("Income")
        lbl_income.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; margin-top: 20px;")
        self.content_layout.addWidget(lbl_income)

        self.table_income = QTableWidget()
        self.setup_table(self.table_income)
        self.content_layout.addWidget(self.table_income)
        
        self.content_layout.addStretch() # Push content to top if empty

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        # --- Bottom Controls (Fixed) ---
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

    def setup_table(self, table):
        # Disable internal scrolling to allow the outer scroll area to handle it
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels(
            ['Main Category', 'Category', 
             'Monthly Budget', 'Current Month', 'Remaining', 'Usage %',
             'L12M Budget', 'L12M Actual', 'L12M Remaining', 'L12M %'])

        header_tooltips = [
            "Main Category",
            "Category",
            "Target Monthly Limit",
            "Actual Spending this Month",
            "Budget - Expenses (Green = Under, Red = Over)",
            "Percentage of budget used",
            "Budget x 12",
            "Spending in Last 12 Months",
            "L12M Budget - L12M Actual",
            "Percentage of L12M budget used"
        ]
        for col, tooltip in enumerate(header_tooltips):
            item = table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tooltip)

        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
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

        table.verticalHeader().hide()

        header = table.horizontalHeader()
        for col in range(10):
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.Interactive) # Changed from ResizeToContents for performance

        table.verticalHeader().setDefaultSectionSize(35)

    def get_selected_period(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentData()
        return year, month

    def load_budget_data(self):
        try:
            year, month = self.get_selected_period()

            # --- EXPENSES DATA ---
            exp_budgets = self.budget_app.get_all_budgets('Expense')
            exp_actuals = self.budget_app.get_budget_vs_actual(year, month, 'Expense', 'expense')
            exp_l12m = self.budget_app.get_l12m_breakdown(year, month, 'Expense', 'expense')
            
            exp_data, exp_totals, exp_grand = self.prepare_data(exp_budgets, exp_actuals, exp_l12m)
            self.populate_table(self.table_expenses, exp_data, exp_totals, exp_grand, is_income=False)

            # --- INCOME DATA ---
            inc_budgets = self.budget_app.get_all_budgets('Income')
            inc_actuals = self.budget_app.get_budget_vs_actual(year, month, 'Income', 'income')
            inc_l12m = self.budget_app.get_l12m_breakdown(year, month, 'Income', 'income')
            
            inc_data, inc_totals, inc_grand = self.prepare_data(inc_budgets, inc_actuals, inc_l12m)
            self.populate_table(self.table_income, inc_data, inc_totals, inc_grand, is_income=True)
            
            # Summary (Net)
            total_inc_actual = inc_grand['actual']
            total_exp_actual = exp_grand['actual']
            net_saved = total_inc_actual - total_exp_actual
            
            self.summary_label.setText(f"Net Result: {format_currency(net_saved)}")
            if net_saved >= 0:
                self.summary_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50; margin: 10px;")
            else:
                self.summary_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #f44336; margin: 10px;")

            month_name = self.month_combo.currentText()
            self.show_status(f'Loaded budget data for {month_name} {year}')

        except Exception as e:
            self.show_status(f"Error loading budget: {e}", error=True)
            import traceback
            traceback.print_exc()
            self.show_status('Error loading budget data', error=True)

    def prepare_data(self, monthly_budgets, current_actuals, l12m_actuals):
        categories = self.budget_app.get_all_categories()
        category_map = {cat.sub_category: cat.category for cat in categories}

        category_data = {}
        category_totals = {}
        grand_totals = {
            'budget': 0.0, 'actual': 0.0, 'remaining': 0.0,
            'l12m_budget': 0.0, 'l12m_actual': 0.0, 'l12m_remaining': 0.0
        }

        # Union of all keys
        all_sub_categories = set(monthly_budgets.keys())
        all_sub_categories.update(current_actuals.keys())
        all_sub_categories.update(l12m_actuals.keys())

        for sub_category in all_sub_categories:
            category = category_map.get(sub_category, 'Other')
            
            budget_amount = monthly_budgets.get(sub_category, 0.0)
            
            actual_data = current_actuals.get(sub_category, {})
            actual_amount = actual_data.get('actual', 0.0) if isinstance(actual_data, dict) else 0.0
            
            remaining = budget_amount - actual_amount

            l12m_budget = budget_amount * 12
            l12m_actual = l12m_actuals.get(sub_category, 0.0)
            l12m_remaining = l12m_budget - l12m_actual

            if category not in category_data:
                category_data[category] = []
                category_totals[category] = {
                    'budget': 0.0, 'actual': 0.0, 'remaining': 0.0,
                    'l12m_budget': 0.0, 'l12m_actual': 0.0, 'l12m_remaining': 0.0
                }

            category_data[category].append({
                'sub_category': sub_category,
                'budget': budget_amount,
                'actual': actual_amount,
                'remaining': remaining,
                'percentage': (actual_amount / budget_amount * 100) if budget_amount > 0 else 0,
                'l12m_budget': l12m_budget,
                'l12m_actual': l12m_actual,
                'l12m_remaining': l12m_remaining,
                'l12m_percentage': (l12m_actual / l12m_budget * 100) if l12m_budget > 0 else 0
            })

            # Update Category Totals
            vals = {
                'budget': budget_amount,
                'actual': actual_amount,
                'remaining': remaining,
                'l12m_budget': l12m_budget,
                'l12m_actual': l12m_actual,
                'l12m_remaining': l12m_remaining
            }
            for key, val in vals.items():
                 category_totals[category][key] += val
                 grand_totals[key] += val

        return category_data, category_totals, grand_totals

    def get_income_by_category(self, year, month):
        # Deprecated: Logic moved to generic loading
        return {}

    def populate_table(self, table, category_data, category_totals, grand_totals, is_income=False):
        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)
        try:
            total_rows = 0
            for category, items in category_data.items():
                total_rows += 1 + len(items) + 1
            
            # Add 1 row for Grand Total + 1 spacer row potentially
            total_rows += 2 

            table.setRowCount(total_rows)

            current_row = 0

            sorted_categories = sorted(category_data.keys())

            for category in sorted_categories:
                items = category_data[category]
                
                # Category Header
                category_item = QTableWidgetItem(category)
                category_item.setBackground(QColor(240, 240, 240))
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                # ... check if font needs to be created every time?
                # Optimization: create strict fonts once outside loop? 
                # Keeping it simple for now, object creation is fast in Python relative to Qt paint.
                category_item.setFont(font)
                table.setItem(current_row, 0, category_item)
                table.setSpan(current_row, 0, 1, 10)
                current_row += 1

                sorted_items = sorted(items, key=lambda x: x['sub_category'])

                for item in sorted_items:
                    sub_category_item = QTableWidgetItem(f"  {item['sub_category']}")
                    table.setItem(current_row, 1, sub_category_item)

                    self.set_numeric_item(table, current_row, 2, item['budget'])
                    self.set_numeric_item(table, current_row, 3, item['actual'])
                    self.set_diff_item(table, current_row, 4, item['remaining'], is_income, is_pct=False)
                    self.set_diff_item(table, current_row, 5, item['percentage'], is_income, is_pct=True)

                    self.set_numeric_item(table, current_row, 6, item['l12m_budget'])
                    self.set_numeric_item(table, current_row, 7, item['l12m_actual'])
                    self.set_diff_item(table, current_row, 8, item['l12m_remaining'], is_income, is_pct=False)
                    self.set_diff_item(table, current_row, 9, item['l12m_percentage'], is_income, is_pct=True)

                    current_row += 1

                # Category Footer
                totals = category_totals[category]
                
                # Recalculate percentages for totals
                total_budget = totals['budget']
                total_actual = totals['actual']
                total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0
                
                total_l12m_budget = totals['l12m_budget']
                total_l12m_actual = totals['l12m_actual']
                total_l12m_pct = (total_l12m_actual / total_l12m_budget * 100) if total_l12m_budget > 0 else 0
                
                # Fill row
                bg = QColor(220, 220, 220)
                font_bold = QFont("Segoe UI", 10, QFont.Weight.Bold)
                
                self.set_numeric_item(table, current_row, 2, total_budget, bg, font_bold)
                self.set_numeric_item(table, current_row, 3, total_actual, bg, font_bold)
                self.set_diff_item(table, current_row, 4, totals['remaining'], is_income, False, bg, font_bold)
                self.set_diff_item(table, current_row, 5, total_pct, is_income, True, bg, font_bold)
                
                self.set_numeric_item(table, current_row, 6, total_l12m_budget, bg, font_bold)
                self.set_numeric_item(table, current_row, 7, total_l12m_actual, bg, font_bold)
                self.set_diff_item(table, current_row, 8, totals['l12m_remaining'], is_income, False, bg, font_bold)
                self.set_diff_item(table, current_row, 9, total_l12m_pct, is_income, True, bg, font_bold)

                current_row += 1
            
            # Spacer Row
            current_row += 1

            # Grand Total Row
            gt_item = QTableWidgetItem("TOTAL")
            bg_color = QColor(220, 220, 220) 
            gt_item.setBackground(bg_color)
            font = QFont("Segoe UI", 11, QFont.Weight.Bold)
            gt_item.setFont(font)
            table.setItem(current_row, 0, gt_item)
            table.setSpan(current_row, 0, 1, 2)

            gt_budget = grand_totals['budget']
            gt_actual = grand_totals['actual']
            gt_pct = (gt_actual / gt_budget * 100) if gt_budget > 0 else 0
            
            gt_l12m_budget = grand_totals['l12m_budget']
            gt_l12m_actual = grand_totals['l12m_actual']
            gt_l12m_pct = (gt_l12m_actual / gt_l12m_budget * 100) if gt_l12m_budget > 0 else 0

            self.set_numeric_item(table, current_row, 2, gt_budget, bg_color, font)
            self.set_numeric_item(table, current_row, 3, gt_actual, bg_color, font)
            self.set_diff_item(table, current_row, 4, grand_totals['remaining'], is_income, False, bg_color, font)
            self.set_diff_item(table, current_row, 5, gt_pct, is_income, True, bg_color, font)
            
            self.set_numeric_item(table, current_row, 6, gt_l12m_budget, bg_color, font)
            self.set_numeric_item(table, current_row, 7, gt_l12m_actual, bg_color, font)
            self.set_diff_item(table, current_row, 8, grand_totals['l12m_remaining'], is_income, False, bg_color, font)
            self.set_diff_item(table, current_row, 9, gt_l12m_pct, is_income, True, bg_color, font)

            table.resizeColumnsToContents()
            
            # Disable internal scrollbars to ensure outer QScrollArea handles scrolling
            table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

            # Calculate exact required height based on header and rows
            # Use verticalHeader().length() for accurate pixel height of all rows
            header_height = table.horizontalHeader().height()
            rows_height = table.verticalHeader().length()
            total_height = header_height + rows_height + 4 # Small buffer for borders
            
            # Force height to match content
            table.setMinimumHeight(total_height)
            table.setMaximumHeight(total_height)
        finally:
            table.setUpdatesEnabled(True)
        
    def set_numeric_item(self, table, row, col, val, bg_color=None, font=None):
        text = format_currency(val)
        item = NumericTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if bg_color:
            item.setBackground(bg_color)
        if font:
            item.setFont(font)
        table.setItem(row, col, item)

    def set_diff_item(self, table, row, col, val, is_income, is_pct, bg_color=None, font=None):
        text = f"{val:.1f}%" if is_pct else format_currency(val)
        item = NumericTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if bg_color:
            item.setBackground(bg_color)
        if font:
            item.setFont(font)
            
        # Color Logic
        # Expense: Remaining < 0 is Bad (Red). Usage > 100 is Bad (Red).
        # Income: Actual > Budget (Remaining < 0? No, Remaining = Budget - Actual. 
        #   If Budget 100, Actual 120, Remaining = -20. This is Good!
        #   If Budget 100, Actual 80, Remaining = 20. This is Bad/neutral.
        
        # So for Income: Remaining < 0 is Good (Green). Remaining >= 0 is Red/Warning?
        # Let's say we want to meet income target. So Actual >= Budget is Green.
        
        color = None
        if is_pct:
            # Usage %
            # Expense: > 100 Red, 85-100 Orange, < 85 Green
            # Income: > 100 Green (Exceeded target), 85-100 Orange, < 85 Red?
            
            if not is_income:
                if val <= 85: color = QColor(0, 128, 0)
                elif val <= 100: color = QColor(255, 165, 0)
                else: color = QColor(255, 0, 0)
            else:
                if val >= 100: color = QColor(0, 128, 0) # Met/Exceeded target
                elif val >= 85: color = QColor(255, 165, 0)
                else: color = QColor(255, 0, 0) # Missed target bad
        else:
            # Remaining Amount = Budget - Actual
            if not is_income:
                # Expense: Remaining > 0 is Good (Green)
                if val >= 0: color = QColor(0, 128, 0)
                else: color = QColor(255, 0, 0)
            else:
                # Income: Remaining < 0 implies Actual > Budget (Good)
                # Remaining > 0 implies Actual < Budget (Missed target)
                if val <= 0: color = QColor(0, 128, 0)
                else: color = QColor(255, 0, 0)
        
        if color:
            item.setForeground(color)
        else:
            # Fallback for neutral?
            pass

        table.setItem(row, col, item)

    def populate_table_grouped(self, category_data, category_totals, grand_totals):
         # Shim for backward compatibility if I missed any calls, or redirect
         self.populate_table(self.table_expenses, category_data, category_totals, grand_totals, is_income=False)

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
            if category.category_type != 'Expense':
                continue
                
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
