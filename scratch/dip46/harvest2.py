import json, sys, os, re, time, urllib.request, urllib.error

UA = {'User-Agent': 'dip-research/1.0 (mailto:research@example.org)'}
FT = '/root/marfagenez/scratch/dip46/ft'
TXT = '/root/marfagenez/scratch/dip46/txt'
os.makedirs(FT, exist_ok=True)
os.makedirs(TXT, exist_ok=True)

import html as _html

def req_bytes(url, timeout=90):
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.read()

def fetch_throttled(url, tries=4):
    last = None
    for i in range(tries):
        try:
            b = req_bytes(url)
            if len(b) > 2000:
                return b
            last = Exception('short body %d' % len(b))
        except Exception as e:
            last = e
        time.sleep(55 + 10 * i)
    raise last

def fulltext(pmcid):
    fn = os.path.join(FT, pmcid + '.xml')
    if os.path.exists(fn) and os.path.getsize(fn) > 2000:
        return open(fn, encoding='utf-8', errors='replace').read()
    b = fetch_throttled('https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML' % pmcid)
    open(fn, 'wb').write(b)
    time.sleep(6)
    return b.decode('utf-8', errors='replace')

def text(xml):
    x = re.sub(r'<title>', '\n## ', xml)
    x = re.sub(r'<p[ >]', '\n<p ', x)
    x = re.sub(r'<td[ >]', ' | ', x)
    x = re.sub(r'<[^>]+>', ' ', x)
    x = _html.unescape(x)
    x = re.sub(r'[ \t]+', ' ', x)
    x = re.sub(r'\n\s*\n+', '\n', x)
    return x

def search_epmc(q, n=25):
    url = ('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='
           + urllib.parse.quote(q) + '&format=json&pageSize=%d&resultType=core' % n)
    return json.loads(req_bytes(url))['resultList']['result']

RATE_KW = ['heating rate', 'drying rate', 'dose rate', 'dose-rate', 'cooling rate',
           'scan rate', 'warming rate', 'fluence rate', 'freezing rate', 'rate of',
           'power density', 'infusion rate', 'shear rate', 'temperature ramp',
           'heating velocity', 'cooling velocity', 'irradiance', 'flow rate', 'ramp rate']

def sentences(t):
    t = t.replace('\n', ' ')
    return [p.strip() for p in re.split(r'(?<=[.!?])\s+', t) if 30 < len(p) < 900]

def score(s):
    low = s.lower()
    sc = 0
    if any(k in low for k in RATE_KW):
        sc += 3
    if re.search(r'(r\s*2|r²|r\^2)\s*[=:]', low):
        sc += 4
    if re.search(r'=\s*[-+]?\d', s):
        sc += 3
    if re.search(r'\b(log10|log|ln|exp|exponential)\b', low):
        sc += 2
    if re.search(r'(increas|decreas|proportional|linear|threshold|plateau|saturat|correlat)', low):
        sc += 2
    if re.search(r'(p\s*[<=]|95%\s*(ci|confidence)|±)', low):
        sc += 2
    return sc

if __name__ == '__main__':
    qs = json.load(open(sys.argv[1]))
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    index = {}
    for q in qs:
        try:
            res = search_epmc(q, per)
        except Exception as e:
            print('SEARCH_ERR', q, e, flush=True)
            continue
        print('\n### %s -> %d' % (q, len(res)), flush=True)
        for r in res:
            p = r.get('pmcid')
            if not p or p in index:
                continue
            index[p] = {'doi': (r.get('doi') or '').lower(), 'title': r.get('title'),
                        'year': r.get('pubYear'), 'query': q}
        time.sleep(2)
    print('\nTOTAL pmc %d' % len(index), flush=True)
    json.dump(index, open('/root/marfagenez/scratch/dip46/index2.json', 'w'), ensure_ascii=False, indent=1)
    for p, meta in index.items():
        try:
            t = text(fulltext(p))
        except Exception as e:
            print('FT_ERR', p, e, flush=True)
            continue
        meta['len'] = len(t)
        open(os.path.join(TXT, p + '.txt'), 'w', encoding='utf-8').write(t)
        sents = sentences(t)
        ranked = sorted(((score(s), s) for s in sents), reverse=True)
        print('\n===== %s %s | %s | %s' % (p, meta['year'], meta['doi'], (meta['title'] or '')[:85]), flush=True)
        shown = 0
        for sc, s in ranked:
            if sc < 8 or shown >= 4:
                break
            print('  (%d) %s' % (sc, s[:300]), flush=True)
            shown += 1
    print('\nDONE', flush=True)
