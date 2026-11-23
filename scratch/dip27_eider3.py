import re
t=open('/root/marfagenez/_dip27_eider.txt').read()
found=0
for m in re.finditer(r"clutch", t, re.I):
    s=max(0,m.start()-230); e=min(len(t),m.end()+230)
    seg=t[s:e]
    if re.search(r"\d\.\d", seg) and re.search(r"(mean|average|eggs)", seg, re.I):
        print('...',seg,'...'); print('-'*70); found+=1
        if found>12: break
print('N', found)
