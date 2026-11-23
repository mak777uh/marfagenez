import json, re, sys, urllib.parse, urllib.request

UA = {'User-Agent': 'marfagenez-dip/1.0 (mailto:dip@marfagenez.local)'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode('utf-8', 'replace')

def epmc(doi):
    url = ('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='
           + urllib.parse.quote('DOI:"%s"' % doi) + '&resultType=core&format=json')
    d = json.loads(get(url))
    res = d.get('resultList', {}).get('result') or []
    if not res:
        return None
    return res[0]

def fulltext(pmcid):
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML' % pmcid
    return get(url)

def strip(x):
    x = re.sub(r'<[^>]+>', ' ', x)
    return re.sub(r'\s+', ' ', x).strip()

if __name__ == '__main__':
    doi = sys.argv[1]
    r = epmc(doi)
    if not r:
        print('NOT IN EPMC', doi); sys.exit(0)
    print('title:', r.get('title'))
    print('pmid:', r.get('pmid'), 'pmcid:', r.get('pmcid'), 'oa:', r.get('isOpenAccess'))
    print('ABSTRACT:', strip(r.get('abstractText') or ''))
    if len(sys.argv) > 2 and r.get('pmcid'):
        txt = strip(fulltext(r['pmcid']))
        open('/root/marfagenez/_dip43_ft_%s.txt' % r['pmcid'], 'w').write(txt)
        print('FULLTEXT chars:', len(txt), 'file: _dip43_ft_%s.txt' % r['pmcid'])
