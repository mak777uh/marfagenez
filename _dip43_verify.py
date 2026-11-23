import json, sys
sys.path.insert(0, '/root/marfagenez')
from _dip43_oa import work, inv2text

CAND = [
 ("10.1101/gr.969603", "MPERs of 0.018-0.032 errors/site/21.6 generations, and the fidelity of methylation pattern was calculated as 99.85%-99.92%/site/generation"),
 ("10.1214/09-aoas297", "The estimated average failure of maintenance rate and daughter de novo rate decline from 0.04 to 0.024 and from 0.14 to 0.07, respectively, when errors are accounted for"),
 ("10.1186/s13100-019-0162-7", "Both penetrant (with kinky tails) and silent (without kinky tails) Axin cL1 mice, regardless of sex, could transmit the phenotype to subsequent generations with similar penetrance (~ 80%)"),
 ("10.1371/journal.pgen.1000530", "stable inheritance of multiple parental DNA methylation variants (epialleles) over at least eight generations"),
 ("10.1534/genetics.118.301456", "In most cases, TEI is limited to a small number of generations (two to three)"),
 ("10.1534/genetics.118.301456", "whose mutation causes RNAi inheritance to last longer (> 20 generations) than normal"),
 ("10.1016/j.cell.2012.06.018", "piRNAs can trigger highly stable long-term silencing lasting at least 20 generations"),
 ("10.1371/journal.pgen.1003773", "The repeat transgene-induced silencing was less efficiently transmitted than silencing induced by the repeats of endogenous b1 alleles, which is always 100% efficient"),
 ("10.1126/science.1212959", "propagated by single-seed descent for 30 generations. We identified 114,287 CG single methylation polymorphisms and 2485 CG differentially methylated regions (DMRs), both of which show patterns of divergence compared with the ancestral state"),
 ("10.1186/1471-2229-2-11", "imprints imposed by the C73 locus were maintained heritably for at least five generations in the absence of the silencer with only sporadic spontaneous reversion"),
 ("10.1093/pcp/pch172", "Strong silencing of the Ltp2-gus gene was detected over five generations in the L0.1 line"),
 ("10.1186/s13148-021-01132-3", "Once established, the methylation status of the nc886 epiallele remains stable for at least 25 years"),
 ("10.1371/journal.pbio.1001075", "we use a recently developed method for swapping epitope tags to measure the disposition of ancestral histone H3 across the yeast genome over six generations"),
]

dois = sorted(set(d for d, _ in CAND))
meta = {}
for d in dois:
    w = work(d)
    meta[d] = {
        'doi': (w.get('doi') or '').replace('https://doi.org/', ''),
        'title': w.get('title'),
        'year': w.get('publication_year'),
        'type': w.get('type'),
        'abs': inv2text(w.get('abstract_inverted_index')),
    }
    print('OK', d, '|', meta[d]['year'], '|', (meta[d]['title'] or '')[:80], '| abs_len', len(meta[d]['abs']))

json.dump(meta, open('/root/marfagenez/_dip43_meta.json', 'w'), ensure_ascii=False, indent=1)

print('\n--- quote check ---')
for d, q in CAND:
    a = meta[d]['abs']
    ok = q in a
    print(('PASS' if ok else 'FAIL'), d, '| words', len(q.split()), '|', q[:70])
    if not ok:
        # show close region
        key = q.split()[0:3]
        i = a.find(' '.join(key))
        print('   ctx:', a[max(0, i-80):i+260] if i >= 0 else a[:300])
