import json,re
p=json.load(open("/root/marfagenez/_dip31_pool.json"))
KW=["saturat","michaelis","km ","vmax","capacity","half-life","half life","clearance","load","burden","threshold","rate of degradation","kinetic"]
rows=[]
for doi,w in p.items():
    ab=w["abstract"] or ""
    score=sum(ab.lower().count(k) for k in KW)
    nums=len(re.findall(r"\d",ab))
    rows.append((score,nums,w["year"],doi,w["title"]))
rows.sort(key=lambda r:-(r[0]*2+min(r[1],40)))
for s,n,y,doi,t in rows[:45]:
    print(f"{s:3d} n={n:3d} {y} {doi}  {t[:110]}")
