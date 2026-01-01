import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

# Path gathered from screenshot
DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"

def debug_invest():
    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    print(f"Connecting to {DB_PATH}...")
    app = BudgetApp(DB_PATH)
    
    print("Fetching available years...")
    years = app.get_available_years()
    print(f"Years: {years}")
    
    # Check Investment Accounts presence
    print("Checking investment accounts...")
    conn = app._get_connection()
    try:
        inv_rows = conn.execute("SELECT id, account, valuation_strategy FROM accounts WHERE is_investment=1").fetchall()
        print(f"Investment Accounts ({len(inv_rows)}):")
        for r in inv_rows:
            print(r)
    except Exception as e:
        print(f"Error checking accounts: {e}")
        
    if years:
        year = years[0]
        print(f"\nFetching investment gains for {year}...")
        try:
            data = app.get_monthly_investment_gains(year) # this calls the method in models.py which we fixed
            print("Monthly Gains Data Fetched!")
            import json
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
        except Exception as e:
            print(f"Error fetching gains: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_invest()
