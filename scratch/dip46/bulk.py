import json, sys, os, re, time, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ft as H

KEY = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
UA = {'User-Agent': 'dip-research/1.0 (mailto:research@example.org)'}

def oa(url):
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.load(resp)

def oa_search(q, per=40):
    url = ('https://api.openalex.org/works?search=' + urllib.parse.quote(q)
           + '&per-page=%d&api_key=%s' % (per, KEY))
    return oa(url)

def pmcid_of(w):
    ids = w.get('ids') or {}
    p = ids.get('pmcid') or ''
    if p:
        return p.rstrip('/').split('/')[-1]
    for l in (w.get('locations') or []):
        if l.get('pmcid'):
            return l['pmcid']
    return ''

if __name__ == '__main__':
    qs = json.load(open(sys.argv[1]))
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    meta = {}
    for q in qs:
        try:
            d = oa_search(q, per)
        except Exception as e:
            print('OA_ERR', q, e, flush=True)
            continue
        print('### %s -> %d' % (q, len(d['results'])), flush=True)
        for w in d['results']:
            p = pmcid_of(w)
            if p and p not in meta:
                meta[p] = {'doi': (w.get('doi') or '').replace('https://doi.org/', ''),
                           'title': w.get('title'), 'year': w.get('publication_year'), 'q': q}
    print('candidates', len(meta), flush=True)
    json.dump(meta, open('/root/marfagenez/scratch/dip46/meta.json', 'w'), ensure_ascii=False, indent=1)
    results = {}
    for i, (p, m) in enumerate(meta.items()):
        try:
            t = H.load_text(p)
        except Exception as e:
            continue
        sents = H.sentences(t)
        ranked = sorted(((H.score(s), s) for s in sents), reverse=True)
        best = [(sc, s) for sc, s in ranked if sc >= 10][:6]
        if best:
            results[p] = {'meta': m, 'len': len(t), 'best': best}
            print('\n===== %s %s | %s | %s' % (p, m['year'], m['doi'], (m['title'] or '')[:80]), flush=True)
            for sc, s in best:
                print('  (%d) %s' % (sc, s[:300]), flush=True)
        time.sleep(0.8)
    json.dump(results, open('/root/marfagenez/scratch/dip46/hits.json', 'w'), ensure_ascii=False, indent=1)
    print('\nDONE with %d useful' % len(results), flush=True)
