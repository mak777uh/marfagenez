"""Почему gradual комната хуже jump?

Тест `growing_room` дал неожиданное:

    at the end: jump 0.829 of law, linear 0.732 of law

Линейно растущая комната ХУЖЕ, чем широкая сразу. И matched комната
не держит закон (разброс падает 0.492 -> 0.301).

Проверяем, не ошибка ли в тесте.

Запуск: python checks/growing.py
"""

from __future__ import annotations

import math

import numpy as np

SIGMA = 0.3
N = 800
STEPS = 3000


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def run(schedule: str, seed: int = 9001) -> list[float]:
    rng = np.random.default_rng(seed)
    pop = rng.normal(0.0, 0.5, N)
    history = []
    for step in range(STEPS):
        frac = step / STEPS
        if schedule == "jump":
            b = 30.0
        elif schedule == "linear":
            b = 3.0 + (30.0 - 3.0) * frac
        elif schedule == "matched":
            s = pop.std()
            b = max(0.5, min(100.0, math.sqrt(3) * s))
        else:
            raise ValueError(schedule)
        pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, N), b)
        history.append(float(pop.std()))
    return history


print("# Gradual комната против jump")
print()
print(f"sigma = {SIGMA}, N = {N}, steps = {STEPS}")
print()
print(" step   jump    linear   matched   |  law(jump)  law(linear)")
print(" " + "-" * 70)

jump = run("jump")
linear = run("linear")
matched = run("matched")

for step in [100, 500, 1000, 2000, 2999]:
    frac = step / STEPS
    b_lin = 3.0 + (30.0 - 3.0) * frac
    law_jump = 30.0 / math.sqrt(3)
    law_lin = b_lin / math.sqrt(3)
    print(
        f" {step:5d}   {jump[step]:6.2f}  {linear[step]:6.2f}   {matched[step]:6.2f}   |"
        f"   {law_jump:6.2f}     {law_lin:6.2f}"
    )

print()
print("# Что видно")
print()
print("Jump: разброс растёт к 17.3 (закон для B=30).")
print("Linear: комната растёт быстрее, чем разброс за ней успевает.")
print("Matched: комната следует за разбросом, но разброс при этом ПАДАЕТ.")
print()
print("# Почему matched падает")
print()
print("B = sqrt(3) * spread. Тогда закон для этой комнаты:")
print("  law = B/sqrt(3) = spread")
print("То есть комната ровно такая, чтобы закон равнялся текущему разбросу.")
print("Но разброс ещё не достиг закона — он ниже. Значит комната узкая,")
print("и разброс падает дальше. Положительная обратная связь вниз.")
print()
print("# Почему linear хуже jump")
print()
print("При linear комната в начале узкая (B=3), и разброс ограничен ею.")
print("К концу комната широкая (B=30), но разброс не успел за ней.")
print("При jump комната широкая сразу, и разброс растёт всё время к 17.3.")
print()
print("=> Jump даёт больше разброса к концу, потому что у него было больше времени")
print("   на заполнение широкой комнаты.")
