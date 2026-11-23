import json, os, sys, time, urllib.parse, urllib.request

KEY = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
BASE = 'https://api.openalex.org'

def get(url):
    sep = '&' if '?' in url else '?'
    if 'api_key' not in url:
        url = url + sep + 'api_key=' + KEY
    req = urllib.request.Request(url, headers={'User-Agent': 'marfagenez-dip/1.0 (mailto:dip@marfagenez.local)'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2)

def inv2text(inv):
    if not inv:
        return ''
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return ' '.join(pos[i] for i in sorted(pos))

def search(q, n=25, extra=''):
    url = BASE + '/works?search=' + urllib.parse.quote(q) + '&per-page=%d' % n + extra
    d = get(url)
    out = []
    for w in d.get('results', []):
        out.append({
            'doi': (w.get('doi') or '').replace('https://doi.org/', ''),
            'title': w.get('title'),
            'year': w.get('publication_year'),
            'type': w.get('type'),
            'cited': w.get('cited_by_count'),
            'has_abs': bool(w.get('abstract_inverted_index')),
            'abs': inv2text(w.get('abstract_inverted_index')),
            'venue': ((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
        })
    return out

def work(doi):
    return get(BASE + '/works/https://doi.org/' + urllib.parse.quote(doi))

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 's':
        q = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 25
        res = search(q, n)
        for r in res:
            print('%-46s %s %5s c%-5s %s' % (r['doi'], r['year'], 'ABS' if r['has_abs'] else '---', r['cited'], (r['title'] or '')[:95]))
    elif mode == 'w':
        w = work(sys.argv[2])
        print(json.dumps({'doi': w.get('doi'), 'title': w.get('title'), 'year': w.get('publication_year'),
                          'type': w.get('type'), 'abs': inv2text(w.get('abstract_inverted_index'))}, ensure_ascii=False, indent=1))
