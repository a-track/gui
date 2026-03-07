# Budget Tracker v4.5

A powerful and user-friendly desktop application for personal finance management, built with Python, PyQt6, and DuckDB.

## Core Features

- **Transaction Management**: Easily record income, expenses, and transfers.
- **Efficient Data Entry**: 
    - Form persistence for Accounts, Categories, and Payees to speed up bulk entry.
    - **Smart Math Input**: Enter expressions like `12+5+20` directly into amount fields.
- **Account Management**: 
    - Support for multiple accounts and currencies.
    - **Active/Inactive Status**: Hide old accounts from selection lists without deleting history.
    - **Account Perspective**: Clear structured header with distinct Filter and Balance sections for exact balances.
- **Budgeting**: Set and track monthly budgets per sub-category.
- **Interactive Dashboards**: Completely redesigned for deeper insights.
    - **Hierarchical Breakdown**: View expenses by Category > Subcategory.
    - **Interactive Charts**: Pie, Trend, and Top Payees charts with detailed tooltips.
    - **Category Filter**: Filter charts to see specific costs (e.g. Living only).
- **Cash Flow Analysis**:
    - **Interactive Charts**: Visualize monthly income and expenses.
    - **Net Invested tracking** (Solid Purple Line) side-by-side with Income/Expenses.
    - **Cash Saved** metric in header (Net Savings - Investments).
- **Investment Performance**:
    - **Advanced Return Metrics**: Features **IRR** (Internal Rate of Return) and **TWR** (Time-Weighted Return).
    - True "Unrealized P&L" based on historical Cost Basis.
- **Global Search**:
    - **Persistent Search Bar**: Always accessible at the top of the window with `Ctrl+F`.
    - Filters content across Transactions, Categories, Accounts, Overview, and Performance tabs instantly.
- **Currency Conversion**: All charts and calculations strictly use historical exchange rates for maximum accuracy.
- **Robust Storage**: Fast and reliable local database using DuckDB (`budget.duckdb`).

## Requirements

- Python 3.8+
- PyQt6
- DuckDB

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/a-track/budget-tracker.git
   cd budget-tracker
   ```

2. Install dependencies (it is recommended to use a virtual environment):
   ```bash
   pip install PyQt6 duckdb
   ```

## Usage

Run the application using:
```bash
python src/main.py
```

## Project Structure

- `src/main.py`: Application entry point.
- `src/main_window_tabbed.py`: Main dashboard and tabbed interface logic.
- `src/transactions_dialog.py`: Dialog for viewing and editing transaction history.
- `src/accounts_dialog.py`: Account management (add/edit/archive).
- `src/budget_dialog.py`: Budget setting interface.
- `src/models.py`: Database interaction layer (DuckDB).
- `src/utils.py`: Utility functions (e.g., safe math evaluation).

## Version History

### v4.5 Updates
- Updated application to version 4.5
- Cleaned up obsolete Microsoft Access Code & Unused Python UI Files

### v4.4 Updates (Account Perspective Enhancements)
- **Account Perspective**:
  - **Start Period Balance**: Added a new "Period Start" balance display to clearly show the account status at the beginning of the selected timeframe.
  - **Multi-Month Selection**: Completely revamped the Month filter. Now supports selecting **multiple specific months** (e.g., "Jan + Mar") or using the new **"Select All"** toggle.
  - **Smart Filtering**: The filter dropdown stays open for easier multiple selections and defaults to "All Months" if nothing is selected.
  - **Default View**: Automatically selects the **Current Month** by default for quicker access to relevant data.
- **Transactions Tab**:
  - **Default View**: Automatically defaults to the **Current Month** when opening the application.
- **Inactive Accounts**: Hidden inactive accounts from the selection list to keep the interface clean.
- **UI Cleanup**: Simplified table headers by removing unused Excel-style column filters across all tabs.

### v4.3 Updates (UI Polish & Bug Fixes)
- **Header Visibility Fixes**: 
  - Increased column padding across **Investment Performance**, **Transactions**, **Investment Tab**, **Account Perspective**, and **Manage Accounts** tables to ensure all header titles are fully visible and readable.
- **Account Entries Layout**:
  - Refactored the **Account Perspective** header into two distinct rows to prevent UI overlap on smaller screens.
- **Bug Fixes**:
  - Fixed a critical bug where editing a confirmed transaction (which is blocked) would visually revert the row to incorrect data (e.g., wrong payee) when the table was sorted. Now reverts strictly to the original confirmed data.

### v4.2 Updates (Safety & Protection)
- **Confirmed Transactions Protection**:
  - **Sorting-Safe Logic**: Completely refactored edit/delete operations to use unique Transaction IDs. Modifying transactions is now 100% reliable even when the table is sorted by date, amount, or any other column.
  - **Lockdown**: Confirmed transactions are strictly protected from accidental deletion or modification.
  - **Smart Toggles**: Toggling the "Confirmed" checkbox (on/off) allows for quick status updates without triggering "blocked" warnings.

### v4.1 Updates (Global Visuals & Search)
- **Global Search & Visuals**:
  - Persistent Search Bar (`Ctrl+F`). Unified filtering across tabs.
  - Swiss Number Formatting (`12'345.67`).

### v3.11 Updates (Investment Performance)
- **Advanced Metrics**: Added IRR and TWR to calculate true ROI regardless of continuous deposits and withdrawals.

### v3.9 Updates 
- Account Perspective Overhaul with split balance view and smart filtering dates.

### v3.8 Updates
- Expenses Dashboard 2.0 with detailed interactive pie and trend charts.

## License

[MIT](LICENSE)
