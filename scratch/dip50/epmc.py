import json,sys,urllib.parse,urllib.request,re
HDR={'User-Agent':'marfagenez-dip50/1.0'}
E='https://www.ebi.ac.uk/europepmc/webservices/rest'
def get(u,raw=False):
    r=urllib.request.urlopen(urllib.request.Request(u,headers=HDR),timeout=90)
    b=r.read()
    return b.decode('utf-8','replace') if raw else json.loads(b)
def find(q):
    d=get(E+'/search?query='+urllib.parse.quote(q)+'&format=json&pageSize=10&resultType=lite')
    print('--- Q:',q,'hits=',d.get('hitCount'))
    for r in d.get('resultList',{}).get('result',[]):
        print('   ',r.get('doi'),'|',r.get('pmcid'),'|',r.get('pmid'),'|',r.get('pubYear'),'|',(r.get('title') or '')[:110],'|OA=',r.get('isOpenAccess'))
def plain(p):
    t=get(E+'/'+p+'/fullTextXML',raw=True)
    t=re.sub(r'<title>','\n<TITLE>',t); t=re.sub(r'<p>','\n<P>',t)
    t=re.sub(r'<table-wrap','\n[[TABLE]]<table-wrap',t); t=re.sub(r'<tr>','\n<TR>',t)
    t=re.sub(r'<td[^>]*>|<th[^>]*>',' | ',t); t=re.sub(r'<[^>]+>',' ',t)
    t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n{3,}','\n\n',t)
    return t
if __name__=='__main__':
    c=sys.argv[1]
    if c=='f':
        for q in sys.argv[2:]: find(q)
    elif c=='t':
        p=sys.argv[2]; n=int(sys.argv[3]) if len(sys.argv)>3 else 4000
        t=plain(p)
        open('/root/marfagenez/scratch/dip50/'+p+'.txt','w').write(t)
        print(t[:n])
