"""Наблюдение vs воздействие: три условия на одинаковых начальных состояниях.

## Исправление после первой версии

Первый прогон дал C = A. Причина: воздействие `width = clip(2.5*spread, 0.5, 3.0)`
при `spread = 1.75` всегда давало `3.0` — потолок. Воздействия не было.

**Эксперимент, в котором условие не срабатывает, — не отрицательный результат.**

Здесь коэффициент и потолок выбраны так, чтобы ширина реально менялась.

## Вопрос

Принцип проекта: «среда не измеряет». Но это смешивает три вещи:

  A. наблюдение
  B. оценивание
  C. обратное воздействие

## Эксперимент

Три условия, одинаковые seed и начальные состояния:

  A. контроль: никто не смотрит
  B. наблюдатель: читает и пишет в лог, но НЕ влияет
  C. управляющая связь: читает и меняет ширину комнаты

Запуск: python checks/observe_vs_act.py
"""

from __future__ import annotations

import numpy as np

B0 = 2.0          # стартовая ширина
SIGMA = 0.3
N = 4000
STEPS = 3000
SEED = 20250101
GAIN = 1.2        # коэффициент связи
WMIN, WMAX = 0.5, 4.0


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def run(condition: str, seed: int = SEED) -> tuple[float, float, list[float], list[float]]:
    """Runs one condition. Returns (mean, spread, widths, observed spreads)."""
    rng = np.random.default_rng(seed)
    pop = rng.normal(0.0, 0.5, N)
    width = B0
    widths: list[float] = []
    observed: list[float] = []

    for _ in range(STEPS):
        if condition in ("B", "C"):
            s = float(pop.std())
            observed.append(s)
            if condition == "C":
                width = float(np.clip(GAIN * s, WMIN, WMAX))

        widths.append(width)
        pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, N), width)

    return float(pop.mean()), float(pop.std()), widths, observed


print("# Наблюдение vs воздействие")
print()
print(f"B0 = {B0}, sigma = {SIGMA}, N = {N}, steps = {STEPS}")
print(f"связь: width = clip({GAIN} * spread, {WMIN}, {WMAX})")
print(f"seed = {SEED} (одинаковый для всех условий)")
print()

mA, sA, wA, _ = run("A")
mB, sB, wB, _ = run("B")
mC, sC, wC, obsC = run("C")

print("условие   mean      spread    ширина (мин/макс)")
print("-" * 58)
print(f"  A       {mA:+.4f}   {sA:.4f}    {min(wA):.2f} / {max(wA):.2f}")
print(f"  B       {mB:+.4f}   {sB:.4f}    {min(wB):.2f} / {max(wB):.2f}")
print(f"  C       {mC:+.4f}   {sC:.4f}    {min(wC):.2f} / {max(wC):.2f}")
print()

dAB = abs(sA - sB) / sA * 100
dAC = abs(sA - sC) / sA * 100

print("# Сравнения")
print()
print(f"  B против A (наблюдение):  разница {dAB:.6f}%")
print(f"  C против A (воздействие): разница {dAC:.2f}%")
print()

# Sanity: did the control actually change?
width_varies = max(wC) - min(wC)
print(f"  разброс ширины в C: {width_varies:.3f} (если 0 — воздействия не было)")
print()

print("# Вывод")
print()

if dAB < 1e-9:
    print("B = A: наблюдение без записи в динамику НЕ меняет организм.")
    print("  Наблюдатель только читает, ничего не пишет обратно.")
else:
    print(f"B != A на {dAB:.6f}% — неожиданно.")

print()

if width_varies < 0.01:
    print("ГЕЙТ ПРОВАЛЕН: ширина в C не менялась — эксперимент недействителен.")
elif dAC > 1.0:
    print(f"C != A на {dAC:.1f}%: управляющая связь меняет организм.")
    print("  Вред от воздействия, не от наблюдения.")
else:
    print(f"C близко к A ({dAC:.2f}%) — связь слабая.")

print()
print("# Что это значит для принципа")
print()
print("Принцип «среда не измеряет» неточен. Правильно:")
print()
print("  Наблюдение отделено от управления.")
print("  Ни один измерительный канал не изменяет динамику,")
print("  если обратное воздействие явно не включено.")
print()
print("A и B: наблюдение само по себе безвредно.")
print("C: вред от воздействия, не от наблюдения.")
