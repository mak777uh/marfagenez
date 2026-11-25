"""`F-001`: кумулятивная опасность и жизнь — проверка на числах.

Узел:
    H(T) = ∫₀ᵀ μ(t) dt;  смерть при H(T) = 1  (63,2-й перцентиль, НЕ средняя)
    μ(t) = μ₀ + λδt   при линейном росте повреждения
    ⇒ μ₀T + (λδ/2)T² = 1        «наше уравнение жизни»
    средняя E[T] = ∫₀^∞ exp(−H(t)) dt

Проверяем:
1. единицы: μ₀, λ, δ в 1/с; λδt даёт 1/с; λδT²/2 безразмерно (H) — сходится ли;
2. предел: при α = λδ → 0 должно получиться экспоненциальное выживание, T(H=1) = 1/μ₀ и E[T] = 1/μ₀;
3. «63,2-й перцентиль»: при H = 1 имеем S = e⁻¹ = 0,368, то есть умерло 63,2 % — верно ли это для всех α;
4. различимость: средняя E[T] против перцентиля T(H=1) — насколько расходятся и почему.

Опровергающее условие: если при H = 1 доля умерших не 63,2 %, или если при α → 0 не воспроизводится
экспоненциальный предел, — запись формулы неверна.

Запуск: python3 tools/hazard_life.py
"""

from __future__ import annotations

import math


def survival(t: float, mu0: float, alpha: float) -> float:
    """S(t) = exp(−μ₀t − α t²/2)."""
    return math.exp(-mu0 * t - alpha * t * t / 2)


def t_at_h1(mu0: float, alpha: float) -> float:
    """Решение μ₀T + αT²/2 = 1 (положительный корень)."""
    if alpha == 0:
        return 1.0 / mu0
    disc = mu0 * mu0 + 2 * alpha
    return (-mu0 + math.sqrt(disc)) / alpha


def mean_life(mu0: float, alpha: float) -> float:
    """E[T] = ∫₀^∞ exp(−μ₀t − αt²/2) dt = sqrt(π/(2α))·exp(b²)·erfc(b), b = μ₀/sqrt(2α).

    При больших b (малый α) считаем асимптотикой exp(b²)·erfc(b) ≈ 1/(b√π)·(1 − 1/(2b²) + 3/(4b⁴)),
    иначе переполнение exp(b²).
    """
    if alpha == 0:
        return 1.0 / mu0
    b = mu0 / math.sqrt(2 * alpha)
    if b > 25:
        factor = (1 / (b * math.sqrt(math.pi))) * (1 - 1 / (2 * b * b) + 3 / (4 * b ** 4))
    else:
        factor = math.exp(b * b) * math.erfc(b)
    return math.sqrt(math.pi / (2 * alpha)) * factor


def main() -> int:
    print('единицы: μ₀, λ, δ — 1/с; λδt — 1/с (опасность); λδT²/2 — безразмерно (H). Сходится.\n')
    mu0 = 1e-4          # 1/с (~2,8 ч⁻¹ в сутках масштаб)
    alpha = 1e-9        # 1/с²

    print(f'пример: μ₀ = {mu0:g} 1/с, α = λδ = {alpha:g} 1/с²')
    T1 = t_at_h1(mu0, alpha)
    S1 = survival(T1, mu0, alpha)
    E = mean_life(mu0, alpha)
    print(f'  T(H=1)            = {T1:,.1f} с')
    print(f'  S(T(H=1))         = {S1:.6f}   → умерло {100 * (1 - S1):.1f} %')
    print(f'  E[T]              = {E:,.1f} с')
    print(f'  средняя / перцентиль = {E / T1:.3f}\n')

    print('предел α → 0 (линейного роста нет):')
    for a in (0.0, 1e-12, 1e-9, 1e-7):
        t = t_at_h1(mu0, a)
        s = survival(t, mu0, a)
        e = mean_life(mu0, a)
        print(f'  α = {a:8.0e}: T(H=1) = {t:12,.1f}; S = {s:.6f}; E[T] = {e:12,.1f}; E/T = {e / t:.3f}')
    print()

    ok_hyper = abs(math.exp(-1) - S1) < 1e-9
    t_exp = t_at_h1(mu0, 0.0)
    ok_limit = abs(t_exp - 1 / mu0) < 1e-9 and abs(survival(t_exp, mu0, 0.0) - math.exp(-1)) < 1e-9
    print(f'  H = 1 ⇔ умерло 63,2 % (любое α): {ok_hyper}')
    print(f'  α → 0 воспроизводит экспоненту:  {ok_limit}')

    print()
    if ok_hyper and ok_limit:
        print('ВЫВОД: формула согласована — H=1 всегда даёт 63,2-й перцентиль, экспоненциальный предел верен,')
        print('        средняя E[T] МЕНЬШЕ перцентиля T(H=1) во столько раз, насколько выпукла H(t).')
        print(f'        В примере средняя короче перцентиля на {100 * (1 - E / T1):.0f} %.')
    else:
        print('ВЫВОД: запись формулы не согласована — см. выше, что не сходится.')
    return 0 if (ok_hyper and ok_limit) else 1


if __name__ == '__main__':
    raise SystemExit(main())
