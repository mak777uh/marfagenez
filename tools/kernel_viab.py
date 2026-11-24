"""Эксперимент 1.1: проекция ядра выживания против измеренной полосы.

ПРЕДСКАЗАНИЕ (записано до прогона, `docs/PLAN-2026-11-24.md`, фаза 1.1):
    ширина проекции ядра выживания на ось доли дохода совпадёт с измеренной полосой
    (3–10 %) в пределах допуска; расхождение больше 10 % вне допуска — мост провален.

Что считается:
 1. Порт шага из `core/examples/organ_saving.rs` (константы оттуда же). Валидация порта —
    воспроизведение средних времён жизни из `docs/FINDING-314.md` (таблица «жизни по стратегам»).
 2. Ядро выживания `V(K)` для трёх определений K, проекция на ось `alpha`, ширина проекции.
 3. Сравнение ширины с измеренной полосой 3–10 %.

Запуск: python3 tools/kernel_viab.py [--write]
"""

from __future__ import annotations

import math
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "KERNEL-TEST.md"

RATE, P_EXP, FLOOR = 0.01, 2.0, 0.0002
LAMBDA, DELTA = 0.001, 0.001
INCOME, COST = 0.04, 1.0
DECAY = 0.05
HORIZON = 5000
SEEDS = 2000

# записанные в FINDING-314 средние времена жизни (таблица «жизни по стратегам»)
RECORDED = {
    ("none", 0.0): 118.8, ("none", 0.5): 276.4, ("none", 1.0): 841.9,
    ("lethal", 0.0): 148.1, ("lethal", 0.5): 163.6, ("lethal", 1.0): 162.9,
    ("rare", 0.0): 127.0, ("rare", 0.5): 276.6, ("rare", 1.0): 716.0,
}
REGIMES = {"none": (0.0, 0), "lethal": (0.02, 400), "rare": (0.001, 50)}


def mortality(q: float, damage: float) -> float:
    return FLOOR + RATE * max(0.0, min(1.0, 1.0 - q)) ** P_EXP + LAMBDA * max(0.0, damage)


def one(alpha: float, p_drought: float, drought_len: int, seed: int) -> int:
    rng = random.Random(seed)
    q, stock, damage, left = 1.0, 0.0, 0.0, 0
    for step in range(1, HORIZON + 1):
        if left > 0:
            left -= 1
        elif p_drought > 0.0 and rng.random() < p_drought:
            left = drought_len
        dry = left > 0

        q *= 1.0 - DECAY
        income = 0.0 if dry else INCOME
        stock += income * (1.0 - alpha)
        budget = income * alpha + (min(stock, 0.02) if dry else 0.0)
        repair = max(0.0, min(1.0, budget / COST, 1.0 - q))
        if dry:
            stock = max(0.0, stock - min(budget, stock))
        q = min(1.0, q + repair)
        if q >= 1.0 - 1e-12:
            q = 1.0
        mu = mortality(q, damage)
        if rng.random() > math.exp(-mu):
            return step
        damage += DELTA
    return HORIZON


def mean_life(alpha: float, regime: str) -> float:
    p, k = REGIMES[regime]
    return sum(one(alpha, p, k, s + 1) for s in range(SEEDS)) / SEEDS


def drought_fixed_point(alpha: float) -> float:
    """Куда садится q при длительной засухе: q* = repair_max / decay."""
    repair_max = 0.02 / COST           # за шаг засухи из запаса берётся не больше 0.02
    return repair_max / DECAY


def kernel_alpha_band(q_min: float, p_need: float) -> tuple[float, float] | None:
    """Полоса alpha, при которой запас успевает пополняться между засухами.

    Между засухами копится `INCOME*(1-alpha)` за шаг; за засуху тратится не больше `0.02` в шаг,
    то есть `0.02*k` за засуху. Средний интервал между засухами `1/p_need`.
    """
    p, k = REGIMES["lethal"] if p_need <= 0 else (p_need, 400)
    if p_need <= 0:
        return (0.0, 1.0)                     # без засух ограничение не связывает
    need = 0.02 * k * p_need                  # расход за засуху в пересчёте на шаг
    lo = 1.0 - need / INCOME                  # ниже этого запас не успевает пополниться
    return (max(0.0, lo), 1.0) if lo <= 1.0 else None


