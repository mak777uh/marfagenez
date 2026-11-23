import sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_search49 import search

QUERIES = [
    'ABSTRACT:"8-oxoguanine" AND ABSTRACT:"steady-state" AND ABSTRACT:"repair" AND ABSTRACT:"per day"',
    'ABSTRACT:"mitophagy" AND ABSTRACT:"rate" AND TITLE:"neurons" AND ABSTRACT:"per hour"',
    'ABSTRACT:"lipid" AND ABSTRACT:"turnover" AND TITLE:"plasma membrane"',
    'ABSTRACT:"DNA repair" AND TITLE:"kinetics" AND ABSTRACT:"breaks per"',
    'TITLE:"oxidative DNA damage" AND TITLE:"formation" AND ABSTRACT:"per cell per day"',
    'TITLE:"membrane repair" AND ABSTRACT:"seconds" AND ABSTRACT:"resealing"',
]

for q in QUERIES:
    print("=" * 12, q)
    try:
        search(q)
    except Exception as e:
        print("ERR", repr(e))
