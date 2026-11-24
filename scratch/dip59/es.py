import json,urllib.request,urllib.parse
def s(q,n=8):
    u='https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='+urllib.parse.quote(q)+'&format=json&pageSize=%d&resultType=core'%n
    try:
        d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=90))
    except Exception as e:
        print('ERR',q,e); return
    print('### QUERY:',q,'| hits',d.get('hitCount'))
    for r in d['resultList']['result']:
        print(' -',r.get('doi'),'|',r.get('pmcid'),'|',r.get('pubYear'),'|',(r.get('title') or '')[:100])
        print('   ',(r.get('abstractText') or '')[:320].replace('\n',' '))
    print()
for q in ['ABSTRACT:"repair capacity" AND ABSTRACT:"dose" AND ABSTRACT:"saturat"',
          'ABSTRACT:"autophagic flux" AND ABSTRACT:"aggregate" AND ABSTRACT:"declin"',
          'ABSTRACT:"repair" AND ABSTRACT:"half-life" AND ABSTRACT:"dose-dependent"',
          'ABSTRACT:"degradation rate" AND ABSTRACT:"misfolded" AND ABSTRACT:"decreas"']:
    s(q)