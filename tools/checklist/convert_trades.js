
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
