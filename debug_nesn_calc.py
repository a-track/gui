import sys
import os
import shutil

sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"
TEMP_DB = "debug_nesn_calc.duckdb"

def check_calc():
    if not os.path.exists(DB_PATH): return
    try: shutil.copy2(DB_PATH, TEMP_DB)
    except: pass
    target = TEMP_DB if os.path.exists(TEMP_DB) else DB_PATH
    
    app = BudgetApp(target)
    year = 2025
    print(f"Calculating for {year}...")
    data = app.get_monthly_investment_gains(year)
    
    found = False
    for m, res in data.items():
        gains = res.get('details', {}).get('gains', {})
        losses = res.get('details', {}).get('losses', {})
        
        val_g = 0
        if 'NESN.SW' in gains:
            val_g = gains['NESN.SW']
            found = True
            
        val_l = 0
        if 'NESN.SW' in losses:
            val_l = losses['NESN.SW']
            found = True
            
        if val_g != 0 or val_l != 0:
            print(f"Month {m}: Gain={val_g}, Loss={val_l}")
            
    if not found:
        print("NESN.SW not found in any month results.")
    else:
        print("NESN.SW found in results.")

    if os.path.exists(TEMP_DB): 
        try: os.remove(TEMP_DB)
        except: pass

if __name__ == "__main__":
    check_calc()
