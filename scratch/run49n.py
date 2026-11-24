import re, sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_probe49 import fulltext, strip

def grab(p):
    t = strip(fulltext(p))
    open("/root/marfagenez/scratch/ft49_%s.txt" % p, "w").write(t)
    print("OK", p, len(t))

for p in ["PMC7764904", "PMC6284305", "PMC1187820"]:
    try:
        grab(p)
    except Exception as e:
        print("ERR", p, repr(e))

def show(p, pats, n=5, w=300):
    txt = open("/root/marfagenez/scratch/ft49_%s.txt" % p).read()
    print("#" * 16, p)
    for pat in pats:
        print("-" * 6, pat)
        c = 0
        for m in re.finditer(pat, txt, re.I):
            s = max(0, m.start() - w); e = min(len(txt), m.end() + w)
            print(" ...", txt[s:e].strip(), "...\n")
            c += 1
            if c >= n:
                break

show("PMC7764904", [r"per Gy", r"half-time", r"t1/2", r"DSB/cell", r"repair"])
show("PMC6284305", [r"8-oxoG", r"repair rate", r"half-life"], n=3)
show("PMC1187820", [r"per hour", r"repair rate", r"half-time"], n=3)
