import sys
import os
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

        try:
            self._anchor_conn = duckdb.connect(self.db_path)
        except Exception as e:
            print(f"Failed to acquire DB lock: {e}")
            self._anchor_conn = None

        self.init_database()
        self.update_database_schema()
        self.get_or_create_starting_balance_account()

    def close(self):
        """Explicitly close the anchor connection to release the file lock."""
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
                        amount DECIMAL(10, 2),
                        account_id INTEGER,
                        category_id INTEGER,
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
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                """)
            except Exception as e:

                pass

            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS budgets (
                        category_id INTEGER PRIMARY KEY,
                        budget_amount DECIMAL(10, 2) NOT NULL,
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

    def add_exchange_rates_bulk(self, rates_data: list):
        """
        Bulk add exchange rates efficiently.
        rates_data: list of tuples (date, currency, rate)
        """
        conn = self._get_connection()
        try:

            new_id_res = conn.execute(
                "SELECT COALESCE(MAX(id), 0) FROM exchange_rates").fetchone()
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
        """
        Bulk delete exchange rates.
        rates_data: list of tuples (date, currency)
        """
        if not rates_data:
            return True

        conn = self._get_connection()
        try:
            for date, currency in rates_data:
                conn.execute(
                    "DELETE FROM exchange_rates WHERE date = ? AND currency = ?", (date, currency))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting exchange rates: {e}")
            return False
        finally:
            conn.close()

    def get_exchange_rate_for_date(self, currency: str, target_date: str = None):
        """
        Get the effective exchange rate for a currency at a specific date.
        SCD2 logic: valid from date until next record.
        """
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
        """
        Get a dictionary of {currency: rate} for all known currencies at a specific date.
        Efficient bulk fetch to avoid multiple DB connections.
        Ensures valid rates are taken up to the very end of the target_date (SCD2).
        """
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
                "SELECT DISTINCT currency FROM exchange_rates").fetchall()
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
        """
        Fetch all exchange rates raw data for Matrix UI construction.
        Returns: list of (date_str, currency, rate) sorted by date DESC.
        """
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
                    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = [t[0] for t in tables]

                if 'categories' not in table_names and 'categories_new' in table_names:
                    print("Recovering categories table...")
                    conn.execute(
                        "ALTER TABLE categories_new RENAME TO categories")

                if 'transactions' not in table_names and 'transactions_new' in table_names:
                    print("Recovering transactions table...")
                    conn.execute(
                        "ALTER TABLE transactions_new RENAME TO transactions")

                if 'budgets' not in table_names and 'budgets_new_schema' in table_names:
                    print("Recovering budgets table...")
                    conn.execute(
                        "ALTER TABLE budgets_new_schema RENAME TO budgets")

                if 'budgets' not in table_names and 'budgets_new' in table_names:
                    print("Recovering budgets table (from budgets_new)...")
                    conn.execute("ALTER TABLE budgets_new RENAME TO budgets")

            except Exception as e:
                print(f"Recovery check failed: {e}")

            conn.execute("DROP TABLE IF EXISTS budgets_new_schema")
            conn.execute("DROP TABLE IF EXISTS transactions_new")
            conn.execute("DROP TABLE IF EXISTS categories_new")

            conn.execute(
                "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS show_in_balance BOOLEAN DEFAULT TRUE")
            conn.execute(
                "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
            conn.execute(
                "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS valuation_strategy VARCHAR DEFAULT NULL")
            conn.execute(
                "ALTER TABLE categories ADD COLUMN IF NOT EXISTS category_type VARCHAR DEFAULT 'Expense'")

            columns_result = conn.execute(
                "PRAGMA table_info(categories)").fetchall()
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
                        amount DECIMAL(10, 2),
                        account_id INTEGER,
                        category_id INTEGER,
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
                        budget_amount DECIMAL(10, 2) NOT NULL,
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
                    "INSERT INTO categories SELECT * FROM categories_new")

                conn.execute("""
                    CREATE TABLE budgets (
                        category_id INTEGER PRIMARY KEY,
                        budget_amount DECIMAL(10, 2) NOT NULL,
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                """)
                conn.execute(
                    "INSERT INTO budgets SELECT * FROM budgets_new_schema")

                conn.execute("""
                    CREATE TABLE transactions (
                        id INTEGER PRIMARY KEY,
                        date DATE NOT NULL,
                        type VARCHAR NOT NULL,
                        amount DECIMAL(10, 2),
                        account_id INTEGER,
                        category_id INTEGER,
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
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                """)
                conn.execute(
                    "INSERT INTO transactions SELECT * FROM transactions_new")

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

    def get_all_accounts(self):
        conn = self._get_connection()
        try:

            result = conn.execute("""
                SELECT id, account, type, company, currency, show_in_balance, is_active, is_investment, valuation_strategy
                FROM accounts
                ORDER BY id
            """).fetchall()

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
                "UPDATE transactions SET category_id = ? WHERE category_id = ?", (next_id, cat_id))

            budget_row = conn.execute(
                "SELECT budget_amount FROM budgets WHERE category_id = ?", [cat_id]).fetchone()
            if budget_row:
                amt = budget_row[0]
                conn.execute(
                    "INSERT INTO budgets (category_id, budget_amount) VALUES (?, ?)", (next_id, amt))
                conn.execute(
                    "DELETE FROM budgets WHERE category_id = ?", [cat_id])

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

    def get_balance_summary(self):
        conn = self._get_connection()
        try:
            balances = {}
            accounts = self.get_all_accounts()

            for account in accounts:
                balances[account.id] = {
                    'account_name': account.account,
                    'balance': 0.0,
                    'type': account.type,
                    'count': 0,
                    'is_investment': getattr(account, 'is_investment', False)
                }

            incomes = conn.execute("""
                SELECT account_id, SUM(amount)
                FROM transactions
                WHERE type = 'income' AND account_id IS NOT NULL
                GROUP BY account_id
            """).fetchall()

            for acc_id, amount in incomes:
                if acc_id in balances:
                    balances[acc_id]['balance'] += float(amount)

            expenses = conn.execute("""
                SELECT account_id, SUM(amount)
                FROM transactions
                WHERE type = 'expense' AND account_id IS NOT NULL
                GROUP BY account_id
            """).fetchall()

            for acc_id, amount in expenses:
                if acc_id in balances:
                    balances[acc_id]['balance'] -= float(amount)

            transfers_out = conn.execute("""
                SELECT account_id, SUM(amount)
                FROM transactions
                WHERE type = 'transfer' AND account_id IS NOT NULL
                GROUP BY account_id
            """).fetchall()

            for acc_id, amount in transfers_out:
                if acc_id in balances:
                    balances[acc_id]['balance'] -= float(amount)

            transfers_in = conn.execute("""
                SELECT to_account_id, SUM(to_amount)
                FROM transactions
                WHERE type = 'transfer' AND to_account_id IS NOT NULL
                GROUP BY to_account_id
            """).fetchall()

            for acc_id, amount in transfers_in:
                if acc_id in balances:
                    balances[acc_id]['balance'] += float(amount)

            qty_transfer_in = conn.execute("""
                SELECT to_account_id, SUM(qty)
                FROM transactions
                WHERE type = 'transfer' AND to_account_id IS NOT NULL AND qty IS NOT NULL
                GROUP BY to_account_id
            """).fetchall()

            for acc_id, q in qty_transfer_in:
                if acc_id in balances:
                    balances[acc_id]['qty'] = balances[acc_id].get(
                        'qty', 0.0) + float(q)

            qty_income = conn.execute("""
                SELECT account_id, SUM(qty)
                FROM transactions
                WHERE type = 'income' AND account_id IS NOT NULL AND qty IS NOT NULL
                GROUP BY account_id
            """).fetchall()
            for acc_id, q in qty_income:
                if acc_id in balances:
                    balances[acc_id]['qty'] = balances[acc_id].get(
                        'qty', 0.0) + float(q)

            qty_transfer_out = conn.execute("""
                SELECT account_id, SUM(qty)
                FROM transactions
                WHERE type = 'transfer' AND account_id IS NOT NULL AND qty IS NOT NULL
                GROUP BY account_id
            """).fetchall()
            for acc_id, q in qty_transfer_out:
                if acc_id in balances and balances[acc_id]['is_investment']:
                    balances[acc_id]['qty'] = balances[acc_id].get(
                        'qty', 0.0) - float(q)

            qty_expense = conn.execute("""
                SELECT account_id, SUM(qty)
                FROM transactions
                WHERE type = 'expense' AND account_id IS NOT NULL AND qty IS NOT NULL
                GROUP BY account_id
            """).fetchall()
            for acc_id, q in qty_expense:
                if acc_id in balances and balances[acc_id]['is_investment']:
                    balances[acc_id]['qty'] = balances[acc_id].get(
                        'qty', 0.0) - float(q)

            counts_1 = conn.execute(
                "SELECT account_id, COUNT(*) FROM transactions WHERE account_id IS NOT NULL GROUP BY account_id").fetchall()
            for acc_id, count in counts_1:
                if acc_id in balances:
                    balances[acc_id]['count'] += count

            counts_2 = conn.execute(
                "SELECT to_account_id, COUNT(*) FROM transactions WHERE to_account_id IS NOT NULL GROUP BY to_account_id").fetchall()
            for acc_id, count in counts_2:
                if acc_id in balances:
                    balances[acc_id]['count'] += count

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
        """Helper to get account ID from 'Name Currency' string format"""
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
                'accounts': account_counts,
                'categories': category_counts,
                'payees': payee_counts
            }
        except Exception as e:
            print(f"Error getting transaction counts: {e}")
            return {'accounts': {}, 'categories': {}, 'payees': {}}
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
                              'amount': (row[2] or 0.0)} for row in result_sub]

            return {'main': main_breakdown, 'sub': sub_breakdown}
        except Exception as e:
            print(f"Error getting expenses breakdown: {e}")
            return {'main': {}, 'sub': []}
        finally:
            conn.close()

    def get_expenses_breakdown(self, year, month, category_ids=None):
        """
        Get hierarchical expenses breakdown for a specific month.
        Returns: { 'Category Name': {'total': float, 'subs': {'Sub Name': float}} }
        """
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
        """
        Get monthly total expenses for the trailing 12 months ending at end_year-end_month.
        Returns: [ {'month_str': 'Jan 2024', 'amount': 100.0, 'year': 2024, 'month': 1}, ... ]
        """
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
                           "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

            for y, m in months_list:
                amt = data_map.get((y, m), 0.0)
                label = f"{month_names[m]} {y}"
                trend_data.append({
                    'month_str': label,
                    'amount': amt,
                    'year': y,
                    'month': m
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
        """
        Calculate total dividends (income attributed to investment account) per investment account.
        Returns: { invest_account_id: total_amount_in_chf }
        """
        conn = self._get_connection()
        try:

            rates = self.get_exchange_rates_map()

            result = conn.execute("""
                SELECT t.invest_account_id, t.amount, a.currency, c.sub_category, strftime('%Y', t.date) as year
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'income' AND t.invest_account_id IS NOT NULL
            """).fetchall()

            income_summary = {}

            for invest_acc_id, amount, currency, category_name, year in result:
                if invest_acc_id not in income_summary:
                    income_summary[invest_acc_id] = {'total': 0.0, 'years': {}}

                rate = rates.get(currency, 1.0)

                if amount:
                    val_chf = float(amount) * rate
                    income_summary[invest_acc_id]['total'] += val_chf

                    if year not in income_summary[invest_acc_id]['years']:
                        income_summary[invest_acc_id]['years'][year] = {
                            'total': 0.0, 'breakdown': {}}

                    year_data = income_summary[invest_acc_id]['years'][year]
                    year_data['total'] += val_chf

                    cat_key = category_name if category_name else "Uncategorized"
                    year_data['breakdown'][cat_key] = year_data['breakdown'].get(
                        cat_key, 0.0) + val_chf

            return income_summary

        except Exception as e:
            print(f"Error calculating accumulated dividends: {e}")
            return {}

    def get_accumulated_expenses(self):
        """
        Calculate total expenses (fees/taxes attributed to investment account) per investment account.
        Returns: { invest_account_id: total_amount_in_chf }
        """
        conn = self._get_connection()
        try:

            rates = self.get_exchange_rates_map()

            result = conn.execute("""
                SELECT t.invest_account_id, t.amount, a.currency, c.sub_category, strftime('%Y', t.date) as year
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense' AND t.invest_account_id IS NOT NULL
            """).fetchall()

            expense_summary = {}

            for invest_acc_id, amount, currency, category_name, year in result:
                if invest_acc_id not in expense_summary:
                    expense_summary[invest_acc_id] = {
                        'total': 0.0, 'years': {}}

                rate = rates.get(currency, 1.0)

                if amount:
                    val_chf = float(amount) * rate
                    expense_summary[invest_acc_id]['total'] += val_chf

                    if year not in expense_summary[invest_acc_id]['years']:
                        expense_summary[invest_acc_id]['years'][year] = {
                            'total': 0.0, 'breakdown': {}}

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
        """Add or update a monthly budget for a subcategory"""
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

    def get_all_budgets(self):
        """Get all monthly budgets"""
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT c.sub_category, b.budget_amount
                FROM budgets b
                JOIN categories c ON b.category_id = c.id
                ORDER BY c.sub_category
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
                        trans_date = datetime.datetime.strptime(
                            trans_date, '%Y-%m-%d').date()

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

    def get_investment_history_matrix_data(self):
        """
        Fetch all investment valuations raw data for Matrix UI construction.
        Returns: list of (date_str, account_id, value) sorted by date DESC.
        """
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
        """
        Bulk add investment valuations.
        valuations_data: list of tuples (date, account_id, value)
        """
        conn = self._get_connection()
        try:

            new_id_res = conn.execute(
                "SELECT COALESCE(MAX(id), 0) FROM investment_valuations").fetchone()
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
        """
        Bulk delete investment valuations.
        valuations_data: list of tuples (date, account_id)
        """
        if not valuations_data:
            return True

        conn = self._get_connection()
        try:
            for date, account_id in valuations_data:
                conn.execute(
                    "DELETE FROM investment_valuations WHERE date = ? AND account_id = ?", (date, account_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting investment valuations: {e}")
            return False
        finally:
            conn.close()

    def get_investment_valuation_for_date(self, account_id: int, target_date: str = None) -> float:
        """
        Get the effective valuation for an account at a specific date.
        Uses SCD2-like logic: valid from date until next record.
        Ensures strict End-Of-Day inclusion.
        """
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
        """Get all subcategories grouped by category"""
        categories = self.get_all_categories()
        result = {}
        for category in categories:
            if category.category not in result:
                result[category.category] = []
            result[category.category].append(category.sub_category)
        return result

    def get_available_years(self):
        """Get list of years that have transactions"""
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
        """
        Calculate the total net worth (of show_in_balance accounts)
        at the end of each month for the given year.
        Returns: {month_int: total_balance_float}
        """
        conn = self._get_connection()
        try:

            accounts = conn.execute("""
                SELECT id, currency, is_investment, valuation_strategy, account
                FROM accounts
                WHERE show_in_balance = TRUE AND id != 0
            """).fetchall()

            if not accounts:
                return {m: 0.0 for m in range(1, 13)}

            account_map = {}
            for row in accounts:
                account_map[row[0]] = {
                    'currency': row[1],
                    'is_invest': bool(row[2]) if row[2] else False,
                    'strategy': row[3],
                    'name': row[4],
                    'balance': 0.0,
                    'qty': 0.0
                }

            end_of_year = f"{year}-12-31"

            all_tx = conn.execute("""
                SELECT
                    date, type, amount, account_id,
                    to_account_id, to_amount,
                    qty, invest_account_id
                FROM transactions
                WHERE date <= ?
                ORDER BY date ASC
            """, [end_of_year]).fetchall()

            monthly_data = {}
            current_tx_idx = 0
            num_tx = len(all_tx)

            for month in range(1, 13):

                if month == 12:
                    current_month_end_date = date(year, 12, 31)
                    next_bound = date(year + 1, 1, 1)
                else:
                    next_bound = date(year, month + 1, 1)
                    current_month_end_date = next_bound - timedelta(days=1)

                next_bound_str = next_bound.strftime('%Y-%m-%d')

                while current_tx_idx < num_tx:
                    row = all_tx[current_tx_idx]
                    t_date = row[0]
                    t_date_str = str(t_date)

                    if t_date_str >= next_bound_str:
                        break

                    t_type = row[1]
                    amount = float(row[2]) if row[2] else 0.0
                    acc_id = row[3]
                    to_acc_id = row[4]
                    to_amount = float(row[5]) if row[5] else 0.0
                    qty = float(row[6]) if row[6] else 0.0

                    if t_type == 'income':
                        if acc_id in account_map:
                            account_map[acc_id]['balance'] += amount
                            if qty:
                                account_map[acc_id]['qty'] += qty

                    elif t_type == 'expense':
                        if acc_id in account_map:
                            account_map[acc_id]['balance'] -= amount
                            if qty and account_map[acc_id]['is_invest']:
                                account_map[acc_id]['qty'] -= qty

                    elif t_type == 'transfer':
                        if acc_id in account_map:
                            account_map[acc_id]['balance'] -= amount
                            if qty and account_map[acc_id]['is_invest']:
                                account_map[acc_id]['qty'] -= qty

                        if to_acc_id in account_map:
                            account_map[to_acc_id]['balance'] += to_amount
                            if qty:
                                account_map[to_acc_id]['qty'] += qty

                    current_tx_idx += 1

                month_total_chf = 0.0

                curr_month_end_str = current_month_end_date.strftime(
                    '%Y-%m-%d')

                rates_map = self.get_exchange_rates_map(curr_month_end_str)

                for aid, adata in account_map.items():
                    currency = adata['currency']
                    market_val = adata['balance']

                    if adata['is_invest']:

                        if adata['strategy'] == 'Price/Qty':
                            price = self.get_investment_valuation_for_date(
                                aid, curr_month_end_str)
                            market_val = adata['qty'] * price
                        else:

                            val = self.get_investment_valuation_for_date(
                                aid, curr_month_end_str)
                            if val > 0:
                                market_val = val

                    rate = rates_map.get(currency, 1.0)
                    month_total_chf += (market_val * rate)

                monthly_data[month] = month_total_chf

            return monthly_data

        except Exception as e:
            print(f"Error calculating monthly balances: {e}")
            import traceback
            traceback.print_exc()
            return {m: 0.0 for m in range(1, 13)}
        finally:
            conn.close()

    def get_monthly_cashflow(self, year: int) -> dict:
        """
        Calculate total monthly cashflow (Income vs Expenses) in CHF.
        Returns {
            month_int: {
                'income': float,
                'expense': float,
                'details': {
                    'income': {
                        'CategoryName': {'total': float, 'subs': {'SubCat': float, ...}}
                    },
                    'expense': { ... }
                }
            }
        }
        """
        conn = self._get_connection()
        try:

            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

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
                "SELECT date, currency, rate FROM exchange_rates ORDER BY date ASC").fetchall()

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

            monthly_data = {m: {'income': 0.0, 'expense': 0.0, 'details': {
                'income': {}, 'expense': {}}} for m in range(1, 13)}

            for row in transactions:
                t_date_str = str(row[0])
                t_type = row[1]
                amount = float(row[2]) if row[2] else 0.0
                currency = row[3]
                category_name = row[4] if row[4] else "Uncategorized"
                sub_category_name = row[5] if row[5] else "General"

                try:
                    month = int(t_date_str.split('-')[1])
                except:
                    continue

                rate = get_rate_at(t_date_str, currency)
                val_chf = amount * rate

                if t_type == 'income':
                    data_ptr = monthly_data[month]
                    data_ptr['income'] += val_chf
                    details_ptr = data_ptr['details']['income']
                elif t_type == 'expense':
                    data_ptr = monthly_data[month]
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

            return monthly_data

        finally:
            conn.close()
