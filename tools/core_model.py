"""Ядро: одна система, где ремонт — переменная, а не параметр.

Собираем то, что уже лежит в карте отдельными формулами:

- накопление повреждения с насыщающимся удалением (как в модели дефицитов: чем больше груз, тем хуже
  удаляется), `dD/dt = eta - C*D/(K+D)`;
- ремонтная способность как отдельное состояние: восстанавливается к норме и подавляется грузом
  (B9-03-0001 обратное время, B9-03-0002 порочный круг), `dC/dt = (C0-C)/tau - gamma*D*C`;
- риск смерти как функция груза, БЕЗ отдельного постулата о старении: `h = h0 + beta*D^2`.

Проверяем численно: даёт ли такая система гомперцевский (экспоненциальный по времени) рост риска,
и что изменится, если запретить подавление ремонта (gamma = 0).

Usage: python3 tools/core_model.py [--write]
"""

from __future__ import annotations

import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "CORE-MODEL.md"


def simulate(gamma: float, tau: float = 10.0, eta: float = 0.5, K: float = 0.1,
             C0: float = 1.0, beta: float = 1.0, h0: float = 0.01,
             dt: float = 0.01, T: float = 300.0) -> list[tuple[float, float, float, float]]:
    D, C, t = 0.0, C0, 0.0
    rows = [(t, D, C, h0 + beta * D * D)]
    while t < T - 1e-9:
        removal = C * D / (K + D) if D > 0 else 0.0
        dD = eta - removal
        dC = (C0 - C) / tau - gamma * D * C
        D = max(0.0, D + dD * dt)
        C = max(0.0, C + dC * dt)
        t += dt
        rows.append((t, D, C, h0 + beta * D * D))
    return rows


def fit_slope(rows: list[tuple[float, float, float, float]], t0: float, t1: float) -> tuple[float, float]:
    """МНК-наклон ln(h) по t и R^2 на окне [t0, t1]."""
    pts = [(t, math.log(h)) for (t, _, _, h) in rows if t0 <= t <= t1 and h > 0]
    n = len(pts)
    if n < 3:
        return float("nan"), float("nan")
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    den = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / den
    inter = (sy - slope * sx) / n
    ss_tot = sum((p[1] - sy / n) ** 2 for p in pts)
    ss_res = sum((p[1] - (slope * p[0] + inter)) ** 2 for p in pts)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return slope, r2


def main(argv: list[str]) -> int:
    full = simulate(gamma=0.5)
    locked = simulate(gamma=0.0)

    s_full, r2_full = fit_slope(full, 50, 150)
    s_lock, r2_lock = fit_slope(locked, 50, 150)

    def at(rows, t):
        return min(rows, key=lambda r: abs(r[0] - t))

    lines: list[str] = []
    add = lines.append
    add("# Ядро: ремонт как переменная")
    add("")
    add("Сгенерировано `python3 tools/core_model.py`. Числа ниже — результат прогона, не оценка.")
    add("")
    add("## Уравнения")
    add("")
    add("```")
    add("dD/dt = eta - C*D/(K+D)          # груз растёт, удаление насыщается")
    add("dC/dt = (C0-C)/tau - gamma*D*C   # способность восстанавливается и подавляется грузом")
    add("h(t)  = h0 + beta*D(t)^2         # риск — функция груза, без постулата о старении")
    add("```")
    add("")
    add("Параметры прогона: eta=0.5, K=0.1, C0=1, tau=10, beta=1, h0=0.01, dt=0.01, T=300.")
    add("")
    add("## Что получилось")
    add("")
    add(f"- с подавлением ремонта (gamma=0.5): наклон ln h по t = **{s_full:.4f}**, R2 = **{r2_full:.4f}**")
    add(f"- с фиксированной способностью (gamma=0): наклон = **{s_lock:.4f}**, R2 = **{r2_lock:.4f}**")
    add("")
    scan = []
    for g in (0.0, 0.02, 0.05, 0.1, 0.2, 0.5):
        rows = full if g == 0.5 else simulate(gamma=g)
        sl, r2 = fit_slope(rows, 50, 150)
        scan.append((g, sl, r2, at(rows, 300)[1], at(rows, 300)[3]))

    a = at(full, 300)
    b = at(locked, 300)
    add(f"К концу прогона: D={a[1]:.3f}, C={a[2]:.3f}, h={a[3]:.2f} "
        f"(при фиксированном C: D={b[1]:.3f}, h={b[3]:.2f}).")
    add("")
    add("## Зависимость от силы подавления")
    add("")
    add("| gamma | наклон ln h | R2 | D(300) | h(300) |")
    add("|---|---|---|---|---|")
    for g, sl, r2, d300, h300 in scan:
        add(f"| {g} | {sl:.4f} | {'nan' if math.isnan(r2) else f'{r2:.3f}'} | {d300:.3f} | {h300:.2f} |")
    add("")
    add("Таблица показывает не монотонный рост, а **порог**: при gamma <= 0.1 груз выходит на стационар")
    add("(D около 0.1, риск не растёт), при gamma >= 0.2 система уходит в коллапс (D >> 1, риск")
    add("взрывается). Наклон ln h при этом не «растёт с gamma», а зависит от того, насколько далеко")
    add("система за порогом: при gamma=0.2 коллапс наступает позже и окно 50-150 попадает на крутой")
    add("участок, при gamma=0.5 — раньше.")
    add("")
    add("## Что это значит")
    add("")
    add("**Главный результат:** в системе есть порог по силе подавления ремонта. Ниже порога организм")
    add("держится (гомеостаз), выше — коллапс с экспоненциальным ростом риска. То есть старение в этой")
    add("модели — не плавный дрейф, а приближение к границе устойчивости, и «скорость старения» — это")
    add("расстояние до порога, а не константа. Тогда:")
    add("")
    add("- модель объясняет, почему старение выглядит как Гомперц, не вводя «программу старения»;")
    add("- предсказание: усиление ремонта должно не «замедлять старение», а **отодвигать порог** —")
    add("  то есть увеличивать время до коллапса нелинейно (проверяемо на данных с усилением ремонта);")
    add("- и второе предсказание: у особей с одинаковым грузом, но разной способностью, риск должен")
    add("  различаться сильнее, чем предсказывает линейная модель.")
    add("")
    add("## Чем это отличается от того, что уже есть")
    add("")
    add("- DEB (`B7-06-0002`): hazard вводится постулатом, ремонт — параметр, а не состояние.")
    add("- Очередь Ledberg (`B8-05-0001`): способность падает по возрасту, а не от груза.")
    add("- Дефициты Mitnitski (`B8-05-0002`): обратная связь есть, но отдельного состояния ремонта нет.")
    add("- Наша система: способность — состояние, и она падает от груза. Это соединение двух линий.")
    add("")
    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
