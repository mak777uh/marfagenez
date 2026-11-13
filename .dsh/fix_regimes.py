import pathlib

p = pathlib.Path('/root/marfagenez/laws/Medium/Regimes.lean')
s = p.read_text()

old = "At `M = 2, r = 0.8, t\u2080 = 0.8, maintenance = 0.6` the one-organism equilibrium is\n`c* = 1.8` and the two-organism level is `cStar(2) = 1.6`."
new = ("At `M = 2, r = 0.8, t\u2080 = 0.8, maintenance = 0.6` the one-organism equilibrium is\n"
       "`c* = M + t\u2080 - t\u2080/r = 1.2` and the two-organism level is\n"
       "`cStar(2) = M - 2*t\u2080*(1-r)/r = 1.6`.")
assert old in s, 'old equilibrium sentence not found'
s = s.replace(old, new)

old2 = "`c* = 1.8` and the two-organism level is `cStar(2) = 1.6`. With two organisms"
# already replaced above; nothing to do
p.write_text(s)
print('patched Regimes.lean docstring')
