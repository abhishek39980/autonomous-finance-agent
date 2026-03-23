"""
generate_samples.py
-------------------
Generates a realistic dummy bank statement CSV and a static HTML dashboard
preview in the sample_output/ folder.

Run this once to give recruiters a live, click-to-open demo without needing
to install anything or spin up the full app.

Usage:
    python sample_output/generate_samples.py
"""

import csv
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# ── Output directory ─────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).resolve().parent


# ── 1. Generate dummy_statement.csv ──────────────────────────────────────────

TRANSACTIONS = [
    # (Description, Category, amount_range, is_credit)
    ("UPI/CR/241130/SALARY INC/salary@oksbi/Monthly Salary", "Income", (45000, 55000), True),
    ("UPI/P2P/234567890/ZOMATO/zomato@icici/Food order", "Food & Dining", (200, 1200), False),
    ("UPI/P2P/345678901/SWIGGY/swiggy@kotak/Dinner", "Food & Dining", (150, 900), False),
    ("UPI/P2P/456789012/NETFLIX/netflix@hdfcbank/Subscription", "Entertainment", (649, 649), False),
    ("UPI/P2P/567890123/SPOTIFY/spotify@icici/Premium", "Entertainment", (119, 119), False),
    ("UPI/P2P/678901234/AMAZON/amazon@upi/Online order", "Shopping", (500, 8000), False),
    ("UPI/P2P/789012345/FLIPKART/flipkart@axisbank/Purchase", "Shopping", (300, 5000), False),
    ("UPI/P2M/890123456/AIRTEL/airtel@paytm/Mobile Recharge", "Bills & Utilities", (299, 799), False),
    ("UPI/P2M/901234567/TNEB/tneb@upi/Electricity Bill", "Bills & Utilities", (800, 3000), False),
    ("UPI/P2P/012345678/UBER/uber@hdfcbank/Cab ride", "Travel", (120, 800), False),
    ("UPI/P2P/123456780/OLA/ola@upi/Cab charge", "Travel", (100, 600), False),
    ("UPI/P2M/234567801/IRCTC/irctc@upi/Train ticket", "Travel", (400, 3000), False),
    ("UPI/P2M/345678012/BOOKMYSHOW/bms@icici/Movie tickets", "Entertainment", (300, 900), False),
    ("UPI/P2M/456780123/LENSKART/lenskart@upi/Eyeglasses", "Shopping", (1500, 4000), False),
    ("NEFT/CR/678901/FREELANCE CLIENT/client@icici/Project payment", "Income", (10000, 25000), True),
    ("ATM WITHDRAWAL/SBI ATM/CHENNAI", "Cash Withdrawal", (2000, 10000), False),
    ("UPI/P2M/567801234/MEDPLUS/medplus@upi/Pharmacy", "Healthcare", (200, 2000), False),
    ("UPI/P2M/678012345/SWIGGY/swiggy@kotak/Lunch", "Food & Dining", (180, 600), False),
    ("UPI/P2P/780123456/GOOGLE PAY/razorpay@paytm/Bill split", "Transfer", (100, 1000), False),
    ("UPI/P2M/801234567/MAKEMYTRIP/mmt@upi/Flight booking", "Travel", (2500, 12000), False),
    ("POS PURCHASE/DMART/CHENNAI/GROCERIES", "Shopping", (1000, 4000), False),
    ("UPI/P2M/912345678/LIC/lic@upi/Insurance premium", "Insurance", (2000, 8000), False),
    ("CHARGES/SMS ALERT/GST", "Bank Charges", (5, 20), False),
    ("UPI/P2M/023456789/HOTSTAR/hotstar@paytm/Subscription", "Entertainment", (299, 299), False),
    ("UPI/P2M/134567890/JIOFIBER/jio@upi/Broadband bill", "Bills & Utilities", (699, 999), False),
]

CATEGORY_COLORS = {
    "Income":           "#00b894",
    "Food & Dining":    "#ff6b6b",
    "Entertainment":    "#a29bfe",
    "Shopping":         "#fd79a8",
    "Bills & Utilities":"#74b9ff",
    "Travel":           "#55efc4",
    "Cash Withdrawal":  "#ffeaa7",
    "Transfer":         "#dfe6e9",
    "Healthcare":       "#e17055",
    "Insurance":        "#6c5ce7",
    "Bank Charges":     "#b2bec3",
}


