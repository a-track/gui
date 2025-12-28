from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                             QFileDialog, QMessageBox, QGroupBox, QProgressBar, QApplication, QLineEdit)
from PyQt6.QtCore import QSettings
import os
from import_export import DataManager
from models import BudgetApp


class DataManagementTab(QWidget):
    def __init__(self, budget_app, parent=None):
        super().__init__(parent)
        self.budget_app = budget_app
        self.data_manager = DataManager(budget_app.db_path)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        title = QLabel("Data Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        db_group = QGroupBox("Database Information")
        db_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        db_layout = QVBoxLayout()
        db_layout.setSpacing(10)

        db_label = QLabel("Current Database Location:")
        db_layout.addWidget(db_label)

        db_path_field = QLineEdit(self.budget_app.db_path)
        db_path_field.setReadOnly(True)
        db_path_field.setStyleSheet(
            "background-color: #f5f5f5; color: #333; padding: 5px;")
        db_layout.addWidget(db_path_field)

        switch_btn = QPushButton("Switch Database...")
        switch_btn.clicked.connect(self.switch_database)
        switch_btn.setStyleSheet("""
            QPushButton {
                 background-color: #FF9800;
                 color: white;
                 padding: 5px 10px;
                 border-radius: 4px;
                 font-weight: bold;
            }
            QPushButton:hover {
                 background-color: #F57C00;
            }
        """)
        switch_btn.setToolTip(
            "Select a different database file (.db) to open.")
        db_layout.addWidget(switch_btn)

        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        export_group = QGroupBox("Export Data")
        export_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        export_layout = QVBoxLayout()
        export_layout.setSpacing(10)

        export_desc = QLabel(
            "Export all your data (Accounts, Categories, Transactions, Budgets) to an Excel file.")
        export_desc.setWordWrap(True)
        export_layout.addWidget(export_desc)

        export_btn = QPushButton("Export to Excel (.xlsx)")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        export_btn.clicked.connect(self.export_data)
        export_btn.setToolTip(
            "Export all Accounts, Transactions, Budgets, and Settings to an Excel file.")
        export_layout.addWidget(export_btn)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        import_group = QGroupBox("Import Data")
        import_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        import_layout = QVBoxLayout()
        import_layout.setSpacing(10)

        import_desc = QLabel("Import data from an Excel file into a NEW database.\n"
                             "This will create a fresh database file.")
        import_desc.setStyleSheet("color: #D32F2F;")
        import_desc.setWordWrap(True)
        import_layout.addWidget(import_desc)

        import_btn = QPushButton("Import from Excel (.xlsx)")
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        import_btn.clicked.connect(self.import_data)
        import_btn.setToolTip(
            "Overwrite current database with data from an Excel file.\nA backup will be created automatically.")
        import_layout.addWidget(import_btn)

        template_btn = QPushButton("Download Sample Template")
        template_btn.clicked.connect(self.download_template)
        template_btn.setToolTip(
            "Generate an empty Excel file with the correct structure for importing data.")
        template_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        import_layout.addWidget(template_btn)

        import_group.setLayout(import_layout)
        layout.addWidget(import_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        layout.addStretch()

    def update_progress(self, value):
        self.progress_bar.setValue(int(value))
        QApplication.processEvents()

    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data",
            os.path.expanduser("~/Desktop/budget_export.xlsx"),
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        if not file_path.endswith('.xlsx'):
            file_path += '.xlsx'

        self.progress_bar.show()
        self.progress_bar.setValue(0)
        QApplication.processEvents()

        try:
            success, msg = self.data_manager.export_to_excel(
                file_path, self.update_progress)

            if success:
                QMessageBox.information(self, "Export Successful", msg)
            else:
                QMessageBox.critical(self, "Export Failed", msg)
        except Exception as e:
            self.progress_bar.hide()
            QMessageBox.critical(
                self, "Export Error", f"An unexpected error occurred during export: {str(e)}")
        finally:
            self.progress_bar.hide()
            self.progress_bar.setValue(0)

    def import_data(self):

        new_db_path, _ = QFileDialog.getSaveFileName(
            self, "Create New Database for Import",
            os.path.expanduser("~/Documents/my_budget.duckdb"),
            "DuckDB Database (*.duckdb)"
        )

        if not new_db_path:
            return

        excel_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File to Import",
            os.path.expanduser("~/Desktop"),
            "Excel Files (*.xlsx)"
        )

        if not excel_path:
            return

        self.progress_bar.show()
        self.progress_bar.setValue(0)
        QApplication.processEvents()

        try:

            temp_app = BudgetApp(new_db_path)
            temp_app.close()

            importer = DataManager(new_db_path)

            success, msg = importer.import_from_excel(
                excel_path, self.update_progress, skip_backup=True)

            if success:
                QMessageBox.information(self, "Import Successful",
                                        f"{msg}\n\nThe application will now restart and open your new database.")

                settings = QSettings()
                settings.setValue("db_path", new_db_path)

                QApplication.exit(888)
            else:
                QMessageBox.critical(self, "Import Failed", msg)

                try:
                    if os.path.exists(new_db_path):
                        os.remove(new_db_path)
                except:
                    pass
        except Exception as e:
            self.progress_bar.hide()
            QMessageBox.critical(self, "Import Error",
                                 f"An unexpected error occurred: {str(e)}")
        finally:
            self.progress_bar.hide()
            self.progress_bar.setValue(0)

    def download_template(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Template",
            os.path.expanduser("~/Desktop/budget_template.xlsx"),
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        if not file_path.endswith('.xlsx'):
            file_path += '.xlsx'

        success, message = self.data_manager.generate_template(file_path)

        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

    def switch_database(self):
        reply = QMessageBox.question(
            self, 'Switch Database',
            "Are you sure you want to switch databases?\n"
            "The application will restart and ask for a database location.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:

            settings = QSettings()
            settings.remove("db_path")

            QApplication.exit(888)
