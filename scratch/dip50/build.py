import json, re, urllib.request, urllib.parse, html, os

K = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
TXT = '/root/marfagenez/scratch/dip50/'

def load(p):
    t = open(TXT + p, encoding='utf-8').read()
    t = html.unescape(t)
    t = re.sub(r'\s+', ' ', t)
    return t

TEXTS = {
 'tcells': load('PMC6399228.txt'),
 'ostrich': load('PMC7694958.txt'),
 'coral': load('PMC13749476.txt'),
 'wheat': load('PMC8850252.txt'),
 'endo': load('PMC4659675.txt'),
 'stallion': load('PMC12785071.txt'),
}

def check(key, q):
    qn = re.sub(r'\s+', ' ', html.unescape(q))
    return qn in TEXTS[key]

def oa(doi):
    u = 'https://api.openalex.org/works/https://doi.org/' + doi + '?' + urllib.parse.urlencode(
        {'mailto': 'marfagenez@example.org', 'api_key': K})
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'dip50'}), timeout=90))
    return {'doi': doi, 'resolved_title': d.get('title'), 'resolved_year': d.get('publication_year'),
            'is_oa': (d.get('open_access') or {}).get('is_oa')}

DOIS = {
 'tcells': '10.1038/s41598-019-39957-x',
 'ostrich': '10.3390/foods9111624',
 'coral': '10.1002/advs.78550',
 'wheat': '10.1007/s00299-021-02819-w',
 'endo': '10.1371/journal.pone.0142828',
 'stallion': '10.3390/ani16010021',
}
RES = {k: oa(v) for k, v in DOIS.items()}
for k, v in RES.items():
    print('DOI', k, v['doi'], v['resolved_year'], 'OA=', v['is_oa'], '|', (v['resolved_title'] or '')[:90])
