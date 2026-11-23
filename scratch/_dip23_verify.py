import json,urllib.request
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
DOIS='''10.18632/aging.100613 10.1091/mbc.e13-01-0010 10.1091/mbc.e14-08-1262 10.1242/jcs.140087
10.1093/hmg/ddn157 10.1093/hmg/ddg074 10.1016/j.jbc.2022.102680 10.1074/jbc.m117.811448
10.1096/fj.05-5080fje 10.1016/j.stem.2023.02.010 10.7554/elife.06197 10.15252/embr.201643458'''.split()
out={}
for doi in DOIS:
    try:
        d=json.load(urllib.request.urlopen('https://api.openalex.org/works/https://doi.org/'+doi+'?api_key='+KEY,timeout=40))
    except Exception as e:
        print('FAIL',doi,e); continue
    assert d.get('doi'), doi
    out[doi]={'id':d['id'],'doi':d['doi'],'title':d['title'],'year':d['publication_year'],'type':d['type'],'has_abs':bool(d.get('abstract_inverted_index'))}
    print('OK',doi,'->',d['doi'],'|',d['publication_year'],d['type'],'| abs',out[doi]['has_abs'],'|',d['title'][:70])
json.dump(out,open('_dip23_verified.json','w'),ensure_ascii=False,indent=1)
print('verified:',len(out))
