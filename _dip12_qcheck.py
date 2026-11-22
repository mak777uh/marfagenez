import json
p = '/root/marfagenez/literature/dips/reports/dip-2026-11-23-12.jsonl'
for l in open(p):
    r = json.loads(l)
    for w in r['works']:
        n = len(w['quote'].split())
        flag = 'OK' if 10 <= n <= 30 else '!!'
        print(f"{r['atom']} {r['kind']:11s} {flag} words={n:2d} {w['doi']}")
print('cells', sum(1 for _ in open(p)))
