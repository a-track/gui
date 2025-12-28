from PyQt6.QtWidgets import QComboBox


class NoScrollComboBox(QComboBox):
    """
    A QComboBox that ignores wheel events to prevent accidental
    value changes when scrolling through a form.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def wheelEvent(self, event):

        event.ignore()
