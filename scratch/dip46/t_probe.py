import urllib.request, sys

ids = sys.argv[1:]
UA = {'User-Agent': 'dip-research/1.0'}
for p in ids:
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML' % p
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        print(p, r.status, len(b))
    except Exception as e:
        print(p, 'ERR', e)
