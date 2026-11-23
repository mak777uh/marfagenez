import pathlib
t = pathlib.Path("/root/marfagenez/_dip26_txt/h_10_13189_ujme_2020_080601.txt").read_text(encoding="utf-8", errors="replace")
i = t.find("IN the case of")
print(repr(t[i:i+520]))
