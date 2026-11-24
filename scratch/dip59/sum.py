import json,collections
p='literature/dips/reports/dip-2026-11-24-59.jsonl'
ds=[json.loads(l) for l in open(p,encoding='utf-8')]
print('cells',len(ds)); print('kinds',dict(collections.Counter(d['kind'] for d in ds)))
print('dois',len({w['doi'] for d in ds for w in d['works']}))
print('access',dict(collections.Counter(w['access'] for d in ds for w in d['works'])))
print('--- sample cell 1 ---')
print(json.dumps(ds[0],ensure_ascii=False)[:700])