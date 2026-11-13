import os
os.chdir("/root/marfagenez")
P = "docs/CLAIMS.md"
s = open(P, encoding="utf-8").read()
i = s.find("## Что доказано (уровень A)")
print(repr(s[i:i+1400]))
