import re
B = '/root/marfagenez/scratch/dip46/txt/'
def show(p, needle, w=90):
    t = open(B + p + '.txt', encoding='utf-8').read().replace('\n', ' ')
    i = t.find(needle)
    print(p, i)
    print(repr(t[i - 10:i + w]))

show('4980389', 'for the treatments with a maximum heating')
show('7570385', 'shear rate of 0.06')
show('7570385', 'these temperatures decreased to 66')
show('13351016', 'cell cryosurvival is negligible')
show('13351016', 'survival increased when the cooling rate')
