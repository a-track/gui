"""
Custom delegates for table cell editing.
Simplified version without complex painting.
"""

from PyQt6.QtWidgets import QComboBox, QStyledItemDelegate
from PyQt6.QtCore import Qt


class ComboBoxDelegate(QStyledItemDelegate):
    """Delegate for displaying combo boxes in table cells."""
    
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        # Make dropdown wider to show full text
        editor.setMinimumWidth(200)
        editor.setMaxVisibleItems(15)
        editor.view().setMinimumWidth(200)
        # Clean styling
        editor.setStyleSheet("""
            QComboBox { 
                background-color: white; 
                border: 2px solid #4A90E2;
                padding: 4px 8px;
                font-size: 11pt;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #4A90E2;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #4A90E2;
                selection-background-color: #4A90E2;
                selection-color: white;
                outline: none;
                padding: 2px;
                font-size: 11pt;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #E3F2FD;
                color: black;
            }
        """)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.ItemDataRole.EditRole)
        if value:
            idx = editor.findText(str(value))
            if idx >= 0:
                editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
    
    def updateEditorGeometry(self, editor, option, index):
        # Make editor wider than cell to show full dropdown content
        rect = option.rect
        rect.setWidth(max(rect.width(), 200))
        editor.setGeometry(rect)