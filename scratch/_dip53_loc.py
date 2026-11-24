import importlib.util, re, html
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

Q = {
 "PMC13583149": "IIa exhibits moderate reaction dominance",
 "PMC12978645": "Da < 1 indicates a transport dominant system",
 "PMC12092104": "the Péclet number is large: P e ∼ 1000",
 "PMC13319206": "P e = 75–300",
 "PMC13593633": "Pe Adu",
 "PMC5466690": "Deborah numbers of individually swimming sperm",
 "PMC4361863": "the Deborah number 0 ≤ De < 7",
 "PMC6412255": "the Deborah number was estimated to be De ≈ 0.2",
 "PMC5515263": "a value of the Thiele modulus of ϕ o =2.82",
 "PMC12779220": "2% Manugel 2.31 0.61 6.67 0.21",
 "PMC12988972": "both Biot numbers were calculated",
 "PMC13522592": "which varied from 5.10 to 7.10",
}
for pmc, q in Q.items():
    for title, body in e.sections(e.fulltext(pmc)):
        if q in body:
            print(pmc, "|", title[:150])
            break
    else:
        print(pmc, "| NOT FOUND")
