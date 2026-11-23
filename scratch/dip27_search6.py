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
Q=[
 'immune challenge decreased egg production percent reduction',
 'LPS injection reduced fecundity number of eggs percentage',
 'cost of mounting immune response reduced reproductive success fledglings',
 'immune activation trade-off fecundity reduction proportion',
 'PHA response cost reduced clutch size experiment',
 'antibody response cost reduced fecundity bird measured',
]
for q in Q:
    url='https://api.openalex.org/works?'+urllib.parse.urlencode({'search':q,'per_page':12,'mailto':'research@example.org','select':'doi,title,publication_year,abstract_inverted_index'})
    d=get(url)
    if not d: continue
    print('###',q,'n=',d['meta']['count'])
    for w in d.get('results',[]):
        ab=inv2txt(w.get('abstract_inverted_index'))
        doi=(w.get('doi') or '').replace('https://doi.org/','')
        if not doi or not ab: continue
        # require a percent or a number adjacent to fecundity/egg words
        strong = re.search(r'\d+(\.\d+)?\s?%', ab) and re.search(r'(fecund|egg|offspring|fledg|clutch|reproduct)', ab, re.I)
        if strong:
            print('---',doi,'|',w.get('publication_year'),'|',(w.get('title') or '')[:95])
            for m in re.finditer(r'\d+(\.\d+)?\s?%', ab):
                s=max(0,m.start()-200); e=min(len(ab),m.end()+160)
                seg=ab[s:e]
                if re.search(r'(fecund|egg|offspring|fledg|clutch|reproduct|immun)', seg, re.I):
                    print('   ...',seg,'...')
    time.sleep(0.3)
