import pathlib, re

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")


def ctx(t, pat, n=3, w=340):
    out = []
    for m in list(re.finditer(pat, t, re.I))[:n]:
        s = max(0, m.start() - w // 3)
        e = min(len(t), m.end() + w)
        out.append(t[s:e].replace("\n", " | ")[:w + 100])
    return out


print("=" * 25, "rairo80 head")
t = (TXT / "h_10_1051_ro_1980140302491.txt").read_text(encoding="utf-8", errors="replace")
print(len(t))
print(t[:1500])
print("--- rairo80 imperfect hits")
for h in ctx(t, r"imperfect|preventive|Weibull", 4):
    print("  *", h)

print("=" * 25, "imperfect PM across texts")
for f in sorted(TXT.glob("h_*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    low = t.lower()
    a = low.count("age reduction")
    b = low.count("improvement factor")
    if a or b:
        print(f.name, "ageReduction", a, "improveFactor", b)
        for h in ctx(t, r"age reduction|improvement factor", 2):
            print("   *", h)
