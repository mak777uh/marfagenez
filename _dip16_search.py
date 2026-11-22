import json, subprocess, pathlib
KEY=pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()
CURL="/mnt/c/Windows/System32/curl.exe"
def get(url, params):
    args=[CURL,"-sS","-G",url]
    for k,v in params.items(): args+=["--data-urlencode",f"{k}={v}"]
    r=subprocess.run(args,capture_output=True,text=True)
    if r.returncode!=0: return {"__err":r.stderr[:300]}
    try: return json.loads(r.stdout)
    except Exception as e: return {"__err":str(e)+r.stdout[:200]}
def absx(inv):
    if not inv: return ""
    pos={}
    for w,idxs in inv.items():
        for i in idxs: pos[i]=w
    return " ".join(pos[i] for i in sorted(pos))
QUERIES=[
 "fatty acid vesicle growth and division",
 "vesicle content loss during division",
 "membrane permeability nutrient uptake protocell",
 "lipid synthesis cost protocells",
 "coacervate protocells fuel driven",
 "competition between vesicles protocell growth",
 "osmotic pressure vesicle stability division",
 "protocell growth rate membrane cost",
 "asymmetric division vesicle membrane surface area",
 "oleic acid vesicle division external fatty acid micelles",
]
pool={}
for q in QUERIES:
    for page in (1,2):
        d=get("https://api.openalex.org/works",{"search":q,"per_page":"25","page":str(page),
          "select":"id,doi,title,publication_year,abstract_inverted_index","api_key":KEY})
        if "__err" in d:
            print("ERR",q,d["__err"][:200]); continue
        for w in d.get("results",[]):
            doi=(w.get("doi") or "").replace("https://doi.org/","").lower()
            a=absx(w.get("abstract_inverted_index"))
            if not doi or not a: continue
            if doi not in pool:
                pool[doi]={"doi":doi,"title":w.get("title"),"year":w.get("publication_year"),"abstract":a,"queries":[q]}
print("POOL",len(pool))
pathlib.Path("/root/marfagenez/_dip16_pool.json").write_text(json.dumps(pool,ensure_ascii=False,indent=1))
