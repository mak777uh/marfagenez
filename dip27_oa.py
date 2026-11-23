import json, urllib.request, urllib.parse, time, sys, re
def get(url, raw=False):
    req=urllib.request.Request(url, headers={'User-Agent':'dip-researcher/1.0 (mailto:research@example.org)'})
    for a in range(3):
        try:
            r=urllib.request.urlopen(req, timeout=60)
            b=r.read()
            return b.decode('utf-8','replace') if raw else json.loads(b)
        except Exception as e:
            print('ERR',url,e, file=sys.stderr); time.sleep(2)
    return None
# 1) check OA locations for lipl-4 paper and others
for doi in ['10.3389/fnmol.2017.00101','10.3354/ab00626','10.1111/are.13621','10.1098/rsbl.2004.0171','10.1186/1471-2148-13-68','10.1111/j.1474-9726.2006.00261.x']:
    d=get('https://api.openalex.org/works/https://doi.org/'+doi+'?select=id,doi,title,open_access,best_oa_location,primary_location,locations')
    if not d: continue
    print(doi,'| OA:',d.get('open_access'),'| best:',(d.get('best_oa_location') or {}).get('pdf_url'),(d.get('best_oa_location') or {}).get('landing_page_url'))
    for l in (d.get('locations') or [])[:6]:
        print('   loc:',l.get('is_oa'),l.get('pdf_url'),l.get('landing_page_url'))
