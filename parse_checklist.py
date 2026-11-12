import re
import json

with open('Master_Quality_Inspection_Checklist.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

m = re.search(r'const TRADES = (\[.*?\]);\s*\nlet state', text, re.DOTALL)
if not m:
    # try another delimiter
    m = re.search(r'const TRADES = (\[.*?\]);', text, re.DOTALL)

if m:
    trades_js = m.group(1)
    print("Found TRADES! Length:", len(trades_js))
    # Let's save trades_js to a file so we can inspect and parse cleanly
    with open('trades_raw.js', 'w', encoding='utf-8') as out:
        out.write(trades_js)
else:
    print("Could not match TRADES")
