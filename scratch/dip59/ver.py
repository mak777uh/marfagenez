import json,urllib.request,urllib.parse
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
dois=['10.1073/pnas.1117849108','10.1073/pnas.1200583109','10.1080/19491034.2026.2673717','10.1080/09553009314551901','10.1093/nar/gkp237','10.18632/oncotarget.17861','10.1038/emm.2016.133','10.1242/jcs.179978','10.1038/ncomms10399']
for d in dois:
    u='https://api.openalex.org/works/https://doi.org/'+d+'?api_key='+KEY
    try:
        w=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'marfagenez/1.0 (mailto:lead@marfagenez.local)'}),timeout=60))
        inv=w.get('abstract_inverted_index') or {}
        pos={}
        for tok,idx in inv.items():
            for i in idx: pos[i]=tok
        ab=' '.join(pos[i] for i in sorted(pos))
        print('OK',d,'|',w.get('publication_year'),'|',(w.get('title') or '')[:95])
        print('   ABS:',ab[:300])
    except Exception as e:
        print('ERR',d,e)