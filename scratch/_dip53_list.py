import json
d = json.load(open('/root/marfagenez/scratch/_dip53_epmc.json'))
for k, rows in d.items():
    print('=====', k, len(rows))
    for i, r in enumerate(rows[:100]):
        print(f"{i:3d} {r['year']} {str(r['pmcid']):12s} {str(r['doi'])[:32]:32s} {(r['title'] or '')[:95]}")
