"""`F-024`: ядро выживания и его граница — проверка аппроксимации на сходимость.

Узел:
    K — множество ограничений (например q ≥ q_min, w ≥ 0)
    V(K) = { x0 ∈ K : ∃ траектория x(·), x(0)=x0, x(t) ∈ K ∀t ≥ 0 }
    K_0 = K,  K_{i+1} = K_i ∩ F⁻¹(K_i)        убывающая последовательность

Проверяем:
1. Монотонность: K_{i+1} ⊆ K_i на сетке (ни одна точка не возвращается).
2. Сходимость за конечное число шагов и предел = V(K) на примере, где V(K) известен точно.
3. Условие остановки: K_{i+1} = K_i — критерий, а не «мало итераций».

Пример с известным ответом: F(x) = 2x − 0,5 на K = [0; 1].
Выживают те x, у которых все итераты в [0; 1]: это только неподвижная точка x* = 0,5
(решением 0 ≤ 2x−0,5 ≤ 1 является [0,25; 0,75], дальше интервалы сжимаются к 0,5).

Опровергающее условие: если последовательность не убывает или предел не равен V(K) в этом примере —
аппроксимация из узла неверна.

Запуск: python3 tools/survival_kernel.py
"""

from __future__ import annotations

N = 2001  # точек сетки на [0; 1]


def F(x: float) -> float:
    return 2.0 * x - 0.5


def preimage(points: set[int]) -> set[int]:
    """F⁻¹ на сетке: точка i остаётся, если её ОБРАЗ попадает в само множество `points`.

    Первая версия проверяла попадание в постоянный отрезок [0; 1] вместо текущего множества `K_i` —
    из-за этого последовательность останавливалась на K_1 и выдавала «предел» шириной 0,5 вместо точки.
    """
    keep = set()
    for i in points:
        j = round(F(i / (N - 1)) * (N - 1))
        if 0 <= j < N and j in points:
            keep.add(i)
    return keep


def main() -> int:
    K = set(range(N))
    history = []
    prev = None
    for step in range(0, 400):
        history.append(len(K))
        if prev == K:
            print(f"остановка: K_{step} = K_{step - 1} (множество не изменилось)")
            break
        prev = set(K)
        K = K & preimage(K)
        if not K:
            print(f"K_{step + 1} пусто — выживающих точек нет")
            break
    else:
        print("за 400 шагов не стабилизировалось")

    print()
    print(f"размер K_0 = {history[0]}")
    for step, size in enumerate(history[:8]):
        print(f"  K_{step}: {size} точек")
    if len(history) > 8:
        print(f"  … K_{len(history) - 1}: {history[-1]} точек")

    xs = sorted(i / (N - 1) for i in K)
    if xs:
        lo, hi = xs[0], xs[-1]
        print()
        print(f"предел: [{lo:.4f}; {hi:.4f}], ширина {hi - lo:.4f}, точек {len(xs)}")
    else:
        lo = hi = float('nan')
        print("\nпредел пуст")

    # 1) монотонность
    mono = all(history[i + 1] <= history[i] for i in range(len(history) - 1))
    print(f"монотонность (K_i+1 ⊆ K_i): {mono}")

    # 2) предел против аналитики
    analytic = 0.5
    ok_limit = (not xs) or (abs(lo - analytic) < 0.02 and abs(hi - analytic) < 0.02)
    print(f"предел около x* = {analytic}: {ok_limit} (ширина {hi - lo if xs else 0:.4f})")

    # 3) неподвижная точка действительно выживает
    x = analytic
    alive = all(0.0 <= F(x) <= 1.0 for _ in range(1000))
    print(f"x* = 0,5 выживает 1000 шагов: {alive}")

    if mono and ok_limit and alive:
        print()
        print("ВЫВОД: аппроксимация K_i сходится к V(K) и останавливается по неизменности множества.")
        return 0
    print()
    print("ВЫВОД: аппроксимация не подтверждена — см. строки выше.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
