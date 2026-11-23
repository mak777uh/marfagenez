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
QUERIES=[
 'immune challenge reduced fecundity percent experimental birds',
 'heat shock protein overexpression costs fecundity Drosophila',
 'autophagy inhibition reduces fecundity reproduction trade-off',
 'SOD overexpression lifespan cost fecundity Drosophila',
 'protein synthesis cost reproduction somatic maintenance bird',
 'reproductive effort decreased immune function experimental manipulation lizard',
 'telomere shortening reproduction effort cost longitudinal',
 'dietary restriction increased DNA repair decreased fecundity',
 'molecular chaperone maintenance reproduction trade-off experimental',
 'reduced repair increased fecundity experimental evolution mutation',
 'costs of immunity fecundity reduction percentage beetle',
 'maintenance energy budget percentage basal metabolism reproduction allocation',
]
out=[]
for q in QUERIES:
    url='https://api.openalex.org/works?'+urllib.parse.urlencode({'search':q,'per_page':20,'mailto':'research@example.org','select':'id,doi,title,publication_year,abstract_inverted_index,primary_location,type,cited_by_count'})
    d=get(url)
    if not d: continue
    print('### Q:',q,'n=',d['meta']['count'], file=sys.stderr)
    for w in d.get('results',[]):
        ab=inv2txt(w.get('abstract_inverted_index'))
        doi=(w.get('doi') or '').replace('https://doi.org/','')
        if not doi or not ab: continue
        out.append({'doi':doi,'title':w.get('title'),'year':w.get('publication_year'),'cited':w.get('cited_by_count'),'digits':len(re.findall(r'\d',ab)),'abs':ab[:1900],'query':q,
                    'venue':((w.get('primary_location') or {}).get('source') or {}).get('display_name')})
    time.sleep(0.3)
json.dump(out, open('/root/marfagenez/_dip27_pool2.json','w'))
print('TOTAL',len(out))
out.sort(key=lambda x:-x['digits'])
seen=set()
for x in out[:70]:
    if x['doi'] in seen: continue
    seen.add(x['doi'])
    print(x['digits'],'|',x['year'],'|',x['doi'],'|',(x['title'] or '')[:105])
