import re
t = open('/root/marfagenez/scratch/dip46/txt/7447635.txt', encoding='utf-8').read().replace('\n', ' ')
pats = ['Table 2', 'Table 3', 'irradiation power', 'coefficient of variation']
for p in pats:
    for m in re.finditer(p, t):
        s = t[max(0, m.start() - 200):m.start() + 500]
        if re.search(r'\d', s):
            print('\n---', p, '\n', s)
            break
