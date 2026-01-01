import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"

def list_tables():
    if not os.path.exists(DB_PATH):
        print("DB not found")
        return

    app = BudgetApp(DB_PATH)
    conn = app._get_connection()
    
    print("Tables:")
    rows = conn.execute("SHOW TABLES").fetchall()
    for r in rows:
        print(r)

if __name__ == "__main__":
    list_tables()
