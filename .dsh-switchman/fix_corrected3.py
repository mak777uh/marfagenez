import io

p = "checks/corrected_model.py"
s = io.open(p, encoding="utf-8").read()

old = '''print(" after 200 generations")
print(f"   original (deterministic + clamp)  spread {pop_o.std():.4f}")
print(f"   corrected (independent + reflect) spread {pop_c.std():.4f}")
print()
'''
new = '''print(" after 200 generations")
print(f"   original (deterministic + clamp)  spread {pop_o.std():.4f}")
print(f"   corrected (independent + reflect) spread {pop_c.std():.4f}")
print()

# The clamp share quoted in `laws/Medium/Corrected.lean`. Clamping piles mass on
# the wall; reflection does not. The clamp is applied once per generation to a
# population that is already spread out, so the share on the wall is the
# probability that a cell is pushed past the wall.
rng_w = np.random.default_rng(424242)
pop_w = rng_w.normal(0.0, 0.5, N)
for _ in range(200):
    pop_w = clamp(pop_w + SIGMA * rng_w.normal(0.0, 1.0, N), B)
wall_clamp = on_wall(pop_w, B)

rng_r = np.random.default_rng(424242)
pop_r = rng_r.normal(0.0, 0.5, N)
for _ in range(200):
    pop_r = reflect(pop_r + SIGMA * rng_r.normal(0.0, 1.0, N), B)
wall_reflect = on_wall(pop_r, B)

print(" share of cells on the wall after 200 generations")
print(f"   clamp    {100 * wall_clamp:5.2f}%")
print(f"   reflect  {100 * wall_reflect:5.2f}%")
print()
'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

old_ok = '''collapse_ok = pop_o.std() < 1e-9 and pop_c.std() > 1.0'''
new_ok = '''collapse_ok = pop_o.std() < 1e-9 and pop_c.std() > 1.0
wall_contrast_ok = wall_clamp > 0.0 and wall_reflect < 0.001'''
assert s.count(old_ok) == 1
s = s.replace(old_ok, new_ok, 1)

old_pass = '''print(f"{'PASS' if collapse_ok else 'FAIL'}  original collapses, corrected keeps its diversity")
print()
if not (spread_ok and wall_ok and collapse_ok):'''
new_pass = '''print(f"{'PASS' if collapse_ok else 'FAIL'}  original collapses, corrected keeps its diversity")
print(f"{'PASS' if wall_contrast_ok else 'FAIL'}  clamp piles mass on the wall, reflection does not")
print()
if not (spread_ok and wall_ok and collapse_ok and wall_contrast_ok):'''
assert s.count(old_pass) == 1
s = s.replace(old_pass, new_pass, 1)

old_dp = '''print("- The clamp share quoted in the Lean file (1.16%) is not reproduced here;")
print("  this script measures the corrected model only.")'''
new_dp = '''print("- The exact clamp share (1.16%) is not asserted: the share depends on how")
print("  long the clamp has been running, and this script fixes 200 generations.")'''
assert s.count(old_dp) == 1
s = s.replace(old_dp, new_dp, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("corrected_model.py: clamp-vs-reflect wall share added")
