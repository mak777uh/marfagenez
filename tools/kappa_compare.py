"""Анализ 1.3: различает ли κ-схема и абсолютную поддержку постановка на бумаге?

Числа — из `core/src/organism.rs` (константы по умолчанию) и закона поддержания `income − maintenance ≥ dr·rc`.
Скрипт ничего не симулирует: он решает неравенство и показывает, где границы двух схем совпадают.
"""

from __future__ import annotations

INCOME = 1.0
MAINT = 0.6
REPAIR = 1.5
DAMAGE = 0.01

DRC = DAMAGE * REPAIR


def absolute_boundary() -> float:
    """Граница по доходу: income* = maintenance + dr*rc."""
    return MAINT + DRC


def kappa_boundary(kappa: float) -> float:
    """Граница, если поддержание задано долей: (1-kappa)*income = dr*rc."""
    return DRC / (1.0 - kappa)


def kappa_from_defaults() -> float:
    """Эндогенная κ: доля дохода, уходящая на поддержание при доходе по умолчанию."""
    return MAINT / INCOME


def rho_s(income: float) -> float:
    return DRC / (income - MAINT)


def rho_s_kappa(income: float, kappa: float) -> float:
    return DRC / ((1.0 - kappa) * income)


print(f"dr*rc = {DRC:g}")
print(f"absolute boundary: income* = {absolute_boundary():g}")
print(f"kappa from defaults: {kappa_from_defaults():g}")
print(f"kappa boundary at kappa=0.5: {kappa_boundary(0.5):g}")
print(f"kappa boundary at kappa=0.6: {kappa_boundary(0.6):g}")
print()

# эндогенная κ: обе величины совпадают тождественно
k0 = kappa_from_defaults()
print("эндогенная κ: rho_s и rho_s^κ при income от 0.7 до 2.0")
print(f"{'income':>8} {'rho_s':>10} {'rho_s^k':>10} {'разница':>10}")
for inc in (0.7, 0.8, 1.0, 1.5, 2.0):
    a = rho_s(inc)
    kk = MAINT / inc
    b = rho_s_kappa(inc, kk)
    print(f"{inc:>8.2f} {a:>10.4f} {b:>10.4f} {abs(a-b):>10.2e}")

print()
print("экзогенная κ = 0.5: граница по доходу")
for inc in (0.02, 0.03, 0.05, 0.1, 0.615, 1.0):
    abs_sustains = inc - MAINT >= DRC
    kap_sustains = (1.0 - 0.5) * inc >= DRC
    print(f"  income {inc:>6} абсолютная: {str(abs_sustains):>5}  κ-схема: {str(kap_sustains):>5}")
