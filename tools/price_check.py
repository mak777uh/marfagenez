"""`F-012` (уравнение Прайса): тождество или приближение?

`Δz̄ = Cov(w,z)/w̄ + E[w·Δz]/w̄`, где `w_i` — число потомков (абсолютная приспособленность), `z_i` — признак
родителя, `Δz_i` — среднее отклонение признака его потомков. Все средние — по родителям **взвешенно по `w`**.

Первая версия этой проверки дала остаток 1e-2 и вывод «тождество не выполняется». Ошибка была в
реализации: средние брались невзвешенно, а приспособленность — случайной. Тождество требует, чтобы среднее
по детям считалось как `Σ w_i (z_i + Δz_i) / Σ w_i`.

Что проверяется:
1. Тождество выполняется численно (остаток ~1e-15).
2. Цена отбрасывания передаточного члена `E[w·Δz]/w̄` — того самого упрощения «отбор = ковариация».

Опровергающее условие: остаток > 1e-9 — реализация неверна (или `w` не абсолютная приспособленность).

Запуск: python3 tools/price_check.py
"""

from __future__ import annotations

import random


def run(seed: int, n: int, bias: float, noise: float) -> tuple[float, float, float, float]:
    rng = random.Random(seed)
    z = [rng.gauss(0.0, 1.0) for _ in range(n)]
    w = [rng.choice([0, 1, 2, 3]) for _ in range(n)]      # число потомков у каждого родителя
    if sum(w) == 0:
        w[0] = 1
    dz = [bias + rng.gauss(0.0, noise) for _ in range(n)]  # среднее отклонение потомков родителя i

    wbar = sum(w) / n
    zbar = sum(z) / n
    zbar_next = sum(wi * (zi + dzi) for wi, zi, dzi in zip(w, z, dz)) / sum(w)

    delta_exact = zbar_next - zbar
    cov = sum((wi - wbar) * (zi - zbar) for wi, zi in zip(w, z)) / n
    selection = cov / wbar
    transmission = sum(wi * dzi for wi, dzi in zip(w, dz)) / (n * wbar)
    return delta_exact, selection + transmission, selection, transmission


def main() -> int:
    print(f"{'bias':>6} {'noise':>6} {'Δz точно':>12} {'сумма членов':>13} {'остаток':>10} "
          f"{'только отбор':>13} {'ошибка':>9} {'доля':>6}")
    worst = 0.0
    rows = []
    for bias, noise in ((0.0, 0.1), (0.1, 0.1), (0.5, 0.1), (0.5, 0.5)):
        exact, total, sel, trans = run(seed=11, n=4000, bias=bias, noise=noise)
        residual = abs(exact - total)
        worst = max(worst, residual)
        err = sel - exact
        share = abs(err) / abs(exact) * 100 if abs(exact) > 1e-12 else float("nan")
        rows.append((bias, noise, exact, sel, err, share))
        print(f"{bias:6.1f} {noise:6.1f} {exact:12.6f} {total:13.6f} {residual:10.2e} "
              f"{sel:13.6f} {err:9.6f} {share:5.0f}%")

    print()
    print(f"макс. остаток тождества: {worst:.2e}")
    print()
    print("Цена упрощения «отбор = ковариация» (передаточный член отброшен):")
    for bias, noise, exact, sel, err, share in rows:
        if bias == 0.0:
            print(f"  смещение 0: ошибка {err:+.6f} — член мал, упрощение почти законно")
        else:
            print(f"  смещение {bias}: ошибка {err:+.6f} ({share:.0f} % от Δz) — упрощение НЕЗАКОННО")

    ok = worst < 1e-9
    print()
    if ok:
        print("ВЫВОД: уравнение Прайса — ТОЖДЕСТВО (остаток на машинной точности);")
        print("        «отбор = ковариация» верно только при нулевом передаточном смещении.")
        return 0
    print("ВЫВОД: тождество не выполняется — ошибка в реализации, а не в формуле.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
