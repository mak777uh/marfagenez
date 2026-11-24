import importlib.util, re, html
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

def plain(pmc):
    t = re.sub(r"<[^>]+>", " ", e.fulltext(pmc))
    return html.unescape(re.sub(r"\s+", " ", t))

t = plain("PMC12779220")
for key in ["2.31", "φ crit", "critical value"]:
    for m in re.finditer(re.escape(key), t):
        print(key, "=>", t[max(0,m.start()-250):m.start()+350], "\n")

checks = {
 "PMC5515263": ["In this example, a value of the Thiele modulus of ϕ o =2.82 provides an acceptable description of the data ( Figure 1b ).",
                "The actual ratio of the two fitted values of ϕ o was 4.78/2.82 or 1.70."],
 "PMC12779220": ["2% Manugel 2.31 0.61 6.67 0.21 2% Protanal 1.78 0.79 5.14 0.27 5% Manugel 2.69 0.52 7.79 0.18",
                 "At high cell fractions (10 million MIN6 cells/mL) where the Thiele modulus is large (φ»φ crit ), cells become hypoxic"],
}
for pmc, qs in checks.items():
    tt = plain(pmc)
    print("####", pmc)
    for q in qs:
        print("  ", "OK " if q in tt else "MISS", q[:120])
