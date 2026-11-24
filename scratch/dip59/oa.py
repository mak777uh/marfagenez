import json,sys,urllib.request,urllib.parse,os
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
def get(url):
    sep='&' if '?' in url else '?'
    req=urllib.request.Request(url+sep+'api_key='+KEY, headers={'User-Agent':'marfagenez/1.0 (mailto:lead@marfagenez.local)'})
    return json.load(urllib.request.urlopen(req,timeout=60))
def search(q,n=8):
    u='https://api.openalex.org/works?search='+urllib.parse.quote(q)+'&per-page=%d&mailto=lead@marfagenez.local'%n
    d=get(u)
    out=[]
    for w in d['results']:
        inv=w.get('abstract_inverted_index') or {}
        pos={}
        for tok,idx in inv.items():
            for i in idx: pos[i]=tok
        ab=' '.join(pos[i] for i in sorted(pos)) if pos else ''
        out.append({'doi':(w.get('doi') or '').replace('https://doi.org/',''),'title':w.get('title'),'year':w.get('publication_year'),'cited':w.get('cited_by_count'),'abstract':ab})
    return out
if __name__=='__main__':
    q=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 8
    for r in search(q,n):
        print('===',r['doi'],'|',r['year'],'|cit',r['cited'],'|',r['title'])
        print(r['abstract'][:900])
        print()
