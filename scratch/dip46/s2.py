import json, sys, os, re, time, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

UA = {'User-Agent': 'dip-research/1.0 (mailto:research@example.org)'}

def search_epmc(q, n=12):
    url = ('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='
           + urllib.parse.quote(q) + '&format=json&pageSize=%d&resultType=core' % n)
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.load(resp)['resultList']['result']

if __name__ == '__main__':
    qs = json.load(open(sys.argv[1]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    for q in qs:
        print('\n### ' + q, flush=True)
        try:
            res = search_epmc(q, n)
        except Exception as e:
            print('ERR', e, flush=True)
            continue
        print('hits %d' % len(res), flush=True)
        for r in res:
            print(' %s %s %s | %s' % (r.get('pubYear'), (r.get('pmcid') or '-'), (r.get('doi') or '')[:38],
                  (r.get('title') or '')[:95]), flush=True)
        time.sleep(2)
