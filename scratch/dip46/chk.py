import json
p = '/root/marfagenez/literature/dips/reports/dip-2026-11-23-46.jsonl'
n = 0
for line in open(p, encoding='utf-8'):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    n += 1
    assert r['domain'] == 'bio.integration', r['atom']
    assert r['locator_status'] == 'verified'
    assert r['confidence'] == 'medium'
    for w in r['works']:
        assert w['access'] == 'fulltext' and w['doi'] and w['quote'] and w['locator']
    words = sum(len(w['quote'].split()) for w in r['works'])
    print(r['atom'], r['kind'], 'quotes=%d' % len(r['works']), 'words=%d' % words, '|', r['works'][0]['doi'])
print('TOTAL', n)
