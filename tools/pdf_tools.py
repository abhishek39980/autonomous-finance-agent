"""
PDF Parsing Tools.
Extracted logic for reading bank statements from PDFs.
Rewritten to use Text-Stream Parsing Strategy for better handling of open table layouts.
"""
import re
try:
    import pandas as pd
except ImportError:
    pd = None

def read_pdf_statement(file_path, password=None):
    """
    Helper function to read PDF bank statements using a Text-Stream Strategy.
    This approach iterates line-by-line to identify transactions based on Date and Amount patterns,
    avoiding issues with table extraction in open-layout PDFs.
    """
    if pd is None:
        return "Error: pandas is required but not available."
        
    try:
        import pdfplumber
    except ImportError:
        return "Error: pdfplumber is required for PDF files. Install with: pip install pdfplumber"
    
    print(f"      [Tool] Attempting to read PDF with Text-Stream Strategy...")
    
    all_transactions = []
    
    try:
        with pdfplumber.open(file_path, password=password) as pdf:
            if password:
                print(f"      [Tool] PDF opened successfully with provided password")
            else:
                print(f"      [Tool] PDF opened successfully (no password required)")
            
            # Key Regex Patterns
            # Date: matches "16 Jun 19" or "16/06/19"
            date_pattern = re.compile(r'^(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})|(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})')
            
            # Amount: matches "1,500.00" or "500.00Cr" or "10.50"
            # Looks for number, optional commas, dot, two decimals, optional Dr/Cr
            # Captured groups: (Amount with Dr/Cr)
            amount_pattern = re.compile(r'([\d,]+\.\d{2}[DrCr]*)$')
            
            # State Machine Variables
            current_date = None
            description_buffer = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"      [Tool] Processing page {page_num}...")
                
                # Extract text preserving layout
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Step A: Date Detection
                    date_match = date_pattern.search(line)
                    if date_match:
                        # Found a new date, update state
                        # If detecting a date at the START of a line
                        current_date = date_match.group(0)
                        # We don't remove the date from the line yet, as it might be part of the description line
                        # But typically the date is a separate column.
                        # For now, we keep the line as is for further processing.
                    
                    # Step B: Transaction End Detection (Amount check)
                    # Check if line ends with a valid amount (Balance usually follows Amount, but sometimes just Amount)
                    # The user mentioned: "(Amount) (Balance)$ OR (Amount)$"
                    # Let's try to find amounts at the end of the line.
                    
                    # Find all potential amounts in the line
                    amounts = re.findall(r'([\d,]+\.\d{2}[DrCr]*)', line)
                    
                    is_transaction_end = False
                    txn_amount = None
                    txn_balance = None
                    
                    # Heuristic: A transaction line usually ends with Balance, and has Amount before it.
                    # Or just ends with Amount if no Balance column.
                    # We need to be careful not to trigger on dates or other numbers.
                    # The regex requires .XX decimals, which helps.
                    
                    if len(amounts) >= 1:
                        # Check strictly at the end of the line
                        if amount_pattern.search(line):
                            is_transaction_end = True
                            
                            if len(amounts) >= 2:
                                # Likely Amount and Balance
                                txn_balance = amounts[-1]
                                txn_amount = amounts[-2]
                            else:
                                # Just Amount (or Balance detected as Amount?)
                                # Assume it's the Transaction Amount
                                txn_amount = amounts[-1]
                                txn_balance = None # Unknown or not present
                    
                    # Step C: Decision
                    if is_transaction_end:
                        # This line marks the end of a transaction
                        
                        # Extract the text part (remove the amounts from the end)
                        # Remove txn_amount and txn_balance from the line string
                        clean_line = line
                        if txn_balance:
                            clean_line = clean_line.replace(txn_balance, '').strip()
                        if txn_amount:
                            clean_line = clean_line.replace(txn_amount, '').strip()
                            
                        # Remove Date if it was at the start (to avoid duplicating it in Description)
                        if current_date and clean_line.startswith(current_date):
                            clean_line = clean_line[len(current_date):].strip()
                        
                        # Combine buffer
                        full_description = " ".join(description_buffer + [clean_line])
                        
                        # Create Record
                        # Only if we have a date (or forward fill logic?)
                        # User said "Maintain a current_date variable".
                        if current_date:
                            record = {
                                'Date': current_date,
                                'Description': full_description.strip(),
                                'Amount': txn_amount,
                                'Balance': txn_balance
                            }
                            all_transactions.append(record)
                        
                        # Clear buffer
                        description_buffer = []
                        
                    else:
                        # This is a partial description line OR a header/junk line
                        # Skip known headers
                        upper_line = line.upper()
                        if 'BALANCE FORWARD' in upper_line or 'OPENING BALANCE' in upper_line:
                            continue
                        if 'DATE' in upper_line and 'DESCRIPTION' in upper_line: # Header row
                            continue
                        
                        # Add to buffer
                        # If it's a date-only line, we might have updated current_date but added text to buffer.
                        # If the line is JUST the date, we probably shouldn't add it to description.
                        if date_match and line.strip() == date_match.group(0):
                            pass # Just a date line, don't add to desc buffer
                        else:
                             # If line starts with date, strip it for description buffer
                            if current_date and line.startswith(current_date):
                                content = line[len(current_date):].strip()
                                if content:
                                    description_buffer.append(content)
                            else:
                                description_buffer.append(line)

            
            # Create DataFrame
            if all_transactions:
                df = pd.DataFrame(all_transactions)
                print(f"      [Tool] Extracted {len(df)} transactions using Text-Stream Strategy")
                
                # Check columns
                required_cols = ['Date', 'Description', 'Amount', 'Balance']
                for col in required_cols:
                    if col not in df.columns:
                        df[col] = None
                
                # Clean Data
                df = _clean_dataframe_v2(df)
                return df
            else:
                return "Error: No transactions found matching the Text-Stream logic."

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error reading PDF: {e}"


