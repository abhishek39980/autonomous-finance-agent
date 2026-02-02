"""
Actual Finance Logic (Final - Improved for Offline Wealth Manager).
Uses a global state to share data between the standalone functions.
"""

import os
import webbrowser
import re

# Global state to share data between tools
# This is required because the tools are independent functions
GLOBAL_STATE = {
    "df": None
}

__all__ = ["read_statement", "categorize_transactions", "generate_dashboard"]

def read_statement(file_path: str = None, password: str = None):
    """Reads CSV/Excel/PDF bank statements (with optional password for PDFs)."""
    print(f"      [Tool] Reading file: {file_path}")
    
    if not file_path:
        return "Error: No file path provided."
        
    # Remove quotes if they exist
    file_path = file_path.strip('"').strip("'")

    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"

    try:
        try:
            import pandas as pd
        except Exception as e:
            return f"Error: pandas is required but not available ({e})"

        # Handle CSV files
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        
        # Handle Excel files
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        
        # Handle PDF files
        elif file_path.endswith('.pdf'):
            df = _read_pdf_statement(file_path, password)
            if isinstance(df, str):  # Error message
                return df
        
        else:
            return "Error: Unsupported format. Please use .csv, .xlsx, or .pdf"
        
        GLOBAL_STATE["df"] = df
        return f"Successfully loaded {len(df)} transactions from {file_path.split('/')[-1].split(chr(92))[-1]}"
    
    except Exception as e:
        return f"Error reading file: {e}"


def _read_pdf_statement(file_path, password=None):
    """Helper function to read PDF bank statements with improved detection."""
    try:
        import pdfplumber
        import pandas as pd
    except ImportError:
        return "Error: pdfplumber is required for PDF files. Install with: pip install pdfplumber"
    
    print(f"      [Tool] Attempting to read PDF...")
    
    def try_extract_tables(pdf_obj):
        """Extract and process tables from PDF."""
        all_tables = []
        all_text_lines = []
        
        for page_num, page in enumerate(pdf_obj.pages, 1):
            print(f"      [Tool] Processing page {page_num}...")
            
            # Method 1: Extract structured tables with better settings
            # Use more lenient table detection settings
            table_settings = {
                "vertical_strategy": "lines_strict",
                "horizontal_strategy": "lines_strict",
                "intersection_tolerance": 15,
            }
            
            tables = page.extract_tables(table_settings)
            if tables:
                print(f"      [Tool] Found {len(tables)} table(s) on page {page_num}")
                all_tables.extend(tables)
            
            # If no tables found with strict strategy, try text-based strategy
            if not tables:
                table_settings = {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                }
                tables = page.extract_tables(table_settings)
                if tables:
                    print(f"      [Tool] Found {len(tables)} table(s) on page {page_num} (text strategy)")
                    all_tables.extend(tables)
            
            # Method 2: Extract text for fallback
            text = page.extract_text()
            if text:
                all_text_lines.extend(text.split('\n'))
        
        # Try to build DataFrame from tables first
        df = _process_tables(all_tables)
        
        # If table extraction failed, try text parsing
        if df is None and all_text_lines:
            print(f"      [Tool] Table extraction failed, trying text parsing...")
            df = _parse_text_statement(all_text_lines)
        
        return df
    
    # Try opening PDF without password first
    try:
        with pdfplumber.open(file_path, password=password) as pdf:
            if password:
                print(f"      [Tool] PDF opened successfully with provided password")
            else:
                print(f"      [Tool] PDF opened successfully (no password required)")
            
            df = try_extract_tables(pdf)
            
            if df is not None and len(df) > 0:
                print(f"      [Tool] Successfully extracted {len(df)} transactions")
                return df
            else:
                return "Error: No transaction data found in PDF."
                
    except Exception as e:
        error_msg = str(e).lower()
        
        # Handle password-protected PDFs
        if ('password' in error_msg or 'encrypted' in error_msg) and password is None:
            print(f"      [Tool] PDF is password-protected")
            print(f"\n" + "="*60)
            print(f"PASSWORD REQUIRED")
            print(f"="*60)
            
            # Try to get password from user
            try:
                import getpass
                user_password = getpass.getpass("Enter PDF password: ")
            except:
                user_password = input("Enter PDF password: ")
            
            if not user_password:
                return "Error: No password provided. Cannot open encrypted PDF."
            
            # Retry with password
            return _read_pdf_statement(file_path, password=user_password)
        else:
            return f"Error reading PDF: {e}"


def _process_tables(tables):
    """Process extracted tables and convert to DataFrame."""
    import pandas as pd
    
    if not tables:
        return None
    
    print(f"      [Tool] Processing {len(tables)} extracted table(s)...")
    
    # Combine all tables into one list of rows
    all_rows = []
    header_row = None
    
    for table_idx, table_data in enumerate(tables):
        if len(table_data) < 1:
            continue
        
        print(f"      [Tool] Analyzing table {table_idx + 1} with {len(table_data)} rows...")
        
        # Look for header row in this table
        for row_idx, row in enumerate(table_data):
            if row and _is_header_row(row):
                if header_row is None:
                    header_row = row
                    print(f"      [Tool] Found header row in table {table_idx + 1}: {header_row}")
                # Skip header rows in subsequent tables
                continue
            
            # Only add data rows (skip empty rows and non-header rows before we found header)
            if header_row is not None and row and any(cell and str(cell).strip() for cell in row):
                all_rows.append(row)
    
    if header_row is None:
        print(f"      [Tool] No header row found, using first row of first table")
        if tables and len(tables[0]) > 0:
            header_row = tables[0][0]
            all_rows = [row for table in tables for row in table[1:] if row and any(cell and str(cell).strip() for cell in row)]
        else:
            return None
    
    if not all_rows:
        print(f"      [Tool] No data rows found")
        return None
    
    
    
    print(f"      [Tool] Found {len(all_rows)} data rows total")
    
    # Expand multi-line cells (transactions packed together with \n)
    # For bank statements: split dates and descriptions, but keep amounts on FIRST row only
    expanded_rows = []
    for row in all_rows:
        # Check if any cell contains newlines
        has_multiline = any(cell and '\n' in str(cell) for cell in row)
        
        if has_multiline:
            # Split cells by newlines
            split_cells = []
            max_lines = 1
            
            for idx, cell in enumerate(row):
                if cell and '\n' in str(cell):
                    lines = str(cell).split('\n')
                    # Filter out empty lines
                    lines = [l.strip() for l in lines if l.strip()]
                    split_cells.append(lines)
                    max_lines = max(max_lines, len(lines))
                else:
                    cell_str = str(cell).strip() if cell else ''
                    split_cells.append([cell_str])
            
            
            # Create a row for each line
            for line_idx in range(max_lines):
                new_row = []
                for cell_idx, cell_lines in enumerate(split_cells):
                    if line_idx < len(cell_lines):
                        new_row.append(cell_lines[line_idx])
                    else:
                        new_row.append('')
                expanded_rows.append(new_row)
        else:
            expanded_rows.append(row)
    
    print(f"      [Tool] Expanded to {len(expanded_rows)} rows after splitting multi-line cells")
    
    
    
    # Now merge rows that belong to the same transaction
    # Strategy:
    # 1. Row with Amount = NEW transaction (Forward fill date if missing)
    # 2. Row with NO Amount = Merge description into current transaction
    merged_rows = []
    current_transaction = None
    last_valid_date = None
    last_valid_value_date = None
    
    for row in expanded_rows:
        # Extract key fields
        date_val = str(row[0]).strip() if len(row) > 0 and row[0] else ''
        value_date_val = str(row[1]).strip() if len(row) > 1 and row[1] else ''
        desc_val = str(row[2]).strip() if len(row) > 2 and row[2] else ''
        deposit_val = str(row[4]).strip() if len(row) > 4 and row[4] else ''
        withdrawal_val = str(row[5]).strip() if len(row) > 5 and row[5] else ''
        
        # Check if this row has an amount
        has_amount = bool(deposit_val or withdrawal_val)
        has_date = bool(date_val)
        
        # Handle BALANCE FORWARD - only skip if it's purely a header/summary line (no amount)
        if 'BALANCE FORWARD' in desc_val.upper() and not has_amount:
            continue
            
        if has_amount:
            # This row IS a transaction
            if has_date:
                # New transaction with its own date
                last_valid_date = date_val
                last_valid_value_date = value_date_val
            else:
                # Transaction without date - forward fill from previous
                if last_valid_date:
                    row[0] = last_valid_date
                    row[1] = last_valid_value_date if last_valid_value_date else ''
            
            # Save previous transaction
            if current_transaction:
                merged_rows.append(current_transaction)
            
            # Start new transaction
            current_transaction = list(row)
            
        elif current_transaction:
            # This is a continuation line (no amount) - merge into current transaction
            
            # Merge description
            if desc_val:
                current_transaction[2] = current_transaction[2] + ' ' + desc_val
            
            # Merge other fields if they exist and current transaction doesn't have them
            for idx in range(3, len(row)):
                if row[idx] and str(row[idx]).strip():
                    current_val = str(current_transaction[idx]).strip() if current_transaction[idx] else ''
                    row_val = str(row[idx]).strip()
                    
                    if not current_val:
                        # Current transaction doesn't have this field, use row's value
                        current_transaction[idx] = row[idx]
                    elif idx in [4, 5, 6]:  # Amount/Balance columns - don't merge strings
                        pass
                    else:
                        # Append to existing value
                        current_transaction[idx] = current_val + ' ' + row_val
        # else: orphan row with no amount and no current transaction - skip
    
    # Don't forget the last transaction
    if current_transaction:
        merged_rows.append(current_transaction)
    
    print(f"      [Tool] Merged to {len(merged_rows)} transactions after combining continuation lines")
    
    # Use merged rows instead of expanded rows
    expanded_rows = merged_rows
    
    # Clean headers
    headers = _clean_headers(header_row)
    
    # Ensure all rows have the same number of columns
    num_cols = len(headers)
    validated_rows = []
    
    for row in expanded_rows:
        if len(row) < num_cols:
            # Pad with empty strings
            row = list(row) + [''] * (num_cols - len(row))
        elif len(row) > num_cols:
            # Truncate
            row = row[:num_cols]
        
        # Check if this row has any meaningful transaction data
        # Skip only if it's PURELY a header/summary row
        row_text = ' '.join(str(cell) for cell in row if cell).strip()
        
        # Skip completely empty rows
        if not row_text:
            continue
        
        # Skip rows that are ONLY balance forward or summary text (no amounts)
        row_text_upper = row_text.upper()
        if row_text_upper in ['BALANCE FORWARD', 'OPENING BALANCE', 'CLOSING BALANCE', 'REWARD POINTS']:
            continue
        
        # Check if row has at least one amount-like value (number with decimals or commas)
        has_amount = any(cell and re.search(r'[\d,]+\.?\d*', str(cell)) for cell in row)
        
        # Skip if it's just text without any amounts (likely a header or note)
        if not has_amount and len(row_text) < 100:  # Short text without amounts = header
            continue
        
        validated_rows.append(row)
    
    if not validated_rows:
        print(f"      [Tool] No valid transaction rows after filtering")
        return None
    
    print(f"      [Tool] Creating DataFrame with {len(validated_rows)} rows and columns: {headers}")
    
    # Create DataFrame
    try:
        df = pd.DataFrame(validated_rows, columns=headers)
        
        # Clean and standardize the DataFrame
        df = _clean_dataframe(df)
        
        # Verify it looks like transaction data
        if _is_valid_transaction_data(df):
            print(f"      [Tool] Valid transaction data created with {len(df)} transactions")
            print(f"      [Tool] Columns: {list(df.columns)}")
            return df
        else:
            print(f"      [Tool] Data doesn't appear to contain valid transactions")
            return None
            
    except Exception as e:
        print(f"      [Tool] Error creating DataFrame: {e}")
        import traceback
        traceback.print_exc()
        return None


def _is_header_row(row):
    """Check if a row looks like a header row."""
    if not row:
        return False
    
    header_keywords = ['date', 'description', 'narration', 'details', 'particular', 
                       'amount', 'withdrawal', 'deposit', 'debit', 'credit', 
                       'balance', 'cheque', 'value']
    
    # Count how many cells contain header keywords
    matches = 0
    non_empty = 0
    
    for cell in row:
        if cell and isinstance(cell, str) and cell.strip():
            non_empty += 1
            cell_lower = str(cell).lower().strip()
            if any(keyword in cell_lower for keyword in header_keywords):
                matches += 1
    
    # Need at least 3 header keywords to be confident it's a header
    return matches >= 3 and non_empty > 0


def _clean_headers(headers):
    """Clean and standardize header names, ensuring uniqueness."""
    cleaned = []
    seen = {}
    
    for h in headers:
        if h is None or (isinstance(h, str) and not h.strip()):
            base_name = f'Column_{len(cleaned)}'
        else:
            # Clean the header text
            h_clean = str(h).strip()
            # Remove extra whitespace and newlines
            h_clean = ' '.join(h_clean.split())
            # Remove special characters but keep spaces
            h_clean = re.sub(r'[^\w\s]', '', h_clean)
            base_name = h_clean if h_clean else f'Column_{len(cleaned)}'
        
        # Ensure uniqueness
        if base_name in seen:
            seen[base_name] += 1
            final_name = f"{base_name}_{seen[base_name]}"
        else:
            seen[base_name] = 0
            final_name = base_name
        
        cleaned.append(final_name)
    
    return cleaned


def _clean_dataframe(df):
    """Clean and standardize the DataFrame."""
    import pandas as pd
    
    # Remove completely empty rows
    df = df.dropna(how='all')
    df = df[df.astype(str).apply(lambda x: x.str.strip()).ne('').any(axis=1)]
    
    # Reset index
    df = df.reset_index(drop=True)
    
    # Standardize column names and identify key columns
    column_mapping = {}
    mapped_targets = set()
    
    for col in df.columns:
        col_lower = str(col).lower().strip()
        target_name = None
        
        # Date column (prioritize "Date" over "Value Date")
        if 'date' in col_lower and 'Date' not in mapped_targets:
            if col_lower == 'date' or col_lower == 'transaction date' or col_lower == 'txn date':
                target_name = 'Date'
            elif 'value' not in col_lower:
                target_name = 'Date'
        
        # Value Date column
        if target_name is None and 'ValueDate' not in mapped_targets:
            if 'value date' in col_lower or 'valuedate' in col_lower:
                target_name = 'ValueDate'
        
        # Description column
        if target_name is None and 'Description' not in mapped_targets:
            if any(kw in col_lower for kw in ['description', 'narration', 'particular', 'details']):
                target_name = 'Description'
        
        # Cheque number column
        if target_name is None and 'Cheque' not in mapped_targets:
            if 'cheque' in col_lower or 'check' in col_lower or 'chq' in col_lower:
                target_name = 'Cheque'
        
        # Withdrawal/Debit column
        if target_name is None and 'Withdrawal' not in mapped_targets:
            if any(kw in col_lower for kw in ['withdrawal', 'debit', 'dr ', ' dr']):
                target_name = 'Withdrawal'
        
        # Deposit/Credit column
        if target_name is None and 'Deposit' not in mapped_targets:
            if any(kw in col_lower for kw in ['deposit', 'credit', 'cr ', ' cr']):
                target_name = 'Deposit'
        
        # Balance column
        if target_name is None and 'Balance' not in mapped_targets:
            if 'balance' in col_lower:
                target_name = 'Balance'
        
        # Amount column (single amount column, not withdrawal/deposit)
        if target_name is None and 'Amount' not in mapped_targets:
            if col_lower == 'amount':
                target_name = 'Amount'
        
        # Add to mapping if we found a target
        if target_name:
            column_mapping[col] = target_name
            mapped_targets.add(target_name)
    
    # Rename columns
    if column_mapping:
        df = df.rename(columns=column_mapping)
        print(f"      [Tool] Mapped columns: {column_mapping}")
    
    # Convert amount columns to numeric
    amount_cols = ['Amount', 'Withdrawal', 'Deposit', 'Balance']
    for col in amount_cols:
        if col in df.columns:
            df[col] = _clean_amount_column(df[col])
    
    # If we have Withdrawal and Deposit columns but no Amount column, create it
    if 'Amount' not in df.columns and 'Withdrawal' in df.columns and 'Deposit' in df.columns:
        # Deposits are positive, withdrawals are negative
        df['Amount'] = df['Deposit'].fillna(0) - df['Withdrawal'].fillna(0)
    
    # Try to parse date columns
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
    
    if 'ValueDate' in df.columns:
        df['ValueDate'] = pd.to_datetime(df['ValueDate'], errors='coerce', dayfirst=True)
    
    return df


def _clean_amount_column(series):
    """Clean and convert amount column to numeric."""
    import pandas as pd
    
    # Remove currency symbols and commas
    cleaned = series.astype(str).str.replace('₹', '', regex=False)
    cleaned = cleaned.str.replace('$', '', regex=False)
    cleaned = cleaned.str.replace(',', '', regex=False)
    cleaned = cleaned.str.replace('Rs.', '', regex=False)
    cleaned = cleaned.str.replace('Rs', '', regex=False)
    cleaned = cleaned.str.strip()
    
    # Handle 'Dr' and 'Cr' suffixes (but keep the sign)
    cleaned = cleaned.str.replace('Dr', '', regex=False)
    cleaned = cleaned.str.replace('Cr', '', regex=False)
    
    # Replace empty strings and 'nan' with NaN
    cleaned = cleaned.replace('', pd.NA)
    cleaned = cleaned.replace('nan', pd.NA)
    cleaned = cleaned.replace('None', pd.NA)
    
    # Convert to numeric
    return pd.to_numeric(cleaned, errors='coerce')


def _is_valid_transaction_data(df):
    """Check if DataFrame contains valid transaction data."""
    # Must have at least one of these column combinations
    has_date = 'Date' in df.columns or 'ValueDate' in df.columns
    has_description = 'Description' in df.columns
    has_amount = 'Amount' in df.columns or ('Withdrawal' in df.columns and 'Deposit' in df.columns)
    
    # Must have at least 1 row of data
    has_data = len(df) >= 1
    
    is_valid = has_data and has_date and has_amount
    
    if not is_valid:
        print(f"      [Tool] Validation failed - has_data:{has_data}, has_date:{has_date}, has_description:{has_description}, has_amount:{has_amount}")
    
    return is_valid


def _parse_text_statement(text_lines):
    """Parse transaction data from raw text lines (fallback method)."""
    import pandas as pd
    
    print(f"      [Tool] Attempting to parse {len(text_lines)} text lines...")
    
    # Pattern for bank statement lines
    # Date (DD Mon YY) ... Description ... Amounts ... Balance
    date_pattern = r'\d{2}\s+[A-Za-z]{3}\s+\d{2}'
    
    transactions = []
    current_transaction = None
    
    for line in text_lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line starts with a date
        if re.match(date_pattern, line):
            # This is a new transaction
            if current_transaction:
                transactions.append(current_transaction)
            current_transaction = line
        elif current_transaction:
            # This is a continuation of the previous transaction
            current_transaction += " " + line
    
    # Don't forget the last transaction
    if current_transaction:
        transactions.append(current_transaction)
    
    if len(transactions) > 0:
        print(f"      [Tool] Found {len(transactions)} potential transactions in text")
        
        # Try to parse each transaction
        parsed_transactions = []
        for txn in transactions:
            # Skip summary lines
            if any(skip in txn.upper() for skip in ['BALANCE FORWARD', 'REWARD POINTS', 'TOTAL']):
                continue
            
            # Try to extract components
            parts = txn.split()
            if len(parts) >= 5:  # At minimum: date (3 parts) + description + amount
                parsed_transactions.append(txn)
        
        if parsed_transactions:
            # Create a simple dataframe with the raw transaction text
            df = pd.DataFrame({
                'Description': parsed_transactions
            })
            
            print(f"      [Tool] Created DataFrame with {len(df)} transactions from text")
            return df
    
    return None


def categorize_transactions(dummy_arg=None):
    """Categorizes the loaded data (Mock AI)."""
    import pandas as pd
    
    df = GLOBAL_STATE["df"]
    if df is None:
        return "Error: No data loaded. Run read_statement first."
    
    print("      [Tool] Categorizing transactions...")
    
    # Simple keyword matching logic with improved patterns
    def get_category(desc):
        # Handle None, NaN, or non-string values
        if desc is None or not isinstance(desc, str) or pd.isna(desc):
            return "Other"
        desc_lower = desc.lower()
        desc_upper = desc.upper()
        
        # ATM Withdrawals (most common pattern)
        if any(kw in desc_lower for kw in ['atm withdrawal', 'atm wd', 'cash withdrawal', 'at nfs', 'at cashnt']):
            return 'Cash Withdrawal'
        
        # Income & Credits
        if any(kw in desc_lower for kw in ['salary', 'neft cr', 'imps cr', 'rtgs cr', 'credit of interest', 'cradj']):
            return 'Income'
        if 'neft' in desc_lower and any(kw in desc_lower for kw in ['credited', 'cr/', '/cr']):
            return 'Income'
        
        # Paytm - check for various patterns
        if any(kw in desc_lower for kw in ['paytm', 'add-money@paytm', 'one97', 'nicationsli']):
            return 'Paytm/Wallet'
        
        # UPI Payments - be more specific
        if 'upi/' in desc_lower or '/upi/' in desc_lower or desc_lower.startswith('upi/'):
            # Paytm
            if 'paytm' in desc_lower:
                return 'Paytm/Wallet'
            # Food delivery
            elif any(kw in desc_lower for kw in ['zomato', 'swiggy', 'uber eats']):
                return 'Food & Dining'
            # Travel
            elif any(kw in desc_lower for kw in ['ixigo', 'makemytrip', 'goibibo', 'travenues', 'redbus']):
                return 'Travel'
            # Shopping
            elif any(kw in desc_lower for kw in ['amazon', 'flipkart', 'myntra', 'ajio']):
                return 'Shopping'
            # Bills
            elif any(kw in desc_lower for kw in ['airtel', 'jio', 'vodafone', 'bsnl', 'electricity', 'tneb']):
                return 'Bills & Utilities'
            # LIC/Insurance
            elif any(kw in desc_lower for kw in ['lic', 'insurance', 'premium']):
                return 'Insurance'
            # Generic UPI
            else:
                return 'UPI Payment'
        
        # Check for phone number patterns (likely UPI continuation)
        if desc.strip().isdigit() and len(desc.strip()) >= 10:
            return 'UPI Payment'
        
        # Check for transaction IDs (numbers with slashes)
        if '/' in desc and any(char.isdigit() for char in desc):
            # Could be UPI, NEFT, or other transaction
            if any(kw in desc_lower for kw in ['@', 'upi', 'paytm', 'oksbi', 'axisbank', 'icici']):
                return 'UPI Payment'
            elif any(kw in desc_lower for kw in ['neft', 'imps', 'rtgs']):
                return 'Transfer'
        
        # Point of Sale (POS) Purchases
        if any(kw in desc_lower for kw in ['purchase', 'pos ', 'swipe']):
            # Restaurants & Hotels
            if any(kw in desc_lower for kw in ['hotel', 'restaurant', 'cafe', 'dhaba', 'vilas', 'bhavan']):
                return 'Food & Dining'
            # Lifestyle & Shopping
            elif any(kw in desc_lower for kw in ['lifestyle', 'reliance', 'dmart', 'big bazaar', 'more', 'supermarket']):
                return 'Shopping'
            # Fuel
            elif any(kw in desc_lower for kw in ['petrol', 'diesel', 'fuel', 'hp ', 'iocl', 'bharat petroleum', 'shell']):
                return 'Travel'
            else:
                return 'Shopping'
        
        # Online Shopping (non-UPI)
        if any(kw in desc_lower for kw in ['amazon', 'flipkart', 'myntra', 'ajio', 'nykaa']):
            return 'Shopping'
        
        # Food & Dining
        if any(kw in desc_lower for kw in ['zomato', 'swiggy', 'dominos', 'pizza', 'mcdonald', 'kfc', 'subway']):
            return 'Food & Dining'
        
        # Travel & Transport
        if any(kw in desc_lower for kw in ['uber', 'ola', 'rapido', 'ixigo', 'makemytrip', 'goibibo', 'irctc', 'railway']):
            return 'Travel'
        
        # Bills & Utilities
        if any(kw in desc_lower for kw in ['airtel', 'jio', 'vodafone', 'bsnl', 'electricity', 'tneb', 'bescom', 'bill payment', 'recharge']):
            return 'Bills & Utilities'
        
        # Entertainment & Subscriptions
        if any(kw in desc_lower for kw in ['netflix', 'amazon prime', 'hotstar', 'spotify', 'youtube', 'bookmyshow']):
            return 'Entertainment'
        
        # Bank Charges & Fees
        if any(kw in desc_lower for kw in ['charges', 'gst', 'sgst', 'cgst', 'service charge', 'annual fee', 'sms charges']):
            return 'Bank Charges'
        
        # Transfers (NEFT/IMPS/RTGS that aren't income)
        if any(kw in desc_lower for kw in ['neft', 'imps', 'rtgs']) and 'cr' not in desc_lower:
            return 'Transfer'
        
        return 'Other'

    # Find Description column
    desc_col = None
    for col in df.columns:
        if col is not None and str(col).lower() in ['description', 'narration', 'details', 'particular', 'transaction details']:
            desc_col = col
            break
            
    if desc_col:
        df['Category'] = df[desc_col].apply(get_category)
        GLOBAL_STATE["df"] = df
        
        # Show category breakdown
        category_counts = df['Category'].value_counts()
        print(f"      [Tool] Category breakdown:")
        for cat, count in category_counts.items():
            print(f"        - {cat}: {count}")
        
        return f"Categorization complete. {len(df)} transactions categorized into {len(category_counts)} categories."
    else:
        return f"Error: Could not find a 'Description' column. Found: {list(df.columns)}"


