import sys
import os
import shutil
import time
import datetime
from decimal import Decimal

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"
TEMP_DB = "debug_flows.duckdb"

def check_flows():
    # Retry loop to copy DB
    copied = False
    for i in range(5):
        try:
            if os.path.exists(TEMP_DB): os.remove(TEMP_DB)
            shutil.copy2(DB_PATH, TEMP_DB)
            copied = True
            break
        except Exception as e:
            time.sleep(1)
            
    if not copied:
        print("Could not copy DB (Locked).")
        return

    app = BudgetApp(TEMP_DB)
    conn = app._get_connection()
    
    # 1. Find VWRL
    res = conn.execute("SELECT id, account FROM accounts WHERE account LIKE '%VWRL%'").fetchone()
    if not res:
        print("VWRL not found.")
        return
    aid, name = res
    print(f"Account: {name} (ID: {aid})")
    
    # 2. Check Txs in Dec 2025
    start = datetime.date(2025, 12, 1)
    end = datetime.date(2025, 12, 31)
    
    rows = conn.execute("""
        SELECT date, description, amount, source_account_id, destination_account_id, type
        FROM transactions 
        WHERE (source_account_id = ? OR destination_account_id = ?)
        AND date >= ? AND date <= ?
    """, (aid, aid, start, end)).fetchall()
    
    print("\nDec 2025 Transactions:")
    if not rows:
        print("No transactions found!")
    for r in rows:
        print(f" - {r[0]}: {r[1]} Amt={r[2]} Src={r[3]} Dst={r[4]} Type={r[5]}")
        
    conn.close()
    try: os.remove(TEMP_DB)
    except: pass

if __name__ == "__main__":
    check_flows()
