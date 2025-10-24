"""
Excel import/export functionality for transactions.
"""
import pandas as pd
from datetime import datetime
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from models import BudgetApp


class ExcelHandler:
    def __init__(self, budget_app: BudgetApp):
        self.budget_app = budget_app
    
    def export_to_excel(self, parent_window):
        """Export all transactions to Excel file with table formatting."""
        try:
            # Get file path from user
            file_path, _ = QFileDialog.getSaveFileName(
                parent_window,
                "Export Transactions to Excel",
                f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return False, "Export cancelled"
            
            # Get all transactions
            transactions = self.budget_app.get_all_transactions()
            accounts = self.budget_app.get_all_accounts()
            
            # Create account ID to name mapping
            account_map = {acc.id: f"{acc.account} {acc.currency}" for acc in accounts}
            
            # Prepare data for Excel
            data = []
            for trans in transactions:
                row = {
                    'ID': trans.id,
                    'Date': trans.date,
                    'Type': trans.type,
                    'Sub Category': trans.sub_category or '',
                    'Amount': float(trans.amount or 0),
                    'Account': account_map.get(trans.account_id, ''),
                    'Account ID': trans.account_id or '',
                    'Payee': trans.payee or '',
                    'Notes': trans.notes or '',
                    'Investment Account': account_map.get(trans.invest_account_id, ''),
                    'Investment Account ID': trans.invest_account_id or '',
                    'Quantity': float(trans.qty or 0),
                    'To Account': account_map.get(trans.to_account_id, ''),
                    'To Account ID': trans.to_account_id or '',
                    'To Amount': float(trans.to_amount or 0),
                    'Confirmed': 'Yes' if trans.confirmed else 'No'
                }
                data.append(row)
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Reorder columns to match your preferred order
            column_order = [
                'ID', 'Date', 'Type', 'Sub Category', 'Amount', 'Account', 
                'Payee', 'Notes', 'Investment Account', 'Quantity', 
                'To Account', 'To Amount', 'Confirmed'
            ]
            df = df[column_order]
            
            # Export to Excel with table formatting
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Transactions')
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Transactions']
                
                # Create a table (Excel structured reference)
                from openpyxl.worksheet.table import Table, TableStyleInfo
                
                # Define the table range
                max_row = len(df) + 1  # +1 for header
                max_col = len(column_order)
                table_range = f"A1:{chr(64 + max_col)}{max_row}"
                
                # Create table
                table = Table(displayName="TransactionsTable", ref=table_range)
                
                # Add a default style with striped rows and banded columns
                style = TableStyleInfo(
                    name="TableStyleMedium9",
                    showFirstColumn=False,
                    showLastColumn=False,
                    showRowStripes=True,
                    showColumnStripes=False
                )
                table.tableStyleInfo = style
                
                # Add the table to the worksheet
                worksheet.add_table(table)
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return True, f"Successfully exported {len(transactions)} transactions to {os.path.basename(file_path)}"
            
        except Exception as e:
            return False, f"Error exporting to Excel: {str(e)}"
    
    def _parse_account_name_currency(self, account_display_name):
        """Parse account display name into name and currency."""
        # Default values
        account_name = account_display_name
        currency = "CHF"  # Default currency
        
        # Try to extract currency from the end (common pattern: "AccountName Currency")
        parts = account_display_name.strip().split()
        if len(parts) >= 2:
            # Check if last part is a currency code (3 uppercase letters)
            last_part = parts[-1].upper()
            if len(last_part) == 3 and last_part.isalpha():
                currency = last_part
                account_name = ' '.join(parts[:-1])
        
        return account_name.strip(), currency
    
    def _scan_excel_file(self, file_path):
        """Scan Excel file for data validation before import."""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Clean the DataFrame - remove completely empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # Validate required columns
            required_columns = ['Date', 'Type', 'Amount', 'Account']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}\n\nFound columns: {', '.join(df.columns.tolist())}", None, None, None, None
            
            # Get all accounts and categories for validation
            accounts = self.budget_app.get_all_accounts()
            categories = self.budget_app.get_all_categories()
            
            # Build account mapping
            account_name_to_id = {}
            for acc in accounts:
                display_name = f"{acc.account} {acc.currency}"
                account_name_to_id[display_name] = acc.id
            
            valid_sub_categories = {cat.sub_category for cat in categories}
            
            # Scan for issues
            missing_accounts = set()
            missing_sub_categories = set()
            invalid_transactions = []  # Store detailed error information
            total_rows = 0
            valid_rows = 0
            
            for index, row in df.iterrows():
                row_errors = []
                row_number = index + 2  # +2 because Excel rows start at 1 and we have header
                
                # Skip completely empty rows
                if pd.isna(row['Date']) and pd.isna(row['Type']) and pd.isna(row['Amount']):
                    continue
                
                total_rows += 1
                
                # Check required fields
                if pd.isna(row['Date']):
                    row_errors.append("Missing Date")
                if pd.isna(row['Type']):
                    row_errors.append("Missing Type")
                if pd.isna(row['Amount']):
                    row_errors.append("Missing Amount")
                
                if row_errors:
                    invalid_transactions.append(f"Row {row_number}: {', '.join(row_errors)}")
                    continue
                
                # Validate transaction type
                trans_type = str(row['Type']).lower().strip()
                if trans_type not in ['income', 'expense', 'transfer']:
                    invalid_transactions.append(f"Row {row_number}: Invalid transaction type '{row['Type']}'. Must be 'income', 'expense', or 'transfer'")
                    continue
                
                # Validate amount
                try:
                    amount = float(row['Amount'])
                    if amount <= 0:
                        invalid_transactions.append(f"Row {row_number}: Amount must be greater than 0 (got {amount})")
                        continue
                except (ValueError, TypeError):
                    invalid_transactions.append(f"Row {row_number}: Invalid amount '{row['Amount']}' - must be a number")
                    continue
                
                # Check account
                account_display_name = str(row['Account']).strip()
                if account_display_name not in account_name_to_id:
                    missing_accounts.add(account_display_name)
                    invalid_transactions.append(f"Row {row_number}: Account '{account_display_name}' not found")
                    continue
                
                # Check sub_category if provided
                if 'Sub Category' in df.columns and not pd.isna(row['Sub Category']):
                    sub_category = str(row['Sub Category']).strip()
                    if sub_category and sub_category not in valid_sub_categories:
                        missing_sub_categories.add(sub_category)
                        invalid_transactions.append(f"Row {row_number}: Sub category '{sub_category}' not found")
                        continue
                
                # Check to_account for transfers
                if trans_type == 'transfer':
                    if 'To Account' not in df.columns or pd.isna(row['To Account']):
                        invalid_transactions.append(f"Row {row_number}: Transfer transactions require 'To Account'")
                        continue
                    
                    to_account_display_name = str(row['To Account']).strip()
                    if to_account_display_name not in account_name_to_id:
                        missing_accounts.add(to_account_display_name)
                        invalid_transactions.append(f"Row {row_number}: To Account '{to_account_display_name}' not found")
                        continue
                    
                    # Check if transferring to same account
                    if account_display_name == to_account_display_name:
                        invalid_transactions.append(f"Row {row_number}: Cannot transfer to the same account '{account_display_name}'")
                        continue
                
                # Check investment account if provided
                if 'Investment Account' in df.columns and not pd.isna(row['Investment Account']):
                    invest_account_display_name = str(row['Investment Account']).strip()
                    if invest_account_display_name and invest_account_display_name not in account_name_to_id:
                        missing_accounts.add(invest_account_display_name)
                        invalid_transactions.append(f"Row {row_number}: Investment account '{invest_account_display_name}' not found")
                        continue
                
                # Validate date format
                try:
                    if isinstance(row['Date'], str):
                        date_str = row['Date']
                        datetime.strptime(date_str, '%Y-%m-%d')
                    else:
                        # It's a pandas timestamp or datetime object
                        date_str = row['Date'].strftime('%Y-%m-%d')
                except:
                    invalid_transactions.append(f"Row {row_number}: Invalid date format '{row['Date']}'. Use YYYY-MM-DD")
                    continue
                
                # Validate to_amount for transfers if provided
                if trans_type == 'transfer' and 'To Amount' in df.columns and not pd.isna(row['To Amount']):
                    try:
                        to_amount = float(row['To Amount'])
                        if to_amount <= 0:
                            invalid_transactions.append(f"Row {row_number}: To Amount must be greater than 0 (got {to_amount})")
                            continue
                    except (ValueError, TypeError):
                        invalid_transactions.append(f"Row {row_number}: Invalid to amount '{row['To Amount']}' - must be a number")
                        continue
                
                # Validate quantity if provided
                if 'Quantity' in df.columns and not pd.isna(row['Quantity']):
                    try:
                        qty = float(row['Quantity'])
                    except (ValueError, TypeError):
                        invalid_transactions.append(f"Row {row_number}: Invalid quantity '{row['Quantity']}' - must be a number")
                        continue
                
                valid_rows += 1
            
            return True, "Scan completed", missing_accounts, missing_sub_categories, invalid_transactions, valid_rows, total_rows
            
        except Exception as e:
            return False, f"Error scanning Excel file: {str(e)}", None, None, None, None, None
    
    def _import_validated_data(self, file_path):
        """Import data after validation has passed."""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Clean the DataFrame
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # Get all accounts and categories for validation
            accounts = self.budget_app.get_all_accounts()
            categories = self.budget_app.get_all_categories()
            
            # Build account mapping
            account_name_to_id = {}
            for acc in accounts:
                display_name = f"{acc.account} {acc.currency}"
                account_name_to_id[display_name] = acc.id
            
            valid_sub_categories = {cat.sub_category for cat in categories}
            
            # Import transactions
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Skip completely empty rows
                    if pd.isna(row['Date']) and pd.isna(row['Type']) and pd.isna(row['Amount']):
                        continue
                    
                    # Validate required fields
                    if pd.isna(row['Date']) or pd.isna(row['Type']) or pd.isna(row['Amount']):
                        errors.append(f"Row {index + 2}: Missing required fields (Date, Type, or Amount)")
                        error_count += 1
                        continue
                    
                    # Validate transaction type
                    trans_type = str(row['Type']).lower().strip()
                    if trans_type not in ['income', 'expense', 'transfer']:
                        errors.append(f"Row {index + 2}: Invalid transaction type '{row['Type']}'")
                        error_count += 1
                        continue
                    
                    # Validate amount
                    try:
                        amount = float(row['Amount'])
                        if amount <= 0:
                            errors.append(f"Row {index + 2}: Amount must be greater than 0")
                            error_count += 1
                            continue
                    except (ValueError, TypeError):
                        errors.append(f"Row {index + 2}: Invalid amount '{row['Amount']}'")
                        error_count += 1
                        continue
                    
                    # Get account
                    account_display_name = str(row['Account']).strip()
                    account_id = account_name_to_id.get(account_display_name)
                    if not account_id:
                        errors.append(f"Row {index + 2}: Account '{account_display_name}' not found")
                        error_count += 1
                        continue
                    
                    # Validate date
                    try:
                        if isinstance(row['Date'], str):
                            date_str = row['Date']
                            datetime.strptime(date_str, '%Y-%m-%d')
                        else:
                            date_str = row['Date'].strftime('%Y-%m-%d')
                    except:
                        errors.append(f"Row {index + 2}: Invalid date format '{row['Date']}'")
                        error_count += 1
                        continue
                    
                    # Validate sub_category if provided
                    sub_category = ''
                    if 'Sub Category' in df.columns and not pd.isna(row['Sub Category']):
                        sub_category = str(row['Sub Category']).strip()
                        if sub_category and sub_category not in valid_sub_categories:
                            errors.append(f"Row {index + 2}: Sub category '{sub_category}' not found")
                            error_count += 1
                            continue
                    
                    # Validate to_account for transfers
                    to_account_id = None
                    to_amount = None
                    if trans_type == 'transfer':
                        if 'To Account' not in df.columns or pd.isna(row['To Account']):
                            errors.append(f"Row {index + 2}: Transfer requires 'To Account'")
                            error_count += 1
                            continue
                        
                        to_account_display_name = str(row['To Account']).strip()
                        to_account_id = account_name_to_id.get(to_account_display_name)
                        if not to_account_id:
                            errors.append(f"Row {index + 2}: To Account '{to_account_display_name}' not found")
                            error_count += 1
                            continue
                        
                        if account_id == to_account_id:
                            errors.append(f"Row {index + 2}: Cannot transfer to same account")
                            error_count += 1
                            continue
                        
                        # Get to_amount if provided
                        if 'To Amount' in df.columns and not pd.isna(row['To Amount']):
                            try:
                                to_amount = float(row['To Amount'])
                                if to_amount <= 0:
                                    errors.append(f"Row {index + 2}: To Amount must be greater than 0")
                                    error_count += 1
                                    continue
                            except (ValueError, TypeError):
                                errors.append(f"Row {index + 2}: Invalid to amount '{row['To Amount']}'")
                                error_count += 1
                                continue
                        else:
                            to_amount = amount
                    
                    # Get other optional fields
                    payee = str(row['Payee']).strip() if 'Payee' in df.columns and not pd.isna(row['Payee']) else ""
                    notes = str(row['Notes']).strip() if 'Notes' in df.columns and not pd.isna(row['Notes']) else ""
                    
                    invest_account_id = None
                    if 'Investment Account' in df.columns and not pd.isna(row['Investment Account']):
                        invest_account_display_name = str(row['Investment Account']).strip()
                        invest_account_id = account_name_to_id.get(invest_account_display_name)
                        if invest_account_display_name and not invest_account_id:
                            errors.append(f"Row {index + 2}: Investment account '{invest_account_display_name}' not found")
                            error_count += 1
                            continue
                    
                    qty = None
                    if 'Quantity' in df.columns and not pd.isna(row['Quantity']):
                        try:
                            qty = float(row['Quantity'])
                        except (ValueError, TypeError):
                            errors.append(f"Row {index + 2}: Invalid quantity '{row['Quantity']}'")
                            error_count += 1
                            continue
                    
                    # Add transaction to database
                    if trans_type == 'income':
                        success = self.budget_app.add_income(
                            date=date_str,
                            amount=amount,
                            account_id=account_id,
                            payee=payee,
                            sub_category=sub_category,
                            notes=notes,
                            invest_account_id=invest_account_id
                        )
                    elif trans_type == 'expense':
                        success = self.budget_app.add_expense(
                            date=date_str,
                            amount=amount,
                            account_id=account_id,
                            sub_category=sub_category,
                            payee=payee,
                            notes=notes
                        )
                    else:  # transfer
                        success = self.budget_app.add_transfer(
                            date=date_str,
                            from_account_id=account_id,
                            to_account_id=to_account_id,
                            from_amount=amount,
                            to_amount=to_amount,
                            qty=qty,
                            notes=notes
                        )
                    
                    if success:
                        success_count += 1
                    else:
                        errors.append(f"Row {index + 2}: Failed to add transaction to database")
                        error_count += 1
                        
                except Exception as e:
                    errors.append(f"Row {index + 2}: Unexpected error - {str(e)}")
                    error_count += 1
            
            return success_count, error_count, errors
            
        except Exception as e:
            return 0, 0, [f"Error during import: {str(e)}"]
    
    def import_from_excel(self, parent_window):
        """Import transactions from Excel file with pre-validation."""
        try:
            # Get file path from user
            file_path, _ = QFileDialog.getOpenFileName(
                parent_window,
                "Import Transactions from Excel",
                "",
                "Excel Files (*.xlsx *.xls)"
            )
            
            if not file_path:
                return False, "Import cancelled"
            
            # First scan the file for validation
            success, message, missing_accounts, missing_sub_categories, invalid_transactions, valid_rows, total_rows = self._scan_excel_file(file_path)
            
            if not success:
                QMessageBox.critical(parent_window, "Scan Failed", message)
                return False, message
            
            # Prepare validation report
            report_parts = []
            report_parts.append("📊 FILE SCAN REPORT")
            report_parts.append("=" * 50)
            report_parts.append(f"Total rows in file: {total_rows}")
            report_parts.append(f"Valid transactions found: {valid_rows}")
            report_parts.append(f"Invalid transactions: {len(invalid_transactions)}")
            
            if missing_accounts:
                report_parts.append(f"\n❌ MISSING ACCOUNTS ({len(missing_accounts)}):")
                for account in sorted(missing_accounts):
                    report_parts.append(f"  • {account}")
            
            if missing_sub_categories:
                report_parts.append(f"\n❌ MISSING SUB-CATEGORIES ({len(missing_sub_categories)}):")
                for category in sorted(missing_sub_categories):
                    report_parts.append(f"  • {category}")
            
            if invalid_transactions:
                report_parts.append(f"\n⚠️ TRANSACTION ERRORS (first 10):")
                for error in invalid_transactions[:10]:
                    report_parts.append(f"  • {error}")
                if len(invalid_transactions) > 10:
                    report_parts.append(f"  ... and {len(invalid_transactions) - 10} more errors")
            
            if not missing_accounts and not missing_sub_categories and not invalid_transactions:
                report_parts.append(f"\n✅ ALL DATA IS VALID!")
            
            report = "\n".join(report_parts)
            
            # Ask for user confirmation
            if missing_accounts or missing_sub_categories or invalid_transactions:
                reply = QMessageBox.warning(
                    parent_window,
                    "Validation Report - Issues Found",
                    f"{report}\n\n"
                    f"Only {valid_rows} out of {total_rows} rows can be imported.\n\n"
                    "Do you want to continue with partial import?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
            else:
                reply = QMessageBox.question(
                    parent_window,
                    "Validation Report - All Good!",
                    f"{report}\n\n"
                    f"Ready to import {valid_rows} transactions.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
            
            if reply != QMessageBox.StandardButton.Yes:
                return False, "Import cancelled by user"
            
            # Clear existing transactions if user confirms
            clear_reply = QMessageBox.question(
                parent_window,
                "Data Import Options",
                "How do you want to handle existing transactions?\n\n"
                "• YES = REPLACE ALL existing transactions with imported data\n"
                "• NO = KEEP existing transactions and ADD imported data\n"
                "• CANCEL = Stop the import",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            
            if clear_reply == QMessageBox.StandardButton.Cancel:
                return False, "Import cancelled"
            
            # Clear existing transactions if requested
            if clear_reply == QMessageBox.StandardButton.Yes:
                conn = self.budget_app._get_connection()
                try:
                    conn.execute("DELETE FROM transactions")
                    conn.commit()
                except Exception as e:
                    return False, f"Error clearing existing transactions: {str(e)}"
                finally:
                    conn.close()
            
            # Now import the validated data
            success_count, error_count, errors = self._import_validated_data(file_path)
            
            # Prepare result message
            result_parts = []
            result_parts.append("📈 IMPORT RESULTS")
            result_parts.append("=" * 30)
            result_parts.append(f"✅ Successfully imported: {success_count}")
            result_parts.append(f"❌ Failed to import: {error_count}")
            
            if errors:
                result_parts.append(f"\n📝 ERROR DETAILS (first 10):")
                for error in errors[:10]:
                    result_parts.append(f"  • {error}")
                if len(errors) > 10:
                    result_parts.append(f"  ... and {len(errors) - 10} more errors")
            
            return True, "\n".join(result_parts)
            
        except Exception as e:
            return False, f"Error importing from Excel: {str(e)}"