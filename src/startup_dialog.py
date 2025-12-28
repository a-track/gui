
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                             QFileDialog, QHBoxLayout, QRadioButton, QLineEdit)
from PyQt6.QtCore import Qt
import os


class StartupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome to Budget Tracker")

        self.setFixedWidth(500)
        self.result_path = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel("Welcome! Let's get started.")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        instruction = QLabel("Where would you like to store your data?")
        instruction.setStyleSheet("margin-bottom: 10px;")
        layout.addWidget(instruction)

        self.radio_new = QRadioButton("Start Fresh (Create new database)")
        self.radio_sample = QRadioButton("Start with Sample Data")
        self.radio_existing = QRadioButton("Open Existing Database")
        self.radio_new.setChecked(True)
        self.mode = 'new'

        layout.addWidget(self.radio_new)
        layout.addWidget(self.radio_sample)
        layout.addWidget(self.radio_existing)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select location...")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_path)

        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)

        self.radio_new.toggled.connect(self.update_ui)
        self.radio_sample.toggled.connect(self.update_ui)
        self.radio_existing.toggled.connect(self.update_ui)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Start")
        self.ok_btn.clicked.connect(self.validate_and_accept)
        self.ok_btn.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
        """)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

        self.update_ui()

    def update_ui(self):
        if self.radio_new.isChecked():
            self.mode = 'new'
            self.path_input.setPlaceholderText(
                "Select folder to create 'budget.duckdb'...")
            self.browse_btn.setText("Select Folder...")
        elif self.radio_sample.isChecked():
            self.mode = 'sample'
            self.path_input.setPlaceholderText(
                "Select folder to create 'budget_sample.duckdb'...")
            self.browse_btn.setText("Select Folder...")
        else:
            self.mode = 'existing'
            self.path_input.setPlaceholderText(
                "Select existing .duckdb file...")
            self.browse_btn.setText("Select File...")

    def browse_path(self):
        if self.radio_new.isChecked():
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                self.path_input.setText(os.path.join(folder, "budget.duckdb"))
        elif self.radio_sample.isChecked():
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                self.path_input.setText(os.path.join(
                    folder, "budget_sample.duckdb"))
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Database", "", "DuckDB Files (*.duckdb);;All Files (*)")
            if file_path:
                self.path_input.setText(file_path)

    def validate_and_accept(self):
        path = self.path_input.text().strip()
        if not path:

            if self.radio_new.isChecked():
                path = os.path.abspath("budget.duckdb")
            elif self.radio_sample.isChecked():
                path = os.path.abspath("budget_sample.duckdb")
            else:
                return

        self.result_path = path
        self.accept()
