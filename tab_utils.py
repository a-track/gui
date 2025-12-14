"""
Wrapper classes to convert existing dialogs into tab widgets for the tabbed interface.
These classes extract the content from dialog classes and present them as tabs.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout


def create_tab_from_dialog(dialog_class, budget_app, parent):
    """
    Generic function to create a tab widget from a dialog class.
    Extracts the dialog's content and returns it as a QWidget suitable for tabs.
    """
    # Create the dialog instance
    dialog = dialog_class(budget_app, parent)
    
    # Create a new widget to hold the dialog's content
    tab_widget = QWidget()
    layout = QVBoxLayout()
    layout.setContentsMargins(10, 10, 10, 10)
    tab_widget.setLayout(layout)
    
    # Get the dialog's layout and transfer all widgets to the tab
    dialog_layout = dialog.layout()
    if dialog_layout:
        # Transfer all widgets from dialog to tab
        while dialog_layout.count():
            item = dialog_layout.takeAt(0)
            if item.widget():
                layout.addWidget(item.widget())
            elif item.layout():
                layout.addLayout(item.layout())
    
    # Store reference to original dialog for method access
    tab_widget.dialog_instance = dialog
    tab_widget.refresh_data = getattr(dialog, 'refresh_table', lambda: None) or getattr(dialog, 'load_data', lambda: None)
    
    return tab_widget
