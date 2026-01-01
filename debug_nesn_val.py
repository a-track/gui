import sys
import os
import shutil

sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"
TEMP_DB = "debug_nesn_val.duckdb"
AID = 119 # NESN.SW

def check_val():
    if not os.path.exists(DB_PATH): return
    try: 
        shutil.copy2(DB_PATH, TEMP_DB)
    except: 
        pass
    
    target = TEMP_DB if os.path.exists(TEMP_DB) else DB_PATH
    
    try:
        app = BudgetApp(target)
        conn = app._get_connection()
        print(f"Checking Valuations for ID {AID}...")
        rows = conn.execute("SELECT date, value FROM investment_valuations WHERE account_id=?", (AID,)).fetchall()
        print(f"Entries: {len(rows)}")
        for r in rows:
            print(r)
            
        print("\nChecking Transactions...")
        txs = conn.execute("SELECT date, type, amount FROM transactions WHERE account_id=?", (AID,)).fetchall()
        print(f"TXs: {len(txs)}")
        for t in txs:
            print(t)
            
    except Exception as e:
        print(e)
    finally:
        if os.path.exists(TEMP_DB):
            try:
                os.remove(TEMP_DB)
            except:
                pass

if __name__ == "__main__":
    check_val()
