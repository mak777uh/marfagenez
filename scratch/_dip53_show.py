import json, re, sys
p = json.load(open('/root/marfagenez/scratch/_dip53_pool.json'))
seen = set()
for q, rs in p.items():
    print('=====', q)
    for r in rs:
        ab = r['abstract'] or ''
        pat = re.compile(r'[^.]{0,70}\b(?:Damk[oö]hler|Da|P[eé]clet|Pe|Deborah|De|Thiele|Biot|Sherwood|Knudsen)\b[^.]{0,90}')
        hits = [m.group(0).strip() for m in pat.finditer(ab)]
        print(f"{r['year']} {r['doi'][:45]:45s} {r['title'][:90]}")
        for h in hits[:2]:
            print('    NUM:', h[:260])
