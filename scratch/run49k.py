import re, sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_probe49 import fulltext, strip

def grab(p):
    t = strip(fulltext(p))
    open("/root/marfagenez/scratch/ft49_%s.txt" % p, "w").write(t)
    print("OK", p, len(t))

for p in ["PMC2112240", "PMC2120667", "PMC3128517"]:
    try:
        grab(p)
    except Exception as e:
        print("ERR", p, repr(e))

def show(p, pats, n=4, w=280):
    txt = open("/root/marfagenez/scratch/ft49_%s.txt" % p).read()
    print("#" * 18, p)
    for pat in pats:
        print("-" * 6, pat)
        c = 0
        for m in re.finditer(pat, txt, re.I):
            s = max(0, m.start() - w); e = min(len(txt), m.end() + w)
            print(" ...", txt[s:e].strip(), "...\n")
            c += 1
            if c >= n:
                break

show("PMC2112240", [r"percent of", r"half-time", r"per minute", r"min-1", r"1-2%"])
show("PMC2120667", [r"reseal", r"seconds", r"30 s", r"µm2"])
show("PMC3128517", [r"half-life", r"turnover"])
show("PMC10012960", [r"min-1", r"min −1", r"rate of", r"flux"], n=5)
