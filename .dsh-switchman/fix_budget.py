import io

p = "laws/Medium/Budget.lean"
s = io.open(p, encoding="utf-8").read()

old1 = """  | allocation | per-trait spreads | total spread |
  |---|---|---|
  | equal `3,3,3,3` | 1.30 1.31 1.31 1.30 | **6.800** |
  | skewed `6,3,2,1` | 1.60 1.29 1.00 0.56 | 5.543 |
  | very skewed `9,1,1,1` | 1.61 0.55 0.56 0.55 | 3.519 |
  | one only `12,0,0,0` | 1.61 0.01 0.01 0.01 | 2.581 |
  [UNVERIFIED: numbers not found in checks/, results/ or docs/ -- illustration, not measurement]"""
new1 = """  | allocation | per-trait spreads | total spread |
  |---|---|---|
  | equal `3,3,3,3` | 1.31 1.29 1.29 1.30 | **1.296** |
  | skewed `6,3,2,1` | 1.58 1.29 1.00 0.56 | 1.169 |
  | very skewed `9,1,1,1` | 1.60 0.56 0.56 0.56 | 0.934 |
  | one only `12,0,0,0` | 1.60 0.00 0.00 0.00 | 0.800 |
  [VERIFIED: `python3 checks/budget_model.py`, `N = 20 000`, 25 000 steps, seed 5001;
  total spread is `sqrt(Σ_k var_k / d)`, the reading `OutsideReading::spread` takes]"""

old2 = """  | d | per-trait half-width | total spread |
  |---|---|---|
  | 2 | 6.00 | 4.828 |
  | 4 | 3.00 | **6.662** |
  | 8 | 1.50 | 5.109 |
  [UNVERIFIED: numbers not found in checks/, results/ or docs/ -- illustration, not measurement]"""
new2 = """  | d | per-trait half-width | total spread |
  |---|---|---|
  | 2 | 6.00 | 1.571 |
  | 4 | 3.00 | **1.296** |
  | 8 | 1.50 | 0.799 |
  [VERIFIED: `python3 checks/budget_model.py`]"""

old3 = """    | allocation | Σ B² | predicted | measured |
    |---|---|---|---|
    | 3,3,3,3 | 36.0 | 12.00 | 12.06 |
    | 6,3,2,1 | 50.0 | 16.67 | 16.64 |
    | 9,1,1,1 | 84.0 | 28.00 | 27.57 |
    [UNVERIFIED: numbers not found in checks/, results/ or docs/ -- illustration, not measurement]"""
new3 = """    | allocation | Σ B² | predicted | measured |
    |---|---|---|---|
    | 3,3,3,3 | 36.0 | 1.73 | 1.73 |
    | 6,3,2,1 | 50.0 | 2.04 | 2.04 |
    | 9,1,1,1 | 84.0 | 2.65 | 2.65 |
    [VERIFIED: `python3 checks/budget_model.py`]"""

old4 = """    | allocation | Σ B² | measured |
    |---|---|---|
    | 3,3,3,3 | 36.0 | **6.74** |
    | 6,3,2,1 | 50.0 | 5.43 |
    | 9,1,1,1 | 84.0 | **3.52** |
    [UNVERIFIED: numbers not found in checks/, results/ or docs/ -- illustration, not measurement]"""
new4 = """    | allocation | Σ B² | measured |
    |---|---|---|
    | 3,3,3,3 | 36.0 | **1.30** |
    | 6,3,2,1 | 50.0 | 1.17 |
    | 9,1,1,1 | 84.0 | **0.93** |
    [VERIFIED: `python3 checks/budget_model.py`]"""

for old, new in ((old1, new1), (old2, new2), (old3, new3), (old4, new4)):
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)

io.open(p, "w", encoding="utf-8").write(s)
print("budget.lean patched")
