import re
t=open('/root/marfagenez/scratch/dip59/nar_gkp237.txt').read()
i=t.find('mathematical calculation of t')
print(repr(t[i-100:i+700]))