import importlib.util, re, html
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

def plain(pmc):
    t = re.sub(r"<[^>]+>", " ", e.fulltext(pmc))
    return html.unescape(re.sub(r"\s+", " ", t))

Q = {
 "PMC13583149": ["IIa exhibits moderate reaction dominance ( Da ≈ 2.3 ), whereas Fbn formation is characterized by a much larger Damköhler number ( Da ≈ 355 )"],
 "PMC12978645": ["Da < 1 indicates a transport dominant system in which DOM composition is unchanged, and Da > 1 indicates a reaction-dominant system in which DOM undergoes chemical transformations"],
 "PMC12092104": ["the Péclet number is large: P e ∼ 1000 for the microspheres used in the experiments and P e ∼ 10 − 100 for other solutes of interest"],
 "PMC13319206": ["P e = 75–300, which is » 1, indicating a clear dominance of advection over diffusion in vortices"],
 "PMC13593633": ["Pe Adu ≈ ( 0.1 μ m / s ) ( 10 μ m ) 30 μ m 2 / s ≈ 3.3 × 10 - 2 ≪ 1",
                  "3.3 × 10 - 2 ≪ 1"],
 "PMC5466690": ["Deborah numbers of individually swimming sperm in 0.7 and 1% LC-PAM are estimated to be 0.51 and 2.0 respectively"],
 "PMC4361863": ["the Deborah number 0 ≤ De < 7 with Re ~ 10 −3"],
 "PMC6412255": ["the Deborah number was estimated to be De ≈ 0.2"],
 "PMC5515263": ["a value of the Thiele modulus of ϕ o =2.82 provides an acceptable description of the data",
                "substrate is completely depleted at some point ( ϕ o >1)"],
 "PMC12779220": ["2% Manugel 2.31 0.61 6.67 0.21"],
 "PMC12988972": ["both Biot numbers were calculated obtaining 0.238 for the unfrozen state and 0.047 for the frozen fluid",
                 "Biot numbers (Bi) < 1/6 ensure a uniform temperature profile inside the cryovial"],
 "PMC13522592": ["which varied from 5.10 to 7.10 for COD removal and 4.60 to 6.42 for nitrate removal"],
}
for pmc, quotes in Q.items():
    t = plain(pmc)
    print("####", pmc)
    for q in quotes:
        print("  ", "OK " if q in t else "MISS", q[:110])
