from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QLineEdit, QComboBox, 
                             QWidget, QDoubleSpinBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import datetime


class CategoriesDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.parent_window = parent
        self.current_budgets = {}
        
        self.setWindowTitle('Manage Categories')
        self.setMinimumSize(1000, 500)
        
        layout = QVBoxLayout()
        
        new_category_layout = QVBoxLayout()
        
        parent_layout = QHBoxLayout()
        parent_layout.addWidget(QLabel('Category:'))
        self.parent_category_combo = QComboBox()
        self.parent_category_combo.setEditable(True)
        self.parent_category_combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.parent_category_combo.currentTextChanged.connect(self.on_parent_category_changed)
        parent_layout.addWidget(self.parent_category_combo)
        
        parent_layout.addStretch()
        new_category_layout.addLayout(parent_layout)
        
        sub_category_layout = QHBoxLayout()
        sub_category_layout.addWidget(QLabel('Sub Category:'))
        self.sub_category_input = QLineEdit()
        self.sub_category_input.setPlaceholderText('Enter sub category name')
        sub_category_layout.addWidget(self.sub_category_input)
        
        sub_category_layout.addStretch()
        
        add_btn = QPushButton('Add Category')
        add_btn.clicked.connect(self.add_category)
        add_btn.setStyleSheet('background-color: #4CAF50; color: white; padding: 8px;')
        sub_category_layout.addWidget(add_btn)
        
        new_category_layout.addLayout(sub_category_layout)
        layout.addLayout(new_category_layout)
        
        budget_layout = QHBoxLayout()
        budget_layout.addWidget(QLabel('Set Monthly Budget:'))
        
        budget_layout.addWidget(QLabel('Year:'))
        self.budget_year_combo = QComboBox()
        self.populate_budget_years()
        budget_layout.addWidget(self.budget_year_combo)
        
        budget_layout.addWidget(QLabel('Month:'))
        self.budget_month_combo = QComboBox()
        self.populate_budget_months()
        budget_layout.addWidget(self.budget_month_combo)
        
        budget_layout.addWidget(QLabel('Sub Category:'))
        self.budget_sub_category_combo = QComboBox()
        budget_layout.addWidget(self.budget_sub_category_combo)
        
        budget_layout.addWidget(QLabel('Amount:'))
        self.budget_amount_input = QDoubleSpinBox()
        self.budget_amount_input.setRange(0, 1000000)
        self.budget_amount_input.setDecimals(2)
        self.budget_amount_input.setPrefix('CHF ')
        self.budget_amount_input.setMaximumWidth(100)
        budget_layout.addWidget(self.budget_amount_input)
        
        set_budget_btn = QPushButton('Set Budget')
        set_budget_btn.clicked.connect(self.set_budget)
        set_budget_btn.setStyleSheet('background-color: #2196F3; color: white; padding: 5px;')
        budget_layout.addWidget(set_budget_btn)
        
        budget_layout.addStretch()
        layout.addLayout(budget_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Category', 'Sub Category', 'Current Month Budget', 'Actions'])

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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
        self.table.setColumnWidth(3, 100)

        content_based_columns = [0, 1, 2]
        for col in content_based_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)

        self.table.verticalHeader().setDefaultSectionSize(35)
        layout.addWidget(self.table)
        
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        self.load_parent_categories()
        self.populate_budget_sub_categories()
        self.load_current_budgets()
        self.load_categories()
    
    def populate_budget_years(self):
        current_year = datetime.datetime.now().year
        years = list(range(current_year - 1, current_year + 2))
        self.budget_year_combo.addItems([str(year) for year in years])
        self.budget_year_combo.setCurrentText(str(current_year))
    
    def populate_budget_months(self):
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        self.budget_month_combo.addItems(months)
        current_month = datetime.datetime.now().month
        self.budget_month_combo.setCurrentIndex(current_month - 1)
    
    def populate_budget_sub_categories(self):
        categories = self.budget_app.get_all_categories()
        self.budget_sub_category_combo.clear()
        for category in categories:
            self.budget_sub_category_combo.addItem(category.sub_category)
    
    def load_parent_categories(self):
        categories = self.budget_app.get_all_categories()
        parent_categories = set()
        
        for category in categories:
            parent_categories.add(category.category)
        
        self.parent_category_combo.clear()
        self.parent_category_combo.addItems(sorted(list(parent_categories)))
    
    def on_parent_category_changed(self, parent_category):
        pass
    
    def load_current_budgets(self):
        """Load current month's budgets for display"""
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        self.current_budgets = self.budget_app.get_all_budgets_for_period(current_year, current_month)
    
    def load_categories(self):
        try:
            categories = self.budget_app.get_all_categories()
            self.table.setRowCount(len(categories))
            
            for row, category in enumerate(categories):
                parent_item = QTableWidgetItem(category.category)
                parent_item.setFlags(parent_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, parent_item)
                
                sub_item = QTableWidgetItem(category.sub_category)
                sub_item.setFlags(sub_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 1, sub_item)
                
                # Current month budget
                current_budget = self.current_budgets.get(category.sub_category, 0.0)
                budget_item = QTableWidgetItem(f"CHF {current_budget:.2f}" if current_budget > 0 else "")
                budget_item.setFlags(budget_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if current_budget > 0:
                    budget_item.setForeground(QColor(0, 128, 0))  # Green for set budgets
                    budget_item.setFont(QFont("", weight=QFont.Weight.Bold))
                self.table.setItem(row, 2, budget_item)
                
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(1, 1, 1, 1)
                action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                delete_btn = QPushButton('✕')
                delete_btn.setFixedSize(22, 22)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #ff4444;
                        color: white;
                        border: none;
                        border-radius: 11px;
                        font-weight: bold;
                        font-size: 9px;
                        margin: 0px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #cc0000;
                    }
                    QPushButton:pressed {
                        background-color: #990000;
                    }
                ''')
                delete_btn.setProperty('sub_category', category.sub_category)
                delete_btn.clicked.connect(self.delete_category)
                delete_btn.setToolTip('Delete category')
                
                action_layout.addWidget(delete_btn)
                action_widget.setLayout(action_layout)
                
                self.table.setCellWidget(row, 3, action_widget)
            
            self.table.resizeColumnsToContents()
            
            self.table.setColumnWidth(0, max(120, self.table.columnWidth(0)))
            self.table.setColumnWidth(1, max(120, self.table.columnWidth(1)))
            self.table.setColumnWidth(2, max(150, self.table.columnWidth(2)))
            self.table.setColumnWidth(3, max(70, self.table.columnWidth(3)))
            
            self.show_status(f'Loaded {len(categories)} categories')
            
            self.load_parent_categories()
            self.populate_budget_sub_categories()
            
        except Exception as e:
            print(f"Error loading categories: {e}")
            self.show_status('Error loading categories', error=True)
    
    def add_category(self):
        parent_category = self.parent_category_combo.currentText().strip()
        sub_category = self.sub_category_input.text().strip()
        
        if not parent_category or not sub_category:
            self.show_status('Please enter both category and sub category', error=True)
            return
        
        success = self.budget_app.add_category(sub_category, parent_category)
        
        if success:
            self.show_status('Category added successfully!')
            self.sub_category_input.clear()
            self.load_categories()
        else:
            self.show_status('Error adding category', error=True)
    
    def set_budget(self):
        try:
            year = int(self.budget_year_combo.currentText())
            month = self.budget_month_combo.currentIndex() + 1
            sub_category = self.budget_sub_category_combo.currentText()
            budget_amount = self.budget_amount_input.value()
            
            if not sub_category:
                self.show_status('Please select a sub category', error=True)
                return
            
            if budget_amount <= 0:
                self.show_status('Budget amount must be greater than 0', error=True)
                return
            
            success = self.budget_app.add_or_update_budget(year, month, sub_category, budget_amount)
            
            if success:
                self.show_status(f'Budget for {sub_category} set to CHF {budget_amount:.2f} for {month}/{year}')
                self.budget_amount_input.setValue(0)
                self.load_current_budgets()
                self.load_categories()
            else:
                self.show_status('Error setting budget', error=True)
                
        except Exception as e:
            print(f"Error setting budget: {e}")
            self.show_status('Error setting budget', error=True)
    
    def delete_category(self):
        try:
            button = self.sender()
            sub_category = button.property('sub_category')
            
            reply = QMessageBox.question(
                self, 
                'Confirm Delete', 
                f'Delete category "{sub_category}"?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success, message = self.budget_app.delete_category(sub_category)
                if success:
                    self.show_status('Category deleted successfully!')
                    self.load_categories()
                else:
                    self.show_status(f'Error: {message}', error=True)
                    
        except Exception as e:
            print(f"Error deleting category: {e}")
            self.show_status('Error deleting category', error=True)
    
    def show_status(self, message, error=False):
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet('color: #f44336; padding: 5px; font-weight: bold;')
        else:
            self.status_label.setStyleSheet('color: #4CAF50; padding: 5px;')
        
        QTimer.singleShot(5000, lambda: self.status_label.setText(''))