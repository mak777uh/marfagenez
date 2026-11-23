t = open('/root/marfagenez/scratch/dip46/txt/PMC13351016.txt', encoding='utf-8').read().replace('\n', ' ')
i = t.find('cell cryosurvival is negligible')
print(repr(t[i - 30:i + 700]))
