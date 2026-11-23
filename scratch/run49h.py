import sys, json, urllib.parse
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_probe49 import get, find_pmcid, epmc_search

Q = [
    '"8-oxoguanine" AND "half-life" AND "repair"',
    '"8-oxodG" AND "steady-state" AND "repair rate"',
    '"mitophagy" AND "rate per hour"',
    '"mitochondrial" AND "turnover" AND "half-life" AND "liver"',
    '"single-strand break repair" AND "half-time" AND "human cells"',
]
for q in Q:
    print("=" * 12, q)
    try:
        d = epmc_search(q, 8)
        for r in d.get("resultList", {}).get("result", []):
            print(r.get("pubYear"), "|", (r.get("title") or "")[:95], "|", r.get("doi"), "|", r.get("pmcid"))
    except Exception as e:
        print("ERR", repr(e))
