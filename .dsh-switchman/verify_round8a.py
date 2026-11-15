"""Решающий тест §D обзора: параметр taken доходит до динамики или нет.

Обзор утверждает, что death_map.py менял income, а resource оставался 0.6,
поэтому все столбцы taken >= maint идентичны. Здесь проверяется, что
death_map.cause_at(taken, dr) передаёт taken как RESOURCE (а income внутри
step берётся дефолтным = income, т.е. ограничение сверху не мешает).

Если параметр доходит, то при taken = 0.65 и 0.80 (dr=0.01) должен быть alive.
Если не доходит — DM, как в таблице.
"""
import death_scan3 as m
import death_map as dm

print("A. Что death_map.cause_at передаёт в step()")
print("   cause_at(taken, dr) -> m.step(e, d, m.MAINT, dr, taken)")
print("   step(energy, damage, income, dr, resource): income=MAINT=0.6, resource=taken")
print()
print("   Значит taken передаётся как RESOURCE, а income жёстко = 0.6.")
print("   Тогда фактическое получение q = min(resource, income) = min(taken, 0.6).")
print("   При taken >= 0.6 все столбцы дают q = 0.6 — параметр мёртв ВЫШЕ 0.6.")
print("   Но НЕ потому, что resource фиксирован: income в вызове равен 0.6.")
print()

print("B. Проверка: q = min(taken, 0.6) при income=0.6")
for taken in (0.55, 0.58, 0.59, 0.599, 0.60, 0.65, 0.80, 1.00):
    print(f"   taken={taken:.3f} -> q={min(taken, 0.6):.3f}")

print()
print("C. Предсказания обзора §D на честном порте (income=1.0, resource=taken)")
print("   dr     taken   исход")
for dr in (0.01, 0.1):
    for tk in (0.60, 0.65, 0.80, 1.00):
        c, t, e, d = m.run(income=1.0, dr=dr, resource=tk, energy0=10.0)
        print(f"   {dr:<6} {tk:.2f}    {c} {t}")

print()
print("D. То же, но с income = MAINT (как в death_map) — параметр мёртв выше 0.6")
for dr in (0.01, 0.1):
    for tk in (0.60, 0.65, 0.80, 1.00):
        c, t, e, d = m.run(income=0.6, dr=dr, resource=tk, energy0=10.0)
        print(f"   {dr:<6} {tk:.2f}    {c} {t}")
