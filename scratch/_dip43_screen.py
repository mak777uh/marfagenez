import json, re, sys
sys.path.insert(0, '/root/marfagenez')
from _dip43_oa import search, work, inv2text

QUERIES = [
 'epigenetic memory maintained for a limited number of cell divisions H3K9me3 percent',
 'loss of DNA methylation across generations percent sites Arabidopsis ddm1',
 'transgene silencing heritability progeny percentage reversion generations',
 'loss of imprinting percentage alleles human tissue',
 'epigenetic inheritance of vernalization FLC repression generations',
 'paramutation mouse Kit percent progeny transmit',
 'metastable epiallele methylation stable across years human proportion',
 'histone modification inheritance cell divisions number measured dilution',
 'C. elegans RNAi inheritance percentage F2 F3 generations duration',
 'DNA methylation fidelity maintenance 99% per replication',
]

seen = set()
pool = []
for q in QUERIES:
    try:
        res = search(q, 12)
    except Exception as e:
        print('ERR', q, e)
        continue
    for r in res:
        if not r['doi'] or not r['has_abs'] or r['doi'] in seen:
            continue
        seen.add(r['doi'])
        pool.append(r)

print('pool with abstracts:', len(pool))
num = re.compile(r'\d')
kw = re.compile(r'(generation|division|%|percent|proportion|fraction|progeny|offspring|maintain|inherit|stable|loss|retain)', re.I)
out = []
for r in pool:
    sents = re.split(r'(?<=[.!?])\s+', r['abs'])
    hits = [s for s in sents if num.search(s) and kw.search(s)]
    if not hits:
        continue
    out.append(r['doi'])
    print('=' * 90)
    print(r['doi'], r['year'], '|', (r['title'] or '')[:90], '|', r['venue'])
    for s in hits[:4]:
        print('   *', s.strip()[:300])

json.dump(out, open('/root/marfagenez/_dip43_numdois.json', 'w'), indent=1)
print('\nDOIs with numeric sentences:', len(out))
