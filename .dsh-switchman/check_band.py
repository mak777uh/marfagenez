"""Проверка аналитики шестого круга против ТОЧНОЙ модели step().

Внешний обзор утверждает:
  (1) полоса смерти от урона по taken = (maint - dr^2*rc, maint], ширина dr^2*rc;
  (2) сетка шага 0.05 даёт 3 попадания из 63 = 4.76% < 5% => passed недостижим;
  (3) T=5000 недостаточно при dr=0.001.

Проверяем на модели death_scan3 (точная копия core/src/organism.rs::step).
"""
import death_scan3 as m

print("=" * 78)
print("(1) ТОЧНАЯ граница полосы: бисекция по taken при фиксированном dr")
print("=" * 78)
print(f"{'dr':>6} {'аналит.низ':>13} {'бисекция':>13} {'ширина':>12} {'dr^2*rc':>12}")
for dr in (0.001, 0.01, 0.05, 0.1, 0.2):
    # ищем наибольший taken, при котором смерть ещё от урона
    lo, hi = 0.0, m.MAINT
    for _ in range(60):
        mid = (lo + hi) / 2
        cause, t, e, d = m.run(m.MAINT, dr, resource=mid, energy0=m.CAP)
        if cause == "damage":
            lo = mid
        else:
            hi = mid
    print(f"{dr:>6.3f} {m.MAINT - dr*dr*m.REPAIR:>13.9f} {lo:>13.9f} "
          f"{m.MAINT - lo:>12.9f} {dr*dr*m.REPAIR:>12.9f}")

print()
print("=" * 78)
print("(2) СЕТКА ПРОТОКОЛА: taken in {0.00,0.05,...,1.00} x dr in {0.001,0.01,0.1}")
print("=" * 78)
hits = 0
total = 0
for dr in (0.001, 0.01, 0.1):
    row = []
    for k in range(21):
        taken = k * 0.05
        total += 1
        cause, t, e, d = m.run(m.MAINT, dr, resource=taken, energy0=m.CAP)
        if cause == "damage":
            hits += 1
            row.append(f"{taken:.2f}:damage@{t}")
    print(f"  dr={dr:<6} попадания: {row or 'нет'}")
print(f"  ИТОГО попаданий {hits} из {total} = {100*hits/total:.2f}%  (критерий: >5%)")

print()
print("=" * 78)
print("(3) ГОРИЗОНТ: сколько шагов нужно при dr=0.001 и taken=maint")
print("=" * 78)
for dr in (0.001, 0.01, 0.1):
    cause, t, e, d = m.run(m.MAINT, dr, resource=m.MAINT, energy0=m.CAP)
    print(f"  dr={dr:<6} смерть от {cause} на шаге {t} (горизонт 5000)")
