import re, sys
sys.path.insert(0, "/root/marfagenez/scratch")
from epmc_probe49 import fulltext, strip

def show(p, pats, n=4, w=300):
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

show("PMC3316722", [r"median half-life", r"half-lives ranged", r"23 h", r"average half-life"])
show("PMC12730232", [r"turnover time", r"half-time", r"hours after", r"18 h", r"48 h"])
show("PMC2033588", [r"per Gy", r"dsb per", r"breaks per cell", r"Gy-1"])
show("PMC4915191", [r"wound", r"\bµm2\b", r"rescal", r"30 s"])