def _clean_dataframe_v2(df):
    """Clean and standardize the DataFrame (Version 2 for Text parsing)."""
    
    # Clean Amount and Balance
    for col in ['Amount', 'Balance']:
         if col in df.columns:
            # Handle Dr/Cr logic
            # Standard Chartered: 
            # Dr = Debit (Negative)
            # Cr = Credit (Positive) - usually? Or depends on account type.
            # Bank Statement Convention:
            # Deposits are Credits (+), Withdrawals are Debits (-)
            
            # Helper to convert string with Dr/Cr to float
            def parse_amount(val):
                if not val: return 0.0
                s = str(val).replace(',', '').strip()
                if not s: return 0.0
                
                # Extract sign from Dr/Cr
                mult = 1.0
                if s.upper().endswith('DR'):
                    mult = -1.0
                    s = s[:-2]
                elif s.upper().endswith('CR'):
                    mult = 1.0
                    s = s[:-2]
                # Sometimes just negative sign
                
                try:
                    return float(s) * mult
                except:
                    return 0.0

            df[col] = df[col].apply(parse_amount)

    # Standardize Dates
    if 'Date' in df.columns:
        # User explicitly requested support for "DD Mon YY"
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)

    # Ensure Description is clean string
    df['Description'] = df['Description'].fillna('').astype(str).str.strip()
    
    # Filter out Balance Forward / Opening Balance rows
    # These are not actual transactions and skew totals
    df = df[~df['Description'].str.upper().str.contains('BALANCE FORWARD|OPENING BALANCE|BROUGHT FORWARD|TOTAL')]
    df = df.reset_index(drop=True)
    
    # Infer Transaction Sign (Debit/Credit) based on Description and Balance
    if 'Amount' in df.columns:
        for i in range(len(df)):
            amt = df.at[i, 'Amount']
            if abs(amt) < 0.01: continue
            
            # If already negative (from Dr suffix), trust it
            if amt < 0: continue
            
            # Logic: Check Description for known keywords
            desc = str(df.at[i, 'Description']).upper()
            
            # Strong signal keywords
            is_withdrawal = any(kw in desc for kw in ['WITHDRAWAL', 'DEBIT', 'DR', 'PURCHASE', 'SPENT', 'PAYTM', 'UPI', 'POS ', 'BUS', 'METRO', 'UBER', 'OLA'])
            is_deposit = any(kw in desc for kw in ['DEPOSIT', 'CREDIT', 'CR', 'REFUND', 'REVERSAL', 'NEFT CR', 'IMPS CR', 'SALARY', 'INTEREST'])
            
            # If Description mentions both (e.g., "UPI... CR"), it's likely a credit/refund
            if 'CR' in desc.split() or 'CREDIT' in desc: 
                is_deposit = True
                is_withdrawal = False
                
            if is_withdrawal and not is_deposit:
                df.at[i, 'Amount'] = -abs(amt)
            elif is_deposit:
                df.at[i, 'Amount'] = abs(amt)
            else:
                # Fallback: Use Balance Difference if available
                # If Balance went DOWN, it's a withdrawal
                if i > 0 and 'Balance' in df.columns:
                    prev_bal = df.at[i-1, 'Balance']
                    curr_bal = df.at[i, 'Balance']
                    
                    if abs(prev_bal) > 0.01 or abs(curr_bal) > 0.01:
                        diff = curr_bal - prev_bal
                        # If diff is negative and matches amount magnitude
                        if diff < 0 and abs(diff + amt) < 1.0: # (e.g. -1500 + 1500 ~ 0)
                            df.at[i, 'Amount'] = -abs(amt)
                        # If diff is positive and matches amount magnitude
                        elif diff > 0 and abs(diff - amt) < 1.0:
                            df.at[i, 'Amount'] = abs(amt)
                            
    return df
