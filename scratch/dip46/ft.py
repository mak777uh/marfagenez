import json, sys, os, re, time, urllib.request, urllib.error
import html as _html

UA = {'User-Agent': 'dip-research/1.0 (mailto:research@example.org)'}
BASE = '/root/marfagenez/scratch/dip46'
FT = os.path.join(BASE, 'ft')
TXT = os.path.join(BASE, 'txt')
os.makedirs(FT, exist_ok=True)
os.makedirs(TXT, exist_ok=True)

def req_bytes(url, timeout=90):
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.read()

def get_xml(pmcid):
    fn = os.path.join(FT, pmcid + '.xml')
    if os.path.exists(fn) and os.path.getsize(fn) > 3000:
        return open(fn, encoding='utf-8', errors='replace').read()
    num = pmcid.replace('PMC', '')
    errs = []
    for url in ('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=%s' % num,
                'https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML' % pmcid):
        for i in range(2):
            try:
                b = req_bytes(url)
                s = b.decode('utf-8', errors='replace')
                if len(s) > 3000 and '<article' in s:
                    open(fn, 'w', encoding='utf-8').write(s)
                    return s
                errs.append('short %d' % len(s))
            except Exception as e:
                errs.append(str(e))
            time.sleep(3)
    raise RuntimeError(';'.join(errs[-3:]))

def text(xml):
    x = re.sub(r'(?is)<ref-list.*?</ref-list>', ' ', xml)
    x = re.sub(r'<title>', '\n## ', x)
    x = re.sub(r'<p[ >]', '\n<p ', x)
    x = re.sub(r'<td[ >]', ' | ', x)
    x = re.sub(r'<[^>]+>', ' ', x)
    x = _html.unescape(x)
    x = re.sub(r'[ \t]+', ' ', x)
    x = re.sub(r'\n\s*\n+', '\n', x)
    return x

def load_text(pmcid):
    fn = os.path.join(TXT, pmcid + '.txt')
    if os.path.exists(fn) and os.path.getsize(fn) > 2000:
        return open(fn, encoding='utf-8').read()
    t = text(get_xml(pmcid))
    open(fn, 'w', encoding='utf-8').write(t)
    return t

def search_epmc(q, n=25):
    import urllib.parse
    url = ('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='
           + urllib.parse.quote(q) + '&format=json&pageSize=%d&resultType=core' % n)
    return json.loads(req_bytes(url))['resultList']['result']

RATE_KW = ['heating rate', 'drying rate', 'dose rate', 'dose-rate', 'cooling rate',
           'scan rate', 'warming rate', 'fluence rate', 'freezing rate', 'rate of',
           'power density', 'infusion rate', 'shear rate', 'temperature ramp',
           'heating velocity', 'cooling velocity', 'irradiance', 'flow rate', 'ramp rate',
           'cooling velocity', 'heating rates', 'cooling rates']

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
