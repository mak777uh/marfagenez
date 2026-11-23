import pathlib, re

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")
t = (TXT / "h_10_1051_ro_1980140302491.txt").read_text(encoding="utf-8", errors="replace")
i = t.find("1. Introduction")
if i < 0:
    i = t.find("Introduction")
print("rairo80 len", len(t), "idx", i)
print(t[i:i + 4200])
print("#### res2005 cost rate contexts")
t2 = (TXT / "h_10_1016_j_ress_2005_03_012.txt").read_text(encoding="utf-8", errors="replace")
for m in list(re.finditer(r"long-run average cost|cost rate|C\(T\)|expected cost", t2, re.I))[:6]:
    s = max(0, m.start() - 150)
    print("  *", t2[s:m.end() + 320].replace("\n", " | ")[:430])
