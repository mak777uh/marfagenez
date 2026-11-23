import urllib.request, re
def fetch(url):
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'})
    return urllib.request.urlopen(req, timeout=90).read().decode('utf-8','replace')
html=fetch('https://pmc.ncbi.nlm.nih.gov/articles/PMC1599870/')
t=re.sub(r'<script.*?</script>','',html,flags=re.S)
t=re.sub(r'<style.*?</style>','',t,flags=re.S)
t=re.sub(r'<[^>]+>',' ',t)
t=t.replace('&nbsp;',' ').replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
t=re.sub(r'\s+',' ',t)
open('/root/marfagenez/_dip27_eider.txt','w').write(t)
print('LEN',len(t))
for m in re.finditer(r'(fecundit|number of eggs|clutch size|eggs laid)', t, re.I):
    s=max(0,m.start()-300); e=min(len(t),m.end()+300)
    seg=t[s:e]
    if re.search(r'\d', seg) and re.search(r'(reduc|decreas|lower|fewer|higher|increase)', seg, re.I):
        print('...',seg,'...'); print('-'*80)
