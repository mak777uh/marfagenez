import json
for l in open("literature/map/atoms.jsonl"):
    a=json.loads(l)
    if a.get("domain")=="bio.protocell":
        print(a["atom"],"|",a["statement"][:120])
        for w in a.get("works",[]):
            print("    doi:",w.get("doi"))
