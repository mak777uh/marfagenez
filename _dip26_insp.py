import pathlib, re, sys

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")
slugs = sys.argv[1].split(",")
pats = sys.argv[2].split("||")
width = int(sys.argv[3]) if len(sys.argv) > 3 else 260
maxper = int(sys.argv[4]) if len(sys.argv) > 4 else 4
for slug in slugs:
    f = TXT / (slug + ".txt")
    if not f.exists():
        print("MISSING", slug)
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    print("#" * 30, slug, len(t))
    for p in pats:
        ms = list(re.finditer(p, t, re.I))[:maxper]
        for m in ms:
            s = max(0, m.start() - width // 3)
            e = min(len(t), m.end() + width)
            print(f"  [{p}] ..." + t[s:e].replace("\n", " | ")[:width + 120] + "...")
