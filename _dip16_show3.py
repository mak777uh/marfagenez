import json
pool=json.load(open("_dip16_pool.json"))
for d in ["10.1016/j.bpj.2010.06.057","10.2478/biocosmos-2026-0004","10.1371/journal.pbio.3002048","10.1021/la503933x","10.1021/ja900919c","10.1073/pnas.1309299110"]:
    w=pool.get(d)
    if not w: print("MISSING",d); continue
    print("="*90); print(d,"|",w["year"],"|",w["title"]); print(w["abstract"][:1500])
