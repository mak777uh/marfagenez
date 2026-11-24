txt = open("/root/marfagenez/scratch/PMC6959996.txt").read()
for q in ["In neurons, we see on average ~1-5 events per cell, which is low",
          "engulfed mitochondria remained in non-acidified organelles for hours to days, illustrating efficient autophagosome sequestration"]:
    print("OK" if q in txt else "MISS", len(q.split()), repr(q))
