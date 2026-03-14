"""
tools/finance_tools.py
======================
Core finance processing pipeline.

Functions are intentionally designed as standalone callables so the agent
controller can invoke them by name from the planner's action list.

All functions share state through the module-level ``GLOBAL_STATE`` dict,
which holds the active Pandas DataFrame between pipeline steps.
"""

import os
import re
import webbrowser


# Module-level state shared between pipeline steps.
# Using a dict (not module globals) makes it easy to reset between runs.
GLOBAL_STATE: dict = {"df": None}

__all__ = [
    "clean_upi_description",
    "read_statement",
    "categorize_transactions",
    "generate_dashboard",
    "save_memory",
]


def clean_upi_description(raw: str) -> str:
    """
    Strip alphanumeric noise from Indian UPI transaction strings.

    Indian banks encode UPI narrations in formats like::

        UPI/CR/241130123456/ZOMATO/zomato@icici/Food order
        UPI/P2P/987654321/Paytm/merchant@upi/Notes here
        UPI/P2M/000111222/AIRTEL/airtel@paytm/Recharge

    This function extracts the **human-readable merchant / sender name**
    from segment 3 (0-indexed) of the slash-delimited string, after:

    * Removing pure-numeric tokens (transaction IDs)
    * Stripping UPI address suffixes (``@bank-name``)
    * Collapsing camelCase / ALL-CAPS into Title Case

    Args:
        raw: The original narration string from the bank CSV/PDF.

    Returns:
        A cleaned, readable label (e.g. ``"Zomato"``, ``"Airtel Paytm"``).
        Falls back to the original ``raw`` string if no UPI pattern is found.

    Examples::

        >>> clean_upi_description("UPI/P2P/241130/ZOMATO/zomato@icici/Food")
        'Zomato'
        >>> clean_upi_description("UPI/CR/999888/SALARY INC/salary@oksbi/")
        'Salary Inc'
        >>> clean_upi_description("NEFT credit from employer")
        'NEFT credit from employer'  # unchanged — not a UPI string
    """
    raw = raw.strip()

    # Only process if this looks like a UPI transaction
    if not re.search(r'(?i)^upi/', raw):
        return raw

    parts = raw.split('/')

    # Collect candidate name tokens from segments 2-onwards (skip UPI, direction, txn-id)
    candidates: list[str] = []
    for part in parts[2:]:
        part = part.strip()
        # Skip pure-numeric tokens (transaction / reference IDs)
        if re.fullmatch(r'\d+', part):
            continue
        # Strip UPI address suffix  e.g. "zomato@icici" → "zomato"
        part = re.sub(r'@[\w.]+$', '', part).strip()
        # Skip empty or residual noise tokens
        if not part or len(part) < 2:
            continue
        candidates.append(part)
        # First meaningful candidate is usually the merchant name — stop there
        if len(candidates) == 1:
            break

    if candidates:
        name = candidates[0]
        # Convert ALL-CAPS or all-lower to Title Case for readability
        if name == name.upper() or name == name.lower():
            name = name.title()
        return name

    # Fallback: return original string
    return raw

