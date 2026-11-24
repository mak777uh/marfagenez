import os, re, sys

D = "/root/marfagenez/scratch/dip56_txt"
label = sys.argv[1]
needles = sys.argv[2:]
txt = open(os.path.join(D, label + ".txt")).read()
flat = re.sub(r"\s+", " ", txt)
for n in needles:
    i = flat.find(n)
    print("===== %s :: %r (idx %s)" % (label, n, i))
    if i < 0:
        continue
    print(flat[max(0, i - 320):i + 420])
    print()