def generate_dashboard(dummy_arg=None):
    """Generates HTML Report."""
    import pandas as pd
    
    df = GLOBAL_STATE["df"]
    if df is None:
        return "Error: No data loaded."
    
    print("      [Tool] Creating HTML Dashboard...")
    
    # Calculate totals
    total_tx = len(df)
    
    # Handle different amount column structures
    if 'Amount' in df.columns:
        total_income = df[df['Amount'] > 0]['Amount'].sum()
        total_spent = abs(df[df['Amount'] < 0]['Amount'].sum())
    elif 'Withdrawal' in df.columns and 'Deposit' in df.columns:
        total_income = df['Deposit'].fillna(0).sum()
        total_spent = df['Withdrawal'].fillna(0).sum()
    else:
        total_income = 0
        total_spent = 0
    
    # Calculate net
    net_balance = total_income - total_spent
    
    # Category breakdown with amounts
    category_html = ""
    if 'Category' in df.columns:
        # Calculate spending by category
        if 'Amount' in df.columns:
            category_spending = df[df['Amount'] < 0].groupby('Category')['Amount'].sum().abs().sort_values(ascending=False).reset_index()
            category_spending.columns = ['Category', 'Total Spent']
            category_spending['Total Spent'] = category_spending['Total Spent'].apply(lambda x: f'₹{x:,.2f}')
        elif 'Withdrawal' in df.columns:
            category_spending = df.groupby('Category')['Withdrawal'].sum().sort_values(ascending=False).reset_index()
            category_spending.columns = ['Category', 'Total Spent']
            category_spending['Total Spent'] = category_spending['Total Spent'].apply(lambda x: f'₹{x:,.2f}')
        else:
            category_spending = df.groupby('Category').size().reset_index(name='Count').sort_values('Count', ascending=False)
        
        category_html = f"""
        <div class="card">
            <h2>💳 Spending by Category</h2>
            {category_spending.to_html(index=False, classes='table')}
        </div>
        """
    
    # Format the dataframe for display
    display_df = df.copy()
    
    # Format amount columns
    for col in ['Amount', 'Withdrawal', 'Deposit', 'Balance']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f'₹{x:,.2f}' if pd.notna(x) else '')
    
    # Format date columns
    for col in ['Date', 'ValueDate']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: x.strftime('%d-%b-%Y') if pd.notna(x) else '')
    
    html = f"""
    <html>
    <head>
        <title>Wealth Report - Bank Statement Analysis</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                   padding: 20px; 
                   background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   margin: 0; }}
            .container {{ max-width: 1400px; margin: 0 auto; }}
            h1 {{ color: white; text-align: center; margin-bottom: 30px; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
            .card {{ background: white; 
                    padding: 25px; 
                    margin-bottom: 20px; 
                    border-radius: 12px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .summary-grid {{ display: grid; 
                            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                            gap: 20px; 
                            margin-bottom: 20px; }}
            .summary-item {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            padding: 20px;
                            border-radius: 12px;
                            text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.2); }}
            .summary-item h3 {{ margin: 0 0 10px 0; font-size: 1em; opacity: 0.9; }}
            .summary-item .value {{ font-size: 2em; font-weight: bold; margin: 0; }}
            .positive {{ color: #10b981; }}
            .negative {{ color: #ef4444; }}
            table {{ width: 100%; 
                    border-collapse: collapse; 
                    margin-top: 10px;
                    font-size: 0.85em; }}
            th, td {{ border: 1px solid #e5e7eb; 
                     padding: 10px; 
                     text-align: left; }}
            th {{ background-color: #667eea; 
                 color: white; 
                 font-weight: 600;
                 position: sticky;
                 top: 0; }}
            tr:nth-child(even) {{ background-color: #f9fafb; }}
            tr:hover {{ background-color: #f3f4f6; }}
            h2 {{ color: #374151; margin-top: 0; }}
            .table-container {{ max-height: 600px; overflow-y: auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💰 Wealth Report Dashboard</h1>
            
            <div class="summary-grid">
                <div class="summary-item">
                    <h3>📊 Total Transactions</h3>
                    <p class="value">{total_tx}</p>
                </div>
                <div class="summary-item">
                    <h3>💵 Total Income</h3>
                    <p class="value">₹{total_income:,.2f}</p>
                </div>
                <div class="summary-item">
                    <h3>💸 Total Spending</h3>
                    <p class="value">₹{total_spent:,.2f}</p>
                </div>
                <div class="summary-item">
                    <h3>💰 Net Balance</h3>
                    <p class="value {'positive' if net_balance >= 0 else 'negative'}">
                        ₹{net_balance:,.2f}
                    </p>
                </div>
            </div>

            {category_html}

            <div class="card">
                <h2>📋 Detailed Transactions</h2>
                <div class="table-container">
                    {display_df.to_html(index=False, classes='table')}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Ensure reports directory exists
    os.makedirs("reports", exist_ok=True)
    
    out_file = "reports/dashboard.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
        
        
    # Open automatically in browser with cache-busting timestamp
    abs_path = os.path.abspath(out_file)
    import time
    timestamp = int(time.time())
    
    print(f"      [Tool] Dashboard saved to {out_file}")
    print(f"      [Tool] Opening in browser...")
    
    # Try multiple methods to open browser (Robust Windows Support)
    try:
        # Method 1: webbrowser module with timestamp
        webbrowser.open(f"file://{abs_path}?v={timestamp}")
    except Exception as e:
        print(f"      [Tool] webbrowser.open warning: {e}")
    
    # Method 2: Force Windows start command (failsafe)
    try:
        import subprocess
        subprocess.Popen(['start', '', abs_path], shell=True)
    except Exception as e2:
        print(f"      [Tool] subprocess fallback warning: {e2}")
    
    return f"Dashboard generated successfully at {out_file}. Check your browser!"