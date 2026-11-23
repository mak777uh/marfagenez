import re
t=open('/root/marfagenez/_dip27_eider.txt').read()
pats=['mass loss','lymphocyte','antibod','tetanus','diphtheria','SRBC']
seen=set()
for p in pats:
    for m in re.finditer(p, t, re.I):
        s=max(0,m.start()-250); e=min(len(t),m.end()+250)
        seg=t[s:e]
        if re.search(r'\d', seg) and re.search(r'(table|mean|higher|lower|reduc|increas|%|±)', seg, re.I):
            k=seg[:80]
            if k in seen: continue
            seen.add(k)
            print('['+p+'] ...',seg,'...')
            print('-'*70)
