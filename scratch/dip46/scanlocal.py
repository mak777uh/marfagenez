import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest2 import sentences, score, text

FT = '/root/marfagenez/scratch/dip46/ft'
TXT = '/root/marfagenez/scratch/dip46/txt'
os.makedirs(TXT, exist_ok=True)
pms = [f[:-4] for f in os.listdir(FT) if f.endswith('.xml')]
for p in sorted(pms):
    fn = os.path.join(TXT, p + '.txt')
    if os.path.exists(fn) and os.path.getsize(fn) > 2000:
        t = open(fn, encoding='utf-8').read()
    else:
        try:
            t = text(open(os.path.join(FT, p + '.xml'), encoding='utf-8', errors='replace').read())
        except Exception as e:
            print(p, 'ERR', e)
            continue
        open(fn, 'w', encoding='utf-8').write(t)
    ranked = sorted(((score(s), s) for s in sentences(t)), reverse=True)
    print('\n===== %s len=%d' % (p, len(t)))
    shown = 0
    for sc, s in ranked:
        if sc < 9 or shown >= 4:
            break
        print('  (%d) %s' % (sc, s[:280]))
        shown += 1
