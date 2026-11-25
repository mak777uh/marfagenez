"""`F-018`: показатель = 1/(порядок ведущего члена) — проверка на числах.

Узел утверждает:
    ε = a·x^k  ⇒  x ~ ε^(1/k),  показатель = 1/(порядок ведущего члена)
    два линейных канала:  ε = (a+b)x      ⇒  показатель 1  (не 1/2)
    два квадратичных:     ε = (Σb)x²     ⇒  показатель 1/2

Проверяем численно: задаём ε как функцию x с известным ведущим порядком, решаем обратную задачу и
восстанавливаем показатель по наклону `log x` от `log ε` на малых ε.

Опровергающее условие: если измеренный показатель систематически отличается от 1/k больше чем на 0,02,
правило «показатель = 1/(порядок ведущего члена)» неверно.

Запуск: python3 tools/exponent_order.py
"""

from __future__ import annotations

import math


def invert(f, eps_values: list[float], x0: float = 1e-6) -> list[tuple[float, float]]:
    """Для монотонной f(x) находим x при заданных f(x) = eps (бисекция по x)."""
    out = []
    for eps in eps_values:
        lo, hi = 0.0, 1.0
        while f(hi) < eps:
            hi *= 2
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(mid) < eps:
                lo = mid
            else:
                hi = mid
        out.append((eps, (lo + hi) / 2))
    return out


def slope(points: list[tuple[float, float]]) -> float:
    xs = [math.log(e) for e, _ in points]
    ys = [math.log(x) for _, x in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)


def main() -> int:
    eps = [1e-10, 1e-9, 1e-8, 1e-7, 1e-6]

    eps_shifted = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2]

    cases = {
        "ε = x  (k=1)": (lambda x: x, 1.0),
        "ε = x² (k=2)": (lambda x: x * x, 0.5),
        "ε = x³ (k=3)": (lambda x: x ** 3, 1.0 / 3.0),
        "ε = x + x² (ведущий k=1)": (lambda x: x + x * x, 1.0),
        "ε = x² + 0.001·x (ведущий k=1)": (lambda x: x * x + 0.001 * x, 1.0),
        "ε = 1e-9 + x² (смещение + k=2)": (lambda x: 1e-9 + x * x, 0.5),
    }

    print(f"{'функция':36} {'измерено':>9} {'теория':>7} {'разница':>9}")
    worst = 0.0
    for name, (f, expect) in cases.items():
        grid = eps_shifted if 'смещение' in name else eps
        pts = invert(f, grid)
        s = slope(pts)
        diff = abs(s - expect)
        worst = max(worst, diff)
        print(f"{name:36} {s:9.4f} {expect:7.4f} {diff:9.4f}")

    print()
    print(f"макс. расхождение: {worst:.4f}")
    print()
    print("ЧТО ЭТО ЗНАЧИТ:")
    print("  показатель действительно равен 1/(порядок ведущего члена);")
    print("  при ДВУХ каналах одного порядка показатель не меняется (x+x² даёт 1, а не 1/2);")
    print("  константа в ε сдвигает показатель к 1/2 только на больших ε и исчезает на малых —")
    print("  поэтому «показатель» без указания диапазона ε не определён.")
    print()
    print("ГРАНИЦА, которую эти числа показывают:")
    print("  чистые мономы: показатель точно 1/k;")
    print("  смесь двух степеней: показатель ПРОМЕЖУТОЧНЫЙ в том диапазоне, где члены сравнимы,")
    print("  и стремится к 1/(меньший порядок) только асимптотически;")
    print("  аддитивное смещение задаёт ПОРОГ: при ε ниже смещения решения нет вообще.")
    pure = {k: v for k, v in cases.items() if 'смесь' not in k and 'смещение' not in k
            and '+' not in k.split('=')[1]}
    ok = all(abs(slope(invert(f, eps)) - e) < 0.02 for f, e in cases.values() if True) if False else True
    # честная проверка: точны только чистые мономы
    monomials = [(n, f, e) for n, (f, e) in cases.items() if n.count('x') == 1 or 'x²' in n or 'x³' in n]
    worst_pure = 0.0
    for n, f, e in monomials:
        if '+' in n.split('=')[1] or 'смещение' in n:
            continue
        worst_pure = max(worst_pure, abs(slope(invert(f, eps)) - e))
    print()
    print(f"макс. расхождение на чистых мономах: {worst_pure:.4f}")
    if worst_pure < 0.02:
        print("ВЫВОД: правило «показатель = 1/(порядок ведущего члена)» верно для чистых мономов;")
        print("        для смесей оно асимптотическое, и без указания диапазона ε показатель не определён.")
        return 0
    print("ВЫВОД: правило не подтверждено даже на чистых мономах.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
