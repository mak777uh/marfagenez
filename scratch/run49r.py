import re
txt = open("/root/marfagenez/scratch/ft49_PMC2112240.txt").read()
i = txt.find("0.9% of the cell surface pe")
print(repr(txt[i-320:i+160]))
j = txt.find("corresponding to 3.1% of the")
print()
print(repr(txt[j-320:j+160]))
