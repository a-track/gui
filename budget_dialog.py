from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QComboBox, QHeaderView, QWidget, QLineEdit,
                             QMessageBox, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush
import datetime

class BudgetDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        
        self.setWindowTitle('Monthly Budget vs Expenses')
        self.setMinimumSize(1000, 600)
        
        layout = QVBoxLayout()
        
        # Period selection
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel('Year:'))
        self.year_combo = QComboBox()
        current_year = datetime.datetime.now().year
        # Add current year and previous 2 years
        for year in range(current_year - 2, current_year + 1):
            self.year_combo.addItem(str(year))
        self.year_combo.setCurrentText(str(current_year))
        self.year_combo.currentTextChanged.connect(self.load_budget_data)
        period_layout.addWidget(self.year_combo)
        
        period_layout.addWidget(QLabel('Month:'))
        self.month_combo = QComboBox()
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
        
        # Summary info
        self.summary_label = QLabel('')
        self.summary_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.summary_label)
        
        # Income summary
        self.income_summary_label = QLabel('')
        self.income_summary_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        layout.addWidget(self.income_summary_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Category', 'Sub Category', 'Monthly Budget', 'Current Month Expenses', 'Remaining', 'Usage %'])

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                font-size: 11px;
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
                font-size: 11px;
            }
        """)

        self.table.verticalHeader().hide()

        header = self.table.horizontalHeader()
        for col in range(6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.table.verticalHeader().setDefaultSectionSize(35)
        layout.addWidget(self.table)
        
        # Set Budgets button
        set_budgets_btn = QPushButton('Set Monthly Budgets')
        set_budgets_btn.clicked.connect(self.show_set_budgets_dialog)
        set_budgets_btn.setStyleSheet('background-color: #2196F3; color: white; padding: 10px; font-size: 14px;')
        layout.addWidget(set_budgets_btn)
        
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        self.load_budget_data()
    
    def get_selected_period(self):
        """Get the currently selected year and month"""
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentData()
        return year, month
    
    def load_budget_data(self):
        try:
            year, month = self.get_selected_period()
            
            # Get monthly budgets (use selected month as the fixed monthly budget)
            monthly_budgets = self.budget_app.get_all_budgets_for_period(year, month)
            
            # Get current month expenses
            current_expenses = self.budget_app.get_budget_vs_expenses(year, month)
            
            # Get current month income by category
            income_by_category = self.get_income_by_category(year, month)
            
            # Calculate totals
            total_budget = 0.0
            total_actual = 0.0
            total_remaining = 0.0
            total_income = sum(income_by_category.values())
            
            # Prepare data for display - group by category
            categories = self.budget_app.get_all_categories()
            category_map = {cat.sub_category: cat.category for cat in categories}
            
            # Group data by category
            category_data = {}
            category_totals = {}
            
            # Add all budgeted categories
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
            
            # Add categories with expenses but no budget
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
            
            # Update summary
            month_name = self.month_combo.currentText()
            summary_text = f"Selected Period ({month_name} {year}) - Budget: {total_budget:.2f} | Expenses: {total_actual:.2f} | Remaining: {total_remaining:.2f}"
            self.summary_label.setText(summary_text)
            
            # Update income summary
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
            
            # Populate table with grouped data
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
                        trans_date = datetime.datetime.strptime(trans_date, '%Y-%m-%d').date()
                    
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
        """Populate table with data grouped by category including category totals"""
        # Calculate total number of rows (categories + subcategories + category totals)
        total_rows = 0
        for category, items in category_data.items():
            total_rows += 1 + len(items) + 1  # Category header + subcategory rows + category total row
        
        self.table.setRowCount(total_rows)
        
        current_row = 0
        
        # Sort categories alphabetically
        sorted_categories = sorted(category_data.keys())
        
        for category in sorted_categories:
            items = category_data[category]
            totals = category_totals.get(category, {'budget': 0, 'actual': 0, 'remaining': 0})
            
            # Add category header row
            category_item = QTableWidgetItem(category)
            category_item.setBackground(QColor(240, 240, 240))
            category_item.setFont(QFont("", weight=QFont.Weight.Bold))
            self.table.setItem(current_row, 0, category_item)
            
            # Merge cells for category header
            self.table.setSpan(current_row, 0, 1, 6)  # Span all columns
            
            current_row += 1
            
            # Sort subcategories alphabetically
            sorted_items = sorted(items, key=lambda x: x['sub_category'])
            
            for item in sorted_items:
                # Sub Category
                sub_category_item = QTableWidgetItem(f"  {item['sub_category']}")  # Indent subcategories
                self.table.setItem(current_row, 1, sub_category_item)
                
                # Monthly Budget
                budget_item = QTableWidgetItem(f"{item['budget']:.2f}")
                budget_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(current_row, 2, budget_item)
                
                # Current Month Expenses
                actual_item = QTableWidgetItem(f"{item['actual']:.2f}")
                actual_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(current_row, 3, actual_item)
                
                # Remaining
                remaining = item['remaining']
                remaining_item = QTableWidgetItem(f"{remaining:.2f}")
                remaining_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                remaining_item.setFont(QFont("", weight=QFont.Weight.Bold))
                
                # Color code remaining amount
                if remaining >= 0:
                    remaining_item.setForeground(QColor(0, 128, 0))  # Green
                else:
                    remaining_item.setForeground(QColor(255, 0, 0))  # Red
                
                self.table.setItem(current_row, 4, remaining_item)
                
                # Usage Percentage
                percentage = item['percentage']
                percentage_item = QTableWidgetItem(f"{percentage:.1f}%")
                percentage_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                percentage_item.setFont(QFont("", weight=QFont.Weight.Bold))
                
                # Color code percentage
                if percentage <= 75:
                    percentage_item.setForeground(QColor(0, 128, 0))  # Green
                elif percentage <= 90:
                    percentage_item.setForeground(QColor(255, 165, 0))  # Orange
                else:
                    percentage_item.setForeground(QColor(255, 0, 0))  # Red
                
                self.table.setItem(current_row, 5, percentage_item)
                
                current_row += 1
            
            # Add category total row
            total_budget = totals['budget']
            total_actual = totals['actual']
            total_remaining = totals['remaining']
            total_percentage = (total_actual / total_budget * 100) if total_budget > 0 else 0
            

            
            # Budget total
            total_budget_item = QTableWidgetItem(f"{total_budget:.2f}")
            total_budget_item.setBackground(QColor(220, 220, 220))
            total_budget_item.setFont(QFont("", weight=QFont.Weight.Bold))
            total_budget_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(current_row, 2, total_budget_item)
            
            # Actual total
            total_actual_item = QTableWidgetItem(f"{total_actual:.2f}")
            total_actual_item.setBackground(QColor(220, 220, 220))
            total_actual_item.setFont(QFont("", weight=QFont.Weight.Bold))
            total_actual_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(current_row, 3, total_actual_item)
            
            # Remaining total
            total_remaining_item = QTableWidgetItem(f"{total_remaining:.2f}")
            total_remaining_item.setBackground(QColor(220, 220, 220))
            total_remaining_item.setFont(QFont("", weight=QFont.Weight.Bold))
            total_remaining_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # Color code remaining total
            if total_remaining >= 0:
                total_remaining_item.setForeground(QColor(0, 128, 0))  # Green
            else:
                total_remaining_item.setForeground(QColor(255, 0, 0))  # Red
            
            self.table.setItem(current_row, 4, total_remaining_item)
            
            # Usage percentage total
            total_percentage_item = QTableWidgetItem(f"{total_percentage:.1f}%")
            total_percentage_item.setBackground(QColor(220, 220, 220))
            total_percentage_item.setFont(QFont("", weight=QFont.Weight.Bold))
            total_percentage_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # Color code percentage total
            if total_percentage <= 75:
                total_percentage_item.setForeground(QColor(0, 128, 0))  # Green
            elif total_percentage <= 90:
                total_percentage_item.setForeground(QColor(255, 165, 0))  # Orange
            else:
                total_percentage_item.setForeground(QColor(255, 0, 0))  # Red
            
            self.table.setItem(current_row, 5, total_percentage_item)
            
            current_row += 1
        
        self.table.resizeColumnsToContents()
    
    def show_set_budgets_dialog(self):
        """Show the dialog to set monthly budgets"""
        dialog = SetBudgetsDialog(self.budget_app, self)
        if dialog.exec():
            self.load_budget_data()
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))


class SetBudgetsDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        
        self.setWindowTitle('Set Monthly Budgets')
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel('Set fixed monthly budgets for each subcategory.')
        info_label.setStyleSheet('color: #666; padding: 10px;')
        layout.addWidget(info_label)
        
        # Sub Category selection with budget amount
        self.sub_category_widgets = []
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        categories = self.budget_app.get_all_categories()
        sub_categories_by_category = {}
        
        for category in categories:
            if category.category not in sub_categories_by_category:
                sub_categories_by_category[category.category] = []
            sub_categories_by_category[category.category].append(category.sub_category)
        
        # Load current budgets to pre-fill values
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        current_budgets = self.budget_app.get_all_budgets_for_period(current_year, current_month)
        
        for category_name, sub_categories in sub_categories_by_category.items():
            # Category header
            category_header = QLabel(category_name)
            category_header.setStyleSheet('font-weight: bold; background: #f0f0f0; padding: 8px; margin-top: 5px;')
            category_header.setProperty('category_name', category_name)
            scroll_layout.addWidget(category_header)
            
            for sub_category in sorted(sub_categories):
                sub_layout = QHBoxLayout()
                
                sub_label = QLabel(sub_category)
                sub_label.setMinimumWidth(150)
                sub_layout.addWidget(sub_label)
                
                # Amount input layout
                amount_input_layout = QHBoxLayout()
                amount_input_layout.addWidget(QLabel('CHF'))
                
                amount_input = QLineEdit()
                amount_input.setPlaceholderText('0.00')
                amount_input.setMaximumWidth(100)
                
                # Pre-fill with current budget if exists
                current_budget = current_budgets.get(sub_category, 0.0)
                if current_budget > 0:
                    amount_input.setText(f"{current_budget:.2f}")
                else:
                    amount_input.setText('0.00')
                    
                amount_input.textChanged.connect(lambda text, amt_input=amount_input: self.validate_amount_input(text, amt_input))
                amount_input_layout.addWidget(amount_input)
                
                sub_layout.addLayout(amount_input_layout)
                sub_layout.addStretch()
                
                scroll_layout.addLayout(sub_layout)
                
                self.sub_category_widgets.append({
                    'sub_category': sub_category,
                    'category': category_name,
                    'amount_input': amount_input,
                    'category_header': category_header
                })
        
        scroll_layout.addStretch()
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setMinimumHeight(300)
        layout.addWidget(scroll_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        apply_btn = QPushButton('Save Monthly Budgets')
        apply_btn.clicked.connect(self.save_budgets)
        apply_btn.setStyleSheet('background-color: #4CAF50; color: white; padding: 8px;')
        button_layout.addWidget(apply_btn)
        
        clear_btn = QPushButton('Clear All Budgets')
        clear_btn.clicked.connect(self.clear_budgets)
        clear_btn.setStyleSheet('background-color: #f44336; color: white; padding: 8px;')
        button_layout.addWidget(clear_btn)
        
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet('background-color: #666; color: white; padding: 8px;')
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def validate_amount_input(self, text, amount_input):
        if text == '':
            return
        
        try:
            cleaned_text = text.replace(' ', '').replace("'", "")
            if cleaned_text != '':
                float(cleaned_text)
        except ValueError:
            cursor_pos = amount_input.cursorPosition()
            amount_input.setText(text[:-1])
            amount_input.setCursorPosition(max(0, cursor_pos - 1))

    def save_budgets(self):
        try:
            budgets_to_save = []
            
            for widget_info in self.sub_category_widgets:
                amount_text = widget_info['amount_input'].text().strip().replace(' ', '').replace("'", "")
                if amount_text:
                    try:
                        amount = float(amount_text)
                        if amount >= 0:  # Allow 0 to clear budget
                            budgets_to_save.append({
                                'sub_category': widget_info['sub_category'],
                                'amount': amount
                            })
                    except ValueError:
                        continue
            
            if not budgets_to_save:
                QMessageBox.warning(self, 'Warning', 'No budget amounts specified')
                return
            
            # Save budgets for current month (this represents the fixed monthly budget)
            current_year = datetime.datetime.now().year
            current_month = datetime.datetime.now().month
            
            success_count = 0
            for budget_info in budgets_to_save:
                sub_category = budget_info['sub_category']
                amount = budget_info['amount']
                
                success = self.budget_app.add_or_update_budget(current_year, current_month, sub_category, amount)
                if success:
                    success_count += 1
            
            QMessageBox.information(
                self, 
                'Success', 
                f'Monthly budgets saved successfully!\n\n'
                f'Saved {success_count} budgets.'
            )
            self.accept()
                
        except Exception as e:
            print(f"Error saving budgets: {e}")
            QMessageBox.critical(self, 'Error', f'Error saving budgets: {str(e)}')

    def clear_budgets(self):
        reply = QMessageBox.question(
            self, 
            'Confirm Clear', 
            'Clear all monthly budgets?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Set all budget inputs to 0
            for widget_info in self.sub_category_widgets:
                widget_info['amount_input'].setText('0.00')