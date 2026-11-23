import json, urllib.request, re, sys
def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36','Accept':'*/*'})
    return urllib.request.urlopen(req, timeout=90)
d=json.loads(get('https://api.openalex.org/works/https://doi.org/10.1098/rspb.2005.3057?select=doi,title,open_access,locations').read())
print(d['open_access'])
for l in d.get('locations') or []:
    print(l.get('is_oa'), '|', l.get('pdf_url'), '|', l.get('landing_page_url'), '|', (l.get('source') or {}).get('display_name'))
