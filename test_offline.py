"""Quick test: run the finance pipeline and verify no CDN calls in output HTML."""
import sys
sys.path.insert(0, ".")

from tools.finance_tools import read_statement, categorize_transactions, generate_dashboard

print("1. Reading statement...")
r = read_statement("data/dummy_statement.csv")
print("  ", r)

print("2. Categorizing...")
c = categorize_transactions()
print("  ", c)

print("3. Generating dashboard...")
result = generate_dashboard()
print("  ", str(result)[:80])

# Check the HTML
with open("reports/dashboard.html", encoding="utf-8") as f:
    html = f.read()

cdn_refs = []
for cdn in ["cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"]:
    if cdn in html:
        cdn_refs.append(cdn)

print(f"\n--- Offline Verification ---")
print(f"Dashboard size: {len(html):,} bytes")
print(f"External CDN calls: {cdn_refs if cdn_refs else 'NONE ✅'}")
print(f"Chart.js inlined: {'✅ YES' if 'Chart.register' in html or 'chart.js' in html.lower() else '❌ NO'}")
print(f"Result: {'✅ 100% OFFLINE' if not cdn_refs else '⚠ Still has CDN calls: ' + str(cdn_refs)}")
