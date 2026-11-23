import pathlib, re, sys

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")
name = sys.argv[1]
anchor = sys.argv[2]
span = int(sys.argv[3]) if len(sys.argv) > 3 else 2500
t = (TXT / (name + ".txt")).read_text(encoding="utf-8", errors="replace")
i = t.find(anchor)
print("found at", i, "len", len(t))
if i >= 0:
    print(t[max(0, i - 300):i + span])
