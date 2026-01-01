import sys
import os
import shutil

sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"
TEMP_DB = "debug_strat.duckdb"

def check_strat():
    if not os.path.exists(DB_PATH): return
    try: shutil.copy2(DB_PATH, TEMP_DB)
    except: pass
    target = TEMP_DB if os.path.exists(TEMP_DB) else DB_PATH
    
    app = BudgetApp(target)
    conn = app._get_connection()
    r = conn.execute("SELECT id, account, valuation_strategy FROM accounts WHERE id=119").fetchone()
    print(f"ID={r[0]}, Name='{r[1]}', Strat='{r[2]}'")

    if os.path.exists(TEMP_DB): 
        try: os.remove(TEMP_DB)
        except: pass

if __name__ == "__main__":
    check_strat()
