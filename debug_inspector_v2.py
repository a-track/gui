import duckdb
import os
import sys

# Determine path same way as app
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    # Assuming this script is in gui/ folder
    application_path = os.path.join(os.getcwd(), 'src')

db_path = os.path.join(application_path, 'budget.duckdb')
print(f"Target DB Path: {db_path}")

if not os.path.exists(db_path):
    print("ERROR: DB file not found!")
    # Try looking in current dir's src
    db_path = os.path.join(os.getcwd(), 'src', 'budget.duckdb')
    print(f"Trying: {db_path}")
    if not os.path.exists(db_path):
        print("ERROR: DB file still not found!")
        sys.exit(1)

try:
    con = duckdb.connect(db_path, read_only=True)
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

print("\n--- Tables in main ---")
try:
    tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
    for t in tables:
        print(f"Table: {t[0]}")
except Exception as e:
    print(f"List tables failed: {e}")

print("\n--- Constraints referencing 'categories' ---")
try:
    # DuckDB's duckdb_constraints function
    # It returns: database_name, schema_name, table_name, constraint_index, constraint_type, constraint_text
    constraints = con.execute("SELECT * FROM duckdb_constraints()").fetchall()
    for c in constraints:
        # c[5] is constraint_text usually
        txt = str(c)
        if 'categories' in txt:
            print(f"MATCH: {c}")
except Exception as e:
    print(f"Constraints failed: {e}")

con.close()
