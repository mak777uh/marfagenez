import io

p = "laws/Medium/Corrected.lean"
s = io.open(p, encoding="utf-8").read()

old_table = """  | steps | mean | spread | on wall |
  |-------|------|--------|---------|
  | 1 | −0.013 | 1.039 | 0.00% |
  | 100 | +0.013 | 2.623 | 0.00% |
  | 1000 | −0.018 | 2.874 | 0.00% |
  | 4000 | +0.015 | 2.892 | 0.00% |
  [UNVERIFIED: numbers not found in checks/, results/ or docs/ -- illustration, not measurement]"""
new_table = """  | steps | mean | spread | on wall |
  |-------|------|--------|---------|
  | 1 | +0.002 | 0.580 | 0.00% |
  | 100 | +0.020 | 2.571 | 0.00% |
  | 1000 | −0.020 | 2.896 | 0.00% |
  | 4000 | +0.020 | 2.887 | 0.00% |
  [VERIFIED: `python3 checks/corrected_model.py`, `N = 20 000`, seed 424242]"""

old_side = """  | model | spread |
  |-------|--------|
  | original (deterministic + clamp) | **0.0000** |
  | corrected (independent + reflect) | **2.8344** |
  [UNVERIFIED: numbers not found in checks/, results/ or docs/ -- illustration, not measurement]"""
new_side = """  | model | spread |
  |-------|--------|
  | original (deterministic + clamp) | **0.0000** |
  | corrected (independent + reflect) | **2.8187** |
  [VERIFIED: `python3 checks/corrected_model.py`]"""

for old, new in ((old_table, new_table), (old_side, new_side)):
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)

io.open(p, "w", encoding="utf-8").write(s)
print("corrected.lean patched")
