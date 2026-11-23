import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ft as H

RATE = ['cooling rate', 'heating rate', 'dose rate', 'dose-rate', 'drying rate',
        'fluence rate', 'irradiance', 'scan rate', 'scanning rate', 'freezing rate',
        'warming rate', 'shear rate', 'rate of cooling', 'rate of heating',
        'rate of drying', 'heating rates', 'cooling rates', 'freezing rates',
        'rate of freezing', 'rate of warming', 'dose rates']
UNIT = (r'(°C\s?(min|s|h)|°C/min|°C\s?min|Gy\s?(min|h)|Gy/min|mW\s?/?\s?cm|W\s?/?\s?cm|'
        r'mJ\s?/?\s?cm|s⁻|s−1|s-1|K\s?min|K/min|J\s?/?\s?cm)')
REL = r'(increas|decreas|reduc|higher|lower|greater|less|improve|surviv|inactiv|viab|mortal|damage|hemolysis|recovery)'

def good(s):
    low = s.lower()
    return (any(k in low for k in RATE) and re.search(UNIT, s) and re.search(REL, low)
            and re.search(r'\d', s))

if __name__ == '__main__':
    ids = sys.argv[1:] if len(sys.argv) > 1 else sorted(f[:-4] for f in os.listdir(H.TXT) if f.endswith('.txt'))
    meta = {}
    try:
        meta = json.load(open('/root/marfagenez/scratch/dip46/meta.json'))
    except Exception:
        pass
    nfiles = 0
    for p in ids:
        fn = os.path.join(H.TXT, p + '.txt')
        if not os.path.exists(fn):
            continue
        t = open(fn, encoding='utf-8').read()
        sents = [s for s in H.sentences(t) if good(s)]
        if not sents:
            continue
        nfiles += 1
        m = meta.get(p, {})
        print('\n===== %s | %s | %s | %s' % (p, m.get('year', ''), m.get('doi', ''), (m.get('title') or '')[:85]))
        for s in sents[:5]:
            print('  -', s[:340])
    print('\nFILES_WITH_HITS', nfiles)
