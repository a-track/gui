import sys
import os
import duckdb
from datetime import datetime
import datetime as dt


class Transaction:
    def __init__(self, trans_id: int, date: str, type: str, 
                sub_category: str = None, amount: float = None, 
                account_id: int = None, payee: str = None, 
                notes: str = None, invest_account_id: int = None,
                qty: float = None, to_account_id: int = None, 
                to_amount: float = None, confirmed: bool = False):
        self.id = trans_id
        self.date = date
        self.type = type
        self.sub_category = sub_category
        self.amount = amount
        self.account_id = account_id
        self.payee = payee
        self.notes = notes
        self.invest_account_id = invest_account_id
        self.qty = qty
        self.to_account_id = to_account_id
        self.to_amount = to_amount
        self.confirmed = confirmed


class Account:
    def __init__(self, id, account, type, company, currency, show_in_balance=True):
        self.id = id
        self.account = account
        self.type = type
        self.company = company
        self.currency = currency
        self.show_in_balance = show_in_balance


class Category:
    def __init__(self, sub_category: str, category: str, category_type: str = "Expense"):
        self.sub_category = sub_category
        self.category = category
        self.category_type = category_type


class BudgetApp:
    def __init__(self, db_path=None):
        if db_path is None:
            if getattr(sys, 'frozen', False):
                application_path = os.path.dirname(sys.executable)
            else:
                application_path = os.path.dirname(os.path.abspath(__file__))
            
            db_path = os.path.join(application_path, 'budget.duckdb')
        
        self.db_path = db_path
        self.init_database()
        self.update_database_schema()
        self.get_or_create_starting_balance_account()

    def _get_connection(self):
        return duckdb.connect(self.db_path)

    def init_database(self):
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY,
                    account VARCHAR NOT NULL,
                    type VARCHAR NOT NULL,
                    company VARCHAR,
                    currency VARCHAR DEFAULT 'CHF',
                    is_investment BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    sub_category VARCHAR PRIMARY KEY,
                    category VARCHAR NOT NULL,
                    category_type VARCHAR DEFAULT 'Expense'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    date DATE NOT NULL,
                    type VARCHAR NOT NULL,
                    sub_category VARCHAR,
                    amount DECIMAL(10, 2),
                    account_id INTEGER,
                    payee VARCHAR,
                    notes TEXT,
                    invest_account_id INTEGER,
                    qty DECIMAL(10, 4),
                    to_account_id INTEGER,
                    to_amount DECIMAL(10, 2),
                    confirmed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (to_account_id) REFERENCES accounts(id),
                    FOREIGN KEY (invest_account_id) REFERENCES accounts(id),
                    FOREIGN KEY (sub_category) REFERENCES categories(sub_category)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS budgets_new (
                    sub_category VARCHAR PRIMARY KEY,
                    budget_amount DECIMAL(10, 2) NOT NULL,
                    FOREIGN KEY (sub_category) REFERENCES categories(sub_category)
                )
            """)
            conn.commit()
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

    def update_database_schema(self):
        conn = self._get_connection()
        try:
            conn.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS show_in_balance BOOLEAN DEFAULT TRUE")
            conn.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS category_type VARCHAR DEFAULT 'Expense'")
            result = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='budgets'
            """).fetchone()
            
            if result:
                columns_result = conn.execute("PRAGMA table_info(budgets)").fetchall()
                has_year_month = any(col[1] in ['year', 'month'] for col in columns_result)
                
                if has_year_month:
                    print("Migrating from old budget schema to new schema...")
                    conn.execute("""
                        INSERT OR REPLACE INTO budgets_new (sub_category, budget_amount)
                        SELECT DISTINCT sub_category, budget_amount 
                        FROM budgets 
                        WHERE budget_amount > 0
                    """)
                    conn.execute("DROP TABLE budgets")
                    conn.execute("ALTER TABLE budgets_new RENAME TO budgets")
                    print("Budget schema migration completed!")
                else:
                    conn.execute("DROP TABLE IF EXISTS budgets_new")
            else:
                conn.execute("ALTER TABLE budgets_new RENAME TO budgets")
            
            conn.commit()
        except Exception as e:
            print(f"Error updating database schema: {e}")
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS budgets (
                        sub_category VARCHAR PRIMARY KEY,
                        budget_amount DECIMAL(10, 2) NOT NULL,
                        FOREIGN KEY (sub_category) REFERENCES categories(sub_category)
                    )
                """)
                conn.commit()
            except:
                pass
        finally:
            conn.close()

    def _get_next_id(self, table_name: str) -> int:
        conn = self._get_connection()
        try:
            result = conn.execute(f"SELECT MAX(id) FROM {table_name}").fetchone()
            return 1 if result[0] is None else result[0] + 1
        finally:
            conn.close()

    def get_all_accounts(self):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT id, account, type, company, currency, show_in_balance
                FROM accounts 
                ORDER BY id
            """).fetchall()
            
            accounts = []
            for row in result:
                account = Account(row[0], row[1], row[2], row[3], row[4])
                account.show_in_balance = bool(row[5]) if row[5] is not None else True
                accounts.append(account)
            return accounts
        except Exception as e:
            print(f"Error getting accounts: {e}")
            return []
        finally:
            conn.close()

    def add_account(self, account_name, account_type, company, currency, show_in_balance=True):
        conn = self._get_connection()
        try:
            existing_account = conn.execute("""
                SELECT id FROM accounts 
                WHERE account = ? AND currency = ? AND id != 0
            """, [account_name, currency]).fetchone()
            
            if existing_account:
                return False, f"Account '{account_name}' with currency '{currency}' already exists"
            
            next_id = self._get_next_id('accounts')
            
            conn.execute("""
                INSERT INTO accounts (id, account, type, company, currency, show_in_balance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [next_id, account_name, account_type, company, currency, show_in_balance])
            conn.commit()
            return True, "Account added successfully"
        except Exception as e:
            print(f"Error adding account: {e}")
            return False, str(e)
        finally:
            conn.close()

    def update_account(self, account_id: int, account: str, type: str, 
                      company: str = None, currency: str = 'CHF', is_investment: bool = False):
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE accounts 
                SET account = ?, type = ?, company = ?, currency = ?, is_investment = ?
                WHERE id = ?
            """, [account, type, company, currency, is_investment, account_id])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating account: {e}")
            return False
        finally:
            conn.close()

    def update_account_show_in_balance(self, account_id, show_in_balance):
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE accounts 
                SET show_in_balance = ? 
                WHERE id = ?
            """, [show_in_balance, account_id])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating show_in_balance: {e}")
            return False
        finally:
            conn.close()

    def delete_account(self, account_id: int):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT COUNT(*) FROM transactions 
                WHERE account_id = ? OR to_account_id = ? OR invest_account_id = ?
            """, [account_id, account_id, account_id]).fetchone()
            
            if result[0] > 0:
                return False, "Account is used in transactions and cannot be deleted"
            
            conn.execute("DELETE FROM accounts WHERE id = ?", [account_id])
            conn.commit()
            return True, "Account deleted successfully"
        except Exception as e:
            print(f"Error deleting account: {e}")
            return False, str(e)
        finally:
            conn.close()

    def get_all_categories(self):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT sub_category, category
                FROM categories 
                ORDER BY category, sub_category
            """).fetchall()
            return [Category(*row) for row in result]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
        finally:
            conn.close()

    def add_category(self, sub_category: str, category: str):
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO categories (sub_category, category)
                VALUES (?, ?)
            """, [sub_category, category])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding category: {e}")
            return False
        finally:
            conn.close()

    def delete_category(self, sub_category: str):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT COUNT(*) FROM transactions WHERE sub_category = ?
            """, [sub_category]).fetchone()
            
            if result[0] > 0:
                return False, "Category is used in transactions and cannot be deleted"
            
            conn.execute("DELETE FROM categories WHERE sub_category = ?", [sub_category])
            conn.commit()
            return True, "Category deleted successfully"
        except Exception as e:
            print(f"Error deleting category: {e}")
            return False, str(e)
        finally:
            conn.close()

    def add_category(self, sub_category: str, category: str, category_type: str = "Expense"):
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO categories (sub_category, category, category_type)
                VALUES (?, ?, ?)
            """, [sub_category, category, category_type])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding category: {e}")
            return False
        finally:
            conn.close()

    def get_all_categories(self):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT sub_category, category, category_type
                FROM categories 
                ORDER BY category, sub_category
            """).fetchall()
            return [Category(*row) for row in result]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
        finally:
            conn.close()
    def add_income(self, date: str, amount: float, account_id: int, 
                   payee: str = "", sub_category: str = "", 
                   notes: str = "", invest_account_id: int = None):
        trans_id = self._get_next_id('transactions')
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO transactions 
                (id, date, type, amount, account_id, payee, sub_category, notes, invest_account_id)
                VALUES (?, ?, 'income', ?, ?, ?, ?, ?, ?)
            """, [trans_id, date, amount, account_id, payee, sub_category, notes, invest_account_id])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding income: {e}")
            return False
        finally:
            conn.close()

    def add_expense(self, date: str, amount: float, account_id: int,
                    sub_category: str, payee: str = "", notes: str = ""):
        trans_id = self._get_next_id('transactions')
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO transactions 
                (id, date, type, amount, account_id, sub_category, payee, notes)
                VALUES (?, ?, 'expense', ?, ?, ?, ?, ?)
            """, [trans_id, date, amount, account_id, sub_category, payee, notes])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding expense: {e}")
            return False
        finally:
            conn.close()

    def add_transfer(self, date: str, from_account_id: int, to_account_id: int,
                    from_amount: float, to_amount: float = None,
                    qty: float = None, notes: str = ""):
        if to_amount is None:
            to_amount = from_amount
            
        trans_id = self._get_next_id('transactions')
        conn = self._get_connection()
        try:
            if from_account_id == 0 or to_account_id == 0:
                self.get_or_create_starting_balance_account()
                
            conn.execute("""
                INSERT INTO transactions 
                (id, date, type, account_id, to_account_id, amount, to_amount, qty, notes)
                VALUES (?, ?, 'transfer', ?, ?, ?, ?, ?, ?)
            """, [trans_id, date, from_account_id, to_account_id, from_amount, to_amount, qty, notes])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding transfer: {e}")
            return False
        finally:
            conn.close()

 
    def get_or_create_starting_balance_account(self):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT id, account, type, company, currency, show_in_balance
                FROM accounts WHERE id = 0
            """).fetchone()
            
            if result:
                return Account(*result)
            else:
                conn.execute("""
                    INSERT INTO accounts (id, account, type, company, currency, show_in_balance)
                    VALUES (0, 'Starting Balance', 'System', 'System', 'MULTI', FALSE)
                """)
                conn.commit()
                return Account(0, 'Starting Balance', 'System', 'System', 'MULTI', False)
        except Exception as e:
            print(f"Error getting starting balance account: {e}")
            return None
        finally:
            conn.close()

    def get_all_transactions(self):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT id, date, type, sub_category, amount, account_id, 
                    payee, notes, invest_account_id, qty, to_account_id, 
                    to_amount, confirmed
                FROM transactions 
                ORDER BY date DESC, id DESC
            """).fetchall()
            
            transactions = []
            for row in result:
                trans = Transaction(
                    trans_id=row[0], date=row[1], type=row[2],
                    sub_category=row[3], amount=row[4], account_id=row[5],
                    payee=row[6], notes=row[7], invest_account_id=row[8],
                    qty=row[9], to_account_id=row[10], to_amount=row[11],
                    confirmed=row[12]
                )
                transactions.append(trans)
            
            return transactions
        except Exception as e:
            print(f"Error getting transactions: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            conn.close()

    def update_transaction(self, trans_id: int, **kwargs):
        conn = self._get_connection()
        try:
            set_clause = []
            values = []
            
            for key, value in kwargs.items():
                set_clause.append(f"{key} = ?")
                values.append(value)
            
            values.append(trans_id)
            
            query = f"UPDATE transactions SET {', '.join(set_clause)} WHERE id = ?"
            conn.execute(query, values)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating transaction: {e}")
            return False
        finally:
            conn.close()

    def delete_transaction(self, trans_id: int):
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM transactions WHERE id = ?", [trans_id])
            conn.commit()
        finally:
            conn.close()

    def toggle_confirmation(self, trans_id: int):
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE transactions 
                SET confirmed = NOT confirmed
                WHERE id = ?
            """, [trans_id])
            conn.commit()
        finally:
            conn.close()

    def get_balance_summary(self):
        conn = self._get_connection()
        try:
            balances = {}
            accounts = self.get_all_accounts()
            
            for account in accounts:
                balances[account.id] = {
                    'account_name': account.account,
                    'balance': 0.0,
                    'type': account.type
                }
            
            transactions = self.get_all_transactions()
            for trans in transactions:
                if trans.type == 'income' and trans.account_id:
                    balances[trans.account_id]['balance'] += float(trans.amount or 0)
                elif trans.type == 'expense' and trans.account_id:
                    balances[trans.account_id]['balance'] -= float(trans.amount or 0)
                elif trans.type == 'transfer':
                    if trans.account_id:
                        balances[trans.account_id]['balance'] -= float(trans.amount or 0)
                    if trans.to_account_id:
                        balances[trans.to_account_id]['balance'] += float(trans.to_amount or 0)
            
            return balances
        finally:
            conn.close()

    def get_account_currency(self, account_id):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT currency FROM accounts WHERE id = ?
            """, [account_id]).fetchone()
            return result[0] if result else 'USD'
        finally:
            conn.close()

    def get_account_by_name_currency(self, account_name: str, currency: str):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT id, account, type, company, currency, is_investment
                FROM accounts 
                WHERE account = ? AND currency = ?
            """, [account_name, currency]).fetchone()
            
            if result:
                return Account(*result)
            return None
        finally:
            conn.close()
    
    def count_transactions_for_account(self, account_id):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT COUNT(*) FROM transactions 
                WHERE account_id = ? OR to_account_id = ?
            """, (account_id, account_id)).fetchone()
            
            return result[0] if result else 0
            
        except Exception as e:
            print(f"Error counting transactions for account {account_id}: {e}")
            return 0
        finally:
            conn.close()

    def get_transaction_counts(self):
        """Get counts of transactions by account, category, and payee"""
        conn = self._get_connection()
        try:
            account_counts = {}
            result = conn.execute("""
                SELECT account_id, COUNT(*) FROM transactions 
                WHERE account_id IS NOT NULL 
                GROUP BY account_id
                UNION ALL
                SELECT to_account_id, COUNT(*) FROM transactions 
                WHERE to_account_id IS NOT NULL 
                GROUP BY to_account_id
            """).fetchall()
            
            for account_id, count in result:
                if account_id not in account_counts:
                    account_counts[account_id] = 0
                account_counts[account_id] += count
            
            category_counts = {}
            result = conn.execute("""
                SELECT sub_category, COUNT(*) FROM transactions 
                WHERE sub_category IS NOT NULL 
                GROUP BY sub_category
            """).fetchall()
            
            for sub_category, count in result:
                category_counts[sub_category] = count
            
            payee_counts = {}
            result = conn.execute("""
                SELECT payee, COUNT(*) FROM transactions 
                WHERE payee IS NOT NULL AND payee != '' 
                GROUP BY payee
            """).fetchall()
            
            for payee, count in result:
                payee_counts[payee] = count
                
            return {
                'accounts': account_counts,
                'categories': category_counts,
                'payees': payee_counts
            }
        except Exception as e:
            print(f"Error getting transaction counts: {e}")
            return {'accounts': {}, 'categories': {}, 'payees': {}}
        finally:
            conn.close()

    def add_or_update_budget(self, sub_category: str, budget_amount: float):
        """Add or update a monthly budget for a subcategory"""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO budgets (sub_category, budget_amount)
                VALUES (?, ?)
            """, [sub_category, budget_amount])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding/updating budget: {e}")
            return False
        finally:
            conn.close()

    def get_all_budgets(self):
        """Get all monthly budgets"""
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT sub_category, budget_amount FROM budgets
                ORDER BY sub_category
            """).fetchall()
            budgets = {}
            for row in result:
                budgets[row[0]] = float(row[1])
            return budgets
        except Exception as e:
            print(f"Error getting budgets: {e}")
            return {}
        finally:
            conn.close()

    def delete_budget(self, sub_category: str):
        """Delete a budget"""
        conn = self._get_connection()
        try:
            conn.execute("""
                DELETE FROM budgets 
                WHERE sub_category = ?
            """, [sub_category])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting budget: {e}")
            return False
        finally:
            conn.close()

    def get_budget_vs_expenses(self, year: int, month: int):
        """Get budget vs actual expenses for a given month"""
        budgets = self.get_all_budgets()
        all_transactions = self.get_all_transactions()
        
        expenses = {}
        for trans in all_transactions:
            if trans.type == 'expense' and trans.date:
                try:
                    trans_date = trans.date
                    if isinstance(trans_date, str):
                        trans_date = datetime.datetime.strptime(trans_date, '%Y-%m-%d').date()
                    
                    if trans_date.year == year and trans_date.month == month:
                        sub_category = trans.sub_category or 'Uncategorized'
                        amount = float(trans.amount or 0)
                        if sub_category in expenses:
                            expenses[sub_category] += amount
                        else:
                            expenses[sub_category] = amount
                except (ValueError, AttributeError):
                    continue
        
        result = {}
        categories = self.get_all_categories()
        category_map = {cat.sub_category: cat.category for cat in categories}
        
        for sub_category, budget_amount in budgets.items():
            category = category_map.get(sub_category, 'Other')
            actual_amount = expenses.get(sub_category, 0.0)
            remaining = budget_amount - actual_amount
            
            result[sub_category] = {
                'category': category,
                'budget': budget_amount,
                'actual': actual_amount,
                'remaining': remaining,
                'percentage': (actual_amount / budget_amount * 100) if budget_amount > 0 else 0
            }
        
        for sub_category, actual_amount in expenses.items():
            if sub_category not in result:
                category = category_map.get(sub_category, 'Other')
                result[sub_category] = {
                    'category': category,
                    'budget': 0.0,
                    'actual': actual_amount,
                    'remaining': -actual_amount,
                    'percentage': 0.0
                }
        
        return result
    
    def get_subcategories_by_category(self):
        """Get all subcategories grouped by category"""
        categories = self.get_all_categories()
        result = {}
        for category in categories:
            if category.category not in result:
                result[category.category] = []
            result[category.category].append(category.sub_category)
        return result