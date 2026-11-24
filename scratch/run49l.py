import re, sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_probe49 import fulltext, strip
from epmc_search49 import search

# ensure autophagy text saved under ft49 name
try:
    t = strip(fulltext("PMC10012960"))
    open("/root/marfagenez/scratch/ft49_PMC10012960.txt", "w").write(t)
    print("OK PMC10012960", len(t))
except Exception as e:
    print("ERR", repr(e))

txt = open("/root/marfagenez/scratch/ft49_PMC10012960.txt").read()
for pat in [r"min-1", r"min−1", r"per min", r"rate constant", r"h-1"]:
    print("-" * 6, pat)
    c = 0
    for m in re.finditer(pat, txt, re.I):
        s = max(0, m.start() - 300); e = min(len(txt), m.end() + 300)
        print(" ...", txt[s:e].strip(), "...\n")
        c += 1
        if c >= 3:
            break

print("#### SEARCHES")
for q in ['"breaks per hour"', '"8-oxoG" AND "per cell per day"',
          '"repair capacity" AND "per hour" AND "DNA"',
          '"mitochondria" AND "per hour" AND "degrad" AND "hepatocyte"']:
    print("=" * 10, q)
    try:
        search(q)
    except Exception as e:
        print("ERR", repr(e))
