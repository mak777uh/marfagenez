import sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_search49 import search

Q = [
    '"8-oxoguanine" AND "formation rate" AND "steady-state"',
    '"8-oxoG" AND "accumulation rate" AND "repair"',
    '"DSB" AND "per Gy" AND "rejoining" AND "half-time" AND "foci"',
    '"mitochondrial DNA" AND "8-oxoG" AND "repair rate" AND "accumulat"',
    '"protein carbonyl" AND "degradation rate" AND "per hour"',
]
for q in Q:
    print("=" * 10, q)
    try:
        search(q)
    except Exception as e:
        print("ERR", repr(e))
