import json,urllib.request,urllib.parse
def find(doi):
    u='https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='+urllib.parse.quote('DOI:"%s"'%doi)+'&format=json&pageSize=3'
    try:
        d=json.load(urllib.request.urlopen(u,timeout=60))
        for r in d['resultList']['result']:
            print(doi,'->',r.get('pmcid'),r.get('pubYear'),(r.get('title') or '')[:80],'| OA',r.get('isOpenAccess'))
    except Exception as e:
        print(doi,'ERR',e)
for d in ['10.1073/pnas.1117849108','10.1080/19491034.2026.2673717','10.18632/oncotarget.17861','10.1080/15548627.2016.1159376','10.1080/09553009314551901','10.3390/cells13161364']:
    find(d)