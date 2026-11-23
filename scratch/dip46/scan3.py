import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ft as H

pms = sys.argv[1:]
for p in pms:
    fn = os.path.join(H.TXT, p + '.txt')
    t = open(fn, encoding='utf-8').read()
    sents = H.sentences(t)
    print('\n===== %s len=%d nsent=%d' % (p, len(t), len(sents)))
    n = 0
    for s in sents:
        low = s.lower()
        if re.search(r'\brate\b', low) and re.search(r'\d', s):
            print('  -', s[:260])
            n += 1
            if n >= 10:
                break
