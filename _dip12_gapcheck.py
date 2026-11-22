import json
for p in ['/root/marfagenez/literature/dips/reports/dip-2026-11-23-11.jsonl',
          '/root/marfagenez/literature/dips/reports/dip-2026-11-23-09.jsonl']:
    try:
        rows = [json.loads(l) for l in open(p) if l.strip()]
    except Exception as e:
        print('ERR', p, e); continue
    for r in rows:
        if r.get('kind') in ('gap',):
            print(json.dumps(r, ensure_ascii=False, indent=1))
            print('KEYS:', sorted(r.keys()))
