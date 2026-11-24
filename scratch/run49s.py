txt = open("/root/marfagenez/scratch/ft49_PMC2112240.txt").read()
i = txt.find("interiorized the equivalent of their entire cell surface")
print(repr(txt[i-200:i+260]))
