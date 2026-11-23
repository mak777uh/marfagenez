import pathlib, re, json

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")


def read(slug):
    return (TXT / (slug + ".txt")).read_text(encoding="utf-8", errors="replace")


def show(slug, pat, before=120, after=420, n=2, label=""):
    t = read(slug)
    print("-" * 12, slug, label)
    for m in list(re.finditer(pat, t, re.I))[:n]:
        s = max(0, m.start() - before)
        seg = t[s:m.end() + after]
        print(repr(seg))
        print()


show("h_10_13189_ujme_2020_080601", r"dC/dt0", 200, 260, 1, "derivative")
show("h_10_13189_ujme_2020_080601", r"closed form", 100, 500, 3, "closedform")
show("h_10_1016_j_ress_2005_03_012", r"CA\(T,N\) = 1", 200, 420, 1, "costrate")
show("h_10_1016_j_ress_2005_03_012", r"T0 = ", 260, 420, 1, "T0")
show("h_10_17929_tqs_8_51", r"Corollary 1", 60, 700, 1, "corr1")
show("h_10_1214_16_bjps317", r"C\(n,k,L\)=", 260, 120, 1, "costrate")
show("h_10_17531_ein_2022_3_15", r"pm ICTc", 300, 120, 1, "pmcost")
show("h_10_5784_15_0_417", r"cost savings of between", 300, 260, 1, "savings")
show("PMC13591397", r"1\.5 ATPs", 400, 200, 1, "disulfide")
show("PMC13591397", r"25% to ∼40%", 300, 200, 1, "share")
