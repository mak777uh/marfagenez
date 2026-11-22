import json
pool=json.load(open("_dip16_pool.json"))
todo=["10.1038/s41467-021-24111-x","10.1038/s41467-020-18815-9","10.1039/d2cc03541c","10.1038/s41598-017-02799-6","10.1038/srep05675","10.1002/smll.202005320","10.1073/pnas.2221064120","10.1038/s41598-017-02799-6"]
for d in todo:
    w=pool.get(d)
    if not w: print("MISSING",d); continue
    print("="*90); print(d,"|",w["year"],"|",w["title"]); print(w["abstract"][:1700])
