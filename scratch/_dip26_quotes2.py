import pathlib, re

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")


def read(slug):
    return (TXT / (slug + ".txt")).read_text(encoding="utf-8", errors="replace")


def show(slug, pat, before=100, after=400, n=1, label=""):
    t = read(slug)
    print("-" * 12, slug, label)
    for m in list(re.finditer(pat, t, re.I))[:n]:
        s = max(0, m.start() - before)
        print(repr(t[s:m.end() + after]))
        print()


show("h_10_13189_ujme_2020_080601", r"C\(t0\) = \(c \+ k F\(t0\)\)", 200, 220, 1, "Ct0")
show("h_10_1016_j_ress_2005_03_012", r"\(13\)", 700, 60, 1, "T0eq13")
show("h_10_1016_j_ress_2005_03_012", r"\(12\)", 500, 60, 1, "Ncond12")
show("h_10_1214_16_bjps317", r"if the cumulative repair cost", 200, 420, 1, "policyrule")
show("h_10_17929_tqs_8_51", r"cost rate 𝐶𝐶\(𝑇𝑇\) is", 60, 420, 1, "Ctqs")
show("h_10_5784_15_0_417", r"replacing a system by a new \n", 200, 300, 1, "policydef")
show("h_10_23940_ijpe_23_06_p1_359367", r"C\(T\)=", 120, 400, 1, "ijpe")
