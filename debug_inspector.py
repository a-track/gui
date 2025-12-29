import duckdb
import os

db_path = os.path.join(os.getcwd(), 'src', 'budget.duckdb')
print(f"Connecting to {db_path}...")
con = duckdb.connect(db_path)

print("\n--- Tables ---")
tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
for t in tables:
    print(f"- {t[0]}")

print("\n--- Foreign Keys referencing 'categories' ---")
# DuckDB specific way to check constraints might differ, but information_schema works generally.
# DuckDB stores constraint info in duckdb_constraints or similar system tables.
try:
    constraints = con.execute("""
        SELECT 
            table_name, 
            constraint_name, 
            constraint_type 
        FROM information_schema.table_constraints 
        WHERE constraint_type = 'FOREIGN KEY'
    """).fetchall()
    
    # Getting details is harder in standard SQL.
    # Let's try `duckdb_constraints`.
    
    detailed = con.execute("""
        SELECT 
            table_name, 
            constraint_index,
            constraint_type,
            constraint_text
        FROM duckdb_constraints()
        WHERE constraint_text LIKE '%categories%'
    """).fetchall()
    
    for c in detailed:
        print(c)
        
except Exception as e:
    print(f"Error querying schema: {e}")

# Fallback: check count of 39 in transactions and budgets
print("\n--- Checking for ID 39 ---")
try:
    t_count = con.execute("SELECT count(*) FROM transactions WHERE category_id = 39").fetchone()[0]
    b_count = con.execute("SELECT count(*) FROM budgets WHERE category_id = 39").fetchone()[0]
    print(f"Transactions with 39: {t_count}")
    print(f"Budgets with 39: {b_count}")
    
    # Check other tables if found
except Exception as e:
    print(f"Error checking counts: {e}")

con.close()
