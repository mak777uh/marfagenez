import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ft as H

RATE = ['cooling rate', 'heating rate', 'dose rate', 'dose-rate', 'fluence rate', 'irradiance',
        'scan rate', 'shear rate', 'freezing rate', 'warming rate', 'drying rate', 'rate of']
d = H.TXT
meta = {}
try:
    meta = json.load(open('/root/marfagenez/scratch/dip46/meta.json'))
except Exception:
    pass
for f in sorted(os.listdir(d)):
    if not f.endswith('.txt'):
        continue
    p = f[:-4]
    t = open(os.path.join(d, f), encoding='utf-8', errors='replace').read()
    sents = H.sentences(t)
    out = []
    for s in sents:
        low = s.lower()
        if any(k in low for k in RATE) and re.search(r'=\s*[-+]?\d', s) and re.search(r'(log|exp|ln|\^|slope|equation)', low):
            out.append(s)
    if out:
        m = meta.get(p, {})
        print('\n== %s %s %s' % (p, m.get('doi', ''), (m.get('title') or '')[:70]))
        for s in out[:4]:
            print('  -', s[:300])
