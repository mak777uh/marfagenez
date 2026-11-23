import re, sys

PATS = {
 "PMC2033588": [r"half-time", r"rejoining", r"DSB"],
 "PMC12730232": [r"turnover", r"half-life", r"h-1"],
 "PMC3316722": [r"half-life", r"median"],
 "PMC8626426": [r"half-life", r"days", r"mitochond"],
 "PMC7555361": [r"mitophagy rate", r"per hour", r"hours"],
 "PMC4915191": [r"reseal", r"seconds", r"recovery"],
}

for p, pats in PATS.items():
    txt = open("/root/marfagenez/scratch/ft49_%s.txt" % p).read()
    print("#" * 20, p)
    for pat in pats:
        print("-" * 8, pat)
        n = 0
        for m in re.finditer(pat, txt, re.I):
            s = max(0, m.start() - 260); e = min(len(txt), m.end() + 260)
            print("  ...", txt[s:e].strip(), "...\n")
            n += 1
            if n >= 4:
                break
