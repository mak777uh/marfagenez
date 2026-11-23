import json
p = 'literature/dips/reports/dip-2026-11-23-48.jsonl'
rows = [json.loads(l) for l in open(p, encoding='utf-8')]
print('cells', len(rows))
req = {'atom', 'statement', 'domain', 'kind', 'mechanism', 'formula', 'symbols',
       'conditions', 'works', 'confidence', 'locator_status', 'tags', 'notes'}
print('all keys exact:', all(set(r) == req for r in rows))
print('domains', {r['domain'] for r in rows})
print('confidence', {r['confidence'] for r in rows})
print('locator_status', {r['locator_status'] for r in rows})
print('kinds', {r['kind'] for r in rows})
print('quotes', sum(len(r['works']) for r in rows))
print('works keys ok:', all(set(w) == {'doi', 'locator', 'access', 'quote'} for r in rows for w in r['works']))
print('atoms', [r['atom'] for r in rows])
