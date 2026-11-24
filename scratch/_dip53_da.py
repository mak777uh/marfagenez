import importlib.util, re, html
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

def plain(pmc):
    xml = e.fulltext(pmc)
    t = re.sub(r"<[^>]+>", " ", xml)
    t = html.unescape(re.sub(r"\s+", " ", t))
    return t

for pmc in ["PMC12978645", "PMC13584748"]:
    t = plain(pmc)
    print("\n#######", pmc)
    for m in re.finditer(r"\bDa\b", t):
        frag = t[max(0, m.start()-160):m.end()+200]
        if re.search(r"\d", frag):
            print("  ...", frag[:360])
