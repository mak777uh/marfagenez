import json,glob
dois=set()
for l in open("literature/map/atoms.jsonl"):
    a=json.loads(l)
    for w in a.get("works",[]):
        if w.get("doi"): dois.add(w["doi"].lower())
for f in glob.glob("literature/dips/reports/*.jsonl"):
    for l in open(f):
        try: a=json.loads(l)
        except: continue
        for w in a.get("works",[]):
            if w.get("doi"): dois.add(w["doi"].lower())
print(len(dois))
open("_dip42_dups.txt","w").write("\n".join(sorted(dois)))
