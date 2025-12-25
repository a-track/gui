# Budget Tracker GUI v3.9

A powerful and user-friendly desktop application for personal finance management, built with Python, PyQt6, and DuckDB.

## Features

### v3.9 Updates
- **Account Perspective Overhaul**:
    - **New Layout**: Clear structured header with distinct Filter and Balance sections.
    - **Balance Cards**: Split view for "Period End Balance" (balance at selected date) vs "Total Balance" (current actual balance).
    - **Precision**: Fixed Swiss Franc rounding logic for exact balance matching.
- **Show All Dates**: New checkbox to toggle off date filters and view complete history instantly.
- **Tab Management**:
    - **Persistent Context Menu**: Easier tab organization.
    - **Safety**: Prevents closing the last tab or accidental hiding of active tabs.
- **Stability**: Fixed crashes related to empty charts and zero-tab states.

### v3.8 Updates
- **Expenses Dashboard 2.0**: Completely redesigned for deeper insights.
    - **Hierarchical Breakdown**: View expenses by Category > Subcategory.
    - **Interactive Charts**: Pie, Trend, and Top Payees charts with detailed tooltips.
    - **Category Filter**: Filter charts to see specific costs (e.g. Living only).
    - **Currency Conversion**: All expenses are automatically converted to CHF using historical rates.
- **Top Payees**: Improved visualization with interactive value labels.

### Core Features
- **Transaction Management**: Easily record income, expenses, and transfers.
- **Efficient Data Entry**: 
    - Form persistence for Accounts, Categories, and Payees to speed up bulk entry.
    - **Smart Math Input**: Enter expressions like `12+5+20` directly into amount fields.
- **Budgeting**: Set and track monthly budgets per sub-category.
- **Cash Flow Analysis**:
    - **Interactive Charts**: Visualize monthly income and expenses.
    - **Smart Filtering**: Automatically hides future months for cleaner views.
- **Account Management**: 
    - Support for multiple accounts and currencies.
    - **Active/Inactive Status**: Hide old accounts from selection lists without deleting history.
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
