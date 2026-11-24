import json
p='literature/dips/reports/dip-2026-11-24-59.jsonl'
n=0; dois=set()
for line in open(p,encoding='utf-8'):
    d=json.loads(line); n+=1
    assert d['domain']=='bio.integration'
    assert d['kind'] in {'mechanism','formula','measurement','condition','contradiction','gap','definition'}
    assert d['confidence']=='medium' and d['locator_status']=='verified'
    for w in d['works']:
        dois.add(w['doi']); assert w['quote'] and w['locator'] and w['access']
        words=len(w['quote'].split()); print(d['atom'],'quote words',words)
print('cells',n,'dois',len(dois))