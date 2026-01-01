import sys
import os
import shutil
import time

sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

# Original Path
DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"
TEMP_DB = "debug_fibi.duckdb"

def deep_debug():
    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    # Copy DB to avoid lock
    print(f"Copying DB to {TEMP_DB}...")
    try:
        shutil.copy2(DB_PATH, TEMP_DB)
    except Exception as e:
        print(f"Failed to copy DB: {e}")
        return

    try:
        app = BudgetApp(TEMP_DB)
        conn = app._get_connection()
        
        # 1. Check Accounts
        print("\n--- Accounts ---")
        inv_rows = conn.execute("SELECT id, account, is_investment, valuation_strategy FROM accounts").fetchall()
        inv_ids = []
        for r in inv_rows:
            is_inv = r[2]
            if is_inv:
                print(f"✅ FOUND INVEST ACCOUNT: ID={r[0]}, Name='{r[1]}', Strat='{r[3]}'")
                inv_ids.append(r[0])
            else:
                # print(f"   Skip '{r[1]}' (is_investment={r[2]})")
                pass
                
        if not inv_ids:
            print("❌ NO INVESTMENT ACCOUNTS FOUND!")
            return

        # 2. Check Data
        print("\n--- Valuations Data ---")
        # Check investment_valuations
        for aid in inv_ids:
            count = conn.execute("SELECT count(*) FROM investment_valuations WHERE account_id=?", (aid,)).fetchone()[0]
            print(f"Account {aid}: {count} valuation entries.")
            if count > 0:
                rows = conn.execute("SELECT date, value FROM investment_valuations WHERE account_id=? ORDER BY date DESC LIMIT 3", (aid,)).fetchall()
                print(f"   Latest: {rows}")

        # 3. Check Transactions
        print("\n--- Transactions Data ---")
        for aid in inv_ids:
            count = conn.execute("SELECT count(*) FROM transactions WHERE account_id=? OR to_account_id=?", (aid, aid)).fetchone()[0]
            print(f"Account {aid}: {count} transactions.")

        # 4. Run Logic
        print("\n--- Running Logic ---")
        years = app.get_available_years()
        print(f"Available Years: {years}")
        
        if years:
            target_year = years[0] # Pick first one, usually current
            print(f"running get_monthly_investment_gains({target_year})...")
            try:
                data = app.get_monthly_investment_gains(target_year)
                print(f"\nResult Keys: {list(data.keys())}")
                if not data:
                    print("❌ RESULT IS EMPTY DICT!")
                else:
                    for m, res in data.items():
                        print(f"Month {m}: Gain={res.get('total_gain')}, Loss={res.get('total_loss')}, Net={res.get('net')}")
                        if res.get('total_gain') == 0 and res.get('total_loss') == 0:
                            print(f"   WARNING: Zero result for Month {m}")
            except Exception as e:
                print(f"❌ CRASH IN LOGIC: {e}")
                import traceback
                traceback.print_exc()

    finally:
        if os.path.exists(TEMP_DB):
            try:
                os.remove(TEMP_DB)
                print("\nCleaned up temp DB.")
            except:
                pass

if __name__ == "__main__":
    deep_debug()
