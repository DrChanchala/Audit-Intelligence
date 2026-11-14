import re
import json

with open('trades_raw.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace JS keys without quotes: id:, name:, badge:, bc:, btc:, groups:, sub:, items:
# with "key":
text_clean = text
keys = ['id', 'name', 'badge', 'bc', 'btc', 'groups', 'sub', 'items']
for k in keys:
    text_clean = re.sub(rf'\b{k}\s*:', f'"{k}":', text_clean)

# Replace single quotes around strings with double quotes
# Be careful with escaped quotes or apostrophes in text
# Let's write a proper character scanner or regex for single-quoted strings:
def replace_quotes(match):
    s = match.group(1)
    # escape unescaped double quotes inside
    s = s.replace('\\"', '"').replace('"', '\\"')
    return f'"{s}"'

text_clean = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", replace_quotes, text_clean)

# remove trailing commas before ] or }
text_clean = re.sub(r',\s*([\]}])', r'\1', text_clean)

try:
    data = json.loads(text_clean)
    print("SUCCESS parsing with JSON!")
    with open('master_checklist_parsed.json', 'w', encoding='utf-8') as out:
        json.dump(data, out, indent=2)
    print(f"Total stages: {len(data)}")
    sub_count = sum(len(t.get('groups', [])) for t in data)
    item_count = sum(len(g.get('items', [])) for t in data for g in t.get('groups', []))
    print(f"Total subgroups: {sub_count}")
    print(f"Total checkpoints: {item_count}")
except Exception as e:
    print("Direct JSON parse error:", e)
    # If there is a parse error, let's pinpoint position
    m = re.search(r'char (\d+)', str(e))
    if m:
        pos = int(m.group(1))
        print("Near text:", text_clean[max(0, pos-80):min(len(text_clean), pos+80)])
