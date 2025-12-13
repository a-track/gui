from models import BudgetApp
import os

# Create a temporary DB for testing
if os.path.exists('test_budget.duckdb'):
    os.remove('test_budget.duckdb')

app = BudgetApp('test_budget.duckdb')

# Setup data
app.add_account('TestAccount', 'Bank', 'Test', 'USD')
acc_id = app.get_account_id_from_name_currency('TestAccount USD')

app.add_category('OldCat', 'Expenses', 'Expense')
app.add_or_update_budget('OldCat', 100.0)

app.add_expense('2023-01-01', 50.0, acc_id, 'OldCat', 'Payee')

print("Initial State:")
print(f"Categories: {app.get_all_categories()}")
print(f"Transactions: {len(app.get_all_transactions())}")
print(f"Budgets: {app.get_all_budgets()}")

# Rename Category
print("\nRenaming 'OldCat' to 'NewCat'...")
success = app.update_category('OldCat', new_sub_category='NewCat')

print(f"Rename Success: {success}")

# Verify
cats = app.get_all_categories()
print(f"Categories: {[c.sub_category for c in cats]}")
trans = app.get_all_transactions()
print(f"Transaction Category: {trans[0].sub_category}")
budgets = app.get_all_budgets()
print(f"Budgets: {budgets}")

if (len(cats) == 1 and cats[0].sub_category == 'NewCat' and 
    trans[0].sub_category == 'NewCat' and 
    'NewCat' in budgets and 'OldCat' not in budgets):
    print("\nSUCCESS: Rename worked correctly with cascade!")
else:
    print("\nFAILURE: Rename logic failed.")

# Cleanup
os.remove('test_budget.duckdb')
