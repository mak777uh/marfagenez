"""Reproduce the two tables in `laws/Medium/Corrected.lean` (clamp vs reflect).

The Lean file quotes, for `B = 5`, `sigma = 0.3`:

  | steps | mean    | spread | on wall |
  | 1     | -0.013  | 1.039  | 0.00%   |
  | 100   | +0.013  | 2.623  | 0.00%   |
  | 1000  | -0.018  | 2.874  | 0.00%   |
  | 4000  | +0.015  | 2.892  | 0.00%   |

and, after 200 generations, original (deterministic + clamp) spread 0.0000
against corrected (independent + reflect) spread 2.8344.

Run: python3 checks/corrected_model.py
"""

from __future__ import annotations

import sys

import numpy as np

B = 5.0
SIGMA = 0.3
N = 20000
LAW = B / np.sqrt(3.0)


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def clamp(x: np.ndarray, b: float) -> np.ndarray:
    return np.clip(x, -b, b)


def on_wall(x: np.ndarray, b: float) -> float:
    return float(np.mean(np.abs(x) >= b - 1e-12))


print("# Corrected model: independent mutation + reflection")
print()
print(f"B = {B}, sigma = {SIGMA}, N = {N}, law B/sqrt(3) = {LAW:.4f}")
print()
print(" steps    mean      spread   on wall")
print(" " + "-" * 34)

rng = np.random.default_rng(424242)
pop = rng.normal(0.0, 0.5, N)
rows = []
for step in range(1, 4001):
    pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, N), B)
    if step in (1, 100, 1000, 4000):
        m, s, w = float(pop.mean()), float(pop.std()), on_wall(pop, B)
        rows.append((step, m, s, w))
        print(f" {step:5d}  {m:+8.4f}  {s:7.4f}  {100 * w:5.2f}%")

print()

# The original model: one deterministic mutation for the whole population,
# followed by a clamping ceiling. Every cell moves together, so the spread can
# only shrink.
rng_o = np.random.default_rng(424242)
pop_o = rng_o.normal(0.0, 0.5, N)
for _ in range(200):
    pop_o = clamp(pop_o + SIGMA, B)

# The corrected model, same seed, 200 generations.
rng_c = np.random.default_rng(424242)
pop_c = rng_c.normal(0.0, 0.5, N)
for _ in range(200):
    pop_c = reflect(pop_c + SIGMA * rng_c.normal(0.0, 1.0, N), B)

print(" after 200 generations")
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

spread_ok = abs(rows[-1][2] - LAW) / LAW < 0.05
wall_ok = all(r[3] < 0.001 for r in rows)
collapse_ok = pop_o.std() < 1e-9 and pop_c.std() > 1.0
wall_contrast_ok = wall_clamp > 0.0 and wall_reflect < 0.001
print(f"{'PASS' if spread_ok else 'FAIL'}  spread settles at B/sqrt(3)")
print(f"{'PASS' if wall_ok else 'FAIL'}  reflection leaves the wall empty")
print(f"{'PASS' if collapse_ok else 'FAIL'}  original collapses, corrected keeps its diversity")
print(f"{'PASS' if wall_contrast_ok else 'FAIL'}  clamp piles mass on the wall, reflection does not")
print()
if not (spread_ok and wall_ok and collapse_ok and wall_contrast_ok):
    print("The corrected-model table in `laws/Medium/Corrected.lean` does not reproduce.")
    sys.exit(1)
print("# What this proves")
print("Reflection keeps the uniform spread and leaves the wall empty;")
print("a deterministic mutation under a clamp collapses the population to a point.")
print()
print("# What this does NOT prove")
print("- Nothing is proved: this is a simulation, not a Lean theorem.")
print("- The exact clamp share (1.16%) is not asserted: the share depends on how")
print("  long the clamp has been running, and this script fixes 200 generations.")
