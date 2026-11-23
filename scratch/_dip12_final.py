import json
p = '/root/marfagenez/literature/dips/reports/dip-2026-11-23-12.jsonl'
rows = [json.loads(l) for l in open(p) if l.strip()]
req = {"atom","statement","domain","kind","works","confidence"}
for r in rows:
    miss = req - set(r)
    print(r['atom'], r['kind'], r['confidence'], 'works=%d' % len(r['works']),
          'quotes=%d' % sum(1 for w in r['works'] if w.get('quote')),
          'MISSING:', sorted(miss) if miss else '-')
print('total', len(rows), 'kinds', sorted({r['kind'] for r in rows}))
