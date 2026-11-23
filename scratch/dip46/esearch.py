import json, sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epmc import search_epmc

if __name__ == '__main__':
    qs = json.load(open(sys.argv[1]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    for q in qs:
        print('\n### ' + q)
        try:
            res = search_epmc(q, n)
        except Exception as e:
            print('ERR', e)
            continue
        print('hits', len(res))
        for r in res:
            print(r.get('pubYear'), r.get('pmcid') or '-', (r.get('doi') or '')[:40],
                  '|', (r.get('title') or '')[:95])
        time.sleep(1)
