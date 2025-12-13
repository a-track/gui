# Budget Tracker GUI

A powerful and user-friendly desktop application for personal finance management, built with Python, PyQt6, and DuckDB.

## Features

- **Transaction Management**: Easily record income, expenses, and transfers.
- **Efficient Data Entry**: 
    - Form persistence for Accounts, Categories, and Payees to speed up bulk entry.
    - **Smart Math Input**: Enter expressions like `12+5+20` directly into amount fields.
- **Budgeting**: Set and track monthly budgets per sub-category.
- **Account Management**: 
    - Support for multiple accounts and currencies.
    - **Active/Inactive Status**: Hide old accounts from selection lists without deleting history.
- **Reporting**: 
    - Dashboard with summary of balances and recent transactions.
    - Account perspective views.
- **Robust Storage**: Fast and reliable local database using DuckDB (`budget.duckdb`).

## Requirements

- Python 3.8+
- PyQt6
- DuckDB

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/a-track/gui.git
   cd gui
   ```

2. Install dependencies (it is recommended to use a virtual environment):
   ```bash
   pip install PyQt6 duckdb
   ```

## Usage

Run the application using:
```bash
python main.py
```

## Project Structure

- `main.py`: Application entry point.
- `main_window.py`: Main dashboard and transaction entry logic.
- `transactions_dialog.py`: Dialog for viewing and editing transaction history.
- `accounts_dialog.py`: Account management (add/edit/archive).
- `budget_dialog.py`: Budget setting interface.
- `models.py`: Database interaction layer (DuckDB).
- `utils.py`: Utility functions (e.g., safe math evaluation).

## License

[MIT](LICENSE)
