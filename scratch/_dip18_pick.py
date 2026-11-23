import json,re,pathlib
p=json.loads(pathlib.Path("_dip18_pool.json").read_text())
def score(d):
    a=d["abstract"]; t=d["title"] or ""; s=a+" "+t
    ns=len(re.findall(r"\d+(?:\.\d+)?\s?%", s))*2 + len(re.findall(r"\d+(?:\.\d+)?\s?(?:x|times|fold)\b", s))
    kw=len(re.findall(r"overhead|energy|joule|cost|latency|failur|repair|checkpoint|replicat|monitor|availab|degrado", s, re.I))
    return ns*3+kw
rows=sorted(p.values(), key=score, reverse=True)
seen=0
for d in rows[:26]:
    print("###", d["doi"], "|", d["year"], "|", d["title"])
    print(d["abstract"][:850].strip())
    print()
