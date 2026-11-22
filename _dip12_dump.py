import json
d = json.load(open('/root/marfagenez/literature/dips/reports/_dip12_pool.json'))
rows = sorted(d['pool'].items(), key=lambda x: -(x[1]['year'] or 0))
for i, (k, r) in enumerate(rows):
    a = r['abstract']
    print(f"{i:3d} {r['year']} {k}")
    print(f"    {(r['title'] or '')[:160]}")
    print(f"    A[{len(a)}]: {a[:300]}")
