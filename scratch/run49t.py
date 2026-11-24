txt = open("/root/marfagenez/scratch/ft49_PMC3316722.txt").read()
q = "if we correct for protein abundance, it takes \u223c24 h for 50% turnover of the total HeLa proteome"
print("OK" if q in txt else "MISS", len(q.split()))
q2 = "The average turnover rate for HeLa proteins was \u223c20 h."
print("Q2", "OK" if q2 in txt else "MISS", len(q2.split()))
i = txt.find("if we correct for protein abundance")
print(repr(txt[i:i+220]))
