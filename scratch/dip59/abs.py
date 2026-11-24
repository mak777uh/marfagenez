import json,urllib.request,re,html
KEY=open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
for d in ['10.1073/pnas.1200583109','10.1093/nar/gkp237']:
    u='https://api.openalex.org/works/https://doi.org/'+d+'?api_key='+KEY
    w=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'m'}),timeout=60))
    inv=w.get('abstract_inverted_index') or {}
    pos={}
    for tok,idx in inv.items():
        for i in idx: pos[i]=tok
    print('###',d); print(' '.join(pos[i] for i in sorted(pos))); print()
# NAR sentence
t=open('scratch/dip59/nar_gkp237.txt').read()
for m in re.finditer(r'[^.]{0,300}t \u00bd[^.]{0,300}\.',t):
    print('NAR>',m.group(0).strip()[:500])
# emm sentence
t=open('scratch/dip59/emm2016133.txt').read()
for m in re.finditer(r'[^.]{0,200}MG132 \(10[^.]{0,300}\.',t):
    print('EMM>',m.group(0).strip()[:500])