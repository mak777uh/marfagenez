import re, json, sys, os

BASE = '/root/marfagenez/scratch/dip46'
NEEDLES = [
 ('PMC13351016', 'survival increased when the cooling rate was increased'),
 ('PMC6399228', 'viability was reduced by 36%'),
 ('PMC5813933', 'Lowering the cooling rate to 0.5'),
 ('2150183', 'cures were found at the lower fluence rates'),
 ('PMC5710595', 'At lower dose rates (1.0 and 1.5 Gy/min)'),
 ('6545662', 'ranging between 24.6 and 1168'),
 ('PMC4980389', 'about seven log cycles were inactivated'),
 ('PMC7570385', 'these temperatures decreased to 66 and 75'),
 ('7447635', 'four selected levels of irradiance'),
 ('PMC12154012', 'model parameters z = 7.20'),
]

def gettext(p):
    for cand in (p, p.replace('PMC', ''), 'PMC' + p):
        fn = os.path.join(BASE, 'txt', cand + '.txt')
        if os.path.exists(fn):
            return open(fn, encoding='utf-8').read().replace('\n', ' ')
    return ''

for p, needle in NEEDLES:
    t = gettext(p)
    i = t.find(needle)
    print('\n===== %s | %s | found=%s' % (p, needle, i))
    if i < 0:
        continue
    # expand to sentence boundaries
    start = max(t.rfind('. ', 0, i), t.rfind('## ', 0, i))
    end = t.find('. ', i)
    seg = t[start:end + 1].strip(' .')
    print(seg[:700])
