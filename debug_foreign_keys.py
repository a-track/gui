import sys
import os

# App context
sys.path.append(os.path.join(os.getcwd(), 'src'))
from models import BudgetApp

app = BudgetApp()
conn = app._get_connection()

print(f"Connected to DB: {app.db_path}")

try:
    # 1. List all tables
    print("\n--- All Tables ---")
    tables_rs = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
    tables = [t[0] for t in tables_rs]
    for t in tables:
        print(f" - {t}")

    # 2. Check for columns named 'category_id' or similar in each table
    print("\n--- searching for references to 39 ---")
    for t in tables:
        # Get columns
        cols = conn.execute(f"DESCRIBE {t}").fetchall()
        # cols: (column_name, column_type, null, key, default, extra)
        
        has_ref = False
        for c in cols:
            col_name = c[0]
            if 'category' in col_name.lower() or 'cat_id' in col_name.lower():
                # Check for 39
                try:
                    count = conn.execute(f"SELECT count(*) FROM {t} WHERE {col_name} = 39").fetchone()[0]
                    if count > 0:
                        print(f"!!! FOUND REFERENCES IN: {t}.{col_name} -> Count: {count}")
                        has_ref = True
                except Exception as e:
                    # Might fail if type mismatch
                    pass
        
        if not has_ref:
            pass

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
