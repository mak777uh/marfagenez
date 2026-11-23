import json,sys
pool=json.load(open('/root/marfagenez/_dip27_pool.json'))+json.load(open('/root/marfagenez/_dip27_pool2.json'))
want=sys.argv[1:]
seen=set()
for x in pool:
    if x['doi'] in seen: continue
    seen.add(x['doi'])
    if want and not any(w in x['doi'] for w in want): continue
    print('='*100)
    print(x['doi'],'|',x['year'],'|',x['digits'],'|',x['venue'])
    print(x['title'])
    print(x['abs'][:1900])
