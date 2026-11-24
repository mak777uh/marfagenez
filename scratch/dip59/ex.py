import re,html,sys
f=sys.argv[1]; pat=sys.argv[2]
t=open(f,encoding='utf-8',errors='replace').read()
t=re.sub(r'<[^>]+>',' ',t); t=html.unescape(t); t=re.sub(r'\s+',' ',t)
seen=set()
for m in re.finditer(r'[^.]{0,250}(?:%s)[^.]{0,250}\.'%pat,t):
    s=m.group(0).strip()
    if re.search(r'\d',s) and s not in seen:
        seen.add(s); print('-',s[:460])