import json,urllib.request,urllib.parse
dois=['10.1073/pnas.1117849108','10.1242/jcs.179978','10.1080/15548627.2016.1159376','10.1038/emm.2016.133','10.1093/nar/gkp237']
for d in dois:
    u='https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids='+urllib.parse.quote(d)+'&format=json&tool=marfagenez&email=lead@marfagenez.local'
    try:
        r=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60))
        for rec in r.get('records',[]):
            print(d,'->',rec.get('pmcid'),rec.get('pmid'),'ERR' if rec.get('errmsg') else '')
    except Exception as e:
        print(d,'ERR',e)