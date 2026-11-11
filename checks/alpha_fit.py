"""Правильное масштабирование: mu_dt = mu*dt, sigma_dt = sigma*sqrt(dt).

Первый тест дал chi^2 20-30 при 12 dof — не катастрофа, но и не идеал.

Проверяю: может, масштабирование неверное, или формула alpha = 2mu/sigma^2
верна только для непрерывного предела, а дискретный даёт другой alpha.

Метод: для каждого dt подбираю alpha, который лучше всего описывает
распределение, и смотрю, сходится ли он к 2mu/sigma^2.

Запуск: python checks/alpha_fit.py
"""

from __future__ import annotations

import numpy as np

B = 3.0
N = 20000


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


def fit_alpha(pop: np.ndarray, bins: int = 12) -> float:
    """Find the alpha that best fits the histogram, by grid search."""
    edges = np.linspace(-B, B, bins + 1)
    counts, _ = np.histogram(pop, bins=edges)
    mids = 0.5 * (edges[1:] + edges[:-1])
    widths = np.diff(edges)

    best_alpha = 0.0
    best_chi2 = float("inf")
    for alpha in np.linspace(-4, 4, 801):
        dens = np.exp(alpha * mids)
        expected = dens * widths
        expected = expected / expected.sum() * len(pop)
        mask = expected > 5
        if mask.sum() < 4:
            continue
        chi2 = float(np.sum((counts[mask] - expected[mask]) ** 2 / expected[mask]))
        if chi2 < best_chi2:
            best_chi2 = chi2
            best_alpha = alpha
    return best_alpha, best_chi2


print("# Сходится ли подобранный alpha к 2mu/sigma^2?")
print()
print(f"B = {B}, N = {N}")
print()

MU = 0.05
SIGMA = 0.3
ALPHA_THEORY = 2 * MU / (SIGMA**2)
print(f"теория: alpha = 2*mu/sigma^2 = {ALPHA_THEORY:.4f}")
print()
print("  dt      mu_dt    sigma_dt   alpha_подобр   chi^2   ошибка alpha")
print(" " + "-" * 68)

rows = []
for dt in [1.0, 0.5, 0.25, 0.1, 0.05]:
    mu_dt = MU * dt
    sigma_dt = SIGMA * np.sqrt(dt)
    steps = int(400 / dt)
    pop = run(mu_dt, sigma_dt, steps)
    alpha_fit, chi2 = fit_alpha(pop)
    err = abs(alpha_fit - ALPHA_THEORY) / ALPHA_THEORY * 100
    rows.append((dt, alpha_fit, err))
    print(f"  {dt:5.2f}   {mu_dt:7.4f}  {sigma_dt:8.4f}   {alpha_fit:9.3f}   {chi2:6.1f}   {err:6.1f}%")

print()
print("# Вывод")
print()

if len(rows) >= 2:
    first_err = rows[0][2]
    last_err = rows[-1][2]
    print(f"ошибка alpha при dt=1.0:  {first_err:.1f}%")
    print(f"ошибка alpha при dt=0.05: {last_err:.1f}%")
    print()
    if last_err < first_err * 0.5:
        print("alpha СХОДИТСЯ к 2mu/sigma^2 при уменьшении шага.")
        print("Формула верна в непрерывном пределе.")
    elif last_err < 20:
        print(f"alpha близок к теории ({last_err:.1f}% ошибки), но не сходится точно.")
        print("Формула — хорошее приближение, не точный закон.")
    else:
        print("alpha НЕ сходится к 2mu/sigma^2.")
        print("Формула не описывает дискретный процесс.")
