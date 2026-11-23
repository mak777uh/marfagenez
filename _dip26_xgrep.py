import pathlib, re, sys

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")
terms = [t.lower() for t in sys.argv[1].split("||")]
for f in sorted(TXT.glob("h_*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    low = t.lower()
    found = [x for x in terms if x in low]
    if found:
        print(f.name, "->", found)
        # print one context for the first found term
        m = low.find(found[0])
        print("   ", t[max(0, m - 200):m + 300].replace("\n", " | ")[:460])
