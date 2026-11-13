import os, subprocess

os.chdir("/root/marfagenez")
P = "docs/CLAIMS.md"
src = open(P, encoding="utf-8").read()

def rep(old, new, count=1):
    global src
    assert old in src, "NOT FOUND: " + old[:80]
    src = src.replace(old, new, count)

rep("**Дата:** 2026-11-13 (числа пересчитаны командами)",
    "**Дата:** 2026-11-13 (числа пересчитаны командами; формула клетки исправлена — см. ниже)")

rep("### Lean — две библиотеки, 308 теорем и лемм, 0 sorry",
    "### Lean — две библиотеки, 317 теорем и лемм, 0 живых sorry")

rep("| `Medium` — модель клетки | 55 | **281** | **0** | `lake build` |",
    "| `Medium` — модель клетки | 56 | **290** | **0** | `lake build` |")

rep("| `Legacy` — стена/гонка/наклон | 9 | 27 | **0** | `lake build Legacy` |",
    "| `Legacy` — стена/гонка/наклон | 8 | 27 | **0** | `lake build Legacy` |")

rep("""grep -rn 'sorry' Medium/*.lean | wc -l   # 0""",
    """grep -rn 'sorry' Medium/*.lean | wc -l   # 2 — оба в прозе docstring FoldPeriodic.lean:6,12""")

open(P, "w", encoding="utf-8").write(src)
print("patched", P)
