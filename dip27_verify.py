import json, urllib.request, urllib.parse, time, sys, re

SEL = [
 dict(key='0001', doi='10.1111/are.13621',
  quote='the increased energy investment in reproduction (from 1.76% to 15.61%) resulted in a decrease in energy allocated to soma growth (from 17.1% to 5.64%) and self-maintenance (from 47.82% to 34.67%)',
  locator='abstract'),
 dict(key='0002', doi='10.3354/ab00626',
  quote='Immature scallops exposed to thermal stress showed 1.3-and 1.5-fold increases in hsp70 mRNA and HSP70 protein levels, respectively',
  locator='abstract'),
 dict(key='0003', doi='10.1098/rsbl.2004.0171',
  quote='SOD and GPx activity decreased with increasing brood size by 28% and 24%, respectively',
  locator='abstract'),
 dict(key='0004', doi='10.1186/1471-2148-13-68',
  quote='The magnitude of this increase in metabolic rate was positively correlated with Hsp70 gene copy number and reflected an increase as great as 35% of the 22°C metabolic rate',
  locator='abstract'),
 dict(key='0005', doi='10.3389/fnmol.2017.00101',
  quote='Notably, lipl-4(oe) had ~40% less offspring than did their siblings (127 ± 16 and 211 ± 12 offspring, respectively',
  locator='full text: Results, section "Over-expression of lipl-4 disrupts reproduction", Fig. 4A'),
 dict(key='0006', doi='10.1111/j.1474-9726.2006.00261.x',
  quote='median lifespans ranged from 38 days (16% diet) to 46 days (11% diet) to 54 days (7% diet)',
  locator='abstract'),
 dict(key='0007', doi='10.1093/jmedent/47.5.769',
  quote='Merely 6 d of exposure to females with mating activity reduced male survival from a median of 17 d in virgins to 15 d in mated',
  locator='abstract'),
 dict(key='0008', doi='10.1098/rspb.2005.3057',
  quote='Mass loss increased and immune function (lymphocyte levels and specific antibody response to the non-pathogenic antigens diphtheria and tetanus toxoid) was reduced in females incubating large clutches.',
  locator='abstract'),
 dict(key='0009', doi='10.1371/journal.pone.0211605',
  quote='PPO1 and antimicrobial peptide defensin 3 were increased (log2FC = 5.93 and 6.75, respectively), whereas those of VgA and VgB were reduced (log2FC = -17.82 and -18.13, respectively)',
  locator='abstract'),
 dict(key='0010', doi='10.1101/2025.07.09.663850',
  quote='Each independent transition to sociality was associated with an approximately 2-fold reduction in the de novo mutation rate in the germline',
  locator='abstract'),
 dict(key='0011', doi='10.1111/j.1365-2435.2008.01507.x',
  quote='effect size was almost three times as large as where infection prevalence (presence vs. absence of infection among hosts) was measured',
  locator='abstract'),
 dict(key='0012', doi='10.1111/1365-2435.12130',
  quote='had field metabolic rates that were almost 1·5 times greater than females raising control or reduced litters',
  locator='abstract'),
]

def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':'dip-researcher/1.0 (mailto:research@example.org)'})
    for a in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            return {'__http':e.code}
        except Exception as e:
            print('ERR',url,e, file=sys.stderr); time.sleep(3)
    return None

def inv2txt(inv):
    if not inv: return ''
    pos={}
    for w,ps in inv.items():
        for p in ps: pos[p]=w
    return ' '.join(pos[i] for i in sorted(pos))

lipl=open('/root/marfagenez/_dip27_lipl.txt').read()
res=[]
for s in SEL:
    d=get('https://api.openalex.org/works/https://doi.org/'+s['doi']+'?select=doi,id,title,publication_year,abstract_inverted_index,primary_location,type')
    rec=dict(s)
    if not d or '__http' in d:
        rec['ok']=False; rec['why']='OpenAlex HTTP '+str(d); res.append(rec); print('FAIL',s['doi'],rec['why']); continue
    ab=inv2txt(d.get('abstract_inverted_index'))
    rec['title']=d.get('title'); rec['year']=d.get('publication_year'); rec['oa_id']=d.get('id')
    rec['venue']=((d.get('primary_location') or {}).get('source') or {}).get('display_name')
    rec['abstract']=ab
    q=s['quote']
    if s['doi']=='10.3389/fnmol.2017.00101':
        ok = q in lipl
    else:
        ok = q in ab
    rec['quote_in_source']=ok
    rec['ok']=bool(d.get('title')) and ok
    if not ok:
        # try normalisations
        print('QUOTE MISMATCH',s['doi']); print(' WANT:',q[:160])
        i=ab.find(q[:40]) if ab.find(q[:40])>=0 else -1
        if i>=0: print(' FOUND NEAR:',ab[i:i+200])
    res.append(rec)
    print(('OK ' if rec['ok'] else 'BAD'), s['doi'], '|', (d.get('title') or '')[:70],'|',d.get('publication_year'))
    time.sleep(0.25)
json.dump(res, open('/root/marfagenez/_dip27_verified.json','w'), ensure_ascii=False)
print('verified:',sum(1 for r in res if r.get('ok')),'/',len(res))
