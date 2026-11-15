import io

p = "laws/Medium/Budget.lean"
s = io.open(p, encoding="utf-8").read()

old = """    The table shows this: `12,0,0,0` gives total spread `2.581` against `6.800` for an
    equal division. -/"""
new = """    The table shows this: `12,0,0,0` gives total spread `0.800` against `1.296` for an
    equal division. -/"""

assert s.count(old) == 1
s = s.replace(old, new)
io.open(p, "w", encoding="utf-8").write(s)
print("concentration_wastes prose updated")
