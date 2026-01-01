import sys
import os
import shutil
import datetime
from decimal import Decimal

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

DB_PATH = r"C:/Users/wibby/Dropbox/BudgetTracker/fibi.duckdb"
TEMP_DB = "debug_vwrl.duckdb"

def debug_vwrl():
    if os.path.exists(TEMP_DB):
        try: os.remove(TEMP_DB)
        except: pass
    shutil.copy2(DB_PATH, TEMP_DB)
    
    app = BudgetApp(TEMP_DB)
    conn = app._get_connection()
    
    # 1. Find VWRL ID
    res = conn.execute("SELECT id, account FROM accounts WHERE account LIKE '%VWRL%'").fetchone()
    if not res:
        print("VWRL account not found")
        return
    aid = res[0]
    name = res[1]
    print(f"Account: {name} (ID: {aid})")
    
    # 2. Define Period (Nov 30 2025 to Dec 31 2025)
    start_date = datetime.date(2025, 11, 30)
    end_date = datetime.date(2025, 12, 31)
    
    # 3. Get Transactions (Flows)
    # Logic from models.py: tx where (source=aid OR dest=aid) AND date > start AND date <= end
    rows = conn.execute("""
        SELECT id, date, description, amount, source_account_id, destination_account_id, type 
        FROM transactions 
        WHERE (source_account_id = ? OR destination_account_id = ?)
        AND date > ? AND date <= ?
    """, (aid, aid, start_date, end_date)).fetchall()
    
    flow_sum = Decimal('0.0')
    print("\nTransactions:")
    for r in rows:
        amt = Decimal(str(r[3]))
        src = r[4]
        dst = r[5]
        # Inflow: dst = aid. Outflow: src = aid.
        # Note: In models.py valid investment flows are usually transfers or maybe 'Expense' if buying?
        # Let's see raw direction.
        if dst == aid:
            print(f" + Inflow: {amt} ({r[2]}) Type={r[6]}")
            flow_sum += amt
        else:
            print(f" - Outflow: {amt} ({r[2]}) Type={r[6]}")
            flow_sum -= amt
            
    print(f"\nTotal Flow (Net Invested): {flow_sum}")

    # 4. Get Valuations / Quantity
    # Helper to get price/qty or total value
    # We need to mimic 'get_monthly_investment_gains' state tracking or just query current?
    # Simpler: Get valuation entries if Total Value, or Prices if Price/Qty.
    
    strat = conn.execute("SELECT valuation_strategy FROM accounts WHERE id=?", (aid,)).fetchone()[0]
    print(f"Strategy: {strat}")
    
    if strat == 'Total Value':
        # Get Valuations
        v_start = conn.execute("SELECT value FROM investment_valuations WHERE account_id=? AND date=?", (aid, start_date)).fetchone()
        v_end = conn.execute("SELECT value FROM investment_valuations WHERE account_id=? AND date=?", (aid, end_date)).fetchone()
        val_start = Decimal(str(v_start[0])) if v_start else Decimal(0)
        val_end = Decimal(str(v_end[0])) if v_end else Decimal(0)
    else:
        # Price/Qty - naive check
        # Get Qty at start/end
        # Need to sum specific history? 
        # Let's trust flows are correct for Qty delta, but base Qty?
        # Just query 'total balance' from some helper if possible, or manual sum.
        # Assuming user has 'Total Value' or we need to check prices.
        # Re-using logic:
        p_start = conn.execute("SELECT price FROM stock_prices WHERE account_id=? AND date=?", (aid, start_date)).fetchone()
        p_end = conn.execute("SELECT price FROM stock_prices WHERE account_id=? AND date=?", (aid, end_date)).fetchone()
        price_start = Decimal(str(p_start[0])) if p_start else Decimal(0)
        price_end = Decimal(str(p_end[0])) if p_end else Decimal(0)
        print(f"Prices: Start={price_start}, End={price_end}")
        
        # Need Qty. 
        # Sum all tx until date.
        q_start = conn.execute("""
            SELECT 
                SUM(CASE WHEN destination_account_id=? THEN amount ELSE 0 END) - 
                SUM(CASE WHEN source_account_id=? THEN amount ELSE 0 END)
            FROM transactions WHERE date <= ? AND (source_account_id=? OR destination_account_id=?)
        """, (aid, aid, start_date, aid, aid)).fetchone()[0] or 0
        
        q_end = conn.execute("""
            SELECT 
                SUM(CASE WHEN destination_account_id=? THEN amount ELSE 0 END) - 
                SUM(CASE WHEN source_account_id=? THEN amount ELSE 0 END)
            FROM transactions WHERE date <= ? AND (source_account_id=? OR destination_account_id=?)
        """, (aid, aid, end_date, aid, aid)).fetchone()[0] or 0
        
        val_start = Decimal(str(q_start)) * price_start
        val_end = Decimal(str(q_end)) * price_end
        
        print(f"Qty: Start={q_start}, End={q_end}")

    print(f"\nValuations: Start={val_start}, End={val_end}")
    
    gain = (val_end - val_start) - flow_sum
    print(f"Calculated Gain: ({val_end} - {val_start}) - {flow_sum} = {gain}")
    
    conn.close()
    try: os.remove(TEMP_DB)
    except: pass

if __name__ == "__main__":
    debug_vwrl()
