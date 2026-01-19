from PyQt6.QtWidgets import QComboBox, QStyledItemDelegate
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPalette, QBrush, QColor
from PyQt6.QtCore import Qt, QEvent


class NoScrollComboBox(QComboBox):
    """
    A QComboBox that ignores wheel events to prevent accidental
    value changes when scrolling through a form.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def wheelEvent(self, event):
        event.ignore()


class CheckableComboBox(NoScrollComboBox):
    """
    A ComboBox that allows multiple items to be selected via checkboxes.
    Populated with a list of strings. 'All' functionality can be handled implicitly (none checked = all).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().pressed.connect(self.handle_item_pressed)
        self.setModel(QStandardItemModel(self))
        self.is_programmatic_change = False
        
        # Keep popup open when clicking checks
        self.view().viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.view().viewport():
            if event.type() == QEvent.Type.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().itemFromIndex(index)
                if item and (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                    if item.checkState() == Qt.CheckState.Checked:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Checked)
                    self.update_display_text()
                    return True # Eat the event to prevent closing
        return super().eventFilter(obj, event)

    def handle_item_pressed(self, index):
        # Handled in eventFilter now
        pass

    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        item.setData(data, Qt.ItemDataRole.UserRole)
        self.model().appendRow(item)
        self.update_display_text()
        
    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def get_checked_data(self):
        checked_data = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.CheckState.Checked:
                userData = item.data(Qt.ItemDataRole.UserRole)
                # If no user data, return text (or index?) - consistency with standard addItem
                # Standard addItem stores text. UserRole is extra.
                # Let's return UserRole if present, else text? 
                # or just return list of data. 
                checked_data.append(userData if userData is not None else item.text())
        return checked_data
        
    def get_checked_indices(self):
        return [i for i in range(self.model().rowCount()) 
                if self.model().item(i).checkState() == Qt.CheckState.Checked]

    def update_display_text(self):
        # Use line edit to display summary
        if not self.isEditable():
            self.setEditable(True)
            self.lineEdit().setReadOnly(True)
            
        checked_data = self.get_checked_data()
        if not checked_data:
            self.setEditText("All")
        else:
            self.setEditText(", ".join(map(str, checked_data)))

    def hidePopup(self):
        super().hidePopup()
        self.update_display_text()

    def showPopup(self):
        super().showPopup()
        # Optional: could update checking here if needed


