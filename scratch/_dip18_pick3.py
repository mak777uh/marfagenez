import json,re,pathlib
p=json.loads(pathlib.Path("_dip18_pool.json").read_text())
q3={"monitoring overhead self-adaptive systems measured","self-healing overhead outweighs benefit degradation",
 "survivability formal definition essential services percentage","redundancy energy cost storage cluster replication measured",
 "checkpoint interval optimal overhead energy tradeoff","self-adaptation cost reflects overhead runtime feedback loop"}
n=0
for d in p.values():
    if not (q3 & set(d["queries"])): continue
    a=d["abstract"]
    if not re.search(r"\d+(?:\.\d+)?\s?%|\d+\s?(?:mJ|J\b|W\b|ms)", a): continue
    n+=1
    print("###",d["doi"],"|",d["year"],"|",d["title"])
    print(a[:650].strip()); print()
    if n>=22: break
