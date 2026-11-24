import importlib.util, re
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

for q in ['TITLE_ABS:"Damkohler number" AND (TITLE_ABS:tumor OR TITLE_ABS:spheroid OR TITLE_ABS:immunoassay OR TITLE_ABS:antibody) AND OPEN_ACCESS:y',
          'TITLE_ABS:"Damköhler number" AND (TITLE_ABS:tumor OR TITLE_ABS:spheroid OR TITLE_ABS:tissue) AND OPEN_ACCESS:y',
          'TITLE_ABS:"Deborah number" AND (TITLE_ABS:mucus OR TITLE_ABS:blood OR TITLE_ABS:plasma)']:
    res = e.epmc_search(q, 50)
    print("=====", q, len(res))
    for r in res[:20]:
        print(f"{r.get('pubYear')} {str(r.get('pmcid')):12s} {str(r.get('doi'))[:34]:34s} {(r.get('title') or '')[:90]}")
