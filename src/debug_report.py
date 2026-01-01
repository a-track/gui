
import duckdb
from datetime import date
db_path = "c:/Users/wibby/Desktop/Andrin/Git/gui/src/budget_tracker.duckdb"
conn = duckdb.connect(db_path)

print("--- Transactions Schema ---")
print(conn.execute("DESCRIBE transactions").fetchall())

print("\n--- Sample Dates ---")
print(conn.execute("SELECT date FROM transactions LIMIT 5").fetchall())

print("\n--- Sample Count by Type ---")
print(conn.execute("SELECT type, COUNT(*) FROM transactions GROUP BY type").fetchall())

# Test the params and query
year = 2025
year_start = f"{year}-01-01"
year_end = f"{year}-12-31"

print(f"\n--- Testing Opening Balance Query ({year_start}) ---")
try:
    # Simplified version of the query I wrote
    opening = conn.execute("""
        SELECT 
            account_id, 
            SUM(CASE 
                WHEN type='income' THEN amount 
                WHEN type='expense' THEN -amount 
                WHEN type='transfer' THEN -amount 
                ELSE 0 END)
        FROM transactions t
        WHERE t.date < ?
        GROUP BY account_id
    """, (year_start,)).fetchall()
    print("Opening Results:", opening)
except Exception as e:
    print("Opening Query Error:", e)

print(f"\n--- Testing Delta Query ({year_start} to {year_end}) ---")
try:
    # The one with CAST
    deltas = conn.execute("""
        SELECT 
            MONTH(CAST(date AS DATE)),
            account_id, 
            SUM(amount)
        FROM transactions t
        WHERE t.date >= ? AND t.date <= ?
        GROUP BY MONTH(CAST(date AS DATE)), account_id
    """, (year_start, year_end)).fetchall()
    print("Delta Results Sample:", deltas[:5])
except Exception as e:
    print("Delta Query Error:", e)

conn.close()
