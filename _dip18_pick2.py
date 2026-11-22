import json,re,pathlib
p=json.loads(pathlib.Path("_dip18_pool.json").read_text())
pats={
 "MAPEK": r"MAPE-K|self-adapt|autonomic comput",
 "SURV": r"survivab|resilience metric|resilience quantif",
 "MON": r"monitoring overhead|overhead of monitor|probe overhead",
 "INTEG": r"integrity check|checksum|scrub|verification overhead|energy.*verif",
 "REPL": r"replicat.*(cost|energy|overhead)|erasure cod.*overhead",
}
for name,pat in pats.items():
    print("=========",name)
    for d in p.values():
        s=(d["title"] or "")+" "+d["abstract"]
        if re.search(pat,s,re.I) and re.search(r"\d+(?:\.\d+)?\s?%",d["abstract"]):
            print("###",d["doi"],"|",d["year"],"|",d["title"])
            print(d["abstract"][:600].strip())
            print()
