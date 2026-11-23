import json,sys,urllib.parse,urllib.request
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
def inv(ii):
    if not ii: return ''
    pos=[]
    for w,ps in ii.items():
        for p in ps: pos.append((p,w))
    return ' '.join(w for _,w in sorted(pos))
for doi in sys.argv[1:]:
    url='https://api.openalex.org/works/https://doi.org/'+doi+'?api_key='+KEY
    try:
        d=json.load(urllib.request.urlopen(url,timeout=40))
    except Exception as e:
        print('###',doi,'ERR',e); continue
    print('###',doi,'|',d.get('publication_year'),'|',d.get('type'))
    print('T:',d.get('title'))
    print('A:',inv(d.get('abstract_inverted_index')) or 'NO ABSTRACT')
    print()
