"""Reproduce the tables in `laws/Medium/Budget.lean`.

The Lean file asks: a fixed total budget `T = 12` divided among `d` traits, each
trait `k` getting half-width `B_k` (so `sum B_k = T`), growth `mu = 0.05`, noise
`sigma = 0.4`. Which division keeps the most total spread?

Every trait is an independent reflected Brownian motion in `[-B_k, B_k]` with
drift `mu` and noise `sigma` (the model of `checks/tilt.py` and
`laws/Medium/Growth.lean`). The spread of one trait is its standard deviation.
The *total* spread is the mean squared deviation of a `d`-dimensional reading,
`sqrt(sum_k var_k / d)` — the same definition as `OutsideReading::spread` in
`core/src/child.rs`, which is what a `d`-trait child actually reports.

Run: python3 checks/budget_model.py
"""

from __future__ import annotations

import math
import sys

import numpy as np

T = 12.0
MU = 0.05
SIGMA = 0.4
N = 20000
STEPS = 25000
SEED = 5001


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def trait_spread(b: float, mu: float, rng: np.random.Generator) -> float:
    if b <= 0.0:
        return 0.0
    pop = rng.normal(0.0, 0.5, N)
    for _ in range(STEPS):
        pop = reflect(pop + mu + SIGMA * rng.normal(0.0, 1.0, N), b)
    return float(pop.std())


def total(spreads: list[float]) -> float:
    d = len(spreads)
    return math.sqrt(sum(s * s for s in spreads) / d)


def measure(alloc: tuple[float, ...], mu: float, seed: int = SEED) -> tuple[list[float], float]:
    rng = np.random.default_rng(seed)
    spreads = [trait_spread(b, mu, rng) for b in alloc]
    return spreads, total(spreads)


print("# Budget model: fixed total, growth and noise")
print()
print(f"T = {T}, mu = {MU}, sigma = {SIGMA}, N = {N}, steps = {STEPS}")
print("total spread = sqrt(sum_k var_k / d)")
print()

allocations = [
    ("equal 3,3,3,3", (3.0, 3.0, 3.0, 3.0)),
    ("skewed 6,3,2,1", (6.0, 3.0, 2.0, 1.0)),
    ("very skewed 9,1,1,1", (9.0, 1.0, 1.0, 1.0)),
    ("one only 12,0,0,0", (12.0, 0.0, 0.0, 0.0)),
]

print("## With growth mu = 0.05")
print()
print(" allocation            per-trait spreads        total spread")
print(" " + "-" * 64)
with_growth = {}
for name, alloc in allocations:
    spreads, tot = measure(alloc, MU)
    with_growth[name] = tot
    cells = " ".join(f"{s:5.2f}" for s in spreads)
    print(f" {name:20s}  {cells}   {tot:8.3f}")
print()

print("## The optimum number of traits (equal division, mu = 0.05)")
print()
print(" d   half-width   total spread")
print(" " + "-" * 30)
for d in (2, 4, 8):
    alloc = tuple(T / d for _ in range(d))
    _, tot = measure(alloc, MU)
    print(f" {d:2d}   {T / d:9.2f}   {tot:11.3f}")
print()

print("## No growth: total spread is sqrt(sum B^2/3)")
print()
print(" allocation            sum B^2   predicted   measured")
print(" " + "-" * 56)
no_growth = {}
for name, alloc in allocations[:3]:
    spreads, _ = measure(alloc, 0.0)
    sq = sum(b * b for b in alloc)
    pred = math.sqrt(sq / (3.0 * len(alloc)))
    meas = total(spreads)
    no_growth[name] = meas
    print(f" {name:20s}  {sq:7.1f}   {pred:9.2f}   {meas:8.2f}")
print()

print("## With growth mu = 0.05, same three allocations")
print()
print(" allocation            sum B^2   measured")
print(" " + "-" * 40)
for name, alloc in allocations[:3]:
    sq = sum(b * b for b in alloc)
    print(f" {name:20s}  {sq:7.1f}   {with_growth[name]:8.2f}")
print()

equal = with_growth["equal 3,3,3,3"]
skewed = with_growth["skewed 6,3,2,1"]
conc = with_growth["very skewed 9,1,1,1"]
no_growth_ok = all(
    abs(no_growth[n] - math.sqrt(sum(b * b for b in a) / (3.0 * len(a))))
    / math.sqrt(sum(b * b for b in a) / (3.0 * len(a)))
    < 0.05
    for n, a in allocations[:3]
)
order_ok = equal > skewed > conc
print(f"{'PASS' if no_growth_ok else 'FAIL'}  without growth the total spread is sqrt(sum B^2/3)")
print(f"{'PASS' if order_ok else 'FAIL'}  with growth the order reverses: equal > skewed > concentrated")
print()
if not (no_growth_ok and order_ok):
    print("The budget tables in `laws/Medium/Budget.lean` do not reproduce.")
    sys.exit(1)
print("# What this proves")
print("With growth, equal division gives the LARGEST total spread, not the smallest.")
print("Without growth it gives the smallest, as Cauchy-Schwarz says.")
print()
print("# What this does NOT prove")
print("- Nothing is proved: this is a simulation, not a Lean theorem.")
print("- The interior optimum at d = 4 is measured here only at d = 2, 4, 8.")
