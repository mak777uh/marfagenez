import json, urllib.request, urllib.parse, sys

KEY = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
UA = {'User-Agent': 'dip-research/1.0 (mailto:research@example.org)'}
DOIS = [
 '10.3389/fmicb.2016.01256',
 '10.3390/polym12092145',
 '10.1038/s41598-026-61563-x',
 '10.1038/s41598-019-39957-x',
 '10.1371/journal.pone.0192265',
 '10.3390/ani13193014',
 '10.1038/bjc.1998.231',
 '10.1093/jrr/rrx025',
 '10.1177/1559325819852508',
 '10.1371/journal.pone.0263005',
]
for d in DOIS:
    url = 'https://api.openalex.org/works/https://doi.org/' + d + '?api_key=' + KEY
    try:
        r = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(r, timeout=60) as resp:
            w = json.load(resp)
        print('OK ', d, w.get('publication_year'), (w.get('title') or '')[:80], '| pmcid:', (w.get('ids') or {}).get('pmcid'))
    except Exception as e:
        print('ERR', d, e)
