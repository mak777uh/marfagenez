import json, sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epmc import search_epmc, fulltext, text

RATE_KW = ['heating rate', 'drying rate', 'dose rate', 'cooling rate', 'scan rate',
           'warming rate', 'fluence rate', 'irradiance', 'freezing rate', 'rate of',
           'power density', 'infusion rate', 'shear rate', 'cooling velocity',
           'heating velocity', 'temperature ramp', 'dose-rate', 'flow rate']

def sentences(t):
    t = t.replace('\n', ' ')
    parts = re.split(r'(?<=[.!?])\s+', t)
    return [p.strip() for p in parts if 30 < len(p) < 900]

def score(s):
    sc = 0
    low = s.lower()
    if any(k in low for k in RATE_KW):
        sc += 3
    if re.search(r'(r\s*2|r²|r\^2)\s*[=:]', low):
        sc += 4
    if re.search(r'\b(log10|log|ln|exp)\b', low):
        sc += 1
    if re.search(r'=\s*[-+]?\d', s) or re.search(r'\d\.\d+', s):
        sc += 1
    if re.search(r'(increas|decreas|proportional|linear|exponential|threshold|plateau|saturat)', low):
        sc += 2
    if re.search(r'\b(p\s*[<=]|95%\s*ci|confidence interval|±)\b', low):
        sc += 2
    return sc

if __name__ == '__main__':
    qs = json.load(open(sys.argv[1]))
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    outdir = '/root/marfagenez/scratch/dip46/txt'
    os.makedirs(outdir, exist_ok=True)
    index = {}
    for q in qs:
        try:
            res = search_epmc(q, per)
        except Exception as e:
            print('SEARCH_ERR', q, e)
            continue
        print('\n### %s -> %d' % (q, len(res)))
        for r in res:
            p = r.get('pmcid')
            doi = (r.get('doi') or '').lower()
            if not p:
                continue
            if p in index:
                continue
            index[p] = {'doi': doi, 'title': r.get('title'), 'year': r.get('pubYear'),
                        'journal': (r.get('journalInfo') or {}).get('journal', {}).get('title'),
                        'query': q}
    print('\nTOTAL pmc', len(index))
    for p, meta in index.items():
        try:
            t = text(fulltext(p))
        except Exception as e:
            print('FT_ERR', p, e)
            continue
        meta['len'] = len(t)
        fn = os.path.join(outdir, p + '.txt')
        open(fn, 'w', encoding='utf-8').write(t)
        sents = sentences(t)
        ranked = sorted(((score(s), s) for s in sents), reverse=True)
        print('\n===== %s %s | %s | %s' % (p, meta['year'], meta['doi'], (meta['title'] or '')[:80]))
        shown = 0
        for sc, s in ranked:
            if sc < 7:
                break
            print('  (%d) %s' % (sc, s[:330]))
            shown += 1
            if shown >= 5:
                break
    json.dump(index, open('/root/marfagenez/scratch/dip46/index.json', 'w'), ensure_ascii=False, indent=1)
    print('\nDONE', len(index))
