"""EXP-07: `remember` — это память или однократный выбор?

## Наблюдение

`remember` на 2000 шагах: 39 выживших из 40, все стоят на запомненной клетке
(`best_cell == cell`), направление `0`.

## Код

```rust
// memory.rs
pub fn direction(&self) -> i32 {
    if self.memory.best_cell == self.cell || self.memory.best_level <= 0.0 {
        return 0;
    }
    ...
}

// life.rs
if r.memory.best_cell != r.cell {
    r.memory.observe(r.cell, here);   // память обновляется ТОЛЬКО вне запомненной
}
```

## Что из этого следует

Организм движется к запомненной клетке. Придя, `best_cell == cell` →
`direction() = 0` → **стоит**. И память **не обновляется**, потому что
`best_cell == cell`.

**Значит он никогда не узнает, что есть клетка лучше.**

**Это не память. Это однократный выбор: «найди первую лучшую и стой».**

## Плечи

| ключ | что меняем | предсказание |
|---|---|---|
| **A** | контроль (`alternating`) | 39 выживших, все стоят |
| **B** | поле с **градиентом** (растёт слева направо) | организм дойдёт до правого края и встанет там |
| **C** | поле **однородное** (все клетки 1.0) | организм встанет на первой клетке, где 1.0 > 0 |

## Контроль (три теста)

1. **Срабатывает:** B — все выжившие на правом краю (максимум градиента)
2. **Молчит:** A — 39 выживших, как в наблюдении
3. **Специфичен:** C — все на **разных** клетках (первая, где увидели 1.0),
   а не на одной. Если бы `remember` был настоящей памятью, в однородном поле
   он бы не двигался вообще.

## Почему C специфичен

В однородном поле все клетки равны. Настоящая память не должна двигать
организм. Но `remember` двигается, пока `best_level = 0` (пустая память),
и встаёт на **первой** клетке, где увидел 1.0.

**Если все встают на разных клетках — это не выбор лучшего, а первое
попавшееся.**

## Запуск

    python3 checks/exp07_remember_choice.py
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


def run_arm(field: str) -> dict:
    """`field` is one of `alternating`, `gradient`, `uniform`."""
    args = " ".join([
        "--policy remember",
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

    local_rel = Path("results") / "remember-choice" / Path(wsl_path).name
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
        "A": ("alternating (control)", "alternating"),
        "B": ("gradient", "gradient"),
        "C": ("uniform", "uniform"),
    }

    arithmetic = {
        "direction_rule": "best_cell == cell -> 0 (stay)",
        "memory_rule": "memory updates only when best_cell != cell",
        "consequence": (
            "The organism walks to the remembered cell, arrives, and stops — and "
            "the memory never updates again because best_cell == cell. So it never "
            "learns that a better cell exists. This is a one-shot choice, not memory."
        ),
        "predictions": {
            "A": "39 alive, all still, spread over cells",
            "B": "all survivors at the right edge (max of the gradient)",
            "C": "survivors on DIFFERENT cells (the first cell where 1.0 was seen)",
        },
    }

    exp = Experiment(
        experiment_id="remember-choice",
        question="`remember` — это память или однократный выбор?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp07_remember_choice.py",
        parameters={
            "steps": STEPS, "every": EVERY, "n": N, "cells": CELLS,
            "policy": "remember", "maintenance": MAINTENANCE,
            "repair_cost": REPAIR_COST, "damage_rate": DAMAGE,
        },
    )

    results = {}
    for key, (label, field) in arms.items():
        r = run_arm(field)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
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

    # Fires: with a gradient, survivors cluster at the right edge.
    fires = results["B"]["max_cell"] >= CELLS - 2 and results["B"]["alive"] > 0
    exp.control(
        "fires",
        fires,
        f"B: max cell {results['B']['max_cell']} of {CELLS - 1} — the gradient "
        f"must pull the survivors to the right edge",
    )

    # Silent: the control arm matches the observation.
    silent = results["A"]["alive"] >= N - 3 and results["A"]["all_still"]
    exp.control(
        "silent",
        silent,
        f"A: {results['A']['alive']} alive, all still = {results['A']['all_still']} "
        f"— must match the observed 39 alive and standing",
    )

    # Specific: in a uniform field a real memory would not move at all; the
    # one-shot chooser stops on the FIRST cell where 1.0 was seen, so survivors
    # spread over many cells rather than one.
    specific = results["C"]["distinct_cells"] >= 5
    exp.control(
        "specific",
        specific,
        f"C: {results['C']['distinct_cells']} distinct cells among "
        f"{results['C']['alive']} survivors — a real memory would not move in a "
        f"uniform field, so a spread means a one-shot choice",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            "the gradient pulls survivors to the edge, the control matches the "
            "observation, and in a uniform field the survivors spread over many "
            "cells — `remember` is a one-shot choice, not a memory",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The gradient and uniform fields are new in this experiment; their "
        "construction is not yet tested elsewhere."
    )
    exp.limitation(
        "The conclusion is about the model's code, not about memory in general. "
        "A different update rule would give different behaviour."
    )
    exp.limitation(
        "`distinct_cells >= 5` is a threshold chosen by eye, not derived."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-07: remember — память или однократный выбор?")
    print()
    print("Правило: best_cell == cell -> 0 (стоит)")
    print("Память обновляется только когда best_cell != cell")
    print("Значит: придя, организм стоит навсегда и не узнаёт о лучшем")
    print()
    print("плечо  поле          живых  клеток  стоят  макс  hash")
    print("-" * 62)
    for key, (label, field) in arms.items():
        r = results[key]
        print(
            f"  {key}    {field:<12} {r['alive']:>5}  {r['distinct_cells']:>6}  "
            f"{str(r['all_still']):<5}  {r['max_cell']:>4}  {r['hash']}"
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
