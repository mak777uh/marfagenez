import importlib.util, re, html
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

def plain(pmc):
    xml = e.fulltext(pmc)
    t = re.sub(r"<[^>]+>", " ", xml)
    return html.unescape(re.sub(r"\s+", " ", t))

t = plain("PMC12344991")
i = t.find("global Péclet numbers")
print("PMC12344991:", t[i-200:i+700])

t2 = plain("PMC13319206")
print("\nPMC13319206 len", len(t2))
for m in re.finditer(r"P[eé]clet", t2):
    frag = t2[max(0,m.start()-200):m.end()+200]
    if re.search(r"\d", frag): print("  ...", frag[:400])
