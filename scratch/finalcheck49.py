import json

M = {
 "10.1038/bjc.1995.62": "/root/marfagenez/scratch/ft49_PMC2033588.txt",
 "10.3390/ijms21249488": "/root/marfagenez/scratch/ft49_PMC7764904.txt",
 "10.1186/s13059-018-1582-2": "/root/marfagenez/scratch/ft49_PMC6284305.txt",
 "10.1074/mcp.M111.011429": "/root/marfagenez/scratch/ft49_PMC3316722.txt",
 "10.1038/s41467-021-26842-3": "/root/marfagenez/scratch/ft49_PMC8626426.txt",
 "10.1083/jcb.96.1.1": "/root/marfagenez/scratch/ft49_PMC2112240.txt",
 "10.1080/15548627.2022.2117515": "/root/marfagenez/scratch/ft49_PMC10012960.txt",
 "10.1083/jcb.201512022": "/root/marfagenez/scratch/ft49_PMC4915191.txt",
 "10.7554/eLife.50260": "/root/marfagenez/scratch/PMC6959996.txt",
}

cache = {k: open(v).read() for k, v in M.items()}
rows = [json.loads(l) for l in open("/root/marfagenez/literature/dips/reports/dip-2026-11-23-49.jsonl")]
bad = 0
for r in rows:
    for w in r["works"]:
        q = w["quote"]
        ok = q in cache[w["doi"]]
        if not ok:
            bad += 1
        print(("OK  " if ok else "FAIL"), r["atom"], w["doi"], len(q.split()), "words")
print("FAILURES:", bad)
