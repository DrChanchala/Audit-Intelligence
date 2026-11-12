import json
import re

with open('trades_raw.js', 'r', encoding='utf-8') as f:
    raw = f.read()

# Let's cleanly parse JavaScript object into Python dicts
# Note: trades_raw.js is JS literal with unquoted keys like id:, name:, groups:, sub:, items:
# Let's write a robust JS parser using a quick Node script or Python regex parser.
import subprocess

node_script = """
const fs = require('fs');
const code = fs.readFileSync('trades_raw.js', 'utf8');
const trades = eval(code);
fs.writeFileSync('master_checklist_parsed.json', JSON.stringify(trades, null, 2), 'utf8');
console.log('Successfully parsed ' + trades.length + ' stages.');
let totalSubs = 0;
let totalItems = 0;
trades.forEach(t => {
    totalSubs += (t.groups || []).length;
    (t.groups || []).forEach(g => {
        totalItems += (g.items || []).length;
    });
});
console.log('Total subgroups:', totalSubs);
console.log('Total checkpoints:', totalItems);
"""

with open('convert_trades.js', 'w', encoding='utf-8') as f:
    f.write(node_script)
