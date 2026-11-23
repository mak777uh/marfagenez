import urllib.request, re, sys, json
def fetch(url):
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'})
    return urllib.request.urlopen(req, timeout=90).read().decode('utf-8','replace')
html=fetch('https://pmc.ncbi.nlm.nih.gov/articles/PMC5409330/')
txt=re.sub(r'<script.*?</script>','',html,flags=re.S)
txt=re.sub(r'<style.*?</style>','',txt,flags=re.S)
txt=re.sub(r'<[^>]+>',' ',txt)
txt=re.sub(r'&nbsp;',' ',txt)
txt=re.sub(r'&amp;','&',txt)
txt=re.sub(r'\s+',' ',txt)
open('/root/marfagenez/_dip27_lipl.txt','w').write(txt)
print('LEN',len(txt))
for m in re.finditer(r'(reproduct|fecund|brood|progeny|oocyte|egg)', txt, re.I):
    s=max(0,m.start()-260); e=min(len(txt),m.end()+260)
    seg=txt[s:e]
    if re.search(r'\d', seg) and re.search(r'(reduc|decreas|lower|fewer|impair|cost)', seg, re.I):
        print('...',seg.replace('\n',' '),'...')
        print('-'*80)
