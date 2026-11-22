import json, pathlib

ROOT = pathlib.Path('/root/marfagenez')
p = ROOT / 'literature/dips/reports/dip-2026-11-23-18.jsonl'
rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
for r in rows:
    r['statement'] = r['statement'].replace('петaскейл', 'петаскейл').replace('петaскейле', 'петаскейле')
    r['conditions'] = [c.replace('петaскейл', 'петаскейл') for c in r['conditions']]
    r['notes'] = r['notes'].replace('петaскейла', 'петаскейла')
p.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
bad = [r['atom'] for r in rows if any(ch in r['statement'] for ch in 'abcdefghijklmnopqrstuvwxyz')]
print('cells', len(rows), '| latin chars in statements:', bad)
print('kinds', [r['kind'] for r in rows])
