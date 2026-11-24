import urllib.request,re,html,sys,json
pmcs={'PMC4813294':'jcs179978','PMC5291838':'emm2016133','PMC4854554':'auto20161159376','PMC2709554':'nar_gkp237'}
def grab(pmc):
    url='https://pmc.ncbi.nlm.nih.gov/articles/%s/'%pmc
    r=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64)'})
    t=urllib.request.urlopen(r,timeout=120).read().decode('utf-8','replace')
    t2=re.sub(r'<script.*?</script>','',t,flags=re.S)
    t2=re.sub(r'<style.*?</style>','',t2,flags=re.S)
    t2=re.sub(r'<[^>]+>',' ',t2); t2=html.unescape(t2); t2=re.sub(r'\s+',' ',t2)
    return t2
for pmc,name in pmcs.items():
    try:
        t=grab(pmc); open('scratch/dip59/%s.txt'%name,'w').write(t); print(pmc,name,'OK',len(t))
    except Exception as e:
        print(pmc,name,'ERR',e)