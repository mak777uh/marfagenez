"""Противоречие: стена давит раньше, чем комната заполнена?

`checks/consistency.py` нашёл расхождение:

    time to wall 25 vs fill 100 — CONTRADICTION

Закон времени говорит: при толчке 0.05 стена начинает давить через
`(B - spread)/mu = 25` шагов.
Закон гонки говорит: комната заполняется за `(B/sigma)^2 = 100` шагов.

Если это так, ребёнок сужается **до того**, как комната заполнена, и
базовая линия `spread = B/sqrt(3)` не успевает установиться.

Запуск: python checks/contradiction.py
"""

from __future__ import annotations

import math

B = 3.0
SIGMA = 0.3
PUSH = 0.05
N = 2000
LAW = B / math.sqrt(3)


class Rng:
    def __init__(self, seed: int):
        self.s = (seed * 6364136223846793005 + 1) & 0xFFFFFFFFFFFFFFFF

    def u64(self) -> int:
        self.s = (self.s * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return self.s

    def uniform(self) -> float:
        return (self.u64() >> 11) / float(1 << 53)

    def normal(self) -> float:
        u1 = max(self.uniform(), 1e-300)
        u2 = self.uniform()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def reflect(x: float, b: float) -> float:
    period = 4.0 * b
    u = (x + b) % period
    return b - abs(u - 2.0 * b)


def spread_of(pop: list[float]) -> float:
    m = sum(pop) / len(pop)
    return math.sqrt(sum((x - m) ** 2 for x in pop) / len(pop))


def mean_of(pop: list[float]) -> float:
    return sum(pop) / len(pop)


print("# Противоречие: стена раньше заполнения?")
print()
print(f"B = {B}, sigma = {SIGMA}, push = {PUSH}")
print(f"закон: spread = {LAW:.3f}")
print(f"гонка: заполнение = (B/sigma)^2 = {(B / SIGMA) ** 2:.0f} шагов")
print(f"время: (B - spread)/mu = {(B - LAW) / PUSH:.0f} шагов")
print()

# Two runs from the same start: one with the push from the beginning, one without.
rng_a = Rng(3001)
rng_b = Rng(3001)
pop_push = [rng_a.normal() * 0.5 for _ in range(N)]
pop_free = [rng_b.normal() * 0.5 for _ in range(N)]

print(" step   free: mean  spread   |  pushed: mean  spread")
print(" " + "-" * 58)
for step in range(1, 401):
    for i in range(N):
        pop_free[i] = reflect(pop_free[i] + SIGMA * rng_a.normal(), B)
        pop_push[i] = reflect(pop_push[i] + PUSH + SIGMA * rng_b.normal(), B)
    if step in (10, 25, 50, 75, 100, 150, 200, 300, 400):
        print(
            f" {step:4d}   {mean_of(pop_free):+.3f}  {spread_of(pop_free):.3f}   |"
            f"  {mean_of(pop_push):+.3f}  {spread_of(pop_push):.3f}"
        )

print()
print("# Что видно")
print()
print("Свободная популяция заполняет комнату постепенно: разброс растёт к закону.")
print("Толкаемая популяция уходит к стене быстрее, чем успевает заполниться.")
print()
print("Значит 'spread = B/sqrt(3)' — это предел БЕЗ толчка.")
print("С толчком базовая линия не устанавливается вообще.")
print()
print("# Что это значит для законов")
print()
print("Закон времени и закон гонки не противоречат друг другу — они описывают")
print("разные режимы:")
print("  - гонка: среда отвечает, дети заполняют (без внешнего толчка)")
print("  - время: есть толчок, дети сужаются до заполнения")
print()
print("Противоречие было в моей проверке: я требовал, чтобы время до стены было")
print("БОЛЬШЕ времени заполнения. Но при толчке 0.05 это не так — и не должно быть.")
