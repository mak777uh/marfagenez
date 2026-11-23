import pathlib, re, sys

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")
pat = re.compile(sys.argv[1] if len(sys.argv) > 1 else r"C\(T\)|cost per unit time|cost rate|expected cost", re.I)
for f in sorted(TXT.glob("*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    hits = []
    for m in pat.finditer(t):
        s = max(0, m.start() - 90)
        e = min(len(t), m.end() + 130)
        hits.append(t[s:e].replace("\n", " | "))
        if len(hits) >= int(sys.argv[2] if len(sys.argv) > 2 else 5):
            break
    print("=" * 20, f.name, len(t), "hits:", len(hits))
    for h in hits:
        print("   ", h[:230])
