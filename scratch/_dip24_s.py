import urllib.request, urllib.parse, json, sys, time
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':'marfagenez-dip/1.0 (research)'})
    return json.load(urllib.request.urlopen(req, timeout=90))
def abstract(inv):
    if not inv: return ''
    pos=[]
    for w,ps in inv.items():
        for p in ps: pos.append((p,w))
    return ' '.join(w for p,w in sorted(pos))
def search(q, n=8):
    u='https://api.openalex.org/works?'+urllib.parse.urlencode({'search':q,'per-page':n,'api_key':KEY})
    d=get(u)
    out=[]
    for w in d['results']:
        out.append({'doi':(w.get('doi') or '').replace('https://doi.org/',''),'title':w.get('title'),
                    'year':w.get('publication_year'),'abs':abstract(w.get('abstract_inverted_index'))})
    return d['meta'].get('count'), out
if __name__=='__main__':
    q=sys.argv[1]
    n=int(sys.argv[2]) if len(sys.argv)>2 else 8
    c,res=search(q,n)
    print('COUNT',c)
    for r in res:
        print('=====',r['doi'],'|',r['year'],'|',r['title'])
        print(r['abs'][:2000])
