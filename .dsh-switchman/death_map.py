"""Карта причины смерти по taken при фиксированном dr — точная модель step()."""
import death_scan3 as m


def cause_at(taken, dr, T=200000):
    e, d = m.CAP, 0.0
    for t in range(T):
        e, d = m.step(e, d, m.MAINT, dr, taken)
        if e <= 0:
            return "energy", t
        if d >= 1:
            return "damage", t
    return "alive", T


COLS = (0.0, 0.55, 0.58, 0.59, 0.599, 0.60, 0.65, 0.80, 1.00)
print("maint=0.6  rc=1.5  cap=10  energy0=cap  damage0=0")
print("аналитика: полоса урона = (maint - dr^2*rc, maint]")
print()
hdr = "dr     " + " ".join(f"{c:>9.3f}" for c in COLS)
print(hdr)
print("-" * len(hdr))
for dr in (0.001, 0.01, 0.05, 0.1, 0.2):
    cells = []
    for taken in COLS:
        c, t = cause_at(taken, dr)
        tag = {"energy": "EN", "damage": "DM", "alive": "ok"}[c]
        cells.append(f"{tag}{t}" if t < 100000 else f"{tag}+")
    lo = m.MAINT - dr * dr * m.REPAIR
    print(f"{dr:<6} " + " ".join(f"{x:>9}" for x in cells) + f"   band_lo={lo:.6f}")
print()
print("EN=голод, DM=урон, ok=жив на горизонте; число = шаг смерти")
