import re, sys

def show(p, pats, n=3, w=420):
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

show("PMC3316722", [r"mean turnover", r"turnover of", r"∼20 h"], n=3)
show("PMC2120667", [r"rescal", r"min", r"exocytosis rate"], n=3, w=250)
show("PMC6959996", [r"24 h", r"days", r"per cell"], n=4, w=300)
show("PMC7764904", [r"17\.6", r"15 min"], n=2, w=350)
show("PMC2112240", [r"3\.1%", r"0\.9%"], n=2, w=400)
