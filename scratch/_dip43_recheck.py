import json, sys
sys.path.insert(0, '/root/marfagenez')
from _dip43_oa import work, inv2text

p = '/root/marfagenez/literature/dips/reports/dip-2026-11-23-43.jsonl'
rows = [json.loads(l) for l in open(p, encoding='utf-8')]
print('atoms:', len(rows))

# existing map atoms for duplicate check
existing = [json.loads(l) for l in open('/root/marfagenez/literature/map/atoms.jsonl', encoding='utf-8')]
old_dois = {}
for a in existing:
    for w in a.get('works') or []:
        old_dois.setdefault((w.get('doi') or '').lower(), []).append((a['atom'], a.get('statement', '')[:80]))

problems = []
cache = {}
for a in rows:
    for f in ('atom', 'statement', 'domain', 'kind', 'works', 'confidence'):
        if not a.get(f):
            problems.append(('missing field', a['atom'], f))
    assert a['domain'] == 'bio.genetics_epigenetics', a['atom']
    if a['confidence'] != 'medium':
        problems.append(('confidence', a['atom'], a['confidence']))
    if a['locator_status'] != 'verified':
        problems.append(('locator', a['atom'], a['locator_status']))
    if not a.get('conditions'):
        problems.append(('no conditions', a['atom'], ''))
    for w in a['works']:
        d = w['doi']
        if d not in cache:
            x = work(d)
            cache[d] = ((x.get('doi') or '').replace('https://doi.org/', ''), x.get('title'),
                        inv2text(x.get('abstract_inverted_index')))
        got_doi, title, abs_ = cache[d]
        if got_doi.lower() != d.lower():
            problems.append(('DOI mismatch', a['atom'], d + ' vs ' + got_doi))
        if title != w.get('resolved_title'):
            problems.append(('title mismatch', a['atom'], d))
        if w['quote'] not in abs_:
            problems.append(('QUOTE FAIL', a['atom'], d))
        if w.get('access') != 'abstract':
            problems.append(('access', a['atom'], w.get('access')))
        nw = len(w['quote'].split())
        if not (10 <= nw <= 30):
            problems.append(('quote words %d' % nw, a['atom'], d))
        if d.lower() in old_dois:
            problems.append(('DOI already in map', a['atom'], d))

print('unique DOIs:', len(cache))
for d, (g, t, ab) in sorted(cache.items()):
    print(' checked', d, '|', t[:70])
print('\nPROBLEMS:', len(problems))
for x in problems:
    print('  ', x)
