import sys
import os
import time
import duckdb
from datetime import datetime, date, timedelta

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
    def __init__(self, id, account, type, company, currency, show_in_balance=True, is_active=True, is_investment=False, valuation_strategy=None):
        self.id = id
        self.account = account
        self.type = type
        self.company = company
        self.currency = currency
        self.show_in_balance = show_in_balance
        self.is_active = is_active
        self.is_investment = is_investment
        self.valuation_strategy = valuation_strategy

class Category:
    def __init__(self, id: int, sub_category: str, category: str, category_type: str = "Expense"):
        self.id = id
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

        self._anchor_conn = None
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self._anchor_conn = duckdb.connect(self.db_path)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Database locked, retrying in 1s... ({attempt+1}/{max_retries})")
                    time.sleep(1.0)
                else:
                    print(f"Failed to acquire DB lock after {max_retries} attempts: {e}")
                    raise e

        self.init_database()
        self.update_database_schema()
        self.get_or_create_starting_balance_account()

    def close(self):
        
        try:
            if self._anchor_conn:
                self._anchor_conn.close()
                self._anchor_conn = None
        except Exception as e:
            print(f"Error closing anchor connection: {e}")

    def _get_connection(self):
        return duckdb.connect(self.db_path)

    def init_database(self):
        conn = self._get_connection()
        try:
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
            except Exception as e:
                print(f"Error creating accounts table: {e}")

            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY,
                        sub_category VARCHAR NOT NULL,
                        category VARCHAR NOT NULL,
                        category_type VARCHAR DEFAULT 'Expense',
                        UNIQUE(sub_category, category, category_type)
                    )
                """)
            except Exception as e:
                print(f"Error creating categories table: {e}")

            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY,
                        date DATE NOT NULL,
                        type VARCHAR NOT NULL,
                        amount DECIMAL(18, 2),
                        account_id INTEGER,
                        category_id INTEGER,
                        payee VARCHAR,
                        notes TEXT,
                        invest_account_id INTEGER,
                        qty DECIMAL(10, 4),
                        to_account_id INTEGER,
                        to_amount DECIMAL(18, 2),
                        confirmed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (account_id) REFERENCES accounts(id),
                        FOREIGN KEY (to_account_id) REFERENCES accounts(id),
                        FOREIGN KEY (invest_account_id) REFERENCES accounts(id),
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                """)
            except Exception as e:

                pass

            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS budgets (
                        category_id INTEGER PRIMARY KEY,
                        budget_amount DECIMAL(18, 2) NOT NULL,
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                """)
            except Exception as e:

                pass

            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS exchange_rates (
                        id INTEGER PRIMARY KEY,
                        date DATE NOT NULL,
                        currency VARCHAR NOT NULL,
                        rate DECIMAL(10, 6) NOT NULL,
                        UNIQUE(date, currency)
                    )
                """)
            except Exception as e:
                print(f"Error creating exchange_rates table: {e}")

            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS investment_valuations (
                        id INTEGER PRIMARY KEY,
                        date DATE NOT NULL,
                        account_id INTEGER NOT NULL,
                        value DECIMAL(12, 4) NOT NULL,
                        FOREIGN KEY (account_id) REFERENCES accounts(id),
                        UNIQUE(date, account_id)
                    )
                """)
            except Exception as e:
                print(f"Error creating investment_valuations table: {e}")

            conn.close()
        except Exception as e:
            print(f"Database initialization error: {e}")
            try:
                conn.close()
            except:
                pass

    def get_exchange_rates(self):
        conn = self._get_connection()
        try:
            return conn.execute("SELECT * FROM exchange_rates ORDER BY date DESC, currency").fetchall()
        finally:
            conn.close()

    def add_exchange_rate(self, date: str, currency: str, rate: float):
        return self.add_exchange_rates_bulk([(date, currency, rate)]) is True

    def get_predicted_category(self, payee: str):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT c.category, c.sub_category
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.payee = ?
                GROUP BY c.category, c.sub_category
                ORDER BY COUNT(*) DESC, MAX(t.date) DESC
                LIMIT 1
            """, [payee]).fetchone()
            return result
        except Exception as e:
            print(f"Error predicting category: {e}")
            return None
        finally:
            conn.close()

    def add_exchange_rates_bulk(self, rates_data: list):
        
        conn = self._get_connection()
        try:

            new_id_res = conn.execute(
                ).fetchone()
            current_max_id = new_id_res[0] if new_id_res else 0

            for i, (date, currency, rate) in enumerate(rates_data):

                pass

            for i, (date, currency, rate) in enumerate(rates_data):

                current_max_id += 1
                conn.execute("""
                    INSERT INTO exchange_rates (id, date, currency, rate)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (date, currency) DO UPDATE SET rate = excluded.rate
                """, (current_max_id, date, currency, rate))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding exchange rates: {e}")
            return False
        finally:
            conn.close()

    def delete_exchange_rate(self, rate_id: int):
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM exchange_rates WHERE id = ?", (rate_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting exchange rate: {e}")
            return False
        finally:
            conn.close()

    def delete_exchange_rates_bulk(self, rates_data: list):
        
        if not rates_data:
            return True

        conn = self._get_connection()
        try:
            for date, currency in rates_data:
                conn.execute(
                    , (date, currency))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting exchange rates: {e}")
            return False
        finally:
            conn.close()

    def get_exchange_rate_for_date(self, currency: str, target_date: str = None):
        
        if currency == 'CHF':
            return 1.0

        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')

        conn = self._get_connection()
        try:

            result = conn.execute("""
                SELECT rate FROM exchange_rates
                WHERE currency = ? AND date <= ?
                ORDER BY date DESC
                LIMIT 1
            """, (currency, target_date)).fetchone()

            if result:
                return float(result[0])

            result = conn.execute("""
                SELECT rate FROM exchange_rates
                WHERE currency = ?
                ORDER BY date ASC
                LIMIT 1
            """, (currency,)).fetchone()

            if result:
                return float(result[0])

            return 1.0
        finally:
            conn.close()

    def get_exchange_rates_map(self, target_date: str = None) -> dict:
        
        if target_date is None:
            today = datetime.now().date()
            target_date_str = today.strftime('%Y-%m-%d')

            next_day_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            target_date_str = target_date

            try:
                t_date = datetime.strptime(target_date, '%Y-%m-%d').date()
                next_day = t_date + timedelta(days=1)
                next_day_str = next_day.strftime('%Y-%m-%d')
            except ValueError:

                next_day_str = target_date_str

        conn = self._get_connection()
        try:

            currencies = conn.execute(
                ).fetchall()
            currencies = [c[0] for c in currencies]

            rates_map = {'CHF': 1.0}

            for curr in currencies:
                if curr == 'CHF':
                    continue

                res = conn.execute("""
                    SELECT rate FROM exchange_rates
                    WHERE currency = ? AND date < ?
                    ORDER BY date DESC
                    LIMIT 1
                """, (curr, next_day_str)).fetchone()

                if res:
                    rates_map[curr] = float(res[0])
                else:

                    res = conn.execute("""
                        SELECT rate FROM exchange_rates
                        WHERE currency = ?
                        ORDER BY date ASC
                        LIMIT 1
                    """, (curr,)).fetchone()
                    if res:
                        rates_map[curr] = float(res[0])
                    else:
                        rates_map[curr] = 1.0

            return rates_map
        finally:
            conn.close()

    def get_history_matrix_data(self):
        
        conn = self._get_connection()
        try:
            return conn.execute("""
                SELECT strftime(date, '%Y-%m-%d') as date_str, currency, rate
                FROM exchange_rates
                ORDER BY date DESC, currency ASC
            """).fetchall()
        except Exception as e:
            print(f"Error fetching history matrix: {e}")
            return []
        finally:
            conn.close()

    def update_database_schema(self):
        conn = self._get_connection()
        try:

            try:
                tables = conn.execute(
                    ).fetchall()
                table_names = [t[0] for t in tables]

                if 'categories' not in table_names and 'categories_new' in table_names:
                    print("Recovering categories table...")
                    conn.execute(
                        )

                if 'transactions' not in table_names and 'transactions_new' in table_names:
                    print("Recovering transactions table...")
                    conn.execute(
                        )

                if 'budgets' not in table_names and 'budgets_new_schema' in table_names:
                    print("Recovering budgets table...")
                    conn.execute(
                        )

                if 'budgets' not in table_names and 'budgets_new' in table_names:
                    print("Recovering budgets table (from budgets_new)...")
                    conn.execute("ALTER TABLE budgets_new RENAME TO budgets")

            except Exception as e:
                print(f"Recovery check failed: {e}")

            conn.execute("DROP TABLE IF EXISTS budgets_new_schema")
            conn.execute("DROP TABLE IF EXISTS transactions_new")
            conn.execute("DROP TABLE IF EXISTS categories_new")

            conn.execute(
                )
            conn.execute(
                )
            conn.execute(
                )
            conn.execute(
                )

            columns_result = conn.execute(
                ).fetchall()
            has_id = any(col[1] == 'id' for col in columns_result)

            if not has_id:
                print("Migrating categories to use ID as Primary Key...")

                conn.execute("""
                    CREATE TABLE categories_new (
                        id INTEGER PRIMARY KEY,
                        sub_category VARCHAR NOT NULL,
                        category VARCHAR NOT NULL,
                        category_type VARCHAR DEFAULT 'Expense',
                        UNIQUE(sub_category, category, category_type)
                    )
                """)

                conn.execute("""
                    INSERT INTO categories_new (id, sub_category, category, category_type)
                    SELECT row_number() OVER (), sub_category, category, category_type FROM categories
                """)

                conn.execute("""
                    CREATE TABLE transactions_new (
                        id INTEGER PRIMARY KEY,
                        date DATE NOT NULL,
                        type VARCHAR NOT NULL,
                        amount DECIMAL(18, 2),
                        account_id INTEGER,
                        category_id INTEGER,
                        payee VARCHAR,
                        notes TEXT,
                        invest_account_id INTEGER,
                        qty DECIMAL(10, 4),
                        to_account_id INTEGER,
                        to_amount DECIMAL(18, 2),
                        confirmed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (account_id) REFERENCES accounts(id),
                        FOREIGN KEY (to_account_id) REFERENCES accounts(id),
                        FOREIGN KEY (invest_account_id) REFERENCES accounts(id),
                        FOREIGN KEY (category_id) REFERENCES categories_new(id)
                    )
                """)

                conn.execute("""
                    INSERT INTO transactions_new (
                        id, date, type, amount, account_id, category_id, payee, notes,
                        invest_account_id, qty, to_account_id, to_amount, confirmed, created_at
                    )
                    SELECT
                        t.id, t.date, t.type, t.amount, t.account_id, c.id, t.payee, t.notes,
                        t.invest_account_id, t.qty, t.to_account_id, t.to_amount, t.confirmed, t.created_at
                    FROM transactions t
                    LEFT JOIN categories_new c ON t.sub_category = c.sub_category
                """)

                conn.execute("""
                    CREATE TABLE budgets_new_schema (
                        category_id INTEGER PRIMARY KEY,
                        budget_amount DECIMAL(18, 2) NOT NULL,
                        FOREIGN KEY (category_id) REFERENCES categories_new(id)
                    )
                """)

                conn.execute("""
                    INSERT INTO budgets_new_schema (category_id, budget_amount)
                    SELECT c.id, b.budget_amount
                    FROM budgets b
                    JOIN categories_new c ON b.sub_category = c.sub_category
                """)

                print("Clearing data...")
                conn.execute("DELETE FROM budgets")
                conn.execute("DELETE FROM transactions")

                print("Dropping budgets...")
                conn.execute("DROP TABLE IF EXISTS budgets CASCADE")
                conn.commit()

                print("Dropping transactions...")
                conn.execute("DROP TABLE IF EXISTS transactions CASCADE")
                conn.commit()

                print("Dropping categories...")
                try:
                    conn.execute("DROP TABLE IF EXISTS categories CASCADE")
                    conn.commit()
                except Exception as e:
                    print(f"WARNING: Could not drop categories table: {e}")

                conn.execute("DROP TABLE IF EXISTS budgets_new")

                print("Recreating final tables...")

                conn.execute("""
                    CREATE TABLE categories (
                        id INTEGER PRIMARY KEY,
                        sub_category VARCHAR NOT NULL,
                        category VARCHAR NOT NULL,
                        category_type VARCHAR DEFAULT 'Expense',
                        UNIQUE(sub_category, category, category_type)
                    )
                """)
                conn.execute(
                    )

                conn.execute("""
                    CREATE TABLE budgets (
                        category_id INTEGER PRIMARY KEY,
                        budget_amount DECIMAL(18, 2) NOT NULL,
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                """)
                conn.execute(
                    )

                conn.execute("""
                    CREATE TABLE transactions (
                        id INTEGER PRIMARY KEY,
                        date DATE NOT NULL,
                        type VARCHAR NOT NULL,
                        amount DECIMAL(18, 2),
                        account_id INTEGER,
                        category_id INTEGER,
                        payee VARCHAR,
                        notes TEXT,
                        invest_account_id INTEGER,
                        qty DECIMAL(10, 4),
                        to_account_id INTEGER,
                        to_amount DECIMAL(18, 2),
                        confirmed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (account_id) REFERENCES accounts(id),
                        FOREIGN KEY (to_account_id) REFERENCES accounts(id),
                        FOREIGN KEY (invest_account_id) REFERENCES accounts(id),
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                """)
                conn.execute(
                    )

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS exchange_rates (
                        id INTEGER PRIMARY KEY,
                        date DATE NOT NULL,
                        currency VARCHAR NOT NULL,
                        rate DECIMAL(10, 6) NOT NULL,
                        UNIQUE(date, currency)
                    )
                """)

                conn.execute("DROP TABLE IF EXISTS budgets_new_schema")
                conn.execute("DROP TABLE IF EXISTS transactions_new")
                conn.execute("DROP TABLE IF EXISTS categories_new")

                print("Categories migration completed!")

            result = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='budgets'
            """).fetchone()

            if not result:
                pass

            conn.commit()
        except Exception as e:
            print(f"Error updating database schema: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

    def _get_next_id(self, table_name: str) -> int:
        conn = self._get_connection()
        try:
            result = conn.execute(
                f"SELECT MAX(id) FROM {table_name}").fetchone()
            return 1 if result[0] is None else result[0] + 1
        finally:
            conn.close()

    def get_all_accounts(self, show_inactive=False):
        conn = self._get_connection()
        try:

            query = """
                SELECT id, account, type, company, currency, show_in_balance, is_active, is_investment, valuation_strategy
                FROM accounts
            """
            
            if not show_inactive:
                query += " WHERE is_active = 1"
            
            query += " ORDER BY id"

            result = conn.execute(query).fetchall()

            accounts = []
            for row in result:

                account = Account(row[0], row[1], row[2], row[3], row[4])
                account.show_in_balance = bool(
                    row[5]) if row[5] is not None else True
                account.is_active = bool(
                    row[6]) if row[6] is not None else True
                account.is_investment = bool(row[7]) if len(
                    row) > 7 and row[7] is not None else False
                account.valuation_strategy = row[8] if len(row) > 8 else None
                accounts.append(account)
            return accounts
        except Exception as e:
            print(f"Error getting accounts: {e}")
            return []
        finally:
            conn.close()

    def add_account(self, account_name, account_type, company, currency, show_in_balance=True, is_active=True, is_investment=False, valuation_strategy=None):
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
                INSERT INTO accounts (id, account, type, company, currency, show_in_balance, is_active, is_investment, valuation_strategy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [next_id, account_name, account_type, company, currency, show_in_balance, is_active, is_investment, valuation_strategy])
            conn.commit()
            return True, "Account added successfully"
        except Exception as e:
            print(f"Error adding account: {e}")
            return False, str(e)
        finally:
            conn.close()

    def update_account(self, account_id: int, account: str, type: str,
                       company: str = None, currency: str = 'CHF', is_investment: bool = False, valuation_strategy: str = None):
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE accounts
                SET account = ?, type = ?, company = ?, currency = ?, is_investment = ?, valuation_strategy = ?
                WHERE id = ?
            """, [account, type, company, currency, is_investment, valuation_strategy, account_id])
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

    def update_account_active(self, account_id, is_active):
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE accounts
                SET is_active = ?
                WHERE id = ?
            """, [is_active, account_id])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating is_active: {e}")
            return False
        finally:
            conn.close()

    def update_account_id(self, old_id: int, new_id: int):
        conn = self._get_connection()
        try:
            exists = conn.execute(
                , [new_id]).fetchone()
            if exists:
                return False, f"Account ID {new_id} already exists."

            old_account = conn.execute(
                ,
                [old_id]
            ).fetchone()

            if not old_account:
                return False, "Old account not found."

            conn.execute("""
                INSERT INTO accounts (id, account, type, company, currency, show_in_balance, is_active, is_investment, valuation_strategy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [new_id, *old_account])

            conn.execute(
                , (new_id, old_id))
            conn.execute(
                , (new_id, old_id))
            conn.execute(
                , (new_id, old_id))

            conn.execute("DELETE FROM accounts WHERE id = ?", [old_id])

            conn.commit()
            return True, "Account ID updated successfully."

        except Exception as e:
            print(f"Error updating account ID: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return False, str(e)
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
                SELECT id, sub_category, category, category_type
                FROM categories
                ORDER BY category, sub_category
            """).fetchall()
            return [Category(*row) for row in result]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
        finally:
            conn.close()

    def delete_category(self, cat_id: int):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT COUNT(*) FROM transactions WHERE category_id = ?
            """, [cat_id]).fetchone()

            if result[0] > 0:
                return False, "Category is used in transactions and cannot be deleted"

            conn.execute("DELETE FROM budgets WHERE category_id = ?", [cat_id])

            conn.execute("DELETE FROM categories WHERE id = ?", [cat_id])
            conn.commit()
            return True, "Category deleted successfully"
        except Exception as e:
            print(f"Error deleting category: {e}")
            return False, str(e)
        finally:
            conn.close()

    def add_category(self, sub_category: str, category: str, category_type: str = "Expense"):
        cat_id = self._get_next_id('categories')
        conn = self._get_connection()
        try:

            exists = conn.execute("SELECT 1 FROM categories WHERE sub_category = ?", [
                                  sub_category]).fetchone()
            if exists:
                return False

            conn.execute("""
                INSERT INTO categories (id, sub_category, category, category_type)
                VALUES (?, ?, ?, ?)
            """, [cat_id, sub_category, category, category_type])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding category: {e}")
            return False
        finally:
            conn.close()

    def update_category(self, cat_id: int, new_category: str = None, new_type: str = None, new_sub_category: str = None):
        conn = self._get_connection()
        try:

            row = conn.execute("SELECT sub_category, category, category_type FROM categories WHERE id = ?", [
                               cat_id]).fetchone()
            if not row:
                return False
            current_sub, current_cat, current_type = row

            final_sub = new_sub_category if new_sub_category is not None else current_sub
            final_cat = new_category if new_category is not None else current_cat
            final_type = new_type if new_type is not None else current_type

            if final_sub == current_sub and final_cat == current_cat and final_type == current_type:
                return True

            res = conn.execute("SELECT MAX(id) FROM categories").fetchone()
            next_id = (res[0] if res and res[0] is not None else 0) + 1

            conn.execute("INSERT INTO categories (id, sub_category, category, category_type) VALUES (?, ?, ?, ?)",
                         (next_id, final_sub, final_cat, final_type))

            conn.execute(
                , (next_id, cat_id))

            budget_row = conn.execute(
                , [cat_id]).fetchone()
            if budget_row:
                amt = budget_row[0]
                conn.execute(
                    , (next_id, amt))
                conn.execute(
                    , [cat_id])

            conn.execute("DELETE FROM categories WHERE id = ?", [cat_id])

            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating category (Clone-Repoint): {e}")
            return False
        finally:
            conn.close()

    def add_income(self, date: str, amount: float, account_id: int,
                   payee: str = "", sub_category: str = "",
                   notes: str = "", invest_account_id: int = None):
        trans_id = self._get_next_id('transactions')
        conn = self._get_connection()
        try:

            cat_row = conn.execute("SELECT id FROM categories WHERE sub_category = ?", [
                                   sub_category]).fetchone()
            category_id = cat_row[0] if cat_row else None

            conn.execute("""
                INSERT INTO transactions
                (id, date, type, amount, account_id, payee, category_id, notes, invest_account_id)
                VALUES (?, ?, 'income', ?, ?, ?, ?, ?, ?)
            """, [trans_id, date, amount, account_id, payee, category_id, notes, invest_account_id])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding income: {e}")
            return False
        finally:
            conn.close()

    def add_expense(self, date: str, amount: float, account_id: int,
                    sub_category: str, payee: str = "", notes: str = "", invest_account_id: int = None):
        trans_id = self._get_next_id('transactions')
        conn = self._get_connection()
        try:

            cat_row = conn.execute("SELECT id FROM categories WHERE sub_category = ?", [
                                   sub_category]).fetchone()
            category_id = cat_row[0] if cat_row else None

            conn.execute("""
                INSERT INTO transactions
                (id, date, type, amount, account_id, category_id, payee, notes, invest_account_id)
                VALUES (?, ?, 'expense', ?, ?, ?, ?, ?, ?)
            """, [trans_id, date, amount, account_id, category_id, payee, notes, invest_account_id])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding expense: {e}")
            return False
        finally:
            conn.close()

    def add_transaction(self, date: str, type: str, sub_category: str, amount: float,
                        account_id: int, payee: str = "", notes: str = "",
                        invest_account_id: int = None, qty: float = None,
                        to_account_id: int = None, to_amount: float = None):
        if type.lower() == 'income':
            return self.add_income(date, amount, account_id, payee, sub_category, notes, invest_account_id)
        elif type.lower() == 'expense':
            return self.add_expense(date, amount, account_id, sub_category, payee, notes, invest_account_id)
        elif type.lower() == 'transfer':
            return self.add_transfer(date, account_id, to_account_id, amount, to_amount, qty, notes)
        else:
            return False

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
                SELECT t.id, t.date, t.type, c.sub_category, t.amount, t.account_id,
                    t.payee, t.notes, t.invest_account_id, t.qty, t.to_account_id,
                    t.to_amount, t.confirmed
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                ORDER BY t.date DESC, t.id DESC
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

    def get_balance_summary(self, target_date: str = None):
        conn = self._get_connection()
        try:
            balances = {}
            accounts = self.get_all_accounts()

            for account in accounts:
                balances[account.id] = {
                    : account.account,
                    : 0.0,
                    : account.type,
                    : 0,
                    : getattr(account, 'is_investment', False)
                }
     
            date_filter = ""
            params = []
            if target_date:
                date_filter = " AND date <= ?"
                params = [target_date, target_date, target_date, target_date]

            query = f"""
                SELECT 
                    account_id, 
                    SUM(balance_change), 
                    SUM(qty_in), 
                    SUM(qty_out), 
                    SUM(cnt) 
                FROM (
                    -- Income: +amount, +qty, count=1
                    SELECT account_id, COALESCE(amount, 0) as balance_change, COALESCE(qty, 0) as qty_in, 0.0 as qty_out, 1 as cnt 
                    FROM transactions WHERE type='income' AND account_id IS NOT NULL {date_filter}
                    
                    UNION ALL
                    
                    -- Expense: -amount, qty_out=qty (potentially), count=1
                    SELECT account_id, -COALESCE(amount, 0), 0.0, COALESCE(qty, 0), 1 
                    FROM transactions WHERE type='expense' AND account_id IS NOT NULL {date_filter}
                    
                    UNION ALL
                    
                    -- Transfer Out: -amount, qty_out=qty (potentially), count=1
                    SELECT account_id, -COALESCE(amount, 0), 0.0, COALESCE(qty, 0), 1 
                    FROM transactions WHERE type='transfer' AND account_id IS NOT NULL {date_filter}
                    
                    UNION ALL
                    
                    -- Transfer In: +to_amount, +qty, count=1
                    SELECT to_account_id, COALESCE(to_amount, 0), COALESCE(qty, 0), 0.0, 1 
                    FROM transactions WHERE type='transfer' AND to_account_id IS NOT NULL {date_filter}
                ) 
                GROUP BY account_id
            """
            
            results = conn.execute(query, params).fetchall()

            for row in results:
                acc_id = row[0]
                if acc_id not in balances:
                    continue
                    
                balance_change = float(row[1] or 0)
                qty_in = float(row[2] or 0)
                qty_out = float(row[3] or 0)
                count = row[4] or 0
                
                balances[acc_id]['balance'] += balance_change
                balances[acc_id]['count'] += count
                
                current_qty = balances[acc_id].get('qty', 0.0)
                current_qty += qty_in
                
                if balances[acc_id]['is_investment']:
                    current_qty -= qty_out
                    
                balances[acc_id]['qty'] = current_qty

            return balances
        finally:
            conn.close()

    def get_transactions_by_month(self, year: int, month: int):
        conn = self._get_connection()
        try:
            if month is None or month == 0:

                start_date = f"{year}-01-01"
                end_date = f"{year+1}-01-01"
            else:

                start_date = f"{year}-{month:02d}-01"
                if month == 12:
                    end_date = f"{year+1}-01-01"
                else:
                    end_date = f"{year}-{month+1:02d}-01"

            result = conn.execute("""
                SELECT t.id, t.date, t.type, c.sub_category, t.amount, t.account_id,
                    t.payee, t.notes, t.invest_account_id, t.qty, t.to_account_id,
                    t.to_amount, t.confirmed
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.date >= ? AND t.date < ?
                ORDER BY t.date DESC, t.id DESC
            """, [start_date, end_date]).fetchall()

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
            print(f"Error getting transactions by month: {e}")
            return []
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
                SELECT id, account, type, company, currency, show_in_balance, is_active
                FROM accounts
                WHERE account = ? AND currency = ?
            """, [account_name, currency]).fetchone()

            if result:
                account = Account(result[0], result[1],
                                  result[2], result[3], result[4])
                account.show_in_balance = bool(
                    result[5]) if result[5] is not None else True
                account.is_active = bool(result[6]) if len(
                    result) > 6 and result[6] is not None else True
                return account
            return None
        finally:
            conn.close()

    def get_account_by_id(self, account_id: int):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT id, account, type, company, currency, show_in_balance, is_active, is_investment
                FROM accounts
                WHERE id = ?
            """, [account_id]).fetchone()

            if result:
                account = Account(result[0], result[1],
                                  result[2], result[3], result[4])
                account.show_in_balance = bool(
                    result[5]) if result[5] is not None else True
                account.is_active = bool(
                    result[6]) if result[6] is not None else True
                account.is_investment = bool(result[7]) if len(
                    result) > 7 and result[7] is not None else False
                return account
            return None
        except Exception as e:
            print(f"Error getting account by id: {e}")
            return None
        finally:
            conn.close()

    def get_account_id_from_name_currency(self, account_str):
        
        conn = self._get_connection()
        try:

            accounts = self.get_all_accounts()
            for account in accounts:
                if f"{account.account} {account.currency}" == account_str:
                    return account.id

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
                SELECT c.sub_category, COUNT(*)
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.category_id IS NOT NULL
                GROUP BY c.sub_category
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
                : account_counts,
                : category_counts,
                : payee_counts
            }
        except Exception as e:
            print(f"Error getting transaction counts: {e}")
            return {'accounts': {}, 'categories': {}, 'payees': {}}
        finally:
            conn.close()

    def get_account_transactions_with_balance(self, account_id):
        
        conn = self._get_connection()
        try:
            query = """
                SELECT 
                    t.id, t.date, t.type, c.sub_category, t.amount, t.account_id, t.payee, t.notes, 
                    t.invest_account_id, t.qty, t.to_account_id, t.to_amount, t.confirmed,
                    SUM(
                        CASE 
                            WHEN t.type = 'income' AND t.account_id = ? THEN COALESCE(t.amount, 0)
                            WHEN t.type = 'expense' AND t.account_id = ? THEN -COALESCE(t.amount, 0)
                            WHEN t.type = 'transfer' AND t.account_id = ? THEN -COALESCE(t.amount, 0)
                            WHEN t.type = 'transfer' AND t.to_account_id = ? THEN COALESCE(t.to_amount, 0)
                            ELSE 0 
                        END
                    ) OVER (ORDER BY t.date, t.id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as running_balance
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.account_id = ? OR t.to_account_id = ?
                ORDER BY t.date DESC, t.id DESC
            """
            
            params = (account_id, account_id, account_id, account_id, account_id, account_id)
            
            rows = conn.execute(query, params).fetchall()
            
            transactions = []
            balance_history = {}
            
            for row in rows:
                
                t = Transaction(
                    trans_id=row[0], date=str(row[1]), type=row[2],
                    sub_category=row[3], amount=row[4], account_id=row[5],
                    payee=row[6], notes=row[7], invest_account_id=row[8],
                    qty=row[9], to_account_id=row[10], to_amount=row[11],
                    confirmed=bool(row[12])
                )
                transactions.append(t)
                balance_history[t.id] = float(row[13] or 0.0)
                
            return transactions, balance_history
            
        except Exception as e:
            print(f"Error fetching account transactions with balance: {e}")
            return [], {}
        finally:
            conn.close()

    def update_category_id(self, old_id: int, new_id: int):
        conn = self._get_connection()
        try:
            try:
                tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
                api_tables = [t for t in tables if t.startswith('api_')]
                for tbl in api_tables:
                    try:
                        conn.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
                    except Exception as e:
                        print(f"Failed to drop {tbl}: {e}")
                
                other_zombies = [t for t in tables if t not in api_tables and t not in ['transactions', 'budgets', 'categories', 'accounts', 'exchange_rates']]
                for tbl in other_zombies:
                    try:
                        desc = conn.execute(f"DESCRIBE {tbl}").fetchall()
                        int_cols = [c[0] for c in desc if 'INT' in c[1].upper() or 'DECIMAL' in c[1].upper()]
                        for col in int_cols:
                            conn.execute(f"DELETE FROM {tbl} WHERE {col} = ?", [old_id])
                    except:
                        pass
                        
            except Exception as e:
                print(f"Cleanup warning: {e}")

            trans_ids = [row[0] for row in conn.execute(
                , [old_id]).fetchall()]
            
            budget_row = conn.execute(
                , [old_id]).fetchone()

            try:
                conn.execute("BEGIN TRANSACTION")
                check = conn.execute("SELECT count(*) FROM transactions WHERE category_id = ?", [old_id]).fetchone()[0]
                if check != len(trans_ids):
                    print(f"Warning: Transaction count mismatch {check} vs {len(trans_ids)}")

                if trans_ids:
                    conn.execute("UPDATE transactions SET category_id = NULL WHERE category_id = ?", [old_id])
                
                if budget_row:
                    conn.execute("DELETE FROM budgets WHERE category_id = ?", [old_id])
                
                still_bound = conn.execute("SELECT count(*) FROM transactions WHERE category_id = ?", [old_id]).fetchone()[0]
                if still_bound > 0:
                    raise Exception(f"Decoupling failed! {still_bound} transactions still reference old ID.")
                
                conn.execute("COMMIT")
            except Exception as e:
                conn.execute("ROLLBACK")
                return False, f"Step 1 (Decouple) Failed: {e}"

            try:
                conn.execute("UPDATE categories SET id = ? WHERE id = ?", (new_id, old_id))
            except Exception as e:
                try:
                    print(f"Update failed ({e}), Reverting Step 1...")
                    conn.execute("BEGIN TRANSACTION")
                    if budget_row:
                        conn.execute("INSERT INTO budgets (category_id, budget_amount) VALUES (?, ?)", (old_id, budget_row[0]))
                    if trans_ids:
                        id_list = ",".join(map(str, trans_ids))
                        conn.execute(f"UPDATE transactions SET category_id = ? WHERE id IN ({id_list})", [old_id])
                    conn.execute("COMMIT")
                except Exception as rollback_err:
                    return False, f"CRITICAL: Update failed AND Rollback failed. DB may be inconsistent. Update Error: {e}, Rollback Error: {rollback_err}"
                
                return False, f"Update Category Failed: {e}"

            try:
                conn.execute("BEGIN TRANSACTION")
                if trans_ids:
                    id_list = ",".join(map(str, trans_ids))
                    conn.execute(f"UPDATE transactions SET category_id = ? WHERE id IN ({id_list})", [new_id])
                
                if budget_row:
                    conn.execute("INSERT INTO budgets (category_id, budget_amount) VALUES (?, ?)", (new_id, budget_row[0]))
                
                conn.execute("COMMIT")
                return True, "Category ID updated successfully."
            except Exception as e:
                return False, f"Category Updated, but failed to re-link transactions (IDs: {trans_ids}). Error: {e}"

        except Exception as e:
            return False, f"Unexpected Global Error: {e}"
        finally:
            conn.close()

    def get_account_cash_flows(self, account_id: int):
        
        conn = self._get_connection()
        try:
            flows = []
            
            rows_in = conn.execute("""
                SELECT date, to_amount 
                FROM transactions 
                WHERE type = 'transfer' AND to_account_id = ?
            """, [account_id]).fetchall()
            for d, amt in rows_in:
                if isinstance(d, str):
                    d = datetime.strptime(d, '%Y-%m-%d').date()
                flows.append((d, -1.0 * float(amt)))

            rows_out = conn.execute("""
                SELECT date, amount 
                FROM transactions 
                WHERE type = 'transfer' AND account_id = ?
            """, [account_id]).fetchall()
            for d, amt in rows_out:
                if isinstance(d, str):
                    d = datetime.strptime(d, '%Y-%m-%d').date()
                flows.append((d, float(amt)))
            
            return flows
        except Exception as e:
            print(f"Error getting cash flows: {e}")
            return []
        finally:
            conn.close()
    def get_investment_valuation_history(self, account_id: int):
        
        conn = self._get_connection()
        try:
            rows = conn.execute("""
                SELECT date, value 
                FROM investment_valuations 
                WHERE account_id = ?
                ORDER BY date ASC
            """, [account_id]).fetchall()
            
            history = []
            for d, val in rows:
                if isinstance(d, str):
                    d = datetime.strptime(d, '%Y-%m-%d').date()
                history.append((d, float(val)))
            return history
        except Exception as e:
            print(f"Error getting valuation history: {e}")
            return []
        finally:
            conn.close()

    def get_qty_changes(self, account_id: int):
        
        conn = self._get_connection()
        try:
            changes = []
            
            rows_in = conn.execute("""
                SELECT date, qty FROM transactions 
                WHERE type = 'transfer' AND to_account_id = ? AND qty IS NOT NULL AND qty != 0
            """, [account_id]).fetchall()
            for d, q in rows_in:
                if isinstance(d, str): d = datetime.strptime(d, '%Y-%m-%d').date()
                changes.append((d, float(q)))

            rows_exp = conn.execute("""
                SELECT date, qty FROM transactions 
                WHERE type = 'expense' AND account_id = ? AND qty IS NOT NULL AND qty != 0
            """, [account_id]).fetchall()
            for d, q in rows_exp:
                if isinstance(d, str): d = datetime.strptime(d, '%Y-%m-%d').date()
                changes.append((d, float(q)))

            rows_out = conn.execute("""
                SELECT date, qty FROM transactions 
                WHERE type = 'transfer' AND account_id = ? AND qty IS NOT NULL AND qty != 0
            """, [account_id]).fetchall()
            for d, q in rows_out:
                if isinstance(d, str): d = datetime.strptime(d, '%Y-%m-%d').date()
                changes.append((d, -1.0 * float(q)))
                
            rows_inc = conn.execute("""
                SELECT date, qty FROM transactions 
                WHERE type = 'income' AND account_id = ? AND qty IS NOT NULL AND qty != 0
            """, [account_id]).fetchall()
            for d, q in rows_inc:
                if isinstance(d, str): d = datetime.strptime(d, '%Y-%m-%d').date()
                changes.append((d, -1.0 * float(q)))
            
            changes.sort(key=lambda x: x[0])
            return changes
            
        except Exception as e:
            print(f"Error getting qty changes: {e}")
            return []
        finally:
            conn.close()

    def get_category_by_id(self, category_id):
        conn = self._get_connection()
        try:
            row = conn.execute(
                , [category_id]).fetchone()
            if row:
                return Category(*row)
            return None
        except Exception as e:
            print(f"Error getting category by id: {e}")
            return None
        finally:
            conn.close()

    def get_expenses_breakdown(self, year, month=None):
        conn = self._get_connection()
        try:
            start_date, end_date = self._get_date_range(year, month)

            result_main = conn.execute("""
                SELECT c.category, COALESCE(SUM(t.amount), 0)
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense' AND t.date >= ? AND t.date < ?
                GROUP BY c.category
                ORDER BY SUM(t.amount) DESC
            """, [start_date, end_date]).fetchall()

            main_breakdown = {row[0]: (row[1] or 0.0) for row in result_main}

            result_sub = conn.execute("""
                SELECT c.sub_category, c.category, COALESCE(SUM(t.amount), 0)
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense' AND t.date >= ? AND t.date < ?
                GROUP BY c.sub_category, c.category
                ORDER BY SUM(t.amount) DESC
            """, [start_date, end_date]).fetchall()

            sub_breakdown = [{'sub': row[0], 'main': row[1],
                              : (row[2] or 0.0)} for row in result_sub]

            return {'main': main_breakdown, 'sub': sub_breakdown}
        except Exception as e:
            print(f"Error getting expenses breakdown: {e}")
            return {'main': {}, 'sub': []}
        finally:
            conn.close()

    def get_expenses_breakdown(self, year, month, category_ids=None):
        
        conn = self._get_connection()
        try:
            start_date, end_date = self._get_date_range(year, month)

            if month is not None:
                if month == 12:
                    end_date = f"{year + 1}-01-01"
                else:
                    end_date = f"{year}-{month + 1:02d}-01"

            filter_clause = ""
            params = [start_date, end_date]
            if category_ids:
                placeholders = ','.join(['?'] * len(category_ids))
                filter_clause = f"AND t.category_id IN ({placeholders})"
                params.extend(category_ids)

            result = conn.execute(f"""
                SELECT c.category, c.sub_category,
                    COALESCE(SUM(
                        CASE
                            WHEN a.currency = 'CHF' THEN t.amount
                            ELSE t.amount * COALESCE(
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency AND er.date <= t.date ORDER BY er.date DESC LIMIT 1),
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency ORDER BY er.date ASC LIMIT 1),
                                1.0
                            )
                        END
                    ), 0)
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'expense' AND t.date >= ? AND t.date < ? {filter_clause}
                GROUP BY c.category, c.sub_category
                ORDER BY c.category, 3 DESC
            """, params).fetchall()

            breakdown = {}

            for cat, sub, amount in result:
                if not amount:
                    continue

                amount = float(amount)

                if cat not in breakdown:
                    breakdown[cat] = {'total': 0.0, 'subs': {}}

                breakdown[cat]['total'] += amount
                if sub:
                    breakdown[cat]['subs'][sub] = breakdown[cat]['subs'].get(
                        sub, 0.0) + amount

            return breakdown

        except Exception as e:
            print(f"Error getting expenses breakdown: {e}")
            return {}
        finally:
            conn.close()

    def get_monthly_expense_trend(self, end_year, end_month, category_ids=None):
        
        conn = self._get_connection()
        try:

            date(end_year, end_month, 1)

            months_list = []
            for i in range(11, -1, -1):

                curr_m = end_month - i
                curr_y = end_year

                while curr_m <= 0:
                    curr_m += 12
                    curr_y -= 1

                months_list.append((curr_y, curr_m))

            start_y, start_m = months_list[0]
            start_date_str = f"{start_y}-{start_m:02d}-01"

            if end_month == 12:
                limit_date_str = f"{end_year + 1}-01-01"
            else:
                limit_date_str = f"{end_year}-{end_month + 1:02d}-01"

            filter_clause = ""
            params = [start_date_str, limit_date_str]
            if category_ids:
                placeholders = ','.join(['?'] * len(category_ids))
                filter_clause = f"AND category_id IN ({placeholders})"
                params.extend(category_ids)

            result = conn.execute(f"""
                SELECT strftime('%Y', date), strftime('%m', date),
                    COALESCE(SUM(
                        CASE
                            WHEN a.currency = 'CHF' THEN t.amount
                            ELSE t.amount * COALESCE(
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency AND er.date <= t.date ORDER BY er.date DESC LIMIT 1),
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency ORDER BY er.date ASC LIMIT 1),
                                1.0
                            )
                        END
                    ), 0)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'expense' AND t.date >= ? AND t.date < ? {filter_clause}
                GROUP BY strftime('%Y', date), strftime('%m', date)
            """, params).fetchall()

            data_map = {}
            for r_y, r_m, val in result:
                data_map[(int(r_y), int(r_m))] = float(val)

            trend_data = []
            month_names = ["", "Jan", "Feb", "Mar", "Apr", "May",
                           , "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

            for y, m in months_list:
                amt = data_map.get((y, m), 0.0)
                label = f"{month_names[m]} {y}"
                trend_data.append({
                    : label,
                    : amt,
                    : y,
                    : m
                })

            return trend_data

        except Exception as e:
            print(f"Error getting monthly expense trend: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            conn.close()

    def get_top_payees(self, year, month=None, limit=10, category_ids=None):
        conn = self._get_connection()
        try:
            start_date, end_date = self._get_date_range(year, month)

            filter_clause = ""
            params = [start_date, end_date]
            if category_ids:
                placeholders = ','.join(['?'] * len(category_ids))
                filter_clause = f"AND category_id IN ({placeholders})"
                params.extend(category_ids)

            params.append(limit)

            result = conn.execute(f"""
                SELECT t.payee,
                    COALESCE(SUM(
                        CASE
                            WHEN a.currency = 'CHF' THEN t.amount
                            ELSE t.amount * COALESCE(
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency AND er.date <= t.date ORDER BY er.date DESC LIMIT 1),
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency ORDER BY er.date ASC LIMIT 1),
                                1.0
                            )
                        END
                    ), 0)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'expense' AND t.date >= ? AND t.date < ? AND t.payee IS NOT NULL AND t.payee != '' {filter_clause}
                GROUP BY t.payee
                ORDER BY 2 DESC
                LIMIT ?
            """, params).fetchall()

            return [{'payee': row[0], 'amount': float(row[1] or 0.0)} for row in result]
        except Exception as e:
            print(f"Error getting top payees: {e}")
            return []
        finally:
            conn.close()

    def _get_date_range(self, year, month):
        if month == 'All' or month is None or month == 0:
            start_date = f"{year}-01-01"
            end_date = f"{year+1}-01-01"
        else:
            if isinstance(month, str):

                try:
                    month = int(month)
                except:
                    pass

            if isinstance(month, int):
                start_date = f"{year}-{month:02d}-01"
                if month == 12:
                    end_date = f"{year+1}-01-01"
                else:
                    end_date = f"{year}-{month+1:02d}-01"
            else:

                start_date = f"{year}-01-01"
                end_date = f"{year+1}-01-01"
        return start_date, end_date

    def get_accumulated_dividends(self):
        
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT
                    t.invest_account_id,
                    CASE
                        WHEN a.currency = 'CHF' THEN t.amount
                        ELSE t.amount * COALESCE(
                            (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency AND er.date <= t.date ORDER BY er.date DESC LIMIT 1),
                            (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency ORDER BY er.date ASC LIMIT 1),
                            1.0
                        )
                    END as amount_chf,
                    c.sub_category,
                    strftime('%Y', t.date) as year
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'income' AND t.invest_account_id IS NOT NULL
            """).fetchall()

            income_summary = {}

            for invest_acc_id, val_chf, category_name, year in result:
                if invest_acc_id not in income_summary:
                    income_summary[invest_acc_id] = {'total': 0.0, 'years': {}}

                if val_chf:
                    val_chf = float(val_chf)
                    income_summary[invest_acc_id]['total'] += val_chf

                    if year not in income_summary[invest_acc_id]['years']:
                        income_summary[invest_acc_id]['years'][year] = {
                            : 0.0, 'breakdown': {}}

                    year_data = income_summary[invest_acc_id]['years'][year]
                    year_data['total'] += val_chf

                    cat_key = category_name if category_name else "Uncategorized"
                    year_data['breakdown'][cat_key] = year_data['breakdown'].get(
                        cat_key, 0.0) + val_chf

            return income_summary

        except Exception as e:
            print(f"Error calculating accumulated dividends: {e}")
            return {}
        finally:
            conn.close()

    def get_accumulated_expenses(self):
        
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT
                    t.invest_account_id,
                    CASE
                        WHEN a.currency = 'CHF' THEN t.amount
                        ELSE t.amount * COALESCE(
                            (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency AND er.date <= t.date ORDER BY er.date DESC LIMIT 1),
                            (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency ORDER BY er.date ASC LIMIT 1),
                            1.0
                        )
                    END as amount_chf,
                    c.sub_category,
                    strftime('%Y', t.date) as year
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense' AND t.invest_account_id IS NOT NULL
            """).fetchall()

            expense_summary = {}

            for invest_acc_id, val_chf, category_name, year in result:
                if invest_acc_id not in expense_summary:
                    expense_summary[invest_acc_id] = {
                        : 0.0, 'years': {}}

                if val_chf:
                    val_chf = float(val_chf)
                    expense_summary[invest_acc_id]['total'] += val_chf

                    if year not in expense_summary[invest_acc_id]['years']:
                        expense_summary[invest_acc_id]['years'][year] = {
                            : 0.0, 'breakdown': {}}

                    year_data = expense_summary[invest_acc_id]['years'][year]
                    year_data['total'] += val_chf

                    cat_key = category_name if category_name else "Uncategorized"
                    year_data['breakdown'][cat_key] = year_data['breakdown'].get(
                        cat_key, 0.0) + val_chf

            return expense_summary

        except Exception as e:
            print(f"Error calculating accumulated expenses: {e}")
            return {}
        finally:
            conn.close()

    def add_or_update_budget(self, sub_category: str, budget_amount: float):
        
        conn = self._get_connection()
        try:

            cat_row = conn.execute("SELECT id FROM categories WHERE sub_category = ?", [
                                   sub_category]).fetchone()
            if not cat_row:
                return False
            category_id = cat_row[0]

            conn.execute("""
                INSERT OR REPLACE INTO budgets (category_id, budget_amount)
                VALUES (?, ?)
            """, [category_id, budget_amount])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding/updating budget: {e}")
            return False
        finally:
            conn.close()

    def get_all_budgets(self, category_type='Expense'):
        
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT c.sub_category, b.budget_amount
                FROM budgets b
                JOIN categories c ON b.category_id = c.id
                WHERE c.category_type = ?
                ORDER BY c.sub_category
            """, [category_type]).fetchall()
            budgets = {}
            for row in result:
                budgets[row[0]] = float(row[1])
            return budgets
        except Exception as e:
            print(f"Error getting budgets: {e}")
            return {}
        finally:
            conn.close()

    def get_l12m_breakdown(self, end_year: int, end_month: int, category_type='Expense', transaction_type='expense') -> dict:
        
        conn = self._get_connection()
        try:
            if end_month == 12:
                limit_date_str = f"{end_year + 1}-01-01"
            else:
                limit_date_str = f"{end_year}-{end_month + 1:02d}-01"
            
            limit_dt = datetime.strptime(limit_date_str, "%Y-%m-%d")
            start_dt = limit_dt.replace(year=limit_dt.year - 1)
            start_date_str = start_dt.strftime("%Y-%m-%d")

            query = """
                SELECT t.date, t.amount, a.currency, c.sub_category
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = ? 
                  AND t.date >= ? 
                  AND t.date < ?
                  AND c.category_type = ?
            """
            transactions = conn.execute(query, [transaction_type, start_date_str, limit_date_str, category_type]).fetchall()
            
            all_rates = conn.execute("SELECT date, currency, rate FROM exchange_rates ORDER BY date ASC").fetchall()
            
            rates_history = {}
            for r_date, r_curr, r_rate in all_rates:
                if r_curr not in rates_history:
                    rates_history[r_curr] = []
                rates_history[r_curr].append((str(r_date), float(r_rate)))

            import bisect

            def get_rate_at(date_str, currency):
                if currency == 'CHF': return 1.0
                history = rates_history.get(currency)
                if not history: return 1.0
                
                idx = bisect.bisect_right(history, (date_str, float('inf')))
                if idx > 0:
                    return history[idx-1][1]
                return history[0][1]

            l12m_data = {}
            
            for row in transactions:
                t_date = row[0]
                amount = float(row[1]) if row[1] else 0.0
                currency = row[2]
                sub_cat = row[3]
                
                if not amount: continue
                
                t_date_str = str(t_date)
                rate = get_rate_at(t_date_str, currency)
                val_chf = amount * rate
                
                l12m_data[sub_cat] = l12m_data.get(sub_cat, 0.0) + val_chf

            return l12m_data

        except Exception as e:
            print(f"Error getting L12M breakdown: {e}")
            import traceback
            traceback.print_exc()
            return {}
        finally:
            conn.close()

    def get_l12m_expenses_breakdown(self, end_year, end_month):
        return self.get_l12m_breakdown(end_year, end_month, 'Expense', 'expense')

    def delete_budget(self, sub_category: str):
        
        conn = self._get_connection()
        try:

            cat_row = conn.execute("SELECT id FROM categories WHERE sub_category = ?", [
                                   sub_category]).fetchone()
            if not cat_row:
                return False
            category_id = cat_row[0]

            conn.execute("""
                DELETE FROM budgets
                WHERE category_id = ?
            """, [category_id])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting budget: {e}")
            return False
        finally:
            conn.close()

    def get_budget_vs_actual(self, year: int, month: int, category_type='Expense', transaction_type='expense'):
        
        conn = self._get_connection()
        try:
            start_date_str = f"{year}-{month:02d}-01"
            if month == 12:
                end_date_str = f"{year + 1}-01-01"
            else:
                end_date_str = f"{year}-{month + 1:02d}-01"

            query = """
                SELECT t.date, t.amount, a.currency, c.sub_category, c.category
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = ? 
                  AND t.date >= ? 
                  AND t.date < ?
                  AND c.category_type = ?
            """
            transactions = conn.execute(query, [transaction_type, start_date_str, end_date_str, category_type]).fetchall()
            
            all_rates = conn.execute("SELECT date, currency, rate FROM exchange_rates ORDER BY date ASC").fetchall()
            
            rates_history = {}
            for r_date, r_curr, r_rate in all_rates:
                if r_curr not in rates_history:
                    rates_history[r_curr] = []
                rates_history[r_curr].append((str(r_date), float(r_rate)))

            import bisect

            def get_rate_at(date_str, currency):
                if currency == 'CHF': return 1.0
                history = rates_history.get(currency)
                if not history: return 1.0
                idx = bisect.bisect_right(history, (date_str, float('inf')))
                if idx > 0:
                    return history[idx-1][1]
                return history[0][1]

            actuals_map = {}
            
            for row in transactions:
                t_date = row[0]
                amount = float(row[1]) if row[1] else 0.0
                currency = row[2]
                sub_cat = row[3]
                cat_name = row[4]
                
                if not amount: continue
                
                t_date_str = str(t_date)
                rate = get_rate_at(t_date_str, currency)
                val_chf = amount * rate
                
                if sub_cat not in actuals_map:
                    actuals_map[sub_cat] = {'category': cat_name, 'amount': 0.0}
                actuals_map[sub_cat]['amount'] += val_chf

        finally:
            conn.close()
        
        budgets = self.get_all_budgets(category_type)
        
        final_result = {}
        all_subs = set(budgets.keys()) | set(actuals_map.keys())
        
        categories = self.get_all_categories()
        cat_map = {c.sub_category: c.category for c in categories if c.category_type == category_type}

        for sub in all_subs:
            budget_val = budgets.get(sub, 0.0)
            
            if sub in actuals_map:
                actual_val = actuals_map[sub]['amount']
                cat_name = actuals_map[sub]['category']
            else:
                actual_val = 0.0
                cat_name = cat_map.get(sub, 'Other')
                
            remaining = budget_val - actual_val
            percentage = (actual_val / budget_val * 100) if budget_val > 0 else 0
            
            final_result[sub] = {
                : cat_name,
                : budget_val,
                : actual_val,
                : remaining,
                : percentage
            }
            
        return final_result

    def get_budget_vs_expenses(self, year, month):
        return self.get_budget_vs_actual(year, month, 'Expense', 'expense')

    def get_investment_history_matrix_data(self):
        
        conn = self._get_connection()
        try:
            return conn.execute("""
                SELECT strftime(date, '%Y-%m-%d') as date_str, account_id, value
                FROM investment_valuations
                ORDER BY date DESC, account_id ASC
            """).fetchall()
        except Exception as e:
            print(f"Error fetching investment history matrix: {e}")
            return []
        finally:
            conn.close()

    def add_investment_valuations_bulk(self, valuations_data: list):
        
        conn = self._get_connection()
        try:

            new_id_res = conn.execute(
                ).fetchone()
            current_max_id = new_id_res[0] if new_id_res else 0

            for i, (date, account_id, value) in enumerate(valuations_data):
                current_max_id += 1
                conn.execute("""
                    INSERT INTO investment_valuations (id, date, account_id, value)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (date, account_id) DO UPDATE SET value = excluded.value
                """, (current_max_id, date, account_id, value))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding investment valuations: {e}")
            return False
        finally:
            conn.close()

    def delete_investment_valuations_bulk(self, valuations_data: list):
        
        if not valuations_data:
            return True

        conn = self._get_connection()
        try:
            for date, account_id in valuations_data:
                conn.execute(
                    , (date, account_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting investment valuations: {e}")
            return False
        finally:
            conn.close()

    def get_investment_valuation_for_date(self, account_id: int, target_date: str = None) -> float:
        
        if target_date is None:
            today = datetime.now().date()

            next_day_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            try:
                t_date = datetime.strptime(target_date, '%Y-%m-%d').date()
                next_day = t_date + timedelta(days=1)
                next_day_str = next_day.strftime('%Y-%m-%d')
            except ValueError:
                next_day_str = target_date

        conn = self._get_connection()
        try:

            result = conn.execute("""
                SELECT value FROM investment_valuations
                WHERE account_id = ? AND date < ?
                ORDER BY date DESC
                LIMIT 1
            """, (account_id, next_day_str)).fetchone()

            if result:
                return float(result[0])

            result = conn.execute("""
                SELECT value FROM investment_valuations
                WHERE account_id = ?
                ORDER BY date ASC
                LIMIT 1
            """, (account_id,)).fetchone()

            if result:
                return float(result[0])

            return 0.0
        finally:
            conn.close()

    def get_subcategories_by_category(self):
        
        categories = self.get_all_categories()
        result = {}
        for category in categories:
            if category.category not in result:
                result[category.category] = []
            result[category.category].append(category.sub_category)
        return result

    def get_available_years(self):
        
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT DISTINCT strftime(date, '%Y') as year
                FROM transactions
                WHERE date IS NOT NULL
                ORDER BY year DESC
            """).fetchall()
            years = [int(r[0]) for r in result if r[0] is not None]

            current_year = datetime.now().year
            if current_year not in years:
                years.insert(0, current_year)

            return sorted(years, reverse=True)
        except Exception as e:
            print(f"Error getting available years: {e}")
            return [datetime.now().year]
        finally:
            conn.close()

    def get_monthly_balances(self, year: int) -> dict:
        
        conn = self._get_connection()
        try:
            import bisect
            from datetime import date, timedelta

            accounts = conn.execute("""
                SELECT id, currency, is_investment, valuation_strategy, account
                FROM accounts
                WHERE show_in_balance = TRUE AND id != 0
            """).fetchall()
            
            if not accounts:
                return {m: 0.0 for m in range(1, 13)}

            acc_meta = {}
            for row in accounts:
                acc_meta[row[0]] = {
                    : row[1], 
                    : bool(row[2]) if row[2] else False, 
                    : row[3], 
                    : 0.0, 
                    : 0.0
                }

            year_start = date(year, 1, 1).strftime('%Y-%m-%d')
            year_end = date(year, 12, 31).strftime('%Y-%m-%d')
            
            opening_rows = conn.execute("""
                SELECT 
                    account_id, 
                    SUM(CASE 
                        WHEN t.type='income' THEN t.amount 
                        WHEN t.type='expense' THEN -t.amount 
                        WHEN t.type='transfer' THEN -t.amount 
                        ELSE 0 END),
                    SUM(CASE 
                        WHEN t.type='income' THEN t.qty 
                        WHEN t.type='expense' AND a.is_investment THEN -t.qty 
                        WHEN t.type='transfer' AND a.is_investment THEN -t.qty 
                        ELSE 0 END)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.date < ? AND t.account_id IS NOT NULL
                GROUP BY account_id
                
                UNION ALL 
                
                SELECT 
                    to_account_id, 
                    SUM(to_amount),
                    SUM(qty)
                FROM transactions t
                JOIN accounts a ON t.to_account_id = a.id
                WHERE t.date < ? AND t.to_account_id IS NOT NULL AND t.type='transfer'
                GROUP BY to_account_id
            """, (year_start, year_start)).fetchall()
            
            for aid, bal, qty in opening_rows:
                if aid in acc_meta:
                    acc_meta[aid]['bal'] += float(bal or 0.0)
                    acc_meta[aid]['qty'] += float(qty or 0.0)

            delta_rows = conn.execute("""
                SELECT 
                    MONTH(CAST(t.date AS DATE)),
                    account_id, 
                    SUM(CASE 
                        WHEN t.type='income' THEN t.amount 
                        WHEN t.type='expense' THEN -t.amount 
                        WHEN t.type='transfer' THEN -t.amount 
                        ELSE 0 END),
                    SUM(CASE 
                        WHEN t.type='income' THEN t.qty 
                        WHEN t.type='expense' AND a.is_investment THEN -t.qty 
                        WHEN t.type='transfer' AND a.is_investment THEN -t.qty 
                        ELSE 0 END)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.date >= ? AND t.date <= ? AND t.account_id IS NOT NULL
                GROUP BY MONTH(CAST(t.date AS DATE)), account_id
                
                UNION ALL 
                
                SELECT 
                    MONTH(CAST(t.date AS DATE)),
                    to_account_id, 
                    SUM(to_amount),
                    SUM(qty)
                FROM transactions t
                JOIN accounts a ON t.to_account_id = a.id
                WHERE t.date >= ? AND t.date <= ? AND t.to_account_id IS NOT NULL AND t.type='transfer'
                GROUP BY MONTH(CAST(t.date AS DATE)), to_account_id
            """, (year_start, year_end, year_start, year_end)).fetchall()

            deltas = {}
            for m_idx, aid, d_bal, d_qty in delta_rows:
                if aid in acc_meta:
                    k = (m_idx, aid)
                    if k not in deltas: deltas[k] = {'bal': 0.0, 'qty': 0.0}
                    deltas[k]['bal'] += float(d_bal or 0.0)
                    deltas[k]['qty'] += float(d_qty or 0.0)

            rates_rows = conn.execute("SELECT currency, date, rate FROM exchange_rates ORDER BY date").fetchall()
            rates_cache = {}
            for c, d, r in rates_rows:
                if c not in rates_cache: rates_cache[c] = []
                rates_cache[c].append((str(d), float(r)))

            prices_rows = conn.execute("SELECT account_id, date, value FROM investment_valuations ORDER BY date").fetchall()
            prices_cache = {}
            for aid, d, v in prices_rows:
                if aid not in prices_cache: prices_cache[aid] = []
                prices_cache[aid].append((str(d), float(v)))

            def get_rate_locf(curr, target_d):
                if curr == 'CHF': return 1.0
                history = rates_cache.get(curr, [])
                if not history: return 1.0
                idx = bisect.bisect_right(history, (target_d, float('inf')))
                if idx == 0: return history[0][1]
                return history[idx-1][1]

            def get_price_locf(aid, target_d):
                history = prices_cache.get(aid, [])
                if not history: return 0.0
                idx = bisect.bisect_right(history, (target_d, float('inf')))
                if idx == 0: return history[0][1]
                return history[idx-1][1]

            monthly_totals = {}
            for m in range(1, 13):
                for aid, meta in acc_meta.items():
                    d = deltas.get((m, aid), None)
                    if d:
                        meta['bal'] += d['bal']
                        meta['qty'] += d['qty']
                
                if m == 12: 
                    eom = date(year, 12, 31)
                else: 
                    eom = date(year, m+1, 1) - timedelta(days=1)
                
                total_chf = 0.0
                for aid, meta in acc_meta.items():
                    val_native = meta['bal']
                    
                    if meta['is_inv']:
                        if meta['strat'] == 'Price/Qty':
                             price = get_price_locf(aid, eom)
                             val_native = meta['qty'] * price
                        else:
                             p = get_price_locf(aid, eom)
                             if p > 0: val_native = p
                    
                    rate = get_rate_locf(meta['curr'], eom)
                    total_chf += val_native * rate
                
                monthly_totals[m] = total_chf
                
            return monthly_totals

        except Exception as e:
            print(f"Error calculating monthly balances: {e}")
            import traceback
            traceback.print_exc()
            return {m: 0.0 for m in range(1, 13)}
        finally:
            conn.close()

    def get_net_worth_history(self, start_date: str, end_date: str) -> dict:
        
        conn = self._get_connection()
        try:
            from datetime import datetime, timedelta
            from dateutil.relativedelta import relativedelta

            accounts = conn.execute("""
                SELECT id, currency, is_investment, valuation_strategy, account
                FROM accounts
                WHERE show_in_balance = TRUE AND id != 0
            """).fetchall()
            
            if not accounts:
                return {}

            acc_meta = {}
            for row in accounts:
                acc_meta[row[0]] = {
                    : row[1], 
                    : bool(row[2]) if row[2] else False, 
                    : row[3], 
                    : 0.0, 
                    : 0.0
                }

            opening_rows = conn.execute("""
                SELECT 
                    account_id, 
                    SUM(CASE 
                        WHEN t.type='income' THEN t.amount 
                        WHEN t.type='expense' THEN -t.amount 
                        WHEN t.type='transfer' THEN -t.amount 
                        ELSE 0 END),
                    SUM(CASE 
                        WHEN t.type='income' THEN t.qty 
                        WHEN t.type='expense' AND a.is_investment THEN -t.qty 
                        WHEN t.type='transfer' AND a.is_investment THEN -t.qty 
                        ELSE 0 END)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.date < ? AND t.account_id IS NOT NULL
                GROUP BY account_id
                
                UNION ALL 
                
                SELECT 
                    to_account_id, 
                    SUM(to_amount),
                    SUM(qty)
                FROM transactions t
                JOIN accounts a ON t.to_account_id = a.id
                WHERE t.date < ? AND t.to_account_id IS NOT NULL AND t.type='transfer'
                GROUP BY to_account_id
            """, (start_date, start_date)).fetchall()
            
            for aid, bal, qty in opening_rows:
                if aid in acc_meta:
                    acc_meta[aid]['bal'] += float(bal or 0.0)
                    acc_meta[aid]['qty'] += float(qty or 0.0)

            delta_rows = conn.execute("""
                SELECT 
                    strftime('%Y-%m', t.date),
                    account_id, 
                    SUM(CASE 
                        WHEN t.type='income' THEN t.amount 
                        WHEN t.type='expense' THEN -t.amount 
                        WHEN t.type='transfer' THEN -t.amount 
                        ELSE 0 END),
                    SUM(CASE 
                        WHEN t.type='income' THEN t.qty 
                        WHEN t.type='expense' AND a.is_investment THEN -t.qty 
                        WHEN t.type='transfer' AND a.is_investment THEN -t.qty 
                        ELSE 0 END)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.date >= ? AND t.date <= ? AND t.account_id IS NOT NULL
                GROUP BY strftime('%Y-%m', t.date), account_id
                
                UNION ALL 
                
                SELECT 
                    strftime('%Y-%m', t.date),
                    to_account_id, 
                    SUM(to_amount),
                    SUM(qty)
                FROM transactions t
                JOIN accounts a ON t.to_account_id = a.id
                WHERE t.date >= ? AND t.date <= ? AND t.to_account_id IS NOT NULL AND t.type='transfer'
                GROUP BY strftime('%Y-%m', t.date), to_account_id
            """, (start_date, end_date, start_date, end_date)).fetchall()

            deltas = {} 
            for ym, aid, d_bal, d_qty in delta_rows:
                if aid in acc_meta:
                    k = (ym, aid)
                    if k not in deltas: deltas[k] = {'bal': 0.0, 'qty': 0.0}
                    deltas[k]['bal'] += float(d_bal or 0.0)
                    deltas[k]['qty'] += float(d_qty or 0.0)

            rates_rows = conn.execute("SELECT currency, date, rate FROM exchange_rates ORDER BY date").fetchall()
            rates_cache = {}
            for c, d, r in rates_rows:
                if c not in rates_cache: rates_cache[c] = []
                rates_cache[c].append((str(d), float(r)))

            prices_rows = conn.execute("SELECT account_id, date, value FROM investment_valuations ORDER BY date").fetchall()
            prices_cache = {}
            for aid, d, v in prices_rows:
                if aid not in prices_cache: prices_cache[aid] = []
                prices_cache[aid].append((str(d), float(v)))

            history = {}
            current_meta = {aid: vals.copy() for aid, vals in acc_meta.items()}
            
            s_dt = datetime.strptime(start_date, '%Y-%m-%d')
            e_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            months = []
            curr = s_dt.replace(day=1)
            while curr <= e_dt:
                months.append(curr.strftime('%Y-%m'))
                curr += relativedelta(months=1)
                
            def get_val_at(aid, date_str):
                rates = rates_cache.get(acc_meta[aid]['curr'], [])
                eff_rate = 1.0
                if rates:
                    for d, r in reversed(rates):
                        if d <= date_str:
                            eff_rate = r
                            break
                
                eff_price = 0.0
                if acc_meta[aid]['is_inv']:
                    prices = prices_cache.get(aid, [])
                    if prices:
                        for d, v in reversed(prices):
                            if d <= date_str:
                                eff_price = v
                                break
                
                strat = acc_meta[aid]['strat']
                bal = current_meta[aid]['bal']
                qty = current_meta[aid]['qty']
                
                val_native = bal
                if acc_meta[aid]['is_inv']:
                    if strat == 'Price/Qty':
                        val_native = qty * eff_price
                    else:
                        if eff_price > 0: val_native = eff_price
                        else: val_native = bal

                return val_native * eff_rate

            for ym in months:
                for aid, meta in current_meta.items():
                    d = deltas.get((ym, aid))
                    if d:
                        meta['bal'] += d['bal']
                        meta['qty'] += d['qty']
                
                dt = datetime.strptime(ym, '%Y-%m')
                next_m = dt + relativedelta(months=1)
                eom = next_m - timedelta(days=1)
                eom_str = eom.strftime('%Y-%m-%d')
                
                total_nw = 0.0
                for aid in current_meta:
                    total_nw += get_val_at(aid, eom_str)
                
                history[ym] = total_nw
                
            return history
        finally:
            conn.close()

    def get_monthly_investment_gains(self, year: int, account_ids: list = None) -> dict:
        
        import calendar
        import bisect
        conn = self._get_connection()
        try:
            inv_rows = conn.execute("SELECT id, account, currency, valuation_strategy FROM accounts WHERE is_investment = 1").fetchall()
            
            all_acc_rows = conn.execute("SELECT id, currency FROM accounts").fetchall()
            acc_currencies = {r[0]: r[1] for r in all_acc_rows}

            if not inv_rows:
                return {}
            
            if account_ids is not None:
                inv_rows = [r for r in inv_rows if r[0] in account_ids]
                if not inv_rows:
                    return {}
            
            inv_map = {r[0]: {'name': r[1], 'currency': r[2], 'strat': r[3]} for r in inv_rows}
            inv_ids = list(inv_map.keys())
            
            year_start_str = f"{year}-01-01"
            year_end_str = f"{year}-12-31"
            
            ph = ','.join(['?'] * len(inv_ids))
            
            opening_sql = f"""
                SELECT account_id, 
                    SUM(CASE WHEN t.type='income' THEN t.amount WHEN t.type='expense' THEN -t.amount WHEN t.type='transfer' THEN -t.amount ELSE 0 END),
                    SUM(CASE WHEN t.type='income' THEN t.qty WHEN t.type='expense' THEN -t.qty WHEN t.type='transfer' THEN -t.qty ELSE 0 END)
                FROM transactions t
                WHERE t.account_id IN ({ph}) AND t.date < ?
                GROUP BY account_id
                UNION ALL
                SELECT to_account_id, SUM(to_amount), SUM(qty)
                FROM transactions t
                WHERE t.to_account_id IN ({ph}) AND t.type='transfer' AND t.date < ?
                GROUP BY to_account_id
            """
            opening_params = inv_ids + [year_start_str] + inv_ids + [year_start_str]
            opening_rows = conn.execute(opening_sql, opening_params).fetchall()
            
            state = {aid: {'bal': 0.0, 'qty': 0.0} for aid in inv_ids}
            for aid, bal, qty in opening_rows:
                if aid in state:
                    state[aid]['bal'] += float(bal or 0.0)
                    state[aid]['qty'] += float(qty or 0.0)
                    
            tx_sql = f"""
                SELECT 
                    MONTH(CAST(t.date AS DATE)),
                    t.date, t.type, t.account_id, t.to_account_id, 
                    t.amount, t.to_amount, t.qty, t.invest_account_id
                FROM transactions t
                WHERE t.date >= ? AND t.date <= ? 
                AND (t.account_id IN ({ph}) OR t.to_account_id IN ({ph}) OR t.invest_account_id IN ({ph}))
                ORDER BY t.date
            """
            tx_params = [year_start_str, year_end_str] + inv_ids + inv_ids + inv_ids
            tx_rows = conn.execute(tx_sql, tx_params).fetchall()
            
            rates_rows = conn.execute("SELECT currency, date, rate FROM exchange_rates ORDER BY date").fetchall()
            rates_cache = {}
            for c, d, r in rates_rows:
                if c not in rates_cache: rates_cache[c] = ([], [])
                rates_cache[c][0].append(str(d))
                rates_cache[c][1].append(float(r))
                
            prices_sql = f"""
                SELECT p.account_id, p.date, p.price 
                FROM stock_prices p 
                WHERE p.account_id IN ({ph})
                ORDER BY p.date
            """
            try:
                prices_rows = conn.execute(prices_sql, inv_ids).fetchall()
            except Exception:
                prices_rows = []
            
            prices_cache = {}
            for aid, d, p in prices_rows:
                if aid not in prices_cache: prices_cache[aid] = ([], [])
                prices_cache[aid][0].append(str(d))
                prices_cache[aid][1].append(float(p))

            val_sql = f"""
                SELECT v.account_id, v.date, v.value 
                FROM investment_valuations v
                WHERE v.account_id IN ({ph})
                ORDER BY v.date
            """
            val_rows = conn.execute(val_sql, inv_ids).fetchall()
            val_cache = {}
            for aid, d, v in val_rows:
                if aid not in val_cache: val_cache[aid] = ([], [])
                val_cache[aid][0].append(str(d))
                val_cache[aid][1].append(float(v))
                
            def get_rate(curr, date_str):
                if curr == 'CHF': return 1.0
                if curr not in rates_cache: return 1.0
                dates, rates = rates_cache[curr]
                idx = bisect.bisect_right(dates, date_str) - 1
                if idx >= 0: return rates[idx]
                return 1.0
                
            def get_price(aid, date_str):
                if aid not in prices_cache: return 0.0
                dates, prices = prices_cache[aid]
                idx = bisect.bisect_right(dates, date_str) - 1
                if idx >= 0: return prices[idx]
                return 0.0

            def get_valuation_total(aid, date_str):
                if aid not in val_cache: return 0.0
                dates, vals = val_cache[aid]
                idx = bisect.bisect_right(dates, date_str) - 1
                if idx >= 0: return vals[idx]
                return 0.0
                
            def calculate_account_valuation_chf(aid, s, date_str):
                cur = inv_map[aid]['currency']
                strat = inv_map[aid]['strat']
                rate = get_rate(cur, date_str)
                
                if strat == 'Total Value':
                    val_native = get_valuation_total(aid, date_str)
                    if val_native == 0.0:
                        val_native = s['bal']
                else:
                    price = get_price(aid, date_str)
                    if price == 0.0:
                        price = get_valuation_total(aid, date_str)
                        
                    val_native = s['bal'] + (s['qty'] * price)
                    
                return val_native * rate

            month_end_date_0 = f"{year-1}-12-31"
            prev_valuations = {aid: calculate_account_valuation_chf(aid, state[aid], month_end_date_0) for aid in inv_ids}
            
            results = {}
            
            tx_by_month = {m: [] for m in range(1, 13)}
            for row in tx_rows:
                m = row[0]
                if m and 1 <= m <= 12:
                    tx_by_month[m].append(row)
                    
            for m in range(1, 13):
                last_day = calendar.monthrange(year, m)[1]
                month_end_str = f"{year}-{m:02d}-{last_day}"
                
                flows_chf = {aid: 0.0 for aid in inv_ids}
                income_chf = {aid: 0.0 for aid in inv_ids}
                expense_chf = {aid: 0.0 for aid in inv_ids}
                deposits_chf = {aid: 0.0 for aid in inv_ids}
                withdrawals_chf = {aid: 0.0 for aid in inv_ids}
                
                income_details = {aid: 0.0 for aid in inv_ids}
                expense_details = {aid: 0.0 for aid in inv_ids}
                
                for _, t_date, t_type, aid, to_aid, amt, to_amt, qty, link_aid in tx_by_month[m]:
                    t_date_str = str(t_date)
                    amt_val = float(amt or 0)
                    to_amt_val = float(to_amt if to_amt is not None else amt_val)
                    qty_val = float(qty or 0)
                    
                    target_inc_aid = None
                    if link_aid in inv_ids:
                        target_inc_aid = link_aid
                    elif aid in inv_ids:
                        target_inc_aid = aid
                        
                    source_currency = acc_currencies.get(aid, 'CHF') if 'acc_currencies' in locals() else 'CHF'
                    rate = get_rate(source_currency, t_date_str)
                    val_chf = amt_val * rate
                    
                    if target_inc_aid is not None:
                        if t_type == 'income':
                            income_chf[target_inc_aid] += val_chf
                            income_details[target_inc_aid] += val_chf
                        elif t_type == 'expense':
                            expense_chf[target_inc_aid] += val_chf
                            expense_details[target_inc_aid] += val_chf

                    if aid in inv_ids:
                        if t_type == 'income':
                            state[aid]['bal'] += amt_val
                            state[aid]['qty'] += qty_val
                            flows_chf[aid] += val_chf 
                        elif t_type == 'expense':
                            state[aid]['bal'] -= amt_val
                            state[aid]['qty'] -= qty_val
                            flows_chf[aid] -= val_chf
                        elif t_type == 'transfer':
                            state[aid]['bal'] -= amt_val
                            state[aid]['qty'] -= qty_val
                            flows_chf[aid] -= val_chf
                            withdrawals_chf[aid] += val_chf
                            
                    if t_type == 'transfer' and to_aid in inv_ids:
                        target_currency = inv_map[to_aid]['currency']
                        rate_to = get_rate(target_currency, t_date_str)
                        val_to_chf = to_amt_val * rate_to
                        
                        state[to_aid]['bal'] += to_amt_val
                        state[to_aid]['qty'] += qty_val
                        flows_chf[to_aid] += val_to_chf
                        deposits_chf[to_aid] += val_to_chf

                curr_valuations = {aid: calculate_account_valuation_chf(aid, state[aid], month_end_str) for aid in inv_ids}
                
                income_named_details = {}
                for aid, val in income_details.items():
                    if abs(val) > 0.001:
                        name = inv_map[aid]['name']
                        income_named_details[name] = val
                
                expense_named_details = {}
                for aid, val in expense_details.items():
                    if abs(val) > 0.001:
                        name = inv_map[aid]['name']
                        expense_named_details[name] = val

                month_res = {
                    : 0.0, 
                    : 0.0, 
                    : 0.0, 
                    : sum(income_chf.values()),
                    : sum(expense_chf.values()),
                    : sum(deposits_chf.values()),
                    : sum(withdrawals_chf.values()),
                    : sum(flows_chf.values()),
                    : {
                        : {}, 
                        : {}, 
                        : {},
                        : income_named_details,
                        : expense_named_details
                    }
                }
                
                for aid in inv_ids:
                    
                    prev_bal = state[aid]['bal']
                    pass

                    if abs(flows_chf[aid]) > 0.001:
                        month_res['details']['flows'][inv_map[aid]['name']] = flows_chf[aid]

                    gain = (curr_valuations[aid] - prev_valuations[aid]) - flows_chf[aid]
                    
                    if gain >= 0.001: 
                        month_res['total_gain'] += gain
                        month_res['details']['gains'][inv_map[aid]['name']] = gain
                    elif gain <= -0.001:
                        month_res['total_loss'] += gain
                        month_res['details']['losses'][inv_map[aid]['name']] = gain
                        
                month_res['net'] = month_res['total_gain'] + month_res['total_loss']
                results[m] = month_res
                
                prev_valuations = curr_valuations
                
            return results
        finally:
            conn.close()

    def get_investment_gains_history(self, start_date: str, end_date: str, account_ids: list = None) -> dict:
        
        conn = self._get_connection()
        try:
            from datetime import datetime, timedelta
            from dateutil.relativedelta import relativedelta

            inv_rows = conn.execute("SELECT id, account, currency, valuation_strategy FROM accounts WHERE is_investment = 1").fetchall()
            
            if account_ids:
                inv_rows = [r for r in inv_rows if r[0] in account_ids]

            if not inv_rows:
                return {}
            
            inv_map = {r[0]: {'name': r[1], 'currency': r[2], 'strat': r[3]} for r in inv_rows}
            inv_ids = list(inv_map.keys())
            
            rates_rows = conn.execute("SELECT currency, date, rate FROM exchange_rates ORDER BY date").fetchall()
            rates_cache = {}
            for c, d, r in rates_rows:
                if c not in rates_cache: rates_cache[c] = []
                rates_cache[c].append((str(d), float(r)))

            prices_rows = conn.execute("SELECT account_id, date, value FROM investment_valuations ORDER BY date").fetchall()
            prices_cache = {}
            for aid, d, v in prices_rows:
                if aid not in prices_cache: prices_cache[aid] = []
                prices_cache[aid].append((str(d), float(v)))
                
            def get_rate(curr, d_str):
                if curr == 'CHF': return 1.0
                rs = rates_cache.get(curr, [])
                eff = 1.0
                if rs:
                     for d, r in reversed(rs):
                        if d <= d_str:
                            eff = r
                            break
                return eff

            def get_price(aid, d_str):
                ps = prices_cache.get(aid, [])
                eff = 0.0
                if ps:
                     for d, v in reversed(ps):
                        if d <= d_str:
                            eff = v
                            break
                return eff
            
            ph = ','.join(['?'] * len(inv_ids))
            opening_rows = conn.execute(f"""
                SELECT account_id, SUM(CASE WHEN type='income' THEN qty WHEN type='expense' THEN -qty WHEN type='transfer' THEN -qty ELSE 0 END)
                FROM transactions 
                WHERE account_id IN ({ph}) AND date < ?
                GROUP BY account_id
                
                UNION ALL
                
                SELECT to_account_id, SUM(qty)
                FROM transactions
                WHERE to_account_id IN ({ph}) AND date < ? AND type='transfer'
                GROUP BY to_account_id
            """, inv_ids + [start_date] + inv_ids + [start_date]).fetchall()
            
            holdings = {aid: 0.0 for aid in inv_ids}
            for aid, qty in opening_rows:
                if aid in holdings: holdings[aid] += float(qty or 0.0)

            raw_txs = conn.execute(f"""
                SELECT strftime('%Y-%m', t.date) as ym, t.date, t.type, t.account_id, t.to_account_id, t.amount, t.to_amount, t.qty, a.currency
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE (t.account_id IN ({ph}) OR (t.type='transfer' AND t.to_account_id IN ({ph})))
                  AND t.date >= ? AND t.date <= ?
                ORDER BY t.date
            """, inv_ids + inv_ids + [start_date, end_date]).fetchall()
            
            txs_by_month = {}
            for row in raw_txs:
                ym = row[0]
                if ym not in txs_by_month: txs_by_month[ym] = []
                txs_by_month[ym].append(row)

            history = {}
            s_dt = datetime.strptime(start_date, '%Y-%m-%d')
            e_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            curr = s_dt.replace(day=1)
            months = []
            while curr <= e_dt:
                months.append(curr.strftime('%Y-%m'))
                curr += relativedelta(months=1)
            
            for ym in months:
                dt_obj = datetime.strptime(ym, '%Y-%m')
                som = dt_obj
                prev_eom = som - timedelta(days=1)
                prev_eom_str = prev_eom.strftime('%Y-%m-%d')
                
                next_m = som + relativedelta(months=1)
                eom = next_m - timedelta(days=1)
                eom_str = eom.strftime('%Y-%m-%d')
                
                start_val_chf = 0.0
                for aid, qty in holdings.items():
                    price = get_price(aid, prev_eom_str)
                    rate = get_rate(inv_map[aid]['currency'], prev_eom_str)
                    
                    val_native = 0.0
                    if inv_map[aid]['strat'] == 'Price/Qty':
                        val_native = qty * price
                    else:
                        val_native = price
                    
                    start_val_chf += (val_native * rate)
                
                net_invested_chf = 0.0
                year_txs = txs_by_month.get(ym, [])
                
                for r in year_txs:
                    date_str = str(r[1])
                    typ = r[2]
                    aid = r[3]
                    to_aid = r[4]
                    amt = float(r[5] or 0)
                    to_amt = float(r[6] or 0)
                    qty = float(r[7] or 0)
                    tx_curr = r[8]
                    
                    tx_rate = get_rate(tx_curr if tx_curr else 'CHF', date_str)
                    
                    if aid in holdings:
                        if typ == 'expense':
                            holdings[aid] -= qty
                        elif typ == 'income':
                            holdings[aid] += qty
                        elif typ == 'transfer':
                            holdings[aid] -= qty
                            net_invested_chf -= (amt * tx_rate)
                            
                    if to_aid in holdings:
                        if typ == 'transfer':
                            holdings[to_aid] += qty
                            to_curr = inv_map[to_aid]['currency']
                            to_rate = get_rate(to_curr, date_str)
                            net_invested_chf += (to_amt * to_rate)

                end_val_chf = 0.0
                for aid, qty in holdings.items():
                    price = get_price(aid, eom_str)
                    rate = get_rate(inv_map[aid]['currency'], eom_str)
                    
                    val_native = 0.0
                    if inv_map[aid]['strat'] == 'Price/Qty':
                        val_native = qty * price
                    else:
                        val_native = price 
                    
                    end_val_chf += (val_native * rate)
                
                gain = (end_val_chf - start_val_chf) - net_invested_chf
                
                history[ym] = {
                    : gain,
                    : gain if gain > 0 else 0,
                    : abs(gain) if gain < 0 else 0
                }
                
            return history
        finally:
            conn.close()

    def get_historical_cost_basis(self, account_id: int):
        
        conn = self._get_connection()
        try:
            d_val = conn.execute("""
                SELECT 
                    SUM(
                        CASE
                            WHEN a.currency = 'CHF' THEN t.to_amount
                            ELSE t.to_amount * COALESCE(
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency AND er.date <= t.date ORDER BY er.date DESC LIMIT 1),
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency ORDER BY er.date ASC LIMIT 1),
                                1.0
                            )
                        END
                    )
                FROM transactions t
                JOIN accounts a ON t.to_account_id = a.id
                WHERE t.type = 'transfer' AND t.to_account_id = ?
            """, [account_id]).fetchone()[0]
            deposits = float(d_val) if d_val is not None else 0.0

            w_val = conn.execute("""
                SELECT 
                    SUM(
                        CASE
                            WHEN a.currency = 'CHF' THEN t.amount
                            ELSE t.amount * COALESCE(
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency AND er.date <= t.date ORDER BY er.date DESC LIMIT 1),
                                (SELECT rate FROM exchange_rates er WHERE er.currency = a.currency ORDER BY er.date ASC LIMIT 1),
                                1.0
                            )
                        END
                    )
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'transfer' AND t.account_id = ?
            """, [account_id]).fetchone()[0]
            withdrawals = float(w_val) if w_val is not None else 0.0
            
            return deposits - withdrawals

        except Exception as e:
            print(f"Error calculating historical cost basis: {e}")
            return 0.0
        finally:
            conn.close()

    def get_cashflow_data(self, start_date: str, end_date: str) -> dict:
        
        conn = self._get_connection()
        try:
            tx_query = """
                SELECT t.date, t.type, t.amount, a.currency, c.category, c.sub_category
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.type IN ('income', 'expense')
                  AND t.date >= ? AND t.date <= ?
                ORDER BY t.date ASC
            """
            transactions = conn.execute(
                tx_query, [start_date, end_date]).fetchall()

            all_rates = conn.execute(
                ).fetchall()

            rates_history = {}
            for r_date, r_curr, r_rate in all_rates:
                if r_curr not in rates_history:
                    rates_history[r_curr] = []
                rates_history[r_curr].append((str(r_date), float(r_rate)))

            import bisect

            def get_rate_at(date_str, currency):
                if currency == 'CHF':
                    return 1.0
                history = rates_history.get(currency)
                if not history:
                    return 1.0

                idx = bisect.bisect_right(history, (date_str, float('inf')))

                if idx > 0:
                    return history[idx-1][1]

                return history[0][1]

            monthly_data = {}

            for row in transactions:
                t_date_str = str(row[0])
                t_type = row[1]
                amount = float(row[2]) if row[2] else 0.0
                currency = row[3]
                category_name = row[4] if row[4] else "Uncategorized"
                sub_category_name = row[5] if row[5] else "General"

                try:
                    month_key = t_date_str[:7]
                except:
                    continue
                
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        : 0.0, 'expense': 0.0, 'invested': 0.0, 
                        : {'income': {}, 'expense': {}}
                    }

                rate = get_rate_at(t_date_str, currency)
                val_chf = amount * rate

                data_ptr = monthly_data[month_key]
                if t_type == 'income':
                    data_ptr['income'] += val_chf
                    details_ptr = data_ptr['details']['income']
                elif t_type == 'expense':
                    data_ptr['expense'] += val_chf
                    details_ptr = data_ptr['details']['expense']
                else:
                    continue

                if category_name not in details_ptr:
                    details_ptr[category_name] = {'total': 0.0, 'subs': {}}

                details_ptr[category_name]['total'] += val_chf

                existing_sub_val = details_ptr[category_name]['subs'].get(
                    sub_category_name, 0.0)
                details_ptr[category_name]['subs'][sub_category_name] = existing_sub_val + val_chf

            tf_query = """
                SELECT t.date, t.amount, t.to_amount, 
                       f.currency, f.is_investment,
                       to_acc.currency, to_acc.is_investment
                FROM transactions t
                JOIN accounts f ON t.account_id = f.id
                JOIN accounts to_acc ON t.to_account_id = to_acc.id
                WHERE t.type = 'transfer'
                  AND t.date >= ? AND t.date <= ?
            """
            transfers = conn.execute(tf_query, [start_date, end_date]).fetchall()

            for row in transfers:
                t_date_str = str(row[0])
                amount = float(row[1]) if row[1] else 0.0
                to_amount = float(row[2]) if row[2] else 0.0
                from_curr = row[3]
                from_is_inv = bool(row[4])
                to_curr = row[5]
                to_is_inv = bool(row[6])

                if from_is_inv == to_is_inv:
                    continue

                try:
                    month_key = t_date_str[:7]
                except:
                    continue

                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        : 0.0, 'expense': 0.0, 'invested': 0.0, 
                        : {'income': {}, 'expense': {}}
                    }

                if not from_is_inv and to_is_inv:
                    rate = get_rate_at(t_date_str, from_curr)
                    monthly_data[month_key]['invested'] += (amount * rate)
                
                elif from_is_inv and not to_is_inv:
                    rate = get_rate_at(t_date_str, to_curr)
                    monthly_data[month_key]['invested'] -= (to_amount * rate)

            return monthly_data

        except Exception as e:
            print(f"Error calculating cashflow: {e}")
            return {}
        finally:
            conn.close()