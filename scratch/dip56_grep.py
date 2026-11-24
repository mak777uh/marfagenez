import os, re, sys

D = "/root/marfagenez/scratch/dip56_txt"
label = sys.argv[1]
pats = sys.argv[2:]
txt = open(os.path.join(D, label + ".txt")).read()
# split into sentences
sents = re.split(r"(?<=[.;])\s+", txt)
hits = []
for s in sents:
    low = s.lower()
    if any(p.lower() in low for p in pats):
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) > 25:
            hits.append(s)
print("### %s : %d hits" % (label, len(hits)))
seen = set()
n = 0
for h in hits:
    k = h[:80]
    if k in seen:
        continue
    seen.add(k)
    n += 1
    print("[%02d] %s" % (n, h[:600]))
    if n >= int(os.environ.get("MAXHITS", "25")):
        break
