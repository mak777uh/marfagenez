import json, glob, os
p = sorted(glob.glob('/root/marfagenez/core/results/sighted/*.json'),
           key=os.path.getmtime)[-1]
d = json.load(open(p))
f = d['frames'][-1]
occ = [0] * 40
for s in f['samples']:
    if s['alive']:
        occ[s['cell']] += 1
print('alive', sum(occ))
print('occ  ', ' '.join(str(x) for x in occ))
print('field', ' '.join('%.2f' % x for x in f['field']))
