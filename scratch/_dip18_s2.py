import json, subprocess, pathlib
KEY=pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()
CURL="/mnt/c/Windows/System32/curl.exe"
def get(url, params):
    args=[CURL,"-sS","-G",url]
    for k,v in params.items(): args+=["--data-urlencode",f"{k}={v}"]
    r=subprocess.run(args,capture_output=True,text=True)
    if r.returncode!=0: return {"__err":r.stderr[:300]}
    try: return json.loads(r.stdout)
    except Exception as e: return {"__err":str(e)+" "+r.stdout[:200]}
def absx(inv):
    if not inv: return ""
    pos={}
    for w,idxs in inv.items():
        for i in idxs: pos[i]=w
    return " ".join(pos[i] for i in sorted(pos))
QUERIES=[
 "checkpoint overhead percentage of application runtime measured",
 "replication energy cost storage availability measurement",
 "monitoring overhead measured self-adaptive system experiment percentage",
 "energy overhead integrity verification mobile device measurement",
 "self-healing introduces new failures cascading overhead",
 "availability model repair cost downtime MTBF quantify",
 "performance and energy overhead of fault tolerance mechanisms HPC measurement",
 "cell membrane repair cost metabolic energy bacterium",
 "self-repair cost growth maintenance Escherichia coli energy",
]
pool=json.loads(pathlib.Path("_dip18_pool.json").read_text())
new=0
for q in QUERIES:
    d=get("https://api.openalex.org/works",{"search":q,"per_page":"25",
      "select":"id,doi,title,publication_year,abstract_inverted_index,cited_by_count","api_key":KEY})
    if "__err" in d:
        print("ERR",q,d["__err"][:150]); continue
    n=0
    for w in d.get("results",[]):
        doi=(w.get("doi") or "").replace("https://doi.org/","").lower()
        a=absx(w.get("abstract_inverted_index"))
        if not doi or not a: continue
        n+=1
        if doi not in pool:
            pool[doi]={"doi":doi,"title":w.get("title"),"year":w.get("publication_year"),
                       "cites":w.get("cited_by_count"),"abstract":a,"queries":[q]}; new+=1
        else: pool[doi]["queries"].append(q)
    print(q,"->",n)
print("POOL",len(pool),"new",new)
pathlib.Path("_dip18_pool.json").write_text(json.dumps(pool,ensure_ascii=False,indent=1))
