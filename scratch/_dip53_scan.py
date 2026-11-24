import importlib.util, json, sys, re
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

CAND = {
 "Da": ["PMC12978645", "PMC13584748", "PMC11936424", "PMC13583149", "PMC13319206", "PMC5515263", "PMC5515221", "PMC11854830"],
 "Pe": ["PMC13040666", "PMC12092104", "PMC13641946", "PMC13593633", "PMC13319206", "PMC12854670"],
 "De": ["PMC6412255", "PMC5466690", "PMC4361863", "PMC7893017"],
 "Th": ["PMC5515263", "PMC5515221", "PMC12779220", "PMC4841543"],
 "Bi": ["PMC13584748"],
 "Sh": ["PMC13522592", "PMC13576833", "PMC12854670"],
}
for cat, ids in CAND.items():
    print("#" * 20, cat)
    for pmc in ids:
        try:
            xml = e.fulltext(pmc)
        except Exception as ex:
            print(pmc, "FETCHFAIL", ex); continue
        hits = e.scan(xml, maxhits=4)
        print("=====", pmc, len(xml))
        for h in hits:
            print("  [", h["section"][:55], "] ", h["sentence"][:330])
