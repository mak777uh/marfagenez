import json, urllib.request, urllib.parse, time, sys, re
def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':'dip-researcher/1.0 (mailto:research@example.org)'})
    for a in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            print('ERR',e, file=sys.stderr); time.sleep(2)
    return None
def inv2txt(inv):
    if not inv: return ''
    pos={}
    for w,ps in inv.items():
        for p in ps: pos[p]=w
    return ' '.join(pos[i] for i in sorted(pos))
for doi in ['10.1111/j.1365-2435.2010.01825.x','10.1086/694123','10.1093/jmedent/47.5.769','10.1111/j.1365-2435.2008.01507.x','10.1186/1471-2148-13-68']:
    d=get('https://api.openalex.org/works/https://doi.org/'+doi+'?select=doi,title,publication_year,abstract_inverted_index,primary_location')
    if not d: continue
    ab=inv2txt(d.get('abstract_inverted_index'))
    print('='*100); print(doi,'|',d.get('publication_year')); print(d.get('title')); print(ab[:2100])
    time.sleep(0.2)
