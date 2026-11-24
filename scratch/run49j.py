import re, sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_probe49 import fulltext, strip, find_pmcid
from epmc_search49 import search

for doi in ["10.1083/jcb.96.1.1", "10.1016/j.freeradbiomed.2016.12.049",
            "10.1016/j.molcel.2015.10.009", "10.1083/jcb.131.6.1747"]:
    try:
        print("PMC?", doi, find_pmcid(doi))
    except Exception as e:
        print("ERR", doi, repr(e))

print("#### search mito turnover")
for q in ['TITLE:"mitochondrial protein" AND TITLE:"turnover" AND ABSTRACT:"half-life"',
          'ABSTRACT:"mitochondrial" AND ABSTRACT:"degradation rate" AND ABSTRACT:"per hour"',
          'TITLE:"lipid turnover" AND ABSTRACT:"plasma membrane" AND ABSTRACT:"half-life"']:
    print("=" * 10, q)
    try:
        search(q)
    except Exception as e:
        print("ERR", repr(e))
