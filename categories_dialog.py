from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QLineEdit, QComboBox, 
                             QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import datetime


class CategoriesDialog(QDialog):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        
        self.budget_app = budget_app
        self.parent_window = parent
        
        self.setWindowTitle('Manage Categories')
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        type_parent_layout = QHBoxLayout()
        
        type_parent_layout.addWidget(QLabel('Category Type:'))
        self.category_type_combo = QComboBox()
        self.category_type_combo.addItems(['Expense', 'Income'])
        self.category_type_combo.currentTextChanged.connect(self.on_category_type_changed)
        type_parent_layout.addWidget(self.category_type_combo)
        
        type_parent_layout.addWidget(QLabel('Category:'))
        self.parent_category_combo = QComboBox()
        self.parent_category_combo.setEditable(True)
        self.parent_category_combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.parent_category_combo.currentTextChanged.connect(self.on_parent_category_changed)
        type_parent_layout.addWidget(self.parent_category_combo)
        
        type_parent_layout.addStretch()
        layout.addLayout(type_parent_layout)
        
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
        
        layout.addLayout(sub_category_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Category Type', 'Category', 'Sub Category', 'Actions'])
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)
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
        for col in range(4):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.verticalHeader().setDefaultSectionSize(35)
        layout.addWidget(self.table)
        
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.load_categories()

    def on_category_type_changed(self, category_type):
        """When category type changes, update the parent categories combo"""
        self.load_parent_categories(category_type)

    def on_parent_category_changed(self, parent_category):
        """When parent category changes - placeholder for future functionality"""
        pass

    def load_parent_categories(self, category_type=None):
        """Load parent categories filtered by type"""
        categories = self.budget_app.get_all_categories()
        parent_categories = set()
        
        for category in categories:
            if category_type is None or category.category_type == category_type:
                parent_categories.add(category.category)
        
        current_text = self.parent_category_combo.currentText()
        self.parent_category_combo.clear()
        self.parent_category_combo.addItems(sorted(list(parent_categories)))
        
        index = self.parent_category_combo.findText(current_text)
        if index >= 0:
            self.parent_category_combo.setCurrentIndex(index)

    def load_categories(self):
        try:
            self.table.blockSignals(True)
            categories = self.budget_app.get_all_categories()
            self.table.setRowCount(len(categories))
            
            for row, category in enumerate(categories):
                type_item = QTableWidgetItem(category.category_type)
                self.table.setItem(row, 0, type_item)
                
                parent_item = QTableWidgetItem(category.category)
                self.table.setItem(row, 1, parent_item)
                
                sub_item = QTableWidgetItem(category.sub_category)
                # sub_item.setFlags(sub_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Allow editing now
                self.table.setItem(row, 2, sub_item)
                
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
            
            self.table.setColumnWidth(0, max(100, self.table.columnWidth(0)))
            self.table.setColumnWidth(1, max(120, self.table.columnWidth(1)))
            self.table.setColumnWidth(2, max(120, self.table.columnWidth(2)))
            self.table.setColumnWidth(3, max(70, self.table.columnWidth(3)))
            
            self.table.blockSignals(False)
            self.show_status(f'Loaded {len(categories)} categories')
            
            current_type = self.category_type_combo.currentText()
            self.load_parent_categories(current_type)
            
        except Exception as e:
            print(f"Error loading categories: {e}")
            self.table.blockSignals(False)
            self.show_status('Error loading categories', error=True)

    def on_cell_changed(self, row, column):
        try:
            item = self.table.item(row, column)
            if not item:
                return
                
            # We need the ORIGINAL sub_category to identify the row in DB
            # We can't rely on column 2 item if it was just changed.
            # But wait, if column 2 changed, item.text() is the NEW value.
            # We need the OLD sub_category.
            # The delete button has the property set, we can match row?
            # Or we store it in UserRole data.
            
            # Let's find the delete button for this row to get the original ID?
            # No, if we reload table, everything is fine.
            # But here we are in the middle of editing.
            
            # Better approach: Store original ID in UserRole of the item
            
            # For now, let's try to get it from the delete button which shouldn't have changed yet?
            # Actually, the delete button is created in load_categories with property set.
            # So until we reload, the delete button has the old sub_category.
            
            cell_widget = self.table.cellWidget(row, 3) # Action column
            if cell_widget:
                # Find the button inside
                btn = cell_widget.findChild(QPushButton)
                if btn:
                    sub_category = btn.property('sub_category')
                else:
                    return
            else:
                return

            new_value = item.text().strip()
            
            kwargs = {}
            if column == 0: # Type
                kwargs['new_type'] = new_value
            elif column == 1: # Parent Category
                kwargs['new_category'] = new_value
            elif column == 2: # Sub Category (PK)
                kwargs['new_sub_category'] = new_value
            else:
                return
                
            success = self.budget_app.update_category(sub_category, **kwargs)
            
            if success:
                self.show_status(f'Category updated successfully')
                if column == 2:
                    # If we renamed PK, we MUST reload the table to update all references/buttons
                    self.load_categories()
                else:
                    current_type = self.category_type_combo.currentText()
                    self.load_parent_categories(current_type)
            else:
                self.show_status(f'Error updating category', error=True)
                self.revert_cell(row, column, sub_category)
                
        except Exception as e:
            print(f"Error in on_cell_changed: {e}")
            self.show_status('Error updating category', error=True)
            try:
                 # Revert needs the OLD sub_category
                 cell_widget = self.table.cellWidget(row, 3) 
                 if cell_widget:
                    btn = cell_widget.findChild(QPushButton)
                    if btn:
                        sub_category = btn.property('sub_category')
                        self.revert_cell(row, column, sub_category)
            except:
                pass

    def revert_cell(self, row, column, sub_category):
        try:
            self.table.blockSignals(True)
            # Need to fetch original category data
            # Since we don't have a direct "get_category" by PK method handy that returns object easily without iterating all
            # We iterate all (cached in memory usually fine, or fetch all)
            categories = self.budget_app.get_all_categories()
            category = next((c for c in categories if c.sub_category == sub_category), None)
            
            if category:
                value = ""
                if column == 0:
                    value = category.category_type
                elif column == 1:
                    value = category.category
                
                self.table.item(row, column).setText(value)
        finally:
            self.table.blockSignals(False)

    def add_category(self):
        category_type = self.category_type_combo.currentText()
        parent_category = self.parent_category_combo.currentText().strip()
        sub_category = self.sub_category_input.text().strip()
        
        if not parent_category or not sub_category:
            self.show_status('Please enter both category and sub category', error=True)
            return
        
        success = self.budget_app.add_category(sub_category, parent_category, category_type)
        
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