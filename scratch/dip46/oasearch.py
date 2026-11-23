import json, urllib.request, urllib.parse, sys, os, time

KEY = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
UA = {'User-Agent': 'dip-research/1.0 (mailto:research@example.org)'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)

def search(q, per=25, extra=''):
    url = ('https://api.openalex.org/works?search=' + urllib.parse.quote(q)
           + '&per-page=%d&api_key=%s' % (per, KEY) + extra)
    return get(url)

def pmc(w):
    ids = w.get('ids', {})
    p = ids.get('pmcid') or ''
    if p:
        return p.rstrip('/').split('/')[-1]
    locs = w.get('locations') or []
    for l in locs:
        for k in ('pmcid',):
            if l.get(k):
                return l[k]
    return ''

if __name__ == '__main__':
    qs = json.load(open(sys.argv[1]))
    out = []
    for q in qs:
        try:
            d = search(q, 25)
        except Exception as e:
            print('ERR', q, e)
            continue
        print('=== %s  (total %d)' % (q, d['meta']['count']))
        for w in d['results']:
            p = pmc(w)
            rec = {'q': q, 'doi': (w.get('doi') or '').replace('https://doi.org/', ''),
                   'year': w.get('publication_year'), 'pmcid': p,
                   'title': w.get('title') or '', 'oa': w.get('open_access', {}).get('is_oa'),
                   'cited': w.get('cited_by_count')}
            out.append(rec)
            print(' ', rec['year'], 'PMC' if p else '   ', rec['doi'][:45], '|', rec['title'][:100])
        time.sleep(0.3)
    json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
    print('saved', len(out))
