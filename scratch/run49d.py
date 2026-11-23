import sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_search49 import search

for q in ['ABSTRACT:"8-oxodG"', 'TITLE:"DNA repair"', '"repair half-time"',
          'ABSTRACT:"half-time" AND ABSTRACT:"double-strand"']:
    print("====", q)
    try:
        search(q)
    except Exception as e:
        print("ERR", repr(e))
