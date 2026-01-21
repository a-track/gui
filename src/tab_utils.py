from PyQt6.QtWidgets import QWidget, QVBoxLayout

def create_tab_from_dialog(dialog_class, budget_app, parent):
    
    dialog = dialog_class(budget_app, parent)

    tab_widget = QWidget()
    layout = QVBoxLayout()
    layout.setContentsMargins(10, 10, 10, 10)
    tab_widget.setLayout(layout)

    dialog_layout = dialog.layout()
    if dialog_layout:

        while dialog_layout.count():
            item = dialog_layout.takeAt(0)
            if item.widget():
                layout.addWidget(item.widget())
            elif item.layout():
                layout.addLayout(item.layout())

    tab_widget.dialog_instance = dialog
    tab_widget.refresh_data = getattr(dialog, 'refresh_table', lambda: None) or getattr(
        dialog, 'load_data', lambda: None)

    return tab_widget