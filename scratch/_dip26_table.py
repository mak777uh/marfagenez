import pathlib, re

TXT = pathlib.Path("/root/marfagenez/_dip26_txt")
t = (TXT / "PMC13591397.txt").read_text(encoding="utf-8", errors="replace")
i = t.lower().find("protein disulfide isomerase")
print(repr(t[max(0, i - 2500):i + 400]))
