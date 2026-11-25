"""`F-029`: операционально определить «ширину размытия» перехода и измерить её показатель по `ε`.

Прошлый раунд показал: задержка от нуля по `ε` не масштабируется — потому что `ε` сдвигает начало свипа.
Теперь ширина определяется **явно**:

    W(ε, α) = r_jump − r_dev10

где `r_dev10` — значение `r`, при котором траектория ушла на 10 % от стационарной ветви
`x_s(r) = −sqrt(−(r+ε))`, а `r_jump` — где `x` пересекает 0 (срыв).

Свип медленный (`α` мало), чтобы ширина определялась `ε`, а не скоростью.

Опровергающее условие: если показатель по `ε` отличается от 2/3 больше чем на 0,05, запись `ε^(2/3)` в узле
неверна для этой ширины.

Запуск: python3 tools/fold_width.py
"""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp


def measure(eps: float, alpha: float = 1e-6) -> tuple[float, float, float]:
    """Возвращает (r_dev10, r_jump, W). Система ẋ = r(t) + x², r(t) = α·t − ε."""
    t_fold = eps / alpha                      # r = 0 при t = ε/α

    def f(t: float, y):
        return [alpha * t - eps + y[0] * y[0]]

    # старт ровно на ветви при r = −ε/2 (чуть ниже складки)
    t0 = (eps / 2) / alpha
    x0 = -math.sqrt(eps / 2)

    def jump(t: float, y):
        return y[0]
    jump.terminal = True
    jump.direction = 1

    sol = solve_ivp(f, (t0, t_fold + 100 / alpha), [x0], method="LSODA", events=jump,
                    rtol=1e-11, atol=1e-14, max_step=(1 / alpha) / 50)
    if not sol.t_events or not len(sol.t_events[0]):
        return float("nan"), float("nan"), float("nan")

    t_jump = float(sol.t_events[0][0])
    r_jump = alpha * t_jump - eps

    # точка 10 % отклонения: идём по решению и сравниваем с ветвью
    r_dev = float("nan")
    for t, x in zip(sol.t, sol.y[0]):
        r = alpha * t - eps
        if r >= 0:
            r_dev = r
            break
        xs = -math.sqrt(-r)
        if abs(x - xs) > 0.1 * abs(xs):
            r_dev = r
            break
    return r_dev, r_jump, r_jump - r_dev


def fit_slope(points: list[tuple[float, float]]) -> float:
    xs = [math.log(a) for a, _ in points]
    ys = [math.log(b) for _, b in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    return (sum((a - mx) * (b - my) for a, b in zip(xs, ys))
            / sum((a - mx) ** 2 for a in xs))



def alpha_scan() -> None:
    print()
    print("проверка: ширину задаёт α, а не ε (при ε = 0,01)")
    print(f"{'α':>10} {'W':>12} {'W/α^(2/3)':>12}")
    pts = []
    for alpha in (1e-7, 3e-7, 1e-6, 3e-6, 1e-5):
        _, _, w = measure(0.01, alpha)
        pts.append((alpha, w))
        print(f"{alpha:10.1e} {w:12.6g} {w / alpha ** (2 / 3):12.6g}")
    print(f"наклон W по α: {fit_slope(pts):+.3f} (теория 2/3 = +0,667)")


def main() -> int:
    print(f"{'ε':>9} {'r_dev10':>12} {'r_jump':>12} {'W':>12}")
    pts = []
    for eps in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1):
        r_dev, r_jump, w = measure(eps)
        pts.append((eps, w))
        print(f"{eps:9.4f} {r_dev:12.6g} {r_jump:12.6g} {w:12.6g}")

    slope = fit_slope(pts)
    print()
    print(f"показатель W по ε: {slope:+.3f}")
    print("в узле записано: 2/3 = +0,667; альтернатива из литературы: 1/2 = +0,500")
    alpha_scan()

    ok = abs(slope - 2 / 3) <= 0.05
    print()
    if ok:
        print("ВЫВОД: ширина перехода масштабируется как ε^(2/3) — запись узла подтверждается.")
        return 0
    print("ВЫВОД: показатель не 2/3. Запись узла верна только при другом определении ширины.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
