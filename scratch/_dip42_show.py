import json,re
pool=json.load(open("_dip42_pool1.json"))
dup=set(open("_dip42_dups.txt").read().split())
kw=re.compile(r"divi|growth|grow|vesicl|protocell|membrane|μm|micromet|ratio",re.I)
n=0
for p in pool:
    if p["doi"] in dup: continue
    ab=p["abstract"] or ""
    if not ab: continue
    if not re.search(r"divi|grow|bud|fission|reprod",ab,re.I): continue
    nums=re.findall(r"\d+(?:\.\d+)?",ab)
    if len(nums)<2: continue
    n+=1
    print("###",p["doi"],p["year"])
    print("T:",p["title"])
    print("A:",ab[:700].replace("\n"," "))
    print()
print("CAND",n)
