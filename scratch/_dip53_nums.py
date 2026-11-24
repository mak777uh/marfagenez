import importlib.util, re, html
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

def plain(pmc):
    xml = e.fulltext(pmc)
    t = re.sub(r"<[^>]+>", " ", xml)
    return html.unescape(re.sub(r"\s+", " ", t))

cases = {
 "PMC12978645": [r"Da\s*[m]?\s*[=≈]\s*[\d.]+", r"Da[_\s]?\{?m\}?\s*[=≈]\s*[\d.]+", r"ranged from[^.]{0,80}"],
 "PMC5515221": [r"Thiele modulus[^.]{0,120}", r"P[eé]clet number[^.]{0,120}", r"Da\s*=\s*[\d.]+"],
 "PMC5544429": [r"P[eé]clet number[^.]{0,160}", r"Pe\s*[=≈]\s*[\d.]+"],
 "PMC12344991": [r"P[eé]clet number[^.]{0,160}", r"Pe\s*[=≈]\s*[\d.]+"],
 "PMC10361723": [r"P[eé]clet[^.]{0,160}"],
}
for pmc, pats in cases.items():
    t = plain(pmc)
    print("\n#######", pmc)
    seen = set()
    for pat in pats:
        for m in re.finditer(pat, t, re.I):
            s = max(0, m.start() - 120); frag = t[s:m.end() + 160]
            k = frag[:80]
            if k in seen: continue
            seen.add(k)
            print("  ...", frag[:320])