def generate_csv(n_months: int = 3) -> Path:
    """Generate a realistic multi-month bank statement CSV."""
    rows = []
    balance = 25000.0
    start_date = datetime(2024, 11, 1)

    for month in range(n_months):
        month_start = start_date + timedelta(days=30 * month)
        # Build a month's worth of transactions
        month_txns = []

        for desc, cat, (lo, hi), is_credit in TRANSACTIONS:
            # Randomise occurrence count per month
            count = random.randint(1, 3) if not is_credit else 1
            for _ in range(count):
                day_offset = random.randint(0, 27)
                txn_date = month_start + timedelta(days=day_offset)
                amount = round(random.uniform(lo, hi), 2)
                if not is_credit:
                    amount = -amount
                month_txns.append({
                    "Date": txn_date.strftime("%d/%m/%Y"),
                    "Description": desc,
                    "Category": cat,
                    "Amount": amount,
                })

        # Sort by date within month
        month_txns.sort(key=lambda r: r["Date"])

        for txn in month_txns:
            balance += txn["Amount"]
            txn["Balance"] = round(balance, 2)
            rows.append(txn)

    out_path = OUT_DIR / "dummy_statement.csv"
    fieldnames = ["Date", "Description", "Category", "Amount", "Balance"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅  Generated: {out_path}  ({len(rows)} transactions)")
    return out_path


# ── 2. Generate dashboard.html ────────────────────────────────────────────────

def generate_dashboard_html(csv_path: Path) -> Path:
    """Read the CSV and render a static Chart.js HTML dashboard."""
    import csv as csv_mod

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv_mod.DictReader(f)
        rows = list(reader)

    total_tx = len(rows)
    total_income = sum(float(r["Amount"]) for r in rows if float(r["Amount"]) > 0)
    total_spent = abs(sum(float(r["Amount"]) for r in rows if float(r["Amount"]) < 0))
    net_balance = total_income - total_spent

    # Category spending breakdown
    cat_totals: dict[str, float] = {}
    for r in rows:
        amt = float(r["Amount"])
        if amt < 0:
            cat = r.get("Category", "Other")
            cat_totals[cat] = cat_totals.get(cat, 0) + abs(amt)

    cat_labels = list(cat_totals.keys())
    cat_values = [round(v, 2) for v in cat_totals.values()]
    cat_colors = [CATEGORY_COLORS.get(c, "#636e72") for c in cat_labels]

    # Top 5 expenses
    expenses = sorted(rows, key=lambda r: float(r["Amount"]))[:5]
    top_exp_html = ""
    for r in expenses:
        desc = r["Description"][:50]
        amt = abs(float(r["Amount"]))
        cat = r.get("Category", "Other")
        color = CATEGORY_COLORS.get(cat, "#636e72")
        top_exp_html += f"""
        <div class="expense-item">
          <div class="expense-color" style="background:{color}"></div>
          <div class="expense-details">
            <span class="expense-desc">{desc}</span>
            <span class="expense-cat">{cat}</span>
          </div>
          <span class="expense-amount">₹{amt:,.2f}</span>
        </div>"""

    # Transaction table rows (latest 50)
    table_rows_html = ""
    for r in rows[-50:]:
        amt = float(r["Amount"])
        cls = "positive" if amt > 0 else "negative"
        sym = "+" if amt > 0 else ""
        table_rows_html += f"""
        <tr>
          <td>{r['Date']}</td>
          <td>{r['Description'][:55]}</td>
          <td>{r.get('Category','Other')}</td>
          <td class="{cls}">{sym}₹{abs(amt):,.2f}</td>
          <td>₹{float(r['Balance']):,.2f}</td>
        </tr>"""

    # Generate rendered generation time
    generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    net_cls = "pos" if net_balance >= 0 else "neg"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Finance Dashboard — Sample Output</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg:       #050505;
    --surface:  #121212;
    --border:   #2a2a2a;
    --text:     #EDEDED;
    --muted:    #A1A1AA;
    --accent:   #3B82F6;
    --green:    #34D399;
    --red:      #F87171;
    --grid:     #1a1a1a;
    --radius:   8px;
    --font:     -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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

  .wrap {{ max-width: 1280px; margin: 0 auto; }}

  /* ── Header ── */
  header {{ margin-bottom: 36px; }}
  header h1 {{
    font-size: 22px; font-weight: 600; letter-spacing: -0.3px;
    color: var(--text);
  }}
  header p {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}
  .banner {{
    background: rgba(59, 130, 246, 0.1); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 10px 16px; margin-bottom: 24px;
    font-size: 13px; color: var(--accent);
  }}

  /* ── Generic card ── */
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 24px;
  }}
  .card-title {{
    font-size: 12px; font-weight: 600; letter-spacing: 0.6px;
    text-transform: uppercase; color: var(--muted);
    margin-bottom: 16px;
  }}

  /* ── KPI grid ── */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }}
  @media (max-width: 900px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}

  .kpi-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
  .kpi-value {{
    font-size: 26px; font-weight: 700; margin-top: 6px;
    color: var(--text); letter-spacing: -0.5px;
  }}
  .kpi-value.pos {{ color: var(--green); }}
  .kpi-value.neg {{ color: var(--red); }}
  .kpi-accent {{ color: var(--accent); }}

  /* ── Chart grid ── */
  .chart-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
  }}
  @media (max-width: 800px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
  .chart-wrap {{ position: relative; height: 260px; }}

  /* ── Top expenses ── */
  .exp-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 11px 0; border-bottom: 1px solid var(--border);
  }}
  .exp-row:last-child {{ border-bottom: none; }}
  .exp-color {{ width: 4px; height: 32px; border-radius: 2px; margin-right: 14px; }}
  .exp-desc {{
    flex: 1; font-size: 13px; color: var(--text);
    display: flex; flex-direction: column; gap: 2px;
  }}
  .exp-cat  {{ font-size: 11px; color: var(--muted); }}
  .exp-amt  {{
    font-size: 14px; font-weight: 600; color: var(--red);
    font-variant-numeric: tabular-nums; white-space: nowrap; margin-left: 16px;
  }}

  /* ── Table ── */
  .tbl-wrap {{ overflow-x: auto; max-height: 440px; overflow-y: auto; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{
    text-align: left; padding: 10px 14px;
    background: var(--bg); color: var(--muted);
    font-size: 11px; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase;
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
    <p>Generated {generated_at} &nbsp;·&nbsp; Sample Static Output</p>
  </header>
  
  <div class="banner">
    This is a <strong>pre-generated demo</strong> using synthetic data.
    Run the full app with <code>streamlit run bank_app.py</code> to analyze your real statements locally.
  </div>

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

  <!-- Top Expenses -->
  <div class="card" style="margin-bottom:24px;">
    <h2 class="card-title">Top 5 Expenses</h2>
    {top_exp_html or '<p class="muted">No expense data available.</p>'}
  </div>

  <!-- Transactions Table -->
  <div class="card">
    <h2 class="card-title">Recent Transactions (Last 50)</h2>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Amount</th><th>Balance</th></tr></thead>
        <tbody>{table_rows_html}</tbody>
      </table>
    </div>
  </div>

  <footer>VaultMind &nbsp;·&nbsp; Static Demo Output</footer>
</div>

<script>
  // ── Dark-mode Chart.js defaults ──────────────────────────────────────────
  Chart.defaults.color           = '#A1A1AA';
  Chart.defaults.borderColor     = '#1a1a1a';
  Chart.defaults.font.family     = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  Chart.defaults.font.size       = 12;

  const labels = {json.dumps(cat_labels)};
  const values = {json.dumps(cat_values)};
  
  // Custom muted palette to match the dark theme
  const palette = [
    "#3B82F6", "#6366F1", "#8B5CF6", "#A78BFA",
    "#60A5FA", "#38BDF8", "#34D399", "#4ADE80",
    "#FBBF24", "#F87171", "#FB923C", "#E879F9",
    "#94A3B8", "#CBD5E1", "#64748B",
  ];
  const colors = palette.slice(0, labels.length);

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

    out_path = OUT_DIR / "dashboard.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅  Generated: {out_path}")
    return out_path


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔧  Generating sample output files…\n")
    csv_file = generate_csv(n_months=3)
    html_file = generate_dashboard_html(csv_file)
    print(f"\n🎉  Done! Open this file in your browser to preview the dashboard:")
    print(f"    {html_file.resolve()}")
