import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epmc import *

if __name__ == '__main__':
    pmcid = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'peek'
    t = text(fulltext(pmcid))
    if mode == 'peek':
        print('LEN', len(t))
        print(t[: int(sys.argv[3]) if len(sys.argv) > 3 else 1500])
    elif mode == 'grep':
        kws = sys.argv[3].split('|')
        _, hits = grep_rate(pmcid, tuple(kws), width=int(sys.argv[4]) if len(sys.argv) > 4 else 500)
        print('HITS', len(hits))
        for pos, h in hits[:40]:
            print('---', pos)
            print(h.replace('\n', ' '))
    elif mode == 'save':
        open(sys.argv[3], 'w', encoding='utf-8').write(t)
        print('saved', len(t))
