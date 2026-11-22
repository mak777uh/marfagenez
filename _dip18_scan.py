import json,re,pathlib
p=json.loads(pathlib.Path("_dip18_pool.json").read_text())
rows=[]
for d in p.values():
    a=d["abstract"]; t=d["title"] or ""
    nums=re.findall(r"\d+(?:\.\d+)?\s?(?:%|percent|fold|ms|kJ|mW)", a+t)
    key=bool(re.search(r"overhead|cost|energy|latency|budget|penalt", a+t, re.I))
    rows.append((len(nums),key,d))
rows.sort(key=lambda r:(-r[0],-r[1]))
for n,key,d in rows[:45]:
    yr=str(d["year"])
    print(n, yr, d["doi"][:45], "|", (d["title"] or "")[:95])
