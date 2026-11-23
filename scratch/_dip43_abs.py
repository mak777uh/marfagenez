import json, sys
sys.path.insert(0, '/root/marfagenez')
from _dip43_oa import work, inv2text

dois = sys.argv[1:]
out = {}
for d in dois:
    try:
        w = work(d)
        out[d] = {
            'doi': (w.get('doi') or '').replace('https://doi.org/', ''),
            'title': w.get('title'),
            'year': w.get('publication_year'),
            'type': w.get('type'),
            'venue': ((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
            'abs': inv2text(w.get('abstract_inverted_index')),
        }
    except Exception as e:
        out[d] = {'doi': d, 'error': str(e)}
json.dump(out, open('/root/marfagenez/_dip43_abs.json', 'w'), ensure_ascii=False, indent=1)
for d, v in out.items():
    print('=' * 100)
    print(d, '|', v.get('year'), '|', v.get('type'), '|', v.get('title'))
    print('venue:', v.get('venue'))
    print(v.get('abs') or v.get('error') or '(NO ABSTRACT)')
