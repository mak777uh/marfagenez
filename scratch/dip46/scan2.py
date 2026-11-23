import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ft as H

ids = sys.argv[1:] if len(sys.argv) > 1 else None
d = H.TXT
pms = ids or [f[:-4] for f in os.listdir(d) if f.endswith('.txt')]
for p in pms:
    fn = os.path.join(d, p + '.txt')
    if not os.path.exists(fn):
        continue
    t = open(fn, encoding='utf-8').read()
    ranked = sorted(((H.score(s), s) for s in H.sentences(t)), reverse=True)
    hits = [(sc, s) for sc, s in ranked if sc >= 9][:6]
    print('\n===== %s len=%d hits=%d' % (p, len(t), len([1 for sc, _ in ranked if sc >= 9])))
    for sc, s in hits:
        print('  (%d) %s' % (sc, s[:300]))
