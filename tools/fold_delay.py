"""`F-029` (нормальные формы): показатель размытия перехода `ε^(2/3)`.

Запись в узле: у несовершенной складки `ẋ = r + x²` с несовершенством `ε` переход размыт на ширину,
масштабирующуюся как `ε^(2/3)`. Эмпирика: `p = 0,63 ± 0,10` (реакция иодат–мышьяковистая кислота).

Здесь проверяется **теория**, а не данные: численно измеряется задержка срыва при медленном свипе
`r(t) = α·t − ε` из устойчивой ветви `x = −√ε`.

Классический результат теории задержанной бифуркации: `τ ∝ ε^(2/3)·α^(−1/3)`. Проверяем оба показателя.

Опровергающее условие: если показатель по `ε` отличается от 2/3 больше чем на 0,05, запись неверна.

Запуск: python3 tools/fold_delay.py
"""

from __future__ import annotations

import math

try:
    import numpy as np
    from scipy.integrate import solve_ivp
except Exception:  # noqa: BLE001
    np = None


def delay(eps: float, alpha: float) -> float:
    """Время от момента r=0 до срыва (x пересекает 0). Система ẋ = α·t − ε + x²."""
    t_zero = eps / alpha

    def f(t: float, y):
        return [alpha * t - eps + y[0] * y[0]]

    def escape(t: float, y):
        return y[0]
    escape.terminal = True
    escape.direction = 1

    sol = solve_ivp(f, (0.0, t_zero * 50 + 50.0), [-math.sqrt(eps)], method="LSODA",
                    events=escape, rtol=1e-10, atol=1e-12, dense_output=False)
    if sol.t_events and len(sol.t_events[0]) > 0:
        return float(sol.t_events[0][0]) - t_zero
    return float("nan")


def fit_slope(points: list[tuple[float, float]]) -> float:
    xs = [math.log(a) for a, _ in points]
    ys = [math.log(b) for _, b in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = sum((a - mx) ** 2 for a in xs)
    return num / den


def main() -> int:
    if np is None:
        print("нет scipy — проверка не выполнена")
        return 1

    print("1) задержка от ε при α = 1e-4")
    alpha = 1e-4
    pts_eps = []
    for eps in (0.001, 0.003, 0.01, 0.03, 0.1):
        d = delay(eps, alpha)
        pts_eps.append((eps, d))
        print(f"   ε={eps:<6} задержка={d:.6g}   τ·α^(1/3)={d * alpha ** (1 / 3):.6g}")
    slope_eps = fit_slope(pts_eps)

    print()
    print("2) задержка от α при ε = 0,01")
    eps = 0.01
    pts_alpha = []
    for a in (1e-5, 3e-5, 1e-4, 3e-4, 1e-3):
        d = delay(eps, a)
        pts_alpha.append((a, d))
        print(f"   α={a:<8} задержка={d:.6g}")
    slope_alpha = fit_slope(pts_alpha)

    print()
    print(f"показатель по ε: {slope_eps:+.3f} (теория: +0,667)")
    print(f"показатель по α: {slope_alpha:+.3f} (теория: −0,333)")
    ok = abs(slope_eps - 2 / 3) <= 0.05 and abs(slope_alpha + 1 / 3) <= 0.05
    print()
    if ok:
        print("ВЫВОД: численная складка даёт ε^(2/3)·α^(−1/3) — запись в узле согласуется с теорией.")
        print("        Эмпирика (p = 0,63 ± 0,10) совместима с показателем 2/3.")
        return 0
    print("ВЫВОД: показатели не совпали с теорией — либо запись неверна, либо схема груба.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
