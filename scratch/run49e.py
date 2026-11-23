import re, sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_probe49 import fulltext, strip

pmcs = ["PMC2033588", "PMC12730232", "PMC3316722", "PMC8626426", "PMC7555361", "PMC4915191"]
for p in pmcs:
    try:
        t = strip(fulltext(p))
        open("/root/marfagenez/scratch/ft49_%s.txt" % p, "w").write(t)
        print("OK", p, len(t))
        print("HEAD:", t[:900].replace("\n", " "))
        print()
    except Exception as e:
        print("ERR", p, repr(e))
