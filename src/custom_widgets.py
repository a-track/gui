from PyQt6.QtWidgets import QComboBox
from PyQt6.QtCore import Qt

class NoScrollComboBox(QComboBox):
    """
    A QComboBox that ignores wheel events to prevent accidental
    value changes when scrolling through a form.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def wheelEvent(self, event):
        # Ignore the event so it propagates to the parent (e.g., QScrollArea)
        # and doesn't change the selected item.
        event.ignore()
