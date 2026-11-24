import importlib.util, re, html
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

def plain(pmc):
    xml = e.fulltext(pmc)
    t = re.sub(r"<[^>]+>", " ", xml)
    return html.unescape(re.sub(r"\s+", " ", t))

for pmc, pats in {
 "PMC12567277": [r"Damk[^.]{0,160}"],
 "PMC5515263": [r"Thiele modulus[^.]{0,160}", r"ϕ[^.]{0,120}"],
 "PMC12344991": [r"P[eé]clet number[^.]{0,200}"],
}.items():
    t = plain(pmc)
    print("\n####", pmc)
    seen=set()
    for p in pats:
        for m in re.finditer(p, t, re.I):
            frag = t[max(0,m.start()-100):m.end()+120]
            if re.search(r"\d", frag) and frag[:60] not in seen:
                seen.add(frag[:60]); print("  ...", frag[:340])
