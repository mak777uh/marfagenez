import json
p = '/root/marfagenez/literature/dips/reports/dip-2026-11-23-50.jsonl'
rows = [json.loads(l) for l in open(p, encoding='utf-8')]
out = []
for r in rows:
    nr = {}
    for k, v in r.items():
        nr[k] = v
        if k == 'statement':
            nr['domain'] = 'bio.integration'
    out.append(nr)
with open(p, 'w', encoding='utf-8') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
rows = [json.loads(l) for l in open(p, encoding='utf-8')]
print('cells:', len(rows), 'domains:', set(r['domain'] for r in rows))
print('confidence:', set(r['confidence'] for r in rows), 'locator_status:', set(r['locator_status'] for r in rows))
print('kinds:', sorted(set(r['kind'] for r in rows)))
print('fields:', sorted(rows[0].keys()))
