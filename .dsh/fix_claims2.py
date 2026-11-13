import os
os.chdir("/root/marfagenez")
P = "docs/CLAIMS.md"
s = open(P, encoding="utf-8").read()
old = "## Что доказано (уровень A)\n\n### Lean"
new = """## Что доказано (уровень A)

> **Поправка 2026-11-13, вечер.** Порядок шага клетки был записан неверно:
> стояло `c + (M − c)·r − t` (сначала прирост, потом трата), должно быть
> `(c − t) + (M − (c − t))·r` (сначала трата, потом прирост). Равновесие
> поэтому не `M − t/r`, а **`c* = M + t − t/r = M − t·(1−r)/r`**.
> Исправлено и пересобрано в `Field.lean`, `Convergence.lean`, `Capacity.lean`,
> `Regimes.lean`. Все числа уровня C в этом файле, полученные при старом
> порядке (потолок `C = 80`, `E* = E_max − COST`, `c* = 1.8`), **отозваны** —
> см. `docs/FINDING-140-the-step-order-was-wrong.md`. Проверка:
> `cd laws && lake build` → 18328 jobs, 0 errors.

### Lean"""
assert old in s
s = s.replace(old, new, 1)
open(P, "w", encoding="utf-8").write(s)
print("ok")
