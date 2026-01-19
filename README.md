# Budget Tracker GUI v4.4

A powerful and user-friendly desktop application for personal finance management, built with Python, PyQt6, and DuckDB.

## Features

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
- **Global Search**:
  - **Persistent Search Bar**: Always accessible at the top of the window with `Ctrl+F` shortcut support.
  - **Unified Experience**: Filters content across **Transactions**, **Categories**, **Accounts**, **Overview**, and **Performance** tabs instantly.
- **Swiss Number Formatting**: Standardized number display using apostrophe separators (e.g., `12'345.67`) throughout the entire application for cleaner readability.
- **Global Historical FX**: All charts and calculations now strictly use historical exchange rates for maximum accuracy.
- **Enhanced Cash Flow**:
  - New "Net Invested" tracking (Solid Purple Line) side-by-side with Income/Expenses.
  - "Cash Saved" metric in header (Net Savings - Investments).
- **Investment Performance**:
  - True "Unrealized P&L" based on historical Cost Basis.
  - Aligned visuals across all tabs.
- **UI Improvements**: Reordered tabs for better flow, consistent styling, and code cleanup.

### v3.11 Updates (Investment Perfomance)
- **Advanced Return Metrics**: Added **IRR** (Internal Rate of Return) and **TWR** (Time-Weighted Return) to the Investment Performance tab.
    - **IRR**: Calculates your personal money-weighted return (accuracy requires historical cash flow data).
    - **TWR**: Calculates the asset's true performance independent of your deposits/withdrawals.
    - **Full Support**: TWR now works for both "Total Value" managed accounts AND "Price/Qty" tracked accounts by reconstructing historical value curves.
- **Total Portfolio Metrics**: The "Total" row now aggregates all accounts to show a unified Portfolio IRR and TWR (currency adjusted to CHF).
- **Corrected Logic**: Improved handling of stock purchases/sales in quantity tracking for more accurate performance calculation.

### v3.10 Updates
- **Access / Power BI Export**:
    - **One-Click Export**: Export your entire financial dataset to a Microsoft Access (`.accdb`) database.
    - **Ultra-Fast Performance**: Optimized "Bulk Load" engine using Access Automation (imports 100k+ rows in seconds).
    - **Power BI Ready**: Includes pre-calculated tables (`api_balance`, `api_currency` with historical rates) for instant reporting.
    - **Data Integrity**: Clean dates (no timestamps), SCD2 exchange rates, and full dependency handling.

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
