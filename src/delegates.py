from PyQt6.QtWidgets import QStyledItemDelegate, QComboBox, QDateEdit
from PyQt6.QtCore import Qt, QDate
import datetime
from custom_widgets import NoScrollComboBox

class ComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, items_getter=None):
        super().__init__(parent)
        self.items_getter = items_getter

    def createEditor(self, parent, option, index):
        editor = NoScrollComboBox(parent)
        if self.items_getter:
            items = self.items_getter()
            editor.addItems(items)
            
            # Calculate max width to ensure full text is visible in dropdown
            fm = editor.fontMetrics()
            max_width = 0
            for item in items:
                # horizontalAdvance is PyQt6, width() is older. Let's use horizontalAdvance.
                width = fm.horizontalAdvance(item)
                if width > max_width:
                    max_width = width
            
            # Add padding for scrollbar and frame
            popup_width = max_width + 40
            editor.view().setMinimumWidth(popup_width)
            
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        index = editor.findText(str(value)) 
        if index >= 0:
            editor.setCurrentIndex(index)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, Qt.ItemDataRole.EditRole)

class DateDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        # Value is string YYYY-MM-DD
        if value:
            try:
                 date = QDate.fromString(str(value), "yyyy-MM-dd")
                 editor.setDate(date)
            except:
                editor.setDate(QDate.currentDate())
        else:
             editor.setDate(QDate.currentDate())

    def setModelData(self, editor, model, index):
        date = editor.date()
        value = date.toString("yyyy-MM-dd")
        model.setData(index, value, Qt.ItemDataRole.EditRole)
