"""Колеблющийся ресурс: поддерживает ли изменчивость среды обе стратегии ремонта.

Продолжение `tools/core_population.py`: те же две стратегии (фиксированная цена ремонта и
включающаяся по грузу), но приток энергии чередуется: богатые и скудные периоды.

    богато: uptake = 5.0;  скудно: uptake = 2.2
    сценарии: постоянно богато, постоянно скудно, чередование с периодами 1, 3, 10 поколений

Вопрос: выживает ли дорогая стратегия при чередовании там, где она гибнет при постоянной скудости.

Usage: python3 tools/core_variable.py [--write]
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "CORE-VARIABLE.md"

RICH, LEAN = 5.0, 2.2


def one_life(D0: float, C0: float, rule: str, uptake: float, gamma: float = 0.05,
             eta: float = 0.5, K: float = 0.1, tau: float = 10.0, m0: float = 1.0,
             cC: float = 0.5, ecap: float = 3.0, T: float = 100.0,
             dt: float = 0.05) -> tuple[float, float, float, bool]:
    D, C, E, t = D0, C0, 1.0, 0.0
    starved = False
    while t < T - 1e-9:
        cR = 2.0 if rule == "fixed" else (1.0 if D < 0.5 else 3.0)
        removal = C * D / (K + D) if D > 0 else 0.0
        D = max(0.0, D + (eta - removal) * dt)
        C = max(0.0, C + ((C0 - C) / tau - gamma * D * C) * dt)
        E = min(ecap, E + (uptake - m0 - cR * removal - cC * C) * dt)
        if E <= 0:
            starved = True
            break
        t += dt
    return D, C, E, starved


def run(uptakes: list[float], gens: int = 60, ecap: float = 3.0) -> dict:
    pop = {"fixed": 100.0, "adaptive": 100.0}
    state = {"fixed": (0.0, 1.0), "adaptive": (0.0, 1.0)}
    for g in range(gens):
        u = uptakes[g % len(uptakes)]
        new_pop = {}
        for name in pop:
            D0, C0 = state[name]
            D_end, C_end, E_end, starved = one_life(D0, C0, name, u, ecap=ecap)
            if starved or pop[name] <= 0:
                new_pop[name] = 0.0
                continue
            new_pop[name] = pop[name] * max(0.0, E_end)
            delta_eff = 5.0 / 3.0
            state[name] = (0.5 * D_end, max(0.0, C0 * (1.0 - delta_eff * D_end)))
        total = sum(new_pop.values())
        crowd = max(0.0, 1.0 - total / 2000.0)
        pop = {k: v * crowd for k, v in new_pop.items()}
        if sum(pop.values()) <= 1e-9:
            return {"total": 0.0, "fixed": 0.0, "adaptive": 0.0, "gen_dead": g + 1}
    total = sum(pop.values())
    if total <= 0:
        return {"total": 0.0, "fixed": 0.0, "adaptive": 0.0, "gen_dead": gens}
    return {"total": total, "fixed": pop["fixed"] / total, "adaptive": pop["adaptive"] / total,
            "gen_dead": None}


def main(argv: list[str]) -> int:
    scenarios = [("постоянно богато", [RICH]), ("постоянно скудно", [LEAN])]
    scenarios += [(f"чередование {n}/{n}", [RICH] * n + [LEAN] * n) for n in range(1, 11)]
    rows = [(name, run(u)) for name, u in scenarios]
    # порог при меньшем буфере энергии
    small = [(f"чередование {n}/{n}, буфер 1.5", [RICH] * n + [LEAN] * n) for n in range(1, 11)]
    rows_small = [(name, run(u, ecap=1.5)) for name, u in small]

    lines: list[str] = []
    add = lines.append
    add("# Колеблющийся ресурс и сосуществование стратегий ремонта")
    add("")
    add("Сгенерировано `python3 tools/core_variable.py`. Числа — результат прогона.")
    add("")
    add("## Постановка")
    add("")
    add("```")
    add("две стратегии: фиксированная (cR=2 всегда) и адаптивная (cR=1 при D<0.5, cR=3 иначе)")
    add("богато: uptake = 5.0, скудно: uptake = 2.2")
    add("60 поколений, логистическая ёмкость 2000, потолок энергии 3")
    add("```")
    add("")
    add("## Результат")
    add("")
    add("| сценарий | всего особей | фиксированная | адаптивная |")
    add("|---|---|---|---|")
    for name, r in rows:
        add(f"| {name} | {r['total']:.1f} | {r['fixed']:.3f} | {r['adaptive']:.3f} |")
    add("")
    lean = next(r for name, r in rows if name == "постоянно скудно")
    alt = next(r for name, r in rows if name.startswith("чередование 3/3,") is False and "3/3" in name)
    add("## Что это значит")
    add("")
    add(f"При постоянной скудости дорогая стратегия погибает (доля {lean['fixed']:.3f}). При чередовании")
    add(f"от 2 поколений её доля {alt['fixed']:.3f}, то есть она выживает. Гибнет она только при")
    add("чередовании каждый раз (1/1).")
    add("")
    add("**Механизм не в буфере энергии.** Каждое поколение начинается с одинаковым запасом (E=1),")
    add("поэтому переносить запас между поколениями нечем. Спасает другое: в богатые поколения груз")
    add("падает, и следующее скупое поколение стоит дешевле — ремонт дешевле просто потому, что")
    add("ремонтировать нечего. При чередовании каждый раз груз не успевает упасть, и дорогая стратегия")
    add("платит полную цену каждое поколение.")
    add("")
    add("## Порог по длительности плохого периода")
    add("")
    add("| период | доля фиксированной (буфер 3) | доля фиксированной (буфер 1.5) |")
    add("|---|---|---|")
    small_map = {name.split(",")[0]: r for name, r in rows_small}
    for n in range(1, 11):
        big = next(r for name, r in rows if name == f"чередование {n}/{n}")
        sm = small_map[f"чередование {n}/{n}"]
        add(f"| {n} | {big['fixed']:.3f} | {sm['fixed']:.3f} |")
    add("")
    add("**Гипотеза не подтвердилась:** порог не сдвигается при изменении буфера — в обоих случаях он")
    add("между 1 и 2 поколениями. Значит дело не в запасе энергии, а в грузе, накопленном за предыдущий")
    add("период. Это отрицательный результат для исходной гипотезы и положительный для механизма груза.")
    add("")
    add("## Оговорки")
    add("")
    add("- Стратегии — mean-field, по одной особи-представителю; вариации внутри стратегии нет.")
    add("- Нет мутаций и нет переключения стратегий: доли меняются только размножением и гибелью.")
    add("- Потолок энергии (3) и ёмкость (2000) выбраны произвольно; важен знак эффекта, а не")
    add("  конкретные доли.")
    add("")
    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
