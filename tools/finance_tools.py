"""
Actual Finance Logic (Final - Improved for Offline Wealth Manager).
Uses a global state to share data between the standalone functions.
"""

import os
import webbrowser


# Global state to share data between tools
# This is required because the tools are independent functions
GLOBAL_STATE = {
    "df": None
}

__all__ = ["read_statement", "categorize_transactions", "generate_dashboard", "save_memory"]

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
            from tools.pdf_tools import read_pdf_statement
            df = read_pdf_statement(file_path, password)
            if isinstance(df, str):  # Error message
                return df
        
        else:
            return "Error: Unsupported format. Please use .csv, .xlsx, or .pdf"
        
        # Handle Type column (Credit/Debit) - convert amounts accordingly
        df = _normalize_amounts(df)
        
        GLOBAL_STATE["df"] = df
        return f"Successfully loaded {len(df)} transactions from {file_path.split('/')[-1].split(chr(92))[-1]}"
    
    except Exception as e:
        return f"Error reading file: {e}"





def _normalize_amounts(df):
    """
    Normalize amounts based on 'Type' column if present.
    Ensures Debits are negative and Credits are positive.
    """
    if df is None or df.empty:
        return df

    # check for Type column
    type_col = None
    for col in df.columns:
        if str(col).lower().strip() in ['type', 'transaction type', 'txn type', 'cr/dr']:
            type_col = col
            break
            
    if type_col and 'Amount' in df.columns:
        print(f"      [Tool] Normalizing amounts using column: {type_col}")
        
        # Helper to fix single row
        def fix_amount(row):
            try:
                # Get amount as float
                val = row['Amount']
                if isinstance(val, str):
                   val = float(val.replace(',', '').replace('₹', '').replace('$', '').strip())
                amt = float(val)
                
                txn_type = str(row[type_col]).lower().strip()
                
                # If it's a debit and amount is positive, make it negative
                if any(x in txn_type for x in ['debit', 'dr', 'withdrawal']) and amt > 0:
                    return -amt
                # If it's a credit and amount is negative (unlikely but possible), make it positive
                elif any(x in txn_type for x in ['credit', 'cr', 'deposit']) and amt < 0:
                    return -amt
                    
                return amt
            except Exception:
                return row['Amount']
                
        # Apply to all rows
        df['Amount'] = df.apply(fix_amount, axis=1)
        
    return df





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
    """Generates a Premium HTML Dashboard with pitch black theme and colorful cards."""
    import pandas as pd
    
    df = GLOBAL_STATE["df"]
    if df is None:
        return "Error: No data loaded."
    
    print("      [Tool] Creating Premium Dashboard...")
    
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
    
    net_balance = total_income - total_spent
    
    # Category data for charts
    category_data = {}
    if 'Category' in df.columns:
        if 'Amount' in df.columns:
            cat_spending = df[df['Amount'] < 0].groupby('Category')['Amount'].sum().abs()
        elif 'Withdrawal' in df.columns:
            cat_spending = df.groupby('Category')['Withdrawal'].sum()
        else:
            cat_spending = df.groupby('Category').size()
        category_data = cat_spending.to_dict()
    
    # Generate category labels and values for Chart.js
    cat_labels = list(category_data.keys()) if category_data else ['No Data']
    cat_values = list(category_data.values()) if category_data else [0]
    
    # Color palette for categories (vibrant neon colors)
    colors = [
        '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
        '#dfe6e9', '#fd79a8', '#a29bfe', '#6c5ce7', '#00b894',
        '#e17055', '#74b9ff', '#ff7675', '#55efc4', '#81ecec'
    ]
    
    cat_colors = colors[:len(cat_labels)]
    
    # --- MEMORY INTELLIGENCE START ---
    insights_html = ""
    try:
        # Load Memory Store
        try:
            from memory.memory_store import MemoryStore
            store = MemoryStore("data/memory.json")
            
            # 1. Recurring Transactions Insight
            recurring_txs = store.get_recurring_transactions()
            recurring_html = ""
            if recurring_txs:
                for tx in recurring_txs:
                    recurring_html += f'''
                    <div class="insight-item">
                        <div class="insight-icon">🔄</div>
                        <div class="insight-content">
                            <span class="insight-title">{tx['description']}</span>
                            <span class="insight-subtitle">{tx.get('frequency', 'Monthly')} Subscription</span>
                        </div>
                        <span class="insight-amount">₹{tx['amount']:,.2f}</span>
                    </div>'''
            else:
                recurring_html = '<p class="no-data">No recurring transactions identified yet.</p>'

            # 2. Spending Trends Insight
            trends_html = ""
            history = store.get_spending_history()
            
            # Compare current category spending to history
            if category_data:
                for cat, amount in category_data.items():
                    # Check if we have history for this category
                    cat_history = history.get(str(cat), [])
                    if cat_history:
                        # Calculate average of previous months (excluding this one if possible, but simplified here)
                        amounts = [h['amount'] for h in cat_history]
                        avg_spending = sum(amounts) / len(amounts)
                        
                        if avg_spending > 0:
                            diff_percent = ((amount - avg_spending) / avg_spending) * 100
                            
                            if abs(diff_percent) > 10: # Only significant trends
                                trend_color = "#ff6b6b" if diff_percent > 0 else "#00b894"
                                trend_icon = "📈" if diff_percent > 0 else "📉"
                                trend_text = "Higher" if diff_percent > 0 else "Lower"
                                
                                trends_html += f'''
                                <div class="insight-item">
                                    <div class="insight-icon">{trend_icon}</div>
                                    <div class="insight-content">
                                        <span class="insight-title">{cat}</span>
                                        <span class="insight-subtitle" style="color: {trend_color}">
                                            {abs(diff_percent):.1f}% {trend_text} than average
                                        </span>
                                    </div>
                                    <span class="insight-amount">₹{amount:,.2f}</span>
                                </div>'''
            
            if not trends_html:
                trends_html = '<p class="no-data">Not enough data for trend analysis.</p>'

            # Assemble the Insights Section
            insights_html = f'''
            <div class="insights-grid">
                <div class="insight-card">
                    <h2>🧠 Brain: Spending Trends</h2>
                    <div class="insight-list">
                        {trends_html}
                    </div>
                </div>
                <div class="insight-card">
                    <h2>🔄 Detected Subscriptions</h2>
                    <div class="insight-list">
                        {recurring_html}
                    </div>
                </div>
            </div>
            '''
            print(f"      [Tool] Generated Smart Insights from Memory")
            
        except ImportError:
            pass # Memory module not available or path issue
            print(f"      [Tool] Memory module not found, skipping insights.")
            
    except Exception as e:
        print(f"      [Tool] Error generating insights: {e}")
        insights_html = ""
    # --- MEMORY INTELLIGENCE END ---

    # Get top 5 expenses
    top_expenses_html = ""
    if 'Amount' in df.columns:
        expenses = df[df['Amount'] < 0].nsmallest(5, 'Amount')
    elif 'Withdrawal' in df.columns:
        expenses = df[df['Withdrawal'] > 0].nlargest(5, 'Withdrawal')
    else:
        expenses = df.head(5)
    
    for idx, row in expenses.iterrows():
        desc = row.get('Description', 'Unknown')[:40]
        if 'Amount' in df.columns:
            amt = abs(row['Amount'])
        elif 'Withdrawal' in df.columns:
            amt = row['Withdrawal']
        else:
            amt = 0
        cat = row.get('Category', 'Other')
        color_idx = cat_labels.index(cat) if cat in cat_labels else 0
        top_expenses_html += f'''
            <div class="expense-item">
                <div class="expense-color" style="background: {colors[color_idx % len(colors)]};"></div>
                <div class="expense-details">
                    <span class="expense-desc">{desc}</span>
                    <span class="expense-cat">{cat}</span>
                </div>
                <span class="expense-amount">₹{amt:,.2f}</span>
            </div>
        '''
    
    # Format transactions table
    display_df = df.copy()
    
    for col in ['Amount', 'Withdrawal', 'Deposit', 'Balance']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f'₹{x:,.2f}' if pd.notna(x) else '')
    
    for col in ['Date', 'ValueDate']:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors='coerce')
            display_df[col] = display_df[col].apply(lambda x: x.strftime('%d %b %Y') if pd.notna(x) else '')
    
    # Select key columns for display
    display_cols = ['Date', 'Description', 'Category']
    if 'Amount' in display_df.columns:
        display_cols.append('Amount')
    else:
        if 'Withdrawal' in display_df.columns:
            display_cols.append('Withdrawal')
        if 'Deposit' in display_df.columns:
            display_cols.append('Deposit')
    if 'Balance' in display_df.columns:
        display_cols.append('Balance')
    
    display_cols = [c for c in display_cols if c in display_df.columns]
    display_df = display_df[display_cols]
    
    # Generate table rows
    table_rows = ""
    for _, row in display_df.iterrows():
        cells = ""
        for col in display_cols:
            val = row[col] if pd.notna(row[col]) else ""
            # Add color coding for amounts
            cell_class = ""
            if col == 'Amount':
                if '₹-' in str(val) or (isinstance(val, (int, float)) and val < 0):
                    cell_class = 'negative'
                elif '₹' in str(val):
                    cell_class = 'positive'
            elif col == 'Withdrawal' and val and val != '₹0.00':
                cell_class = 'negative'
            elif col == 'Deposit' and val and val != '₹0.00':
                cell_class = 'positive'
            cells += f'<td class="{cell_class}">{val}</td>'
        table_rows += f'<tr>{cells}</tr>'
    
    # Generate table headers
    table_headers = "".join([f'<th>{col}</th>' for col in display_cols])
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #000000;
            color: #ffffff;
            min-height: 100vh;
            padding: 24px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f64f59 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }}
        
        .header p {{
            color: #6b7280;
            font-size: 0.95rem;
        }}
        
        /* Summary Cards Grid */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 32px;
        }}
        
        @media (max-width: 1024px) {{
            .summary-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        @media (max-width: 640px) {{
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 20px;
            padding: 24px;
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }}
        
        .summary-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            border-radius: 20px 20px 0 0;
        }}
        
        .summary-card.transactions::before {{ background: linear-gradient(90deg, #667eea, #764ba2); }}
        .summary-card.income::before {{ background: linear-gradient(90deg, #00b894, #55efc4); }}
        .summary-card.spending::before {{ background: linear-gradient(90deg, #ff6b6b, #ee5a24); }}
        .summary-card.balance::before {{ background: linear-gradient(90deg, #a29bfe, #6c5ce7); }}
        
        .card-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            margin-bottom: 16px;
        }}
        
        .transactions .card-icon {{ background: rgba(102, 126, 234, 0.2); }}
        .income .card-icon {{ background: rgba(0, 184, 148, 0.2); }}
        .spending .card-icon {{ background: rgba(255, 107, 107, 0.2); }}
        .balance .card-icon {{ background: rgba(162, 155, 254, 0.2); }}
        
        .card-label {{
            font-size: 0.85rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        
        .card-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: #ffffff;
        }}
        
        .card-value.positive {{ color: #00b894; }}
        .card-value.negative {{ color: #ff6b6b; }}
        
        /* Insights Section */
        .insights-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }}

        @media (max-width: 900px) {{
            .insights-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .insight-card {{
            background: linear-gradient(135deg, #2d3436 0%, #000000 100%);
            border-radius: 20px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }}
        
        .insight-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(180deg, #fd79a8, #6c5ce7);
        }}

        .insight-card h2 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #e5e7eb;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .insight-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .insight-item {{
            display: flex;
            align-items: center;
            padding: 12px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            transition: background 0.2s;
        }}
        
        .insight-item:hover {{
            background: rgba(255, 255, 255, 0.06);
        }}

        .insight-icon {{
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.05);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            margin-right: 12px;
        }}

        .insight-content {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}

        .insight-title {{
            font-size: 0.9rem;
            color: #ffffff;
            font-weight: 500;
        }}

        .insight-subtitle {{
            font-size: 0.75rem;
            color: #a0a0a0;
            margin-top: 2px;
        }}

        .insight-amount {{
            font-weight: 600;
            color: #e5e7eb;
            font-size: 0.9rem;
        }}

        .no-data {{
            color: #6b7280;
            font-style: italic;
            font-size: 0.9rem;
        }}

        /* Charts Section */
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }}
        
        @media (max-width: 900px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .chart-card {{
            background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
            border-radius: 20px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .chart-card h2 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #e5e7eb;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .chart-container {{
            position: relative;
            height: 280px;
        }}
        
        /* Top Expenses */
        .expenses-card {{
            background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
            border-radius: 20px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 32px;
        }}
        
        .expenses-card h2 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #e5e7eb;
        }}
        
        .expense-item {{
            display: flex;
            align-items: center;
            padding: 14px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .expense-item:last-child {{
            border-bottom: none;
        }}
        
        .expense-color {{
            width: 4px;
            height: 40px;
            border-radius: 4px;
            margin-right: 16px;
        }}
        
        .expense-details {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        
        .expense-desc {{
            font-weight: 500;
            color: #e5e7eb;
            font-size: 0.95rem;
        }}
        
        .expense-cat {{
            font-size: 0.8rem;
            color: #6b7280;
            margin-top: 4px;
        }}
        
        .expense-amount {{
            font-weight: 600;
            color: #ff6b6b;
            font-size: 1rem;
        }}
        
        /* Transactions Table */
        .table-card {{
            background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
            border-radius: 20px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            overflow: hidden;
        }}
        
        .table-card h2 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #e5e7eb;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            max-height: 500px;
            overflow-y: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        
        th {{
            text-align: left;
            padding: 14px 16px;
            background: rgba(102, 126, 234, 0.15);
            color: #a78bfa;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        td {{
            padding: 14px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            color: #d1d5db;
        }}
        
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        
        td.positive {{
            color: #00b894;
            font-weight: 500;
        }}
        
        td.negative {{
            color: #ff6b6b;
            font-weight: 500;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 24px;
            color: #4b5563;
            font-size: 0.85rem;
        }}
        
        /* Scrollbar Styling */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #1a1a2e;
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: #374151;
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: #4b5563;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 Financial Dashboard</h1>
            <p>Comprehensive analysis of your transactions</p>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card transactions">
                <div class="card-icon">📊</div>
                <div class="card-label">Total Transactions</div>
                <div class="card-value">{total_tx}</div>
            </div>
            <div class="summary-card income">
                <div class="card-icon">💵</div>
                <div class="card-label">Total Income</div>
                <div class="card-value positive">₹{total_income:,.2f}</div>
            </div>
            <div class="summary-card spending">
                <div class="card-icon">💸</div>
                <div class="card-label">Total Spending</div>
                <div class="card-value negative">₹{total_spent:,.2f}</div>
            </div>
            <div class="summary-card balance">
                <div class="card-icon">💰</div>
                <div class="card-label">Net Balance</div>
                <div class="card-value {'positive' if net_balance >= 0 else 'negative'}">₹{net_balance:,.2f}</div>
            </div>
        </div>
        
        {insights_html}
        
        <div class="charts-grid">
            <div class="chart-card">
                <h2>📈 Spending by Category</h2>
                <div class="chart-container">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h2>📊 Category Breakdown</h2>
                <div class="chart-container">
                    <canvas id="barChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="expenses-card">
            <h2>🔥 Top Expenses</h2>
            {top_expenses_html if top_expenses_html else '<p style="color: #6b7280;">No expense data available</p>'}
        </div>
        
        <div class="table-card">
            <h2>📋 All Transactions</h2>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>{table_headers}</tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Autonomous Finance Agent • {pd.Timestamp.now().strftime('%d %b %Y, %I:%M %p')}</p>
        </div>
    </div>
    
    <script>
        // Chart.js Configuration
        Chart.defaults.color = '#9ca3af';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.05)';
        
        // Category Donut Chart
        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
        new Chart(categoryCtx, {{
            type: 'doughnut',
            data: {{
                labels: {cat_labels},
                datasets: [{{
                    data: {cat_values},
                    backgroundColor: {cat_colors},
                    borderWidth: 0,
                    hoverOffset: 10
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{
                            padding: 15,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {{ size: 11 }}
                        }}
                    }}
                }}
            }}
        }});
        
        // Category Bar Chart
        const barCtx = document.getElementById('barChart').getContext('2d');
        new Chart(barCtx, {{
            type: 'bar',
            data: {{
                labels: {cat_labels},
                datasets: [{{
                    label: 'Amount (₹)',
                    data: {cat_values},
                    backgroundColor: {cat_colors},
                    borderRadius: 8,
                    borderSkipped: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ 
                            callback: function(value) {{ return '₹' + value.toLocaleString(); }}
                        }}
                    }},
                    y: {{
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    # Ensure reports directory exists
    os.makedirs("reports", exist_ok=True)
    
    out_file = "reports/dashboard.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    # Open automatically in browser
    abs_path = os.path.abspath(out_file)
    import time
    timestamp = int(time.time())
    
    print(f"      [Tool] Dashboard saved to {out_file}")
    print(f"      [Tool] Opening in browser...")
    
    try:
        webbrowser.open(f"file://{abs_path}?v={timestamp}")
    except Exception as e:
        print(f"      [Tool] webbrowser.open warning: {e}")
    
    try:
        import subprocess
        subprocess.Popen(['start', '', abs_path], shell=True)
    except Exception as e2:
        print(f"      [Tool] subprocess fallback warning: {e2}")
    
    return f"Dashboard generated successfully at {out_file}. Check your browser!"


def save_memory(dummy_arg=None):
    """
    Saves the current financial analysis to persistent memory.
    Connects to the MemoryManager to store insights and patterns.
    """
    import pandas as pd
    try:
        from memory.memory_store import MemoryStore
    except ImportError:
        # Fallback if running relative
        try:
            import sys
            import os
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from memory.memory_store import MemoryStore
        except Exception as e:
            return f"Error importing MemoryStore: {e}"

    df = GLOBAL_STATE["df"]
    if df is None:
        return "Error: No data loaded to save."

    print("      [Tool] Saving analysis to memory...")
    
    # Initialize store
    try:
        # We assume standard path structure
        store = MemoryStore("data/memory.json")
    except Exception as e:
        return f"Error initializing MemoryStore: {e}"

    # Calculate Summary Stats
    total_tx = len(df)
    
    if 'Amount' in df.columns:
        income = df[df['Amount'] > 0]['Amount'].sum()
        spending = abs(df[df['Amount'] < 0]['Amount'].sum())
    else:
        income = 0
        spending = 0
        
    # Store Transaction Summary
    summary = {
        "total_transactions": int(total_tx),
        "total_income": float(income),
        "total_spending": float(spending),
        "net_balance": float(income - spending),
        "analyzed_at": pd.Timestamp.now().isoformat()
    }
    store.add_transaction_summary(summary)
    
    # Store Category Spending Patterns
    if 'Category' in df.columns and 'Amount' in df.columns:
        cat_spending = df[df['Amount'] < 0].groupby('Category')['Amount'].sum().abs()
        for cat, amount in cat_spending.items():
            store.add_spending_pattern(str(cat), float(amount))
            
    # Detect and Store Recurring Transactions (Simple heuristic)
    if 'Description' in df.columns and 'Amount' in df.columns:
        # Group by description and count
        recurrence = df.groupby('Description').size()
        recurring = recurrence[recurrence >= 2]
        
        for desc, count in recurring.items():
            # Get average amount
            avg_amt = df[df['Description'] == desc]['Amount'].mean()
            # Determine frequency (simplified)
            freq = "unknown" 
            store.add_recurring_transaction(str(desc), float(abs(avg_amt)), freq)
            print(f"      [Memory] Identified recurring transaction: {desc}")

    return "Analysis saved to persistent memory successfully."
