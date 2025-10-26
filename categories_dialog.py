from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QLineEdit, QComboBox, QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


class CategoriesDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.parent_window = parent
        
        self.setWindowTitle('Manage Categories')
        self.setMinimumSize(800, 500)
        
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
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Category', 'Sub Category', 'Actions'])

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
        self.table.setColumnWidth(2, 70)

        content_based_columns = [0, 1]
        for col in content_based_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)

        self.table.verticalHeader().setDefaultSectionSize(35)
        layout.addWidget(self.table)
        
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        self.load_categories()
        self.load_parent_categories()
    
    def load_parent_categories(self):
        categories = self.budget_app.get_all_categories()
        parent_categories = set()
        
        for category in categories:
            parent_categories.add(category.category)
        
        self.parent_category_combo.clear()
        self.parent_category_combo.addItems(sorted(list(parent_categories)))
    
    def on_parent_category_changed(self, parent_category):
        pass
    
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
                
                self.table.setCellWidget(row, 2, action_widget)
            
            self.table.resizeColumnsToContents()
            
            self.table.setColumnWidth(0, max(120, self.table.columnWidth(0)))
            self.table.setColumnWidth(1, max(120, self.table.columnWidth(1)))
            self.table.setColumnWidth(2, max(70, self.table.columnWidth(2)))
            
            self.show_status(f'Loaded {len(categories)} categories')
            
            self.load_parent_categories()
            
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