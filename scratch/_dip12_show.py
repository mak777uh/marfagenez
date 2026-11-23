import json, textwrap
P = json.load(open('/root/marfagenez/literature/dips/reports/_dip12_pool.json'))['pool']
SEL = """10.1002/smll.201902898
10.1085/jgp.200308797
10.1016/s0006-3495(98)77904-4
10.1016/j.bpj.2013.11.4486
10.1093/plphys/kiac123
10.1016/j.preteyeres.2021.101037
10.1042/bj1010618
10.1104/pp.51.1.61
10.1083/jcb.37.3.729
10.1002/adma.202504519
10.1021/ja900919c
10.1073/pnas.2318412121
10.1073/pnas.1418491112
10.3389/fphys.2017.00312
10.1073/pnas.0705010104
10.1038/s41467-021-22092-5
10.1016/j.bbabio.2025.149564
10.1073/pnas.1203212109
10.1021/ja202406v
10.1007/s11693-009-9048-1
10.1083/jcb.33.2.319
10.1083/jcb.68.3.567""".split()
for doi in SEL:
    r = P.get(doi)
    if not r:
        print("### MISSING", doi); continue
    print(f"\n### {doi} | {r['year']} | {r['title']}")
    print(textwrap.fill(r['abstract'], 150))
