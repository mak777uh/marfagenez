import sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_search49 import search

QUERIES = [
    'TITLE:"mitophagy rate"',
    'TITLE:"8-oxoguanine" AND ABSTRACT:"repair" AND ABSTRACT:"rate"',
    'TITLE:"proteome turnover" OR TITLE:"protein turnover rates"',
    'TITLE:"plasma membrane" AND ABSTRACT:"internalization rate"',
    'ABSTRACT:"8-oxoG" AND ABSTRACT:"formation rate" AND ABSTRACT:"repair"',
    'TITLE:"single-strand break repair" AND ABSTRACT:"half-life"',
]

for q in QUERIES:
    print("=" * 12, q)
    try:
        search(q)
    except Exception as e:
        print("ERR", repr(e))
