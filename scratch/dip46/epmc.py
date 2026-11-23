import json, urllib.request, urllib.parse, re, sys, os, html, time

UA = {'User-Agent': 'dip-research/1.0 (mailto:research@example.org)'}
FT = '/root/marfagenez/scratch/dip46/ft'

def fetch(url, timeout=90, tries=6, pause=4.0):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(pause * (i + 1))
    raise last

def fulltext(pmcid):
    os.makedirs(FT, exist_ok=True)
    fn = os.path.join(FT, pmcid + '.xml')
    if os.path.exists(fn) and os.path.getsize(fn) > 2000:
        return open(fn, encoding='utf-8', errors='replace').read()
    b = fetch('https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML' % pmcid)
    open(fn, 'wb').write(b)
    time.sleep(1.5)
    return b.decode('utf-8', errors='replace')

def text(xml):
    x = re.sub(r'<title>', '\n## ', xml)
    x = re.sub(r'<p[ >]', '\n<p ', x)
    x = re.sub(r'<td[ >]', ' | ', x)
    x = re.sub(r'<[^>]+>', ' ', x)
    x = html.unescape(x)
    x = re.sub(r'[ \t]+', ' ', x)
    x = re.sub(r'\n\s*\n+', '\n', x)
    return x

def search_epmc(q, n=25):
    url = ('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='
           + urllib.parse.quote(q) + '&format=json&pageSize=%d&resultType=core' % n)
    return json.loads(fetch(url))['resultList']['result']
