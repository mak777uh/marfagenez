"""EXP-05: один организм против популяции.

## Вопрос

Все выводы проекта о «разбросе» — это статистика **популяции**.
Но говорят ли они что-то о **одном** организме?

## Различие

  spread_population = разброс между организмами по координате
  spread_individual = разброс координат ОДНОГО организма

Это разные величины. Первая — про разнообразие группы.
Вторая — про «широту» одного организма.

## Эксперимент

1. Один организм с 8 координатами, 3000 шагов.
   Меряем разброс его координат.

2. Популяция из 8 организмов с 1 координатой, 3000 шагов.
   Меряем разброс между организмами.

Если числа совпадают — величины эквивалентны.
Если нет — их нельзя путать.

Запуск: python checks/one_vs_population.py
"""

from __future__ import annotations

import numpy as np

B = 3.0
SIGMA = 0.3
STEPS = 3000
SEED = 42


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


print("# EXP-05: один организм против популяции")
print()
print(f"B = {B}, sigma = {SIGMA}, steps = {STEPS}, seed = {SEED}")
print()

# --- Case 1: one organism with 8 coordinates ---
rng = np.random.default_rng(SEED)
one = rng.normal(0.0, 0.5, 8)
for _ in range(STEPS):
    one = reflect(one + SIGMA * rng.normal(0.0, 1.0, 8), B)

spread_individual = float(one.std())
print(f"1. Один организм, 8 координат:")
print(f"   координаты: {np.round(one, 3)}")
print(f"   разброс координат: {spread_individual:.4f}")
print()

# --- Case 2: population of 8 organisms with 1 coordinate ---
rng = np.random.default_rng(SEED)
pop = rng.normal(0.0, 0.5, 8)
for _ in range(STEPS):
    pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, 8), B)

spread_population = float(pop.std())
print(f"2. Популяция из 8 организмов, 1 координата:")
print(f"   координаты: {np.round(pop, 3)}")
print(f"   разброс между организмами: {spread_population:.4f}")
print()

# --- Case 3: the law ---
law = B / np.sqrt(3)
print(f"3. Закон для заполненной комнаты: {law:.4f}")
print()

print("# Сравнение")
print()
print(f"  разброс индивида:     {spread_individual:.4f}")
print(f"  разброс популяции:    {spread_population:.4f}")
print(f"  закон:                {law:.4f}")
print()

# --- Case 4: does the individual spread converge to the law? ---
# Repeat with many seeds to see the distribution.
ind_spreads = []
pop_spreads = []
for s in range(200):
    r = np.random.default_rng(s)
    o = r.normal(0.0, 0.5, 8)
    for _ in range(STEPS):
        o = reflect(o + SIGMA * r.normal(0.0, 1.0, 8), B)
    ind_spreads.append(float(o.std()))

    r = np.random.default_rng(s)
    p = r.normal(0.0, 0.5, 8)
    for _ in range(STEPS):
        p = reflect(p + SIGMA * r.normal(0.0, 1.0, 8), B)
    pop_spreads.append(float(p.std()))

print("# Распределение по 200 seed")
print()
print(f"  индивид:   mean {np.mean(ind_spreads):.4f}, sd {np.std(ind_spreads):.4f}")
print(f"  популяция: mean {np.mean(pop_spreads):.4f}, sd {np.std(pop_spreads):.4f}")
print(f"  закон:     {law:.4f}")
print()

print("# Вывод")
print()

ind_err = abs(np.mean(ind_spreads) - law) / law * 100
pop_err = abs(np.mean(pop_spreads) - law) / law * 100

print(f"  средний разброс индивида отличается от закона на {ind_err:.1f}%")
print(f"  средний разброс популяции — на {pop_err:.1f}%")
print()

if ind_err > 10:
    print("Разброс ОДНОГО организма НЕ равен закону.")
    print("  Закон B/sqrt(3) — про ПОПУЛЯЦИЮ, не про индивида.")
else:
    print("Разброс одного организма близок к закону.")

print()
print("Это значит: величины нельзя путать.")
print("  'разброс популяции' — разнообразие группы")
print("  'разброс индивида' — широта одного организма")
