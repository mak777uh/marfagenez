import urllib.request,re,html
url='https://pmc.ncbi.nlm.nih.gov/articles/PMC4873636/'
try:
    t=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=100).read().decode('utf-8','replace')
    t=re.sub(r'<script.*?</script>','',t,flags=re.S); t=re.sub(r'<[^>]+>',' ',t); t=html.unescape(t); t=re.sub(r'\s+',' ',t)
    open('/root/marfagenez/scratch/dip59/ncomms10399.txt','w').write(t); print('OK',len(t))
    for m in re.finditer(r'[^.]{0,200}(fold|PARP1 activity|decreas)[^.]{0,200}\.',t):
        s=m.group(0).strip()
        if re.search(r'\d',s): print('-',s[:330])
except Exception as e:
    print('ERR',e)