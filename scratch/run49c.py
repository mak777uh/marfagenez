import sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_search49 import search

QUERIES = [
    'TITLE:"double-strand break repair" AND ABSTRACT:"half-time" AND ABSTRACT:"human"',
    'ABSTRACT:"single-strand breaks" AND ABSTRACT:"repair" AND ABSTRACT:"half-time" AND ABSTRACT:"min"',
    'TITLE:"8-oxoguanine" AND ABSTRACT:"mitochondrial DNA" AND ABSTRACT:"turnover"',
    'ABSTRACT:"8-oxodG" AND ABSTRACT:"repair rate"',
    'TITLE:"DNA repair" AND TITLE:"rate" AND ABSTRACT:"lesions per"',
    'TITLE:"mitochondrial" AND TITLE:"half-life" AND ABSTRACT:"days"',
]

for q in QUERIES:
    print("=" * 12, q)
    try:
        search(q)
    except Exception as e:
        print("ERR", repr(e))
