import json,sys,urllib.parse,urllib.request
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
QS=sys.argv[1:]
for q in QS:
    url='https://api.openalex.org/works?'+urllib.parse.urlencode({'search':q,'per_page':15,'select':'id,doi,title,publication_year,abstract_inverted_index,type','api_key':KEY})
    try:
        d=json.load(urllib.request.urlopen(url,timeout=40))
    except Exception as e:
        print('ERR',q,e); continue
    print('== Q:',q,'n=',d['meta']['count'])
    for w in d['results']:
        has=bool(w.get('abstract_inverted_index'))
        print('  ',w['publication_year'],('ABS' if has else 'noA'),w.get('doi'),'|',(w.get('title') or '')[:110])
