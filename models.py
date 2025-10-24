"""
Data models and database operations for the Budget Tracker.
"""
import sys
import os
import duckdb
from datetime import datetime


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
    def __init__(self, id: int, account: str, type: str, company: str = None, 
                 currency: str = 'USD', is_investment: bool = False):
        self.id = id
        self.account = account
        self.type = type
        self.company = company
        self.currency = currency
        self.is_investment = is_investment


class Category:
    def __init__(self, sub_category: str, category: str):
        self.sub_category = sub_category
        self.category = category


class BudgetApp:
    def __init__(self, db_path=None):
        if db_path is None:
            # Get the directory where the exe is running
            if getattr(sys, 'frozen', False):
                # Running as compiled exe
                application_path = os.path.dirname(sys.executable)
            else:
                # Running as script
                application_path = os.path.dirname(os.path.abspath(__file__))
            
            db_path = os.path.join(application_path, 'budget.duckdb')
        
        self.db_path = db_path
        self.init_database()

    def _get_connection(self):
        return duckdb.connect(self.db_path)

    def init_database(self):
        conn = self._get_connection()
        try:
            # Create accounts table
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
            
            # Create categories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    sub_category VARCHAR PRIMARY KEY,
                    category VARCHAR NOT NULL
                )
            """)
            

            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    date DATE NOT NULL,
                    type VARCHAR NOT NULL, -- 'income', 'expense', 'transfer'
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

            
            # Insert default data
            self._insert_default_data(conn)
            conn.commit()
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
    
    def _insert_default_data(self, conn):
        # Insert default accounts
        default_accounts = [
            (100, 'Cash', 'Cash', 'Cash', 'CHF', False),
            (110, 'Cash', 'Cash', 'Cash', 'EUR', False),
            (120, 'Cash', 'Cash', 'Cash', 'USD', False),
            (130, 'Cash', 'Cash', 'Cash', 'SGD', False),
            (140, 'Cash', 'Cash', 'Cash', 'MYR', False),
            (200, 'Post', 'Bank', 'Post', 'CHF', False),
            (201, 'Payment Account', 'Bank', 'Post', 'CHF', False),
            (202, 'Post Saving', 'Bank', 'Post', 'CHF', False),
            (203, 'WIR', 'Bank', 'Wir', 'CHF', False),
            (204, 'Zak', 'Bank', 'Cler', 'CHF', False),
            (205, 'E-Trading', 'Bank', 'Post', 'CHF', False),
            (206, 'Valiant', 'Bank', 'Valiant', 'CHF', False),
            (207, 'WIR Saving', 'Bank', 'Wir', 'CHF', False),
            (210, 'Post', 'Bank', 'Post', 'EUR', False),
            (215, 'E-Trading', 'Bank', 'Post', 'EUR', False),
            (220, 'Post', 'Bank', 'Post', 'USD', False),
            (225, 'E-Trading', 'Bank', 'Post', 'USD', False),
            (300, 'Yuh', 'Bank', 'Yuh', 'CHF', False),
            (310, 'Yuh', 'Bank', 'Yuh', 'EUR', False),
            (320, 'Yuh', 'Bank', 'Yuh', 'USD', False),
            (400, 'Certo', 'Credit', 'Cembra', 'CHF', False),
            (401, 'Reka', 'Bank', 'Reka', 'CHF', False),
            (402, 'BR Bauhandel', 'Credit', 'BR Bauhandel', 'CHF', False),
            (403, 'Wyne', 'Credit', 'Cash', 'CHF', False),
            (404, 'Cumulus', 'Bank', 'Cash', 'CHF', False),
            (500, 'NESN.SW', 'Share', 'Post', 'CHF', True),
            (501, 'CALN.SW', 'Share', 'Post', 'CHF', True),
            (502, 'UHRN.SW', 'Share', 'Post', 'CHF', True),
            (503, 'LOGN.SW', 'Share', 'Yuh', 'CHF', True),
            (504, 'ABBN.SW', 'Share', 'Yuh', 'CHF', True),
            (505, 'PGHN.SW', 'Share', 'Yuh', 'CHF', True),
            (506, 'STMN.SW', 'Share', 'Post', 'CHF', True),
            (511, 'PHIA.AS', 'Share', 'Yuh', 'EUR', True),
            (520, 'PM', 'Share', 'Yuh', 'USD', True),
            (521, 'MCD', 'Share', 'Yuh', 'USD', True),
            (522, 'SBUX', 'Share', 'Yuh', 'USD', True),
            (600, 'VWRL.SW', 'ETF', 'Post', 'CHF', True),
            (601, 'CHSPI.SW', 'ETF', 'Post', 'CHF', True),
            (602, 'Viac', 'Fonds', 'Viac', 'CHF', True),
            (610, 'CSSX5E.SW', 'ETF', 'Post', 'EUR', True),
            (611, 'ALAT.SW', 'ETF', 'Post', 'EUR', True),
            (620, 'EIMI.SW', 'ETF', 'Post', 'USD', True),
            (621, 'ICOM.L', 'ETF', 'Post', 'USD', True),
            (700, 'Viac 2', '3a', 'Viac', 'CHF', True),
            (701, 'Viac 1', '3a', 'Viac', 'CHF', True),
            (702, 'Viac 3', '3a', 'Viac', 'CHF', True),
            (703, 'Viac 4', '3a', 'Viac', 'CHF', True),
            (800, 'Mietkaution', 'Bank', 'Valiant', 'CHF', False),
            (830, 'POSB', 'Bank', 'POSB', 'SGD', False),
            (900, 'StartingBalance', 'Other', 'Other', 'CHF', False)
        ]
        
        for account in default_accounts:
            conn.execute("""
                INSERT OR IGNORE INTO accounts (id, account, type, company, currency, is_investment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, account)
        
        # Insert default categories
        default_categories = [
            ('Activities', 'Activities'),
            ('Beauty', 'Health'),
            ('Broker Fees', 'Investment'),
            ('Bycicle', 'Transport'),
            ('Car', 'Transport'),
            ('Clothing', 'Living'),
            ('Dentist', 'Health'),
            ('Dining Out', 'Food'),
            ('Doctor', 'Health'),
            ('Education', 'Pei Pei'),
            ('Fees', 'Tax'),
            ('Flights', 'Transport'),
            ('Furnishing', 'Living'),
            ('Groceries', 'Food'),
            ('Health Insurance', 'Insurance'),
            ('Hygiene', 'Health'),
            ('Optician', 'Health'),
            ('Other Insurance', 'Insurance'),
            ('Pet', 'Activities'),
            ('Pharmacy', 'Health'),
            ('Pocket Money', 'Pei Pei'),
            ('Public Transport', 'Transport'),
            ('Rent', 'Living'),
            ('Tax', 'Tax'),
            ('Utilities', 'Living'),
            ('HDB', 'Living'),
            ('Massage', 'Health'),
            ('Dividend', 'Investment'),
            ('Salary', 'Income'),
            ('Tutti', 'Income'),
            ('Cash Back', 'Income'),
            ('Investment Return', 'Investment'),
            ('Interest', 'Income'),
            ('Gifts', 'Activities')
        ]
        
        for category in default_categories:
            conn.execute("""
                INSERT OR IGNORE INTO categories (sub_category, category)
                VALUES (?, ?)
            """, category)

    def _get_next_id(self, table_name: str) -> int:
        conn = self._get_connection()
        try:
            result = conn.execute(f"SELECT MAX(id) FROM {table_name}").fetchone()
            return 1 if result[0] is None else result[0] + 1
        finally:
            conn.close()

    # Account methods
    def get_all_accounts(self):
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT id, account, type, company, currency, is_investment
                FROM accounts 
                ORDER BY type, account
            """).fetchall()
            return [Account(*row) for row in result]
        except Exception as e:
            print(f"Error getting accounts: {e}")
            return []
        finally:
            conn.close()

    def add_account(self, account: str, type: str, company: str = None, 
                currency: str = 'CHF', is_investment: bool = False):
        # Check if account with same name and currency already exists
        existing_account = self.get_account_by_name_currency(account, currency)
        if existing_account:
            print(f"Account {account} {currency} already exists with ID {existing_account.id}")
            return False  # Prevent duplicate accounts
        
        account_id = self._get_next_id('accounts')
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO accounts (id, account, type, company, currency, is_investment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [account_id, account, type, company, currency, is_investment])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding account: {e}")
            return False
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

    def delete_account(self, account_id: int):
        conn = self._get_connection()
        try:
            # Check if account is used in transactions
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

    # Category methods
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
            # Check if category is used in transactions
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


    # Transaction methods
    def add_income(self, date: str, amount: float, account_id: int, 
                   payee: str = "", sub_category: str = "", 
                   notes: str = "", invest_account_id: int = None):
        """Add an income transaction"""
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
        """Add an expense transaction"""
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
        """Add a transfer transaction"""
        if to_amount is None:
            to_amount = from_amount
            
        trans_id = self._get_next_id('transactions')
        conn = self._get_connection()
        try:
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
            # Build dynamic update query based on provided kwargs
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
        """Get balance summary for all accounts"""
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
                    if trans.account_id:  # from_account_id
                        balances[trans.account_id]['balance'] -= float(trans.amount or 0)
                    if trans.to_account_id:
                        balances[trans.to_account_id]['balance'] += float(trans.to_amount or 0)
            
            return balances
        finally:
            conn.close()


    def get_account_currency(self, account_id):
        """Get the currency for a specific account"""
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT currency FROM accounts WHERE id = ?
            """, [account_id]).fetchone()
            return result[0] if result else 'USD'
        finally:
            conn.close()


    def get_account_by_name_currency(self, account_name: str, currency: str):
        """Get account by name and currency to ensure uniqueness."""
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