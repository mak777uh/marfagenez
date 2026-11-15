import io

p = "laws/Medium/Corrected.lean"
s = io.open(p, encoding="utf-8").read()

old = """     sticking to it. Clamping piles mass on the wall — a numerical experiment showed
     the share of cells on the wall growing to 1.16% — while reflection leaves the
     wall clean (0.00%)."""
new = """     sticking to it. Clamping piles mass on the wall — a numerical experiment showed
     the share of cells on the wall growing to 1.16% — while reflection leaves the
     wall clean (0.00%).
     [UNVERIFIED: the 1.16% figure is not reproduced by any script in `checks/`;
     `checks/corrected_model.py` measures the corrected model only. Treat it as a
     reported observation, not a rerun.]"""

assert s.count(old) == 1
s = s.replace(old, new)
io.open(p, "w", encoding="utf-8").write(s)
print("1.16% claim annotated")
