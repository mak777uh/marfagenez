import importlib.util, re
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

targets = [
    ("PMC8621293", r"Deborah"),
    ("PMC12988972", r"Biot"),
    ("PMC12344991", r"P[eé]clet"),
    ("PMC10361723", r"P[eé]clet"),
    ("PMC5544429", r"P[eé]clet"),
    ("PMC8847403", r"Deborah"),
]
for pmc, pat in targets:
    xml = e.fulltext(pmc)
    print("\n########", pmc, len(xml))
    n = 0
    for title, body in e.sections(xml):
        for sent in e.sentences(body):
            if re.search(pat, sent, re.I) and re.search(r"\d", sent) and 30 < len(sent) < 480:
                print(f"[{title[:55]}] {sent[:400]}")
                n += 1
                if n >= 12: break
        if n >= 12: break
