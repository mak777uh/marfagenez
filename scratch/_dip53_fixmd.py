import pathlib
p = pathlib.Path("/root/marfagenez/literature/dips/reports/dip-2026-11-23-53.md")
t = p.read_text(encoding="utf-8")
old = """- **Pe в эмбрионах** (10.1093/ismeco… нет; 10.1088/… nodal flow, PMC5544429): в тексте только критерий
  Pe = vR/D > 1 без числа; работы по мозжечковому/желудочковому потоку (PMC12344991, PMC13641946)"""
new = """- **Pe в эмбрионах** (nodal flow, PMC5544429): в тексте только критерий
  Pe = vR/D > 1 без числа; работы по желудочковому/субарахноидальному потоку (PMC12344991, PMC13641946)"""
assert old in t
t = t.replace(old, new)
t = t.replace("**Europe PMC** `search` с `OPEN_ACCESS:y` — 16 запросов", "**Europe PMC** `search` с `OPEN_ACCESS:y` — 17 запросов")
p.write_text(t, encoding="utf-8")
print("fixed")
