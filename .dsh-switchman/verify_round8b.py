"""§F обзора: скан по σ = (q - maint)/(dr*rc) вместо доли ячеек сетки.

Обзор прав: критерий «доля ячеек сетки > 5%» зависит от выравнивания сетки.
Здесь: для каждого dr найти интервал q, где исход DM, и выразить его в σ.
Режим 1 (бессмертие) = σ >= 1, режим 2 (DM) = 0 <= σ < 1.
"""
import death_scan3 as m

MAINT, RC = 0.6, 1.5


def outcome(q, dr, T=200000):
    e, d = 10.0, 0.0
    for t in range(1, T + 1):
        e = e + q - MAINT
        d = min(d + dr, 1.0)
        if d > 0.0 and d * RC < e:
            e -= d * RC
            d = 0.0
        e = max(0.0, min(e, 10.0))
        if e <= 0.0:
            return "EN", t
        if d >= 1.0:
            return "DM", t
    return "alive", T


print("По σ = (q - maint)/(dr*rc), горизонт 200000")
print("dr        p=dr*rc   DM-интервал по q        по σ            σ-ширина")
for dr in (0.001, 0.01, 0.05, 0.1, 0.2):
    p = dr * RC
    lo, hi = MAINT, MAINT + 2 * p
    # ищем верхнюю границу DM бисекцией
    a, b = MAINT, MAINT + 2 * p
    for _ in range(50):
        mid = (a + b) / 2
        if outcome(mid, dr)[0] == "DM":
            a = mid
        else:
            b = mid
    q_hi = a
    s_lo = (MAINT - MAINT) / p
    s_hi = (q_hi - MAINT) / p
    print(f"  {dr:<8} {p:.5f}   [{MAINT:.4f}, {q_hi:.6f})   "
          f"[{s_lo:.3f}, {s_hi:.3f})     {s_hi - s_lo:.3f}")

print()
print("Проверка режима 1: σ >= 1 должен давать alive при любом dr")
for dr in (0.01, 0.1, 0.2):
    p = dr * RC
    for sigma in (1.0, 1.5, 2.0):
        q = MAINT + sigma * p
        print(f"  dr={dr:<5} σ={sigma:<4} q={q:.5f} -> {outcome(q, dr)[0]}")

print()
print("Проверка рваного края под maint: σ < 0")
for dr in (0.05, 0.1, 0.2):
    p = dr * RC
    row = []
    for sigma in (-1.0, -0.5, -0.2, -0.1, -0.05, -0.01):
        q = MAINT + sigma * p
        row.append(f"σ={sigma:+.2f}:{outcome(q, dr)[0]}")
    print(f"  dr={dr:<5} " + "  ".join(row))
