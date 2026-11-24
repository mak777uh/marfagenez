import json,sys,urllib.request,urllib.parse
def q(query,n=10):
    u='https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='+urllib.parse.quote(query)+'&format=json&pageSize=%d&resultType=core'%n
    d=json.load(urllib.request.urlopen(u,timeout=60))
    for r in d['resultList']['result']:
        print('===',r.get('doi'),'|PMC',r.get('pmcid'),'|',r.get('pubYear'),'|',r.get('title')[:110])
        ab=(r.get('abstractText') or '')[:600]
        if ab: print(ab)
        print()
def ft(pmcid):
    u='https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML'%pmcid
    return urllib.request.urlopen(u,timeout=90).read().decode('utf-8','replace')
if __name__=='__main__':
    if sys.argv[1]=='ft':
        t=ft(sys.argv[2]); open(sys.argv[3],'w').write(t); print('len',len(t),'->',sys.argv[3])
    else:
        q(sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 10)
