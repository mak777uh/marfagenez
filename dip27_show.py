import json,sys
pool=json.load(open('/root/marfagenez/_dip27_pool.json'))
seen=set()
for x in pool:
    if x['doi'] in seen: continue
    seen.add(x['doi'])
    if x['digits']<5: continue
    print('='*100)
    print(x['doi'],'|',x['year'],'|',x['digits'],'|',x['title'])
    print(x['abs'][:1400])
