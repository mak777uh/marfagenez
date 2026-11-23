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
 'Reproductive effort decreases antibody responsiveness',
 'Assessing the cost of mounting an immune response',
 'Inducing extra copies of the Hsp70 gene Drosophila energetic demand',
 'functional costs and benefits of dietary restriction Drosophila',
 'Reproduction-Longevity Trade-Off Anopheles gambiae',
 'physiological signature of the cost of reproduction parental care',
 'Testing the predictions of energy allocation decisions life-history trade-offs',
 'energy budget sea cucumber breeding period allocation',
 'juvenile hormone regulator trade-off reproduction life span Drosophila',
 'immune challenge female great tits provisioning offspring',
]
out=[]
for q in SPECS:
    url='https://api.openalex.org/works?'+urllib.parse.urlencode({'search':q,'per_page':8,'mailto':'research@example.org','select':'id,doi,title,publication_year,abstract_inverted_index,primary_location,type,cited_by_count'})
    d=get(url)
    if not d: continue
    print('### Q:',q,'n=',d['meta']['count'], file=sys.stderr)
    for w in d.get('results',[])[:6]:
        ab=inv2txt(w.get('abstract_inverted_index'))
        doi=(w.get('doi') or '').replace('https://doi.org/','')
        if not doi: continue
        out.append({'doi':doi,'title':w.get('title'),'year':w.get('publication_year'),'cited':w.get('cited_by_count'),'digits':len(re.findall(r'\d',ab)),'abs':ab[:2200],'query':q,
                    'venue':((w.get('primary_location') or {}).get('source') or {}).get('display_name')})
    time.sleep(0.3)
json.dump(out, open('/root/marfagenez/_dip27_pool5.json','w'))
print('TOTAL',len(out))
for x in out:
    print('-'*90)
    print(x['digits'],'|',x['year'],'|',x['doi'],'|',x['title'])
    print(x['abs'][:1500])