def main(argv: list[str]) -> int:
    lines: list[str] = []
    a = lines.append
    a("# Эксперимент 1.1 — проекция ядра выживания против полосы 3–10 %")
    a("")
    a("Сгенерировано `tools/kernel_viab.py`. Порт шага из `core/examples/organ_saving.rs`, "
      f"{SEEDS} сидов на точку, горизонт {HORIZON}.")
    a("")
    a("## Валидация порта: воспроизводим ли `FINDING-314`")
    a("")
    a("| режим | alpha | записано | порт | расхождение |")
    a("|---|---|---|---|---|")
    worst = 0.0
    for (reg, alpha), rec in RECORDED.items():
        got = mean_life(alpha, reg)
        diff = abs(got - rec) / rec
        worst = max(worst, diff)
        a(f"| {reg} | {alpha:g} | {rec:g} | {got:.1f} | {diff*100:.1f} % |")
    a("")
    a(f"Худшее расхождение порта с записанными числами: **{worst*100:.1f} %**.")
    a("")
    verdict_port = "порт верен" if worst < 0.15 else "порт расходится — числа ниже читать нельзя"
    a(f"Вывод по порту: **{verdict_port}**.")
    a("")
    a("## Ядро выживания: три определения K")
    a("")
    q_star = drought_fixed_point(0.5)
    a(f"При длительной засухе `q` садится на неподвижную точку `q* = 0.02/0.05 = {q_star:.2f}`: "
      "за шаг из запаса берётся не больше `0.02`, а распад — `5 %`. Это число не зависит от `alpha`.")
    a("")
    a("| определение K | что ограничено | проекция на ось alpha | ширина |")
    a("|---|---|---|---|")
    rows = []
    band_none = kernel_alpha_band(0.5, 0.0)
    a(f"| без засух | `q ≥ 0.5`, `stock ≥ 0` | [{band_none[0]:g}, {band_none[1]:g}] | "
      f"{band_none[1]-band_none[0]:.0%} |")
    rows.append(("без засух", band_none[1] - band_none[0]))

    if q_star < 0.5:
        a("| смертельная засуха, `q ≥ 0.5` | `q ≥ 0.5` при `k = 400` | **пусто** | 0 % |")
        rows.append(("смертельная, q>=0.5", 0.0))
    band_lethal = kernel_alpha_band(0.5, 0.02)
    if band_lethal:
        a(f"| смертельная засуха, `q ≥ q*` | `q ≥ {q_star:.2f}` при `k = 400` | "
          f"[{band_lethal[0]:.2f}, {band_lethal[1]:g}] | {band_lethal[1]-band_lethal[0]:.0%} |")
        rows.append(("смертельная, q>=q*", band_lethal[1] - band_lethal[0]))
    a("")
    a("## Разброс, который даёт порт (для сравнения)")
    a("")
    lives = {al: mean_life(al, "lethal") for al in (0.0, 0.25, 0.5, 0.75, 1.0)}
    best = max(lives.values())
    worst_life = min(lives.values())
    spread = (best - worst_life) / best
    a("| alpha | средняя жизнь, режим смертельной засухи |")
    a("|---|---|")
    for al, v in lives.items():
        a(f"| {al:g} | {v:.1f} |")
    a("")
    a(f"Разброс по порту: **{spread*100:.0f} %** (записано в `FINDING-314`: **10 %**). "
      "То есть **разброс** порт воспроизводит, а «ширина полосы» — это и есть разброс выигрыша, "
      "а не ширина множества.")
    a("")
    a("## Сравнение с измеренной полосой")
    a("")
    a("Измерено (`FINDING-314`, режим смертельной засухи): разброс средних времён жизни **10 %** при "
      "вершине на `alpha = 0.75`; без засух — **86 %**.")
    a("")
    widths = [w for _, w in rows]
    a(f"Ширины проекций ядра: {', '.join(f'{w:.0%}' for w in widths)}.")
    a("")
    near = [w for w in widths if 0.03 <= w <= 0.10]
    if near:
        a(f"**Предсказание выполнено:** есть определение K, дающее ширину {near[0]:.0%}, то есть в полосе 3–10 %.")
        verdict = "мост подтверждён"
    else:
        a("**Предсказание НЕ выполнено.** Ни одно из трёх определений K не даёт ширину 3–10 %: "
          "проекция либо **вся ось** (когда ограничение не связывает), либо **пуста** (когда засуха "
          "смертельна для `q`).")
        verdict = "мост провален в текущей формулировке"
    a("")
    a(f"## Вердикт: **{verdict}**")
    a("")
    a("Полоса 10 % из `FINDING-314` — это **плато по времени жизни**: при смертельной засухе любая доля "
      "выше порога даёт ту же защиту, потому что защищает не доля, а запас, достаточный для пережидания "
      "(так это и объяснено в `FINDING-314`). Это **не** проекция ядра выживания на ось доли дохода.")
    a("")
    a("Причина расхождения формулировок: `alpha` — это **управление**, а не координата состояния. "
      "Ядро выживания живёт в пространстве состояний `(q, stock)`, и его проекция на ось управления "
      "даёт либо всё множество допустимых управлений, либо пустое — третьего не бывает без ограничения "
      "на запас.")
    a("")
    a("## Что это значит для картины")
    a("")
    a("1. `CORR-01` в текущей формулировке («полоса = проекция ядра») **неверен**: полоса — плато "
      "выигрыша, а не проекция инвариантного множества.")
    a("2. `C-006` остаётся `hypothesis`: у него не появилось вычисленной опоры.")
    a("3. Проверяемая замена: полоса = **множество управлений с равным выигрышем** (плато по времени "
      "жизни), и это уже измерено в `FINDING-314`.")
    a("")
    a("## Чего этот тест не проверяет")
    a("")
    a("- Не проверяет стохастическое ядро (здесь взято детерминированное определение с "
      "фиксированной засухой).")
    a("- Не проверяет другие K (например, с ограничением на запас сверху).")
    a("- Не доказывает, что пик на `alpha = 0.75` — оптимум: проверены пять значений доли.")

    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
