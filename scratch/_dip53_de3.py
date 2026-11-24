import importlib.util, re
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

for q in ['TITLE_ABS:"Deborah number" AND TITLE_ABS:blood',
          'TITLE_ABS:"Deborah number" AND (TITLE_ABS:mucus OR TITLE_ABS:sputum OR TITLE_ABS:saliva)',
          'TITLE_ABS:"Deborah number" AND TITLE_ABS:blood AND OPEN_ACCESS:y']:
    res = e.epmc_search(q, 50)
    print("=====", q, len(res))
    for r in res[:25]:
        print(f"{r.get('pubYear')} {str(r.get('pmcid')):12s} {str(r.get('doi'))[:34]:34s} {(r.get('title') or '')[:90]}")
