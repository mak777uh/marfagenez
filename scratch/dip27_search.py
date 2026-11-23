import json, urllib.request, urllib.parse, time, sys, re
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':'dip-researcher/1.0 (mailto:research@example.org)'})
    for a in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            print('ERR',e, file=sys.stderr); time.sleep(3)
    return None
def inv2txt(inv):
    if not inv: return ''
    pos={}
    for w,ps in inv.items():
        for p in ps: pos[p]=w
    return ' '.join(pos[i] for i in sorted(pos))
QUERIES=[
 '"disposable soma" repair fecundity trade-off',
 'cost of reproduction immune response fecundity birds measured',
 'dietary restriction DNA repair fecundity trade-off',
 'energy allocation maintenance versus reproduction budget',
 'experimental evolution increased DNA repair reduced fecundity',
 'cost of immunity reproductive output trade-off insect',
 'somatic maintenance reproduction allocation lifespan fecundity experiment',
 'oxidative damage repair cost fecundity trade-off',
]
out=[]
for q in QUERIES:
    url='https://api.openalex.org/works?'+urllib.parse.urlencode({'search':q,'per_page':25,'mailto':'research@example.org','select':'id,doi,title,publication_year,abstract_inverted_index,primary_location,type,cited_by_count'})
    d=get(url)
    if not d: continue
    print('### Q:',q,'n=',d['meta']['count'], file=sys.stderr)
    for w in d.get('results',[]):
        ab=inv2txt(w.get('abstract_inverted_index'))
        doi=(w.get('doi') or '').replace('https://doi.org/','')
        if not doi or not ab: continue
        ndig=len(re.findall(r'\d',ab))
        out.append({'doi':doi,'title':w.get('title'),'year':w.get('publication_year'),'cited':w.get('cited_by_count'),'digits':ndig,'abs':ab[:1800],'query':q,
                    'venue':((w.get('primary_location') or {}).get('source') or {}).get('display_name')})
    time.sleep(0.3)
json.dump(out, open('/root/marfagenez/_dip27_pool.json','w'))
print('TOTAL',len(out))
out.sort(key=lambda x:-x['digits'])
for x in out[:45]:
    print(x['digits'],'|',x['year'],'|',x['doi'],'|',(x['title'] or '')[:110])
