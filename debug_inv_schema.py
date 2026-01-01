import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

# Path gathered from screenshot
DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"

def debug_schema():
    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    print(f"Connecting to {DB_PATH}...")
    app = BudgetApp(DB_PATH)
    conn = app._get_connection()
    
    print("\naccounts table schema:")
    rows = conn.execute("PRAGMA table_info(accounts)").fetchall()
    for r in rows:
        print(r)

if __name__ == "__main__":
    debug_schema()
