import importlib.util, sys, re
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

targets = [
    ("PMC12978645", r"Damk"),
    ("PMC5515221", r"Thiele|Damk|P[eé]clet"),
    ("PMC5515263", r"Thiele"),
    ("PMC12779220", r"Thiele"),
    ("PMC4841543", r"Thiele"),
    ("PMC13522592", r"Sherwood"),
    ("PMC12854670", r"Sherwood"),
    ("PMC13641946", r"P[eé]clet"),
    ("PMC13593633", r"P[eé]clet"),
    ("PMC13040666", r"P[eé]clet"),
    ("PMC13576833", r"Sherwood|Biot"),
]
for pmc, pat in targets:
    xml = e.fulltext(pmc)
    print("\n########", pmc)
    n = 0
    for title, body in e.sections(xml):
        for sent in e.sentences(body):
            if re.search(pat, sent, re.I) and re.search(r"\d", sent) and 40 < len(sent) < 500:
                print(f"[{title[:60]}] {sent[:430]}")
                n += 1
                if n >= 10: break
        if n >= 10: break