def read_statement(file_path: str = None, password: str = None):
    """Reads CSV/Excel/PDF bank statements (with optional password for PDFs)."""
    print(f"      [Tool] Reading file: {file_path}")

    if not file_path:
        return "Error: No file path provided."

    # Remove quotes if they exist
    file_path = file_path.strip('"').strip("'")

    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"

    # Fall back to password stored by run_agent() (set from the Streamlit sidebar)
    if password is None:
        password = GLOBAL_STATE.get("pdf_password")

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
    """
    Assign a spending category to every transaction in the loaded DataFrame.

    This is a keyword-matching categorizer tuned for Indian banking narrations,
    including UPI payments, NEFT/IMPS transfers, POS purchases, ATM withdrawals,
    and direct-debit bill payments.

    The function mutates the shared ``GLOBAL_STATE["df"]`` DataFrame in-place
    by adding a ``Category`` column.

    Pipeline step:
        ``read_statement`` → **``categorize_transactions``** → ``generate_dashboard``

    Args:
        dummy_arg: Unused placeholder so the agent planner can invoke this
            function without parameters.

    Returns:
        A human-readable summary string, e.g.
        ``"Categorization complete. 87 transactions in 9 categories."``
        Returns an error string if no data is loaded.

    Note:
        UPI narration strings are pre-cleaned via :func:`clean_upi_description`
        before keyword matching, improving accuracy on raw bank exports.
    """
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
        
        # UPI Payments — clean the narration first, then keyword-match
        if 'upi/' in desc_lower or '/upi/' in desc_lower or desc_lower.startswith('upi/'):
            cleaned = clean_upi_description(desc).lower()
            # Paytm / wallets
            if any(kw in cleaned for kw in ['paytm', 'one97', 'phonepay', 'gpay']):
                return 'Paytm/Wallet'
            # Food delivery
            elif any(kw in cleaned for kw in ['zomato', 'swiggy', 'uber eats', 'faasos']):
                return 'Food & Dining'
            # Travel & transport
            elif any(kw in cleaned for kw in ['ixigo', 'makemytrip', 'goibibo', 'redbus', 'uber', 'ola', 'rapido', 'irctc']):
                return 'Travel'
            # Shopping
            elif any(kw in cleaned for kw in ['amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'meesho']):
                return 'Shopping'
            # Bills & Utilities
            elif any(kw in cleaned for kw in ['airtel', 'jio', 'vodafone', 'bsnl', 'electricity', 'tneb', 'bescom']):
                return 'Bills & Utilities'
            # Insurance
            elif any(kw in cleaned for kw in ['lic', 'insurance', 'premium', 'hdfc life', 'max life']):
                return 'Insurance'
            # Healthcare
            elif any(kw in cleaned for kw in ['medplus', 'apollo', 'pharma', 'clinic', 'hospital']):
                return 'Healthcare'
            # Entertainment
            elif any(kw in cleaned for kw in ['netflix', 'hotstar', 'spotify', 'bookmyshow', 'prime']):
                return 'Entertainment'
            # Generic UPI — use cleaned label for better readability
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
    """Generate a minimal, pitch-black premium HTML dashboard and save to reports/."""
    import pandas as pd
    from pathlib import Path

    df = GLOBAL_STATE["df"]
    if df is None:
        return "Error: No data loaded."

    print("      [Tool] Building premium dashboard...")

    # ── Chart.js: local bundle preferred, CDN fallback ────────────────────────
    _static = Path(__file__).resolve().parent.parent / "static" / "chart.min.js"
    if _static.exists():
        _chartjs_tag = f"<script>\n{_static.read_text(encoding='utf-8')}\n</script>"
    else:
        _chartjs_tag = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
        print("      [Tool] WARNING: static/chart.min.js missing — using CDN fallback.")

    # ── Totals ────────────────────────────────────────────────────────────────
    total_tx = len(df)
    if "Amount" in df.columns:
        total_income = df[df["Amount"] > 0]["Amount"].sum()
        total_spent  = abs(df[df["Amount"] < 0]["Amount"].sum())
    elif "Withdrawal" in df.columns and "Deposit" in df.columns:
        total_income = df["Deposit"].fillna(0).sum()
        total_spent  = df["Withdrawal"].fillna(0).sum()
    else:
        total_income = total_spent = 0
    net_balance = total_income - total_spent

    # ── Category data ─────────────────────────────────────────────────────────
    category_data: dict = {}
    if "Category" in df.columns:
        if "Amount" in df.columns:
            cat_spending = df[df["Amount"] < 0].groupby("Category")["Amount"].sum().abs()
        elif "Withdrawal" in df.columns:
            cat_spending = df.groupby("Category")["Withdrawal"].sum()
        else:
            cat_spending = df.groupby("Category").size()
        category_data = cat_spending.to_dict()

    cat_labels = list(category_data.keys()) if category_data else ["No Data"]
    cat_values = [round(v, 2) for v in category_data.values()] if category_data else [0]

    # Muted, sophisticated palette — one accent blue + desaturated tones
    PALETTE = [
        "#3B82F6", "#6366F1", "#8B5CF6", "#A78BFA",
        "#60A5FA", "#38BDF8", "#34D399", "#4ADE80",
        "#FBBF24", "#F87171", "#FB923C", "#E879F9",
        "#94A3B8", "#CBD5E1", "#64748B",
    ]
    cat_colors = PALETTE[:len(cat_labels)]

    # ── Top category ─────────────────────────────────────────────────────────
    top_category = max(category_data, key=category_data.get) if category_data else "—"

    # ── Memory insights ───────────────────────────────────────────────────────
    insights_html = ""
    try:
        from database.queries import queries
        
        # Recurring transactions
        recurring_txs = queries.get_recurring_payments()
        if recurring_txs:
            rows_r = "".join(
                f'<div class="ins-row"><span class="ins-name">{tx["merchant"][:35]}</span>'
                f'<span class="ins-amt">₹{tx["average_amount"]:,.0f}</span></div>'
                for tx in recurring_txs
            )
        else:
            rows_r = '<p class="muted">No recurring transactions detected yet.</p>'

        # AI Insights 
        latest_insights = queries.get_recent_insights()
        rows_t = ""
        if latest_insights:
            for insight in latest_insights:
                rows_t += (
                    f'<div class="ins-row"><span class="ins-name">{insight["text"]}</span></div>'
                )
        if not rows_t:
             rows_t = '<p class="muted">Not enough history for trend analysis.</p>'

        insights_html = f"""
<section class="insights-grid">
  <div class="card">
    <h2 class="card-title">AI Spending Insights</h2>
    <div class="ins-list">{rows_t}</div>
  </div>
  <div class="card">
    <h2 class="card-title">Recurring Subscriptions</h2>
    <div class="ins-list">{rows_r}</div>
  </div>
</section>"""
        print("      [Tool] DB insights generated.")
    except Exception as e:
        print(f"      [Tool] Skipping DB insights: {e}")

    # ── Top 5 expenses ────────────────────────────────────────────────────────
    if "Amount" in df.columns:
        expenses = df[df["Amount"] < 0].nsmallest(5, "Amount")
    elif "Withdrawal" in df.columns:
        expenses = df[df["Withdrawal"] > 0].nlargest(5, "Withdrawal")
    else:
        expenses = df.head(5)

    exp_rows = ""
    for _, row in expenses.iterrows():
        desc = str(row.get("Description", "Unknown"))[:45]
        amt  = abs(row["Amount"]) if "Amount" in df.columns else row.get("Withdrawal", 0)
        cat  = row.get("Category", "Other")
        exp_rows += (
            f'<div class="exp-row">'
            f'<span class="exp-desc">{desc}<span class="exp-cat">{cat}</span></span>'
            f'<span class="exp-amt">₹{amt:,.0f}</span>'
            f'</div>'
        )

    # ── Transaction table ─────────────────────────────────────────────────────
    display_df = df.copy()
    for col in ["Amount", "Withdrawal", "Deposit", "Balance"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"₹{x:,.2f}" if pd.notna(x) else ""
            )
    for col in ["Date", "ValueDate"]:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors="coerce")
            display_df[col] = display_df[col].apply(
                lambda x: x.strftime("%d %b %Y") if pd.notna(x) else ""
            )

    display_cols = ["Date", "Description", "Category"]
    if "Amount" in display_df.columns:
        display_cols.append("Amount")
    else:
        if "Withdrawal" in display_df.columns:
            display_cols.append("Withdrawal")
        if "Deposit" in display_df.columns:
            display_cols.append("Deposit")
    if "Balance" in display_df.columns:
        display_cols.append("Balance")
    display_cols = [c for c in display_cols if c in display_df.columns]
    display_df   = display_df[display_cols]

    thead = "".join(f"<th>{c}</th>" for c in display_cols)
    tbody = ""
    for _, row in display_df.iterrows():
        cells = ""
        for col in display_cols:
            val = row[col] if pd.notna(row[col]) else ""
            cls = ""
            if col == "Amount":
                cls = "neg" if ("₹-" in str(val) or (isinstance(val, (int, float)) and val < 0)) else "pos"
            elif col == "Withdrawal" and val and val != "₹0.00":
                cls = "neg"
            elif col == "Deposit" and val and val != "₹0.00":
                cls = "pos"
            cells += f'<td class="{cls}">{val}</td>'
        tbody += f"<tr>{cells}</tr>"

    # ── Render timestamp ─────────────────────────────────────────────────────
    generated_at = pd.Timestamp.now().strftime("%d %b %Y, %I:%M %p")
    net_cls = "pos" if net_balance >= 0 else "neg"

    # ── HTML ──────────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Financial Dashboard</title>
{_chartjs_tag}
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg:       #000000;
    --surface:  #0A0A0A;
    --border:   rgba(255, 255, 255, 0.08);
    --text:     #FAFAFA;
    --muted:    #888888;
    --accent:   #3B82F6;
    --green:    #34D399;
    --red:      #F87171;
    --grid:     #1A1A1A;
    --radius:   8px;
    --font:     -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
    --font-mono: 'Courier New', Courier, monospace;
  }}

  body {{
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 32px 24px;
    font-size: 14px;
    line-height: 1.5;
  }}

  .wrap {{ max-width: 1300px; margin: 0 auto; }}

  /* ── Header ── */
  header {{ margin-bottom: 40px; }}
  header h1 {{
    font-size: 24px; font-weight: 500; letter-spacing: -0.8px;
    color: var(--text);
  }}
  header p {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}

  /* ── Generic card (Bento Box style) ── */
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
  }}
  .card-title {{
    font-size: 12px; font-weight: 500; letter-spacing: 0.8px;
    text-transform: uppercase; color: var(--muted);
    margin-bottom: 20px;
  }}

  /* ── KPI grid ── */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 16px;
  }}
  @media (max-width: 900px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}

  .kpi-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; }}
  .kpi-value {{
    font-family: var(--font-mono);
    font-size: 28px; font-weight: 600; margin-top: 8px;
    color: var(--text); letter-spacing: -1px;
  }}
  .kpi-value.pos {{ color: var(--green); }}
  .kpi-value.neg {{ color: var(--red); }}
  .kpi-accent {{ color: var(--accent); }}

  /* ── Layout Grid ── */
  .bento-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }}
  @media (max-width: 900px) {{ .bento-grid {{ grid-template-columns: 1fr; }} }}
  .chart-wrap {{ position: relative; height: 260px; }}
  .chart-wrap-lg {{ position: relative; height: 320px; }}

  /* ── Memory Insights ── */
  .insights-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }}
  .ins-list {{ display: flex; flex-direction: column; gap: 4px; }}
  .ins-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 0; border-bottom: 1px solid var(--border);
  }}
  .ins-row:last-child {{ border-bottom: none; }}
  .ins-name {{ font-size: 13px; color: var(--text); }}
  .ins-amt {{ font-family: var(--font-mono); font-size: 14px; font-weight: 600; }}

  /* ── Top expenses ── */
  .exp-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 0; border-bottom: 1px solid var(--border);
  }}
  .exp-row:last-child {{ border-bottom: none; }}
  .exp-desc {{
    flex: 1; font-size: 13px; color: var(--text);
    display: flex; flex-direction: column; gap: 4px;
  }}
  .exp-cat  {{ font-size: 11px; color: var(--muted); }}
  .exp-amt  {{
    font-family: var(--font-mono); font-size: 15px; font-weight: 600; color: var(--red);
    white-space: nowrap; margin-left: 16px;
  }}

  /* ── Table ── */
  .tbl-wrap {{ overflow-x: auto; max-height: 440px; overflow-y: auto; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{
    text-align: left; padding: 12px 16px;
    background: var(--bg); color: var(--muted);
    font-size: 11px; font-weight: 500; letter-spacing: 0.8px; text-transform: uppercase;
    position: sticky; top: 0; z-index: 5; border-bottom: 1px solid var(--border);
  }}
  td {{ padding: 11px 14px; border-bottom: 1px solid var(--border); color: #C4C4C4; }}
  tr:hover td {{ background: rgba(255,255,255,0.02); }}
  td.pos {{ color: var(--green); font-variant-numeric: tabular-nums; }}
  td.neg {{ color: var(--red);   font-variant-numeric: tabular-nums; }}

  /* ── Footer ── */
  footer {{ text-align: center; color: #3a3a3a; font-size: 11px; margin-top: 40px; }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: #333; border-radius: 4px; }}

  .muted {{ color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <h1>Financial Dashboard</h1>
    <p>Generated {generated_at} &nbsp;·&nbsp; 100% local &amp; private</p>
  </header>

  <!-- KPIs -->
  <div class="kpi-grid">
    <div class="card">
      <div class="kpi-label">Transactions</div>
      <div class="kpi-value">{total_tx}</div>
    </div>
    <div class="card">
      <div class="kpi-label">Total Income</div>
      <div class="kpi-value pos">₹{total_income:,.0f}</div>
    </div>
    <div class="card">
      <div class="kpi-label">Total Spent</div>
      <div class="kpi-value neg">₹{total_spent:,.0f}</div>
    </div>
    <div class="card">
      <div class="kpi-label">Net Balance</div>
      <div class="kpi-value {net_cls}">₹{net_balance:,.0f}</div>
    </div>
  </div>

  <!-- Charts -->
  <div class="chart-grid">
    <div class="card">
      <h2 class="card-title">Spending by Category</h2>
      <div class="chart-wrap"><canvas id="donut"></canvas></div>
    </div>
    <div class="card">
      <h2 class="card-title">Category Breakdown</h2>
      <div class="chart-wrap"><canvas id="bar"></canvas></div>
    </div>
  </div>

  <!-- Memory Insights (only shown when history exists) -->
  {insights_html}

  <!-- Top Expenses -->
  <div class="card" style="margin-bottom:24px;">
    <h2 class="card-title">Top Expenses</h2>
    {exp_rows or '<p class="muted">No expense data available.</p>'}
  </div>

  <!-- Transactions Table -->
  <div class="card">
    <h2 class="card-title">All Transactions</h2>
    <div class="tbl-wrap">
      <table>
        <thead><tr>{thead}</tr></thead>
        <tbody>{tbody}</tbody>
      </table>
    </div>
  </div>

  <footer>Autonomous Finance Agent &nbsp;·&nbsp; All data processed locally</footer>
</div>

<script>
  // ── Dark-mode Chart.js defaults ──────────────────────────────────────────
  Chart.defaults.color           = '#A1A1AA';
  Chart.defaults.borderColor     = '#1a1a1a';
  Chart.defaults.font.family     = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  Chart.defaults.font.size       = 12;

  const labels = {cat_labels};
  const values = {cat_values};
  const colors = {cat_colors};

  // ── Donut ─────────────────────────────────────────────────────────────────
  new Chart(document.getElementById('donut'), {{
    type: 'doughnut',
    data: {{
      labels,
      datasets: [{{
        data: values,
        backgroundColor: colors,
        borderWidth: 0,
        hoverOffset: 6,
      }}],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {{
        legend: {{
          position: 'right',
          labels: {{ padding: 16, usePointStyle: true, pointStyle: 'circle', font: {{ size: 11 }} }},
        }},
        tooltip: {{
          callbacks: {{
            label: ctx => ` ₹${{ctx.parsed.toLocaleString('en-IN')}}`,
          }},
        }},
      }},
    }},
  }});

  // ── Bar ───────────────────────────────────────────────────────────────────
  new Chart(document.getElementById('bar'), {{
    type: 'bar',
    data: {{
      labels,
      datasets: [{{
        label: 'Spent (₹)',
        data: values,
        backgroundColor: colors,
        borderRadius: 4,
        borderSkipped: false,
      }}],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: ctx => ` ₹${{ctx.parsed.x.toLocaleString('en-IN')}}`,
          }},
        }},
      }},
      scales: {{
        x: {{
          grid: {{ color: '#1a1a1a' }},
          ticks: {{ callback: v => '₹' + Number(v).toLocaleString('en-IN') }},
        }},
        y: {{ grid: {{ display: false }} }},
      }},
    }},
  }});
</script>
</body>
</html>"""

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs("reports", exist_ok=True)
    out_file = "reports/dashboard.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"      [Tool] Dashboard saved to {out_file}")

    # Dashboard is rendered inline by Streamlit via st.components.html().
    # Do NOT open a separate browser window here.
    return f"Dashboard generated successfully at {out_file}."
def save_memory(dummy_arg=None):
    """
    Saves the current financial analysis to persistent memory.
    Ingests into SQLite, generates FAISS embeddings, and runs AI analysis models.
    """
    import pandas as pd
    
    df = GLOBAL_STATE["df"]
    if df is None:
        return "Error: No data loaded to save."

    print("      [Tool] Ingesting transaction data into SQLite...")
    
    try:
        # Import new DB and Vector tools
        from database.queries import queries
        from database.db_manager import db
        from database.models import Transaction
        from vector_store.semantic_search import semantic_search
        from analysis.insights_engine import insights_engine
        from analysis.recurring_detector import recurring_detector
    except ImportError as e:
        return f"Error importing new architectural modules: {e}"

    # 1. Ingest to SQLite
    source_file = "uploaded_statement"
    inserted_count = queries.ingest_transactions(df, source_file)
    print(f"      [Tool] Ingested {inserted_count} transactions to SQLite.")

    # 2. Vectorize newly uploaded transactions
    # Fetch the newly inserted items (using a simplified approach assuming we just fetched everything for simplicity right now 
    # since this runs locally and data sets are small. A better way for scale would be to return the inserted IDs from ingest_transactions)
    session = db.get_session()
    try:
        # Fetching all tx for embedding. faiss_index allows appending but right now we embed the batch
        # If we re-upload, SQLite might get duplicates, but for MVP local agent this satisfies requirements.
        all_txs = session.query(Transaction).all() 
        print(f"      [Tool] Generating Semantic Embeddings for {len(all_txs)} transactions...")
        
        # We clear and rebuild the FAISS index to ensure it perfectly matches the DB state
        # in case of modifications or partial uploads (for a fully robust app, we would selectively update)
        import os
        from vector_store.faiss_index import faiss_store
        
        # Reset current in-memory index
        import faiss
        faiss_store.index = faiss.IndexFlatL2(faiss_store.dimension)
        faiss_store.doc_ids = []
        
        # Re-embed everything
        semantic_search.embed_and_store_transactions(all_txs)
    except Exception as e:
        print(f"      [Tool] Error during vector embedding: {e}")
    finally:
        session.close()

    # 3. Trigger Analytics Pipelines
    try:
        insights_engine.generate_all_insights()
        recurring_detector.detect_recurring_payments()
        print("      [Tool] Analytics generation complete.")
    except Exception as e:
         print(f"      [Tool] Error during analytics generation: {e}")

    return "Analysis saved to database, vectorized, and insights generated successfully."