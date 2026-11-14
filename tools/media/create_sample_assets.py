import os

os.makedirs('static/uploads/evidence', exist_ok=True)

samples = {
    'site_rebar_check_sample.jpg': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <rect width="400" height="300" fill="#1e293b"/>
  <rect x="20" y="20" width="360" height="260" fill="none" stroke="#4fb892" stroke-width="3" stroke-dasharray="8,8"/>
  <text x="200" y="110" fill="#ffffff" font-size="18" font-weight="bold" font-family="sans-serif" text-anchor="middle">SITE QUALITY EVIDENCE</text>
  <text x="200" y="145" fill="#4fb892" font-size="14" font-family="sans-serif" text-anchor="middle">Rebar Spacing &amp; Cover Verification</text>
  <text x="200" y="180" fill="#94a3b8" font-size="12" font-family="sans-serif" text-anchor="middle">Tower 3 · Floor 8 · Sunken Slab</text>
  <text x="200" y="230" fill="#cbd5e1" font-size="11" font-family="monospace" text-anchor="middle">GPS: 28.5355° N, 77.3910° E · 2026-11-03 14:15</text>
</svg>''',
    'sunken_slab_waterproofing_sample.jpg': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <rect width="400" height="300" fill="#0f172a"/>
  <rect x="20" y="20" width="360" height="260" fill="none" stroke="#38bdf8" stroke-width="3"/>
  <text x="200" y="110" fill="#ffffff" font-size="18" font-weight="bold" font-family="sans-serif" text-anchor="middle">WATERPROOFING PONDING TEST</text>
  <text x="200" y="145" fill="#38bdf8" font-size="14" font-family="sans-serif" text-anchor="middle">72h Submersion Observation: PASSED</text>
  <text x="200" y="180" fill="#94a3b8" font-size="12" font-family="sans-serif" text-anchor="middle">Zero seepage detected on underside</text>
  <text x="200" y="230" fill="#cbd5e1" font-size="11" font-family="monospace" text-anchor="middle">GPS: 28.5355° N, 77.3910° E · 2026-11-03 15:40</text>
</svg>''',
    'demarcation_benchmark_sample.jpg': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <rect width="400" height="300" fill="#1e1b4b"/>
  <rect x="20" y="20" width="360" height="260" fill="none" stroke="#a855f7" stroke-width="3" stroke-dasharray="6,6"/>
  <text x="200" y="110" fill="#ffffff" font-size="18" font-weight="bold" font-family="sans-serif" text-anchor="middle">SETTING OUT BENCHMARK</text>
  <text x="200" y="145" fill="#c084fc" font-size="14" font-family="sans-serif" text-anchor="middle">Total Station Benchmark Reference Peg</text>
  <text x="200" y="180" fill="#94a3b8" font-size="12" font-family="sans-serif" text-anchor="middle">Permanent concrete pillar protected</text>
  <text x="200" y="230" fill="#cbd5e1" font-size="11" font-family="monospace" text-anchor="middle">GPS: 28.5355° N, 77.3910° E · 2026-11-03 11:20</text>
</svg>'''
}

for filename, content in samples.items():
    with open(os.path.join('static', 'uploads', 'evidence', filename), 'w', encoding='utf-8') as f:
        f.write(content)

print("Sample evidence photos created successfully.")
