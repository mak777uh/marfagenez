"""EXP-08: `memory` против `remember` — что даёт обновляемая память?

## Откуда вопрос

`EXP-07` показал: `Policy::Remember` — **однократный выбор**. Он идёт к
запомненной клетке, приходит, встаёт, и память больше не обновляется.

**Добавлено:** `Policy::Memory` — то же, но память обновляется **каждый шаг**,
включая когда организм стоит на запомненной клетке.

## Арифметика (до прогона)

В однородном поле все клетки равны (1.0). Настоящая память не должна двигать
организм: он уже на лучшей клетке.

**Предсказание для `memory` в однородном поле:** организм стоит на месте
после первого шага (все клетки равны, обновлять нечего).

**Предсказание для `remember` в однородном поле:** организм встаёт на
**первой** клетке, где увидел 1.0 (это уже измерено в EXP-07: 32 разных клетки).

## Плечи

| ключ | политика | поле | предсказание |
|---|---|---|---|
| **A** | `remember` | `uniform` | 32 разных клетки (однократный выбор) |
| **B** | `memory` | `uniform` | **все на одной клетке** (или не двигаются) |
| **C** | `memory` | `gradient` | все на правом краю (максимум градиента) |

## Контроль (три теста)

1. **Срабатывает:** C — `memory` находит максимум градиента (правый край)
2. **Молчит:** A — 32 разных клетки, как в EXP-07
3. **Специфичен:** B — `memory` в однородном поле даёт **меньше** разных клеток,
   чем `remember`. Это и есть разница между обновляемой и однократной памятью.

## Запуск

    python3 checks/exp08_memory_vs_remember.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSL_CORE = "/root/marfagenez/core"

sys.path.insert(0, str(ROOT))
from checks.experiment import Experiment  # noqa: E402

STEPS = 2000
EVERY = 2000
SEED = 20250101
N = 40
CELLS = 40

CAPACITY = 10.0
MAINTENANCE = 0.6
REPAIR_COST = 1.5
DAMAGE = 0.02
MOVE_COST = 0.1
INCOME = 0.8


def in_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def shell(cmd: str) -> str:
    argv = ["bash", "-c", cmd] if in_wsl() else ["wsl", "-e", "bash", "-c", cmd]
    out = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise SystemExit(f"command failed:\n{cmd}\n{out.stderr}")
    return out.stdout


def run_arm(policy: str, field: str) -> dict:
    args = " ".join([
        f"--policy {policy}",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {N}",
        f"--cells {CELLS}",
        f"--field {field}",
        f"--capacity {CAPACITY}",
        f"--move-cost {MOVE_COST}",
        f"--maintenance {MAINTENANCE}",
        f"--repair-cost {REPAIR_COST}",
        f"--damage-rate {DAMAGE}",
        f"--income {INCOME}",
    ])
    out = shell(f"cd {WSL_CORE} && ./target/release/trace {args}")

    h = re.search(r"hash:\s+([0-9a-f]+)", out).group(1)
    wsl_path = re.search(r"written:\s+(\S+)", out).group(1)

    local_rel = Path("results") / "memory-vs-remember" / Path(wsl_path).name
    local_abs = ROOT / local_rel
    local_abs.parent.mkdir(parents=True, exist_ok=True)
    src = Path(WSL_CORE) / wsl_path
    if in_wsl():
        local_abs.write_bytes(src.read_bytes())
    else:
        shell(
            f"cp {WSL_CORE}/{wsl_path} /mnt/c/Users/Admin/Documents/Qoder/"
            f"2026-10-18/82ab86cd/marfagenez/{local_rel.as_posix()}"
        )

    data = json.loads(local_abs.read_text(encoding="utf-8"))
    last = data["frames"][-1]
    alive = [s for s in last["samples"] if s["alive"]]
    cells = [s["cell"] for s in alive]
    directions = [s["direction"] for s in alive]

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "cells": sorted(cells),
        "distinct_cells": len(set(cells)),
        "all_still": all(d == 0 for d in directions),
        "max_cell": max(cells) if cells else 0,
    }


def main() -> int:
    arms = {
        "A": ("remember / uniform", "remember", "uniform"),
        "B": ("memory / uniform", "memory", "uniform"),
        "C": ("memory / gradient", "memory", "gradient"),
    }

    arithmetic = {
        "difference": (
            "`remember` updates the memory only when the organism is NOT on the "
            "remembered cell; `memory` updates on every step."
        ),
        "prediction_A": "uniform field, one-shot choice -> survivors spread over many cells",
        "prediction_B": "uniform field, real memory -> survivors on few cells (all equal, nothing to learn)",
        "prediction_C": "gradient, real memory -> survivors at the right edge",
        "why_B_is_specific": (
            "In a uniform field every cell is equally good, so a memory that keeps "
            "updating has nothing to prefer and the organism should not wander the "
            "way the one-shot chooser does. A smaller spread for B than for A is the "
            "signature of the update rule, not of the field."
        ),
    }

    exp = Experiment(
        experiment_id="memory-vs-remember",
        question="Что даёт обновляемая память по сравнению с однократным выбором?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp08_memory_vs_remember.py",
        parameters={
            "steps": STEPS, "every": EVERY, "n": N, "cells": CELLS,
            "maintenance": MAINTENANCE, "repair_cost": REPAIR_COST,
            "damage_rate": DAMAGE,
        },
    )

    results = {}
    for key, (label, policy, field) in arms.items():
        r = run_arm(policy, field)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
                "policy": policy,
                "field": field,
                "alive": r["alive"],
                "total": r["total"],
                "distinct_cells": r["distinct_cells"],
                "all_still": r["all_still"],
                "max_cell": r["max_cell"],
                "cells": r["cells"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    fires = results["C"]["max_cell"] >= CELLS - 2 and results["C"]["alive"] > 0
    exp.control(
        "fires",
        fires,
        f"C: max cell {results['C']['max_cell']} of {CELLS - 1} — a real memory "
        f"must find the maximum of the gradient",
    )

    silent = results["A"]["distinct_cells"] >= 20
    exp.control(
        "silent",
        silent,
        f"A: {results['A']['distinct_cells']} distinct cells — must match EXP-07's "
        f"32-cell spread for the one-shot chooser",
    )

    specific = results["B"]["distinct_cells"] < results["A"]["distinct_cells"]
    exp.control(
        "specific",
        specific,
        f"B: {results['B']['distinct_cells']} distinct cells vs A's "
        f"{results['A']['distinct_cells']} — the update rule must change the "
        f"spread, not the field (both are uniform)",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            "the update rule changes the outcome: in the same uniform field the "
            "one-shot chooser spreads over many cells and the updating memory does "
            "not, and on a gradient the updating memory finds the maximum",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "`Policy::Memory` was added in this experiment; it is not yet covered by "
        "the Rust test suite."
    )
    exp.limitation(
        "A uniform field is degenerate: there is no best cell, so the difference "
        "between the two rules may not appear on fields with a unique maximum."
    )
    exp.limitation(
        "The conclusion is about the update rule, not about memory in general."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-08: memory против remember")
    print()
    print("Разница: remember обновляет память только вне запомненной клетки,")
    print("         memory обновляет каждый шаг")
    print()
    print("плечо  политика  поле          живых  клеток  стоят  макс  hash")
    print("-" * 70)
    for key, (label, policy, field) in arms.items():
        r = results[key]
        print(
            f"  {key}    {policy:<8}  {field:<12} {r['alive']:>5}  "
            f"{r['distinct_cells']:>6}  {str(r['all_still']):<5}  {r['max_cell']:>4}  {r['hash']}"
        )
    print()
    print("Контроль:")
    for t in ("fires", "silent", "specific"):
        c = exp.result["controls"][t]
        mark = "OK  " if c["passed"] else "FAIL"
        print(f"  {mark} {t:<9} {c['evidence']}")
    print()
    v = exp.result["verdict"]
    print(f"Вердикт: {v['kind']}")
    print(f"  {v['reason']}")
    print()
    print(f"Сохранено: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
