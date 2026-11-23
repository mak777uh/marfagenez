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
 'lipopolysaccharide immune challenge decreased egg production crickets',
 'brood size manipulation cost of reproduction immune function',
 'immunocompetence handicap reduced fecundity number of eggs',
 'energy allocated to reproduction percentage of assimilated energy',
 'reproduction reduces somatic maintenance oxidative damage repair measured',
 'cost of reproduction increased mortality percentage manipulation',
 'oral antioxidant supplementation reproduction lifespan cost bird',
 'increased DNA repair capacity decreased growth rate trade-off',
 'proteostasis collapse onset of reproduction somatic maintenance',
 'reproduction suppresses somatic repair germline cost measurement',
 'basal metabolic rate maintenance cost fraction energy budget ectotherm',
 'protein turnover cost percent daily energy expenditure',
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
json.dump(out, open('/root/marfagenez/_dip27_pool3.json','w'))
print('TOTAL',len(out))
out.sort(key=lambda x:-x['digits'])
seen=set()
for x in out[:70]:
    if x['doi'] in seen: continue
    seen.add(x['doi'])
    print(x['digits'],'|',x['year'],'|',x['doi'],'|',(x['title'] or '')[:105])
