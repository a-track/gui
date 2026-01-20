import os
import duckdb
import datetime
import sys
import re

def export_to_access(duckdb_path, access_db_path, sql_folder_path, progress_callback=None):
    """
    Export only api_ tables from DuckDB to Microsoft Access database.
    1. Executes SQL scripts from sql_folder_path in DuckDB to generate tables.
    2. Exports resulting api_ tables to Access.
    
    Args:
        duckdb_path (str): Path to the DuckDB database.
        access_db_path (str): Path to the target Access database (.accdb).
        sql_folder_path (str): Path to the folder containing SQL scripts.
        progress_callback (func): Optional callback for status updates (msg).
    """
    
    try:
        import pyodbc
    except ImportError:
        return False, "Required module 'pyodbc' is not installed. Please install it to use this feature."

    def log(msg):
        print(msg)
        if progress_callback:
            progress_callback(msg)

    try:
        duckdb_path = os.path.abspath(duckdb_path)
        access_db_path = os.path.abspath(access_db_path)
        sql_folder_path = os.path.abspath(sql_folder_path)

        log(f"DuckDB path: {duckdb_path}")
        log(f"Access DB path: {access_db_path}")
        log(f"SQL folder: {sql_folder_path}")
        
        os.makedirs(os.path.dirname(access_db_path), exist_ok=True)
        
        if not os.path.exists(access_db_path):
            log(f"Creating new Access database at: {access_db_path}")
            created = False
            
            try:
                import win32com.client
                catalog = win32com.client.Dispatch('ADOX.Catalog')
                catalog.Create(f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={access_db_path};")
                log("Created new Access database file using ADOX.")
                created = True
            except ImportError:
                log("ERROR: 'pywin32' module not installed. Cannot create Access DB automatically.")
            except Exception as e:
                log(f"WARNING: ADOX Creation failed: {e}")
                log("Attempting legacy provider (Jet.OLEDB.4.0)...")
                try: 
                    import win32com.client
                    catalog = win32com.client.Dispatch('ADOX.Catalog')
                    catalog.Create(f"Provider=Microsoft.Jet.OLEDB.4.0;Data Source={access_db_path};")
                    log("Created new Access database file using Jet provider.")
                    created = True
                except Exception as e2:
                    log(f"ERROR: Could not create Access database: {e2}")
            
            if not created:
                return False, "Could not create new Access database file. Please create an empty .accdb file manually or install 'pywin32'."
        else:
             log("Access database file already exists.")
        
        log("\nConnecting to DuckDB...")
        with duckdb.connect(duckdb_path) as duck_conn:
            
            log("Executing SQL scripts...")
            if os.path.exists(sql_folder_path):
                sql_files = [f for f in os.listdir(sql_folder_path) if f.endswith('.sql')]
                
                pending_files = sql_files.copy()
                max_retries = 3
                
                for attempt in range(max_retries):
                    if not pending_files:
                        break
                        
                    log(f"  > Pass {attempt + 1}/{max_retries}, pending: {len(pending_files)}")
                    next_pending = []
                    
                    for sql_file in pending_files:
                        file_path = os.path.join(sql_folder_path, sql_file)
                        table_name = os.path.splitext(sql_file)[0]
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                sql_content = f.read()
                            
                            sql_content = re.sub(r'budget\.(\w+)', r'\1', sql_content)
                            
                            duck_conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS {sql_content}")
                            log(f"    - created {table_name}")
                            
                        except Exception as e:
                            if "Catalog Error" in str(e) or "does not exist" in str(e):
                                next_pending.append(sql_file)
                            else:
                                log(f"    ERROR executing {sql_file}: {e}")
                    
                    if len(next_pending) == len(pending_files):
                         log("  WARNING: No progress made in this pass. Stopping execution loop.")
                         break
                         
                    pending_files = next_pending
                
                if pending_files:
                    log(f"  WARNING: Failed to execute the following scripts after {max_retries} attempts: {pending_files}")
            else:
                log(f"WARNING: SQL folder not found at {sql_folder_path}")

            conn_str = (
                r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
                f"DBQ={access_db_path};"
            )
            
            try:
                log("\nConnecting to Access database...")
                access_conn = pyodbc.connect(conn_str, autocommit=False)
                access_cursor = access_conn.cursor()
                log("Connected.")
                
                tables = duck_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'api_%'"
                ).fetchall()
                table_names = [t[0] for t in tables]
                
                if not table_names:
                    log("No 'api_' tables found to export.")
                    return True, "No 'api_' tables found to export."
                
                log(f"Found tables to export: {', '.join(table_names)}")
                
                csv_exports = []
                
                for table_name in table_names:
                    table_exists = False
                    try:
                        access_cursor.execute(f"SELECT 1 FROM [{table_name}] WHERE 1=0")
                        table_exists = True
                    except:
                        pass

                    if table_exists:
                        try:
                            access_cursor.execute(f"DROP TABLE [{table_name}]")
                            log(f"Dropped existing table: {table_name}")
                            access_conn.commit()
                        except Exception as e:
                            log(f"ERROR: Could not drop table [{table_name}]. It might be open in another program (e.g. Power BI or Access). Error: {e}")
                            raise e 
                    
                    rows = duck_conn.execute(f"SELECT * FROM {table_name}").fetchall()
                    
                    columns_info = duck_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                    
                    if len(rows) >= 0:
                        log(f"Exporting {table_name} ({len(rows)} rows)...")
                        
                        create_cols = []
                        db_cols = []
                        
                        for col_info in columns_info:
                            col_name = col_info[1]
                            col_type = col_info[2].upper()
                            db_cols.append(col_name)
                            
                            if 'INT' in col_type:
                                acc_type = "INTEGER"
                            elif 'FLOAT' in col_type or 'DOUBLE' in col_type or 'DECIMAL' in col_type:
                                acc_type = "DOUBLE"
                            elif 'TIMESTAMP' in col_type:
                                acc_type = "DATETIME" 
                            elif 'DATE' in col_type:
                                acc_type = "DATETIME"
                            elif 'BOOL' in col_type:
                                acc_type = "BIT"
                            else:
                                acc_type = "Memo" if 'VARCHAR' in col_type and '255' not in col_type else "TEXT"
                            
                            create_cols.append(f"[{col_name}] {acc_type}")
                            
                        create_sql = f"CREATE TABLE [{table_name}] ({', '.join(create_cols)})"
                        access_cursor.execute(create_sql)
                        access_conn.commit()
                        
                        try:
                            import tempfile
                            temp_dir = tempfile.gettempdir()
                            csv_filename = f"{table_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
                            csv_path = os.path.join(temp_dir, csv_filename)
                            csv_path = os.path.normpath(csv_path)
                            csv_path_sql = csv_path.replace('\\', '/')
                            
                            duck_conn.execute(f"COPY (SELECT * FROM {table_name}) TO '{csv_path_sql}' (FORMAT CSV, HEADER, DATEFORMAT '%Y-%m-%d', TIMESTAMPFORMAT '%Y-%m-%d %H:%M:%S')")
                            
                            csv_exports.append({
                                'table': table_name,
                                'csv': csv_path,
                                'rows': rows,
                                'cols': db_cols
                            })
                            
                        except Exception as e:
                            log(f"  ERROR generating CSV for {table_name}: {e}")
                            csv_exports.append({
                                'table': table_name,
                                'rows': rows,
                                'cols': db_cols,
                                'error': str(e)
                            })

                access_cursor.close()
                access_conn.close()

                log("\nStarting Batch Import into Access...")
                
                com_success = False
                try:
                    import win32com.client
                    acc_app = win32com.client.Dispatch("Access.Application")
                    acc_app.OpenCurrentDatabase(access_db_path)
                    
                    for item in csv_exports:
                        if 'csv' in item:
                            t_name = item['table']
                            c_path = item['csv']
                            log(f"  - Importing {t_name} via Direct Access...")
                            acc_app.DoCmd.TransferText(0, "", t_name, c_path, True)
                            try:
                                os.remove(c_path)
                            except:
                                pass
                            item['imported'] = True
                            
                    acc_app.CloseCurrentDatabase()
                    acc_app.Quit()
                    acc_app = None
                    com_success = True
                    log("Batch import completed successfully.")

                except Exception as e:
                    log(f"Batch COM Import failed: {e}")
                    log("Switching to fallback method...")

                needs_fallback = any(not item.get('imported', False) for item in csv_exports)
                
                if needs_fallback:
                    log("\nPerforming fallback inserts for failed tables...")
                    access_conn = pyodbc.connect(conn_str, autocommit=False)
                    access_cursor = access_conn.cursor()
                    
                    for item in csv_exports:
                        if not item.get('imported', False):
                            t_name = item['table']
                            log(f"  - Fallback insert for {t_name}...")
                            
                            rows = item.get('rows', [])
                            db_cols = item.get('cols', [])
                            
                            if len(rows) > 0:
                                placeholders = ', '.join(['?' for _ in db_cols])
                                col_names_safe = ', '.join([f"[{c}]" for c in db_cols])
                                insert_sql = f"INSERT INTO [{t_name}] ({col_names_safe}) VALUES ({placeholders})"
                                chunk_size = 20000
                                for i in range(0, len(rows), chunk_size):
                                    chunk = rows[i:i+chunk_size]
                                    access_cursor.executemany(insert_sql, chunk)
                                access_conn.commit()
                                log(f"    - committed {t_name}")
                            
                            if 'csv' in item and os.path.exists(item['csv']):
                                try:
                                    os.remove(item['csv'])
                                except:
                                    pass
                    
                    access_cursor.close()
                    access_conn.close()

                log("\nExport completed successfully.")
                return True, "Export completed successfully."

            except pyodbc.Error as e:
                log(f"\nAccess ODBC Error: {e}")
                return False, f"Access ODBC Error: {e}"

                
    except Exception as e:
        log(f"\nGeneral Error: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

if __name__ == "__main__":
    try:
        import config
        print("Running in test mode...")
        export_to_access(config.get_duckdb_path(), config.get_access_db_path(), os.path.join(os.path.dirname(__file__), '..', 'sql'))
    except ImportError:
        print("Config not found, cannot run test.")