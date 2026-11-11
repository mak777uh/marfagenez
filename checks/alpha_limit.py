"""Сходится ли дискретный процесс к экспоненте exp(αx)?

Формула `α = 2μ/σ²` — из непрерывной отражённой диффузии.

Rust реализует дискретный переход:
    x_{t+1} = R_B(x_t + μ + σξ_t)

Вопрос: совпадает ли стационарное распределение дискретного процесса
с экспонентой exp(αx)?

Метод: уменьшать шаг dt, масштабируя μ и σ как sqrt(dt), и смотреть,
сходится ли к экспоненте.

Запуск: python checks/alpha_limit.py
"""

from __future__ import annotations

import numpy as np

B = 3.0
N = 8000


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def run(mu: float, sigma: float, steps: int, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pop = rng.uniform(-B, B, N)
    for _ in range(steps):
        pop = reflect(pop + mu + sigma * rng.normal(0.0, 1.0, N), B)
    return pop


def chi2_vs_exponential(pop: np.ndarray, alpha: float, bins: int = 15) -> float:
    """Chi-square of the measured histogram against exp(alpha*x) on [-B, B]."""
    edges = np.linspace(-B, B, bins + 1)
    counts, _ = np.histogram(pop, bins=edges)

    # Expected counts for density proportional to exp(alpha*x).
    mids = 0.5 * (edges[1:] + edges[:-1])
    widths = np.diff(edges)
    dens = np.exp(alpha * mids)
    expected = dens * widths
    expected = expected / expected.sum() * len(pop)

    # Avoid division by zero in the tails.
    mask = expected > 5
    if mask.sum() < 3:
        return float("inf")
    chi2 = float(np.sum((counts[mask] - expected[mask]) ** 2 / expected[mask]))
    return chi2


print("# Сходится ли дискретный процесс к exp(alpha*x)?")
print()
print(f"B = {B}, N = {N}")
print()

# The continuous limit: mu = 0.05, sigma = 0.3 gives alpha = 2*mu/sigma^2.
MU = 0.05
SIGMA = 0.3
ALPHA = 2 * MU / (SIGMA**2)
print(f"непрерывный предел: mu = {MU}, sigma = {SIGMA}, alpha = {ALPHA:.3f}")
print()

# Discretisation: dt steps of size dt. To keep the same continuous process,
# mu_dt = MU*dt and sigma_dt = SIGMA*sqrt(dt).
print("  dt      mu_dt    sigma_dt   steps    chi^2 (dof ~12)")
print(" " + "-" * 58)

results = []
for dt in [1.0, 0.5, 0.25, 0.1, 0.05, 0.01]:
    mu_dt = MU * dt
    sigma_dt = SIGMA * np.sqrt(dt)
    # Total time 2000 (in continuous units), so steps = 2000/dt.
    steps = int(600 / dt)
    if steps > 80000:
        print(f"  {dt:5.2f}   {mu_dt:7.4f}  {sigma_dt:8.4f}   {steps:7}   (пропущено, слишком много)")
        continue
    pop = run(mu_dt, sigma_dt, steps)
    chi2 = chi2_vs_exponential(pop, ALPHA)
    results.append((dt, chi2))
    print(f"  {dt:5.2f}   {mu_dt:7.4f}  {sigma_dt:8.4f}   {steps:7}   {chi2:10.1f}")

print()
print("# Вывод")
print()

if len(results) >= 2:
    first = results[0][1]
    last = results[-1][1]
    print(f"chi^2 при dt=1.0: {first:.1f}")
    print(f"chi^2 при dt=0.01: {last:.1f}")
    print()
    if last < first * 0.5:
        print("chi^2 ПАДАЕТ с уменьшением шага — дискретный процесс сходится")
        print("к экспоненте в непрерывном пределе.")
    else:
        print("chi^2 НЕ падает с уменьшением шага — формула alpha = 2mu/sigma^2")
        print("не описывает дискретный процесс даже в пределе.")
        print()
        print("Возможная причина: отражение в дискретном случае не то же самое,")
        print("что отражающая граница в непрерывном (Скороход).")
