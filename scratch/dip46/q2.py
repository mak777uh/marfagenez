import re, os
BASE = '/root/marfagenez/scratch/dip46/txt'
N = [
 ('10571529', 'field-friendly cryopreservation method'),
 ('2150183', 'caused significantly'),
 ('8791532', 'did not have a major influence'),
 ('6399228', 'provided the cooling rate is'),
 ('5813933', 'Lowering the cooling rate to 0.5'),
 ('13351016', 'survival increased when the cooling rate'),
]
for p, needle in N:
    for cand in (p, 'PMC' + p):
        fn = os.path.join(BASE, cand + '.txt')
        if os.path.exists(fn):
            break
    t = open(fn, encoding='utf-8').read().replace('\n', ' ')
    i = t.find(needle)
    print('\n=====', p, i)
    if i < 0:
        continue
    a = max(t.rfind('. ', 0, i), t.rfind('## ', 0, i))
    b = t.find('. ', i)
    print(t[a:b + 1].strip())
