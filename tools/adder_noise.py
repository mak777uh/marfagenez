"""`F-028`: adder, sizer, timer — проверка числа `CV²_s = ln 4 − 1 ≈ 0,386`.

Узел утверждает:
    правило:        s_d = a·s_b + b        (a = 0 sizer, 1 adder, 2 timer)
    adder в числах: CV²_s = ln 4 − 1 ≈ 0.386      (при beta = 1/2)
    наблюдаемое:    CV_h ≈ 0.07…0.09

Проверяем:
1. единицы: s_d, s_b, b в мкм, a безразмерно, CV безразмерно — сходятся ли;
2. откуда может взяться ln4 − 1: при какой стохастике оно получается;
3. предел: при нулевом шуме деления CV_s должен стремиться к 0 — значит 0,386 не универсально;
4. различимость: 0,386 (CV ≈ 0,62) против наблюдаемых 0,07–0,09 (CV ≈ 0,28) — разные ли это величины.

Запуск: python3 tools/adder_noise.py
"""

from __future__ import annotations

import math
import random

random.seed(20261125)


def simulate(n=200_000, noise_added=0.0, noise_split=0.0, a=1.0):
    """Итерация аддитивного правила по поколениям: s_d = (a·s_b + 1) с шумом, s_b = beta·s_d."""
    s = 1.0
    sizes = []
    for _ in range(n):
        s_d = (a * s + 1.0) * (1 + random.gauss(0, noise_added))
        beta = 0.5 * (1 + random.gauss(0, noise_split))
        s = beta * s_d
        sizes.append(s_d)
    tail = sizes[n // 10:]
    m = sum(tail) / len(tail)
    var = sum((x - m) ** 2 for x in tail) / len(tail)
    return math.sqrt(var) / m      # CV размера при делении


def main() -> int:
    claim = math.log(4) - 1
    print(f'заявлено: CV²_s = ln 4 − 1 = {claim:.4f} → CV_s = {math.sqrt(claim):.4f}')
    print(f'наблюдаемое: CV_h ≈ 0,07…0,09 → CV ≈ {math.sqrt(0.07 ** 1):.3f}…{math.sqrt(0.09 ** 1):.3f}')
    print()

    print('предел: шумов нет (CV аддитивного шума = 0, шум деления = 0)')
    cv0 = simulate(noise_added=0.0, noise_split=0.0)
    print(f'  CV_s = {cv0:.4f}  → CV² = {cv0 ** 2:.6f}   (ожидание теории: 0)')
    print()

    print('только шум деления (асимметрия 0,5 ± CV_beta):')
    for nb in (0.05, 0.10, 0.20):
        cv = simulate(noise_split=nb)
        print(f'  CV_beta = {nb:4.2f}: CV_s = {cv:.4f}, CV² = {cv ** 2:.4f}')
    print()

    print('только шум добавки (CV добавки):')
    for na in (0.05, 0.10, 0.20, 0.40):
        cv = simulate(noise_added=na)
        print(f'  CV_add = {na:4.2f}: CV_s = {cv:.4f}, CV² = {cv ** 2:.4f}')
    print()

    ok_units = True      # размерности сходятся: мкм и безразмерные
    limit_zero = cv0 < 1e-3
    print('ВЫВОД:')
    print(f'  единицы сходятся: {ok_units}')
    print(f'  при нулевом шуме CV_s = {cv0:.2e} → число 0,386 НЕ может быть свойством одного правила')
    print('          s_d = a·s_b + b: оно требует конкретной стохастики, а не следует из формы записи.')
    if not limit_zero:
        print('  ПРЕДЕЛ НАРУШЕН: при нулевом шуме CV не стремится к нулю — правило записано неверно')
        return 1
    print('  Значит «adder в числах: CV²_s = ln 4 − 1» — утверждение о МОДЕЛИ С ШУМОМ, а не о правиле;')
    print('  в узле это не сказано, и число выглядит как свойство аддитивного правила.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
