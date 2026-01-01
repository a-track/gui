import sys
import os
import shutil

sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"
TEMP_DB = "debug_nesn.duckdb"

def find_nesn():
    if not os.path.exists(DB_PATH):
        print("DB not found")
        return

    # Copy to avoid lock
    try:
        shutil.copy2(DB_PATH, TEMP_DB)
    except:
        print("Could not copy DB (might be locked). trying to read if possible or failing.")
        # If user is running app, this might fail.
        # But I'll try to use the temp one if it exists from previous run or just try to open main if copy fails (DuckDB might allow read only?)
        # Actually simplest is to try copy, if fail, warn user.
        pass

    target_db = TEMP_DB if os.path.exists(TEMP_DB) else DB_PATH
    
    try:
        app = BudgetApp(target_db)
        conn = app._get_connection()
        
        print(f"Searching for 'NESN' in accounts...")
        rows = conn.execute("SELECT id, account, is_investment, valuation_strategy, currency FROM accounts WHERE account LIKE '%NESN%' OR account LIKE '%Nestle%'").fetchall()
        
        if rows:
            for r in rows:
                print(f"FOUND: ID={r[0]}, Name='{r[1]}', Investment={r[2]}, Strat='{r[3]}', Curr='{r[4]}'")
        else:
            print("No account found with 'NESN' or 'Nestle' in name.")
            
        print("\nSearching for 'NESN' in transactions...")
        # Check if it's just a description
        tx_rows = conn.execute("SELECT count(*) FROM transactions WHERE description LIKE '%NESN%' OR description LIKE '%Nestle%'").fetchone()
        print(f"Transactions containing 'NESN': {tx_rows[0]}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
         if os.path.exists(TEMP_DB):
            try:
                os.remove(TEMP_DB)
            except:
                pass

if __name__ == "__main__":
    find_nesn()
