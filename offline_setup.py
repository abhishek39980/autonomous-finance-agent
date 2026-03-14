"""
offline_setup.py — Run this ONCE to download all assets needed for 100% offline use.
After running this, the project works with no internet connection at all.
"""
import os
import sys
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
STATIC.mkdir(exist_ok=True)

ASSETS = {
    "chart.min.js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js",
}

print("📦 Downloading offline assets...\n")
ok = True
for filename, url in ASSETS.items():
    dest = STATIC / filename
    if dest.exists():
        print(f"  ✅ {filename} already exists ({dest.stat().st_size // 1024} KB)")
        continue
    try:
        print(f"  ⬇ Downloading {filename}...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"  ✅ {filename} saved ({len(r.content) // 1024} KB)")
    except Exception as e:
        print(f"  ❌ Failed to download {filename}: {e}")
        ok = False

print()
if ok:
    print("🎉 All offline assets ready. The project will now run 100% locally with no internet.")
else:
    print("⚠ Some downloads failed. The dashboard will fall back to CDN for missing assets.")
