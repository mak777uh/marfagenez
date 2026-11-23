import json, urllib.request, urllib.parse, time, sys, re
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
SPECS=[
 ('search','"cost of reproduction" fecundity immune measured',30),
 ('search','immune challenge reduced egg production percent Drosophila',20),
 ('search','dietary restriction reduced fecundity increased stress resistance',20),
 ('search','Hsp70 overexpression reduced fecundity cost',20),
 ('search','mating cost lifespan egg laying Drosophila measured',20),
 ('search','reproductive allocation energy budget percent lizard snake',20),
 ('search','somatic maintenance growth reproduction allocation fish measured',20),
 ('search','DNA repair capacity trade-off fecundity growth measured',20),
 ('search','oxidative protection sacrificed reproduction antioxidant enzymes',20),
 ('search','immune activation cost number of offspring bird experiment',20),
]
out=[]
for kind,q,n in SPECS:
    url='https://api.openalex.org/works?'+urllib.parse.urlencode({'search':q,'per_page':n,'mailto':'research@example.org','select':'id,doi,title,publication_year,abstract_inverted_index,primary_location,type,cited_by_count'})
    d=get(url)
    if not d: continue
    print('### Q:',q,'n=',d['meta']['count'], file=sys.stderr)
    for w in d.get('results',[]):
        ab=inv2txt(w.get('abstract_inverted_index'))
        doi=(w.get('doi') or '').replace('https://doi.org/','')
        if not doi or not ab: continue
        out.append({'doi':doi,'title':w.get('title'),'year':w.get('publication_year'),'cited':w.get('cited_by_count'),'digits':len(re.findall(r'\d',ab)),'abs':ab[:2200],'query':q,
                    'venue':((w.get('primary_location') or {}).get('source') or {}).get('display_name')})
    time.sleep(0.3)
json.dump(out, open('/root/marfagenez/_dip27_pool4.json','w'))
print('TOTAL',len(out))
out.sort(key=lambda x:-x['digits'])
seen=set()
for x in out[:80]:
    if x['doi'] in seen: continue
    seen.add(x['doi'])
    print(x['digits'],'|',x['year'],'|',x['doi'],'|',(x['title'] or '')[:105])
