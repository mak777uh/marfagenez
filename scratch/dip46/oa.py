import json, urllib.request, urllib.parse, sys, os
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':'dip-research/1.0 (mailto:research@example.org)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)
def search(q, per=25, extra=''):
    url='https://api.openalex.org/works?search='+urllib.parse.quote(q)+'&per-page=%d&api_key=%s'%(per,KEY)+extra
    return get(url)
if __name__=='__main__':
    q=sys.argv[1]
    per=int(sys.argv[2]) if len(sys.argv)>2 else 25
    d=search(q,per)
    print('total', d['meta']['count'])
    for w in d['results']:
        ids=w.get('ids',{})
        print(w.get('publication_year'), (w.get('doi') or '')[:70], '| PMC:', (ids.get('pmcid') or '-'), '| OA:', w.get('open_access',{}).get('is_oa'), '|', (w.get('title') or '')[:110])
