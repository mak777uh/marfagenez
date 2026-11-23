import json, sys, os, re, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epmc import fulltext, text, fetch

KEY = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
UA = {'User-Agent': 'dip-research/1.0'}

def resolve(doi):
    url = 'https://api.openalex.org/works/https://doi.org/' + doi + '?api_key=' + KEY
    req = __import__('urllib.request', fromlist=['Request']).Request(url, headers=UA)
    with __import__('urllib.request', fromlist=['urlopen']).urlopen(req, timeout=60) as r:
        w = json.load(r)
    ids = w.get('ids', {})
    p = (ids.get('pmcid') or '')
    if p:
        return p.rstrip('/').split('/')[-1], w
    for l in (w.get('locations') or []):
        if l.get('pmcid'):
            return l['pmcid'], w
    return '', w

if __name__ == '__main__':
    dois = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
    kws = sys.argv[2].split('|')
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 350
    outdir = '/root/marfagenez/scratch/dip46/txt'
    os.makedirs(outdir, exist_ok=True)
    for doi in dois:
        try:
            pmc, w = resolve(doi)
        except Exception as e:
            print('RESOLVE_ERR', doi, e)
            continue
        print('\n===== %s | %s | %s' % (doi, pmc or 'NO-PMC', (w.get('title') or '')[:90]))
        if not pmc:
            continue
        try:
            t = text(fulltext(pmc))
        except Exception as e:
            print('FT_ERR', e)
            continue
        safe = re.sub(r'[^a-z0-9]+', '_', doi.lower())
        open(os.path.join(outdir, safe + '.txt'), 'w', encoding='utf-8').write(t)
        print('LEN', len(t))
        low = t.lower()
        seen = set()
        n = 0
        for k in kws:
            for m in re.finditer(re.escape(k), low):
                s = max(0, m.start() - width // 3)
                if any(abs(m.start() - x) < width for x in seen):
                    continue
                seen.add(m.start())
                n += 1
                if n > 18:
                    break
                print('  [%s] ...%s...' % (k, t[s:m.start() + width].replace('\n', ' ')))
            if n > 18:
                break
