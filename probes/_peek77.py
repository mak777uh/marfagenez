import json, glob, sys
p = sorted(glob.glob('/root/marfagenez/results/EXP-77/*.json'))[-1]
d = json.load(open(p))
for k, v in d['conditions'].items():
    m = v['metrics']
    print(k, 'alive', m['alive'], 'occ', m['occupied'], 'moving', m['moving'],
          'fmin', round(m['field_min'], 4), 'fmax', round(m['field_max'], 4),
          'overfull', m['overfull'], 'empty', m['empty_cells'])
print()
for k, v in d['controls'].items():
    print(k, v['passed'], '|', v['evidence'][:240])
print()
print(d['verdict']['kind'], '|', d['verdict']['reason'][:500])
