import json,re
pool=json.load(open("_dip16_pool.json"))
skip={"10.3390/life15050724","10.1126/science.1089904","10.1021/ja900919c","10.1126/science.1100757","10.1038/ncomms9352","10.1186/s13322-014-0006-2","10.1016/0303-2647(86)90008-0"}
must=re.compile(r"vesicl|protocell|liposom|coacerv|micelle|bilayer|fatty acid|lipid|membrane",re.I)
out=[]
for d,w in pool.items():
    if d in skip: continue
    a=w["abstract"]
    if not must.search((w["title"] or "")+a): continue
    nums=re.findall(r"[0-9]+(?:\.[0-9]+)?\s*(?:%|fold|mM|uM|µM|nM|nm|µm|um|min|h|s\b|M\b)|[0-9]+\.[0-9]+",a)
    out.append((len(nums),w["year"],d,w["title"],nums[:8]))
out.sort(key=lambda r:(-r[0],-int(r[1] or 0)))
for i,r in enumerate(out[:40]):
    print("%02d|n=%d|%s|%s|%s|%s"%(i,r[0],r[1],r[2],(r[3] or "?")[:80],r[4]))
