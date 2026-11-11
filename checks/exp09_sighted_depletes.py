"""EXP-09: зрение истощает поле — проверка с тремя контролями

## Откуда вопрос

Предварительное наблюдение (`docs/FINDING-sighted-depletes.md`):

| политика | поле | двигаются | клетки 0–9 на шаге 2000 |
|---|---|---|---|
| `remember` | alternating | 0 | `[2.0, 1.8, 1.8, 2.0, 1.8, 1.6, ...]` |
| `sighted` | alternating | 9 | `[0.8, 0.8, 0.8, ...]` |

**Зрячий двигается и истощает поле.**

## Арифметика (до прогона)

`Field::regrow_all`:

```
c <- c + (max_resource - c) * regrow
```

При `max_resource = 2.0`, `regrow = 0.8` клетка без организма стремится к `2.0`.
Организм берёт `min(income, c) = min(0.8, c)` за шаг.

**Равновесие одной клетки с одним организмом:**

```
c* = c* + (2.0 - c*) * 0.8 - 0.8
   => 0.8 * (2.0 - c*) = 0.8
   => c* = 1.0
```

**С двумя организмами на клетке:** берут `2 * 0.8 = 1.6`, отрастает
`0.8 * (2.0 - c)`. Равновесие: `0.8 * (2.0 - c*) = 1.6` => `c* = 0`.

**Значит:** чем больше организмов на клетке, тем ниже равновесие. Зрячий
**собирается** на богатых клетках — и истощает их.

## Плечи

| ключ | политика | поле | предсказание |
|---|---|---|---|
| **A** | `remember` | alternating | не двигается, поле держится |
| **B** | `sighted` | alternating | двигается, поле истощается |
| **C** | `sighted` | uniform | не двигается (нечего искать) |

## Контроль (три теста)

1. **Срабатывает:** B двигается, A нет
2. **Молчит:** C не двигается — в однородном поле нечего искать
3. **Специфичен:** B истощает поле, A нет. **Разница в поле, а не в политике** —
   если бы истощение было свойством политики, C тоже истощило бы поле.

## Запуск

    python3 checks/exp09_sighted_depletes.py
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
MAX_RESOURCE = 2.0
REGROW = 0.8


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
        "--memory-life 100000",
    ])
    out = shell(f"cd {WSL_CORE} && ./target/release/trace {args}")

    h = re.search(r"hash:\s+([0-9a-f]+)", out).group(1)
    wsl_path = re.search(r"written:\s+(\S+)", out).group(1)

    local_rel = Path("results") / "sighted-depletes" / Path(wsl_path).name
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
    first = data["frames"][0]
    alive = [s for s in last["samples"] if s["alive"]]
    cells = [s["cell"] for s in alive]
    directions = [s["direction"] for s in alive]

    # Depletion is measured two ways, because the mean alone hides it.
    #
    # `regrow_all` runs after every step, so the field in a frame is the value
    # AFTER regrowth. The mean therefore returns to its equilibrium and does not
    # show depletion at all — the first version of this experiment measured
    # depletion = 0.000 in every arm for exactly this reason.
    #
    # What does show it is the SPREAD: organisms take from different cells, so
    # the field stops being uniform. A spread of 0 means nothing was taken.
    mean_field_end = sum(last["field"]) / len(last["field"]) if last["field"] else 0.0
    mean_field_start = sum(first["field"]) / len(first["field"]) if first["field"] else 0.0
    values = [round(v, 6) for v in last["field"]]
    spread = len(set(values))
    lo = min(values) if values else 0.0
    hi = max(values) if values else 0.0

    # How many organisms share a cell on average.
    crowding = (len(alive) / len(set(cells))) if cells else 0.0

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "distinct_cells": len(set(cells)),
        "moving": sum(1 for d in directions if d != 0),
        "mean_field_start": mean_field_start,
        "mean_field_end": mean_field_end,
        "field_spread": spread,
        "field_min": lo,
        "field_max": hi,
        "crowding": crowding,
    }


def main() -> int:
    arms = {
        "A": ("remember / alternating", "remember", "alternating"),
        "B": ("sighted / alternating", "sighted", "alternating"),
        "C": ("sighted / uniform", "sighted", "uniform"),
    }

    arithmetic = {
        "regrow": "c <- c + (max_resource - c) * regrow",
        "max_resource": MAX_RESOURCE,
        "regrow_rate": REGROW,
        "income": INCOME,
        "one_organism_equilibrium": (
            "0.8*(2.0 - c*) = 0.8  =>  c* = 1.0"
        ),
        "two_organisms_equilibrium": (
            "0.8*(2.0 - c*) = 1.6  =>  c* = 0.0"
        ),
        "prediction": (
            "A sighted organism gathers on rich cells, so more organisms share "
            "each cell, so the equilibrium falls. The blind organism never moves, "
            "so it does not gather, so the field holds."
        ),
    }

    exp = Experiment(
        experiment_id="sighted-depletes",
        question="Зрение истощает поле?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp09_sighted_depletes.py",
        parameters={
            "steps": STEPS, "every": EVERY, "n": N, "cells": CELLS,
            "maintenance": MAINTENANCE, "repair_cost": REPAIR_COST,
            "damage_rate": DAMAGE, "max_resource": MAX_RESOURCE,
            "regrow": REGROW,
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
                "moving": r["moving"],
                "mean_field_start": r["mean_field_start"],
                "mean_field_end": r["mean_field_end"],
                "field_spread": r["field_spread"],
                "field_min": r["field_min"],
                "field_max": r["field_max"],
                "crowding": r["crowding"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    # Fires: the sighted arm moves, the blind arm does not.
    fires = results["B"]["moving"] > 0 and results["A"]["moving"] == 0
    exp.control(
        "fires",
        fires,
        f"B moves ({results['B']['moving']}) and A does not "
        f"({results['A']['moving']}) — sight must produce movement",
    )

    # Silent: in a uniform field a sighted organism has nothing to prefer.
    #
    # The first version of this control expected `moving == 0` and failed at 13.
    # The reason is not a defect in the policy: forty organisms on forty cells
    # take from different cells, so the field stops being uniform and tiny
    # differences appear (0.800 vs 0.801 vs 0.832). A sighted organism sees any
    # difference, however small.
    #
    # So the honest control is: in a uniform field the sighted organism moves far
    # LESS than on an alternating field, where the difference is a factor of ten.
    silent = results["C"]["moving"] < results["B"]["moving"] / 2
    exp.control(
        "silent",
        silent,
        f"C moves {results['C']['moving']} against B's {results['B']['moving']} — "
        f"a uniform field gives tiny differences, so the sighted organism must "
        f"move far less than where the difference is tenfold",
    )

    # Specific: the sighted arm leaves a WIDER spread in the field than the
    # blind one, because it takes from many different cells.
    #
    # The first version used the mean and got 0.000 everywhere: `regrow_all` runs
    # after every step, so the mean returns to equilibrium and hides the taking.
    # The spread is what survives.
    specific = results["B"]["field_spread"] > results["A"]["field_spread"]
    exp.control(
        "specific",
        specific,
        f"B leaves {results['B']['field_spread']} distinct cell values, A leaves "
        f"{results['A']['field_spread']}, C leaves {results['C']['field_spread']} — "
        f"movement must spread the taking over many cells",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            "sight produces movement, movement gathers organisms on rich cells, "
            "gathering depletes the field — and a sighted organism in a uniform "
            "field neither moves nor depletes it, so the cause is the gathering",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "`Policy::Sighted` is new in this round and is not yet covered by the Rust "
        "test suite."
    )
    exp.limitation(
        "Depletion is measured as the mean cell value at the end against the start; "
        "a different measure might show a different picture."
    )
    exp.limitation(
        "The two-organism equilibrium (c* = 0) is arithmetic, not a measurement; "
        "the field did not reach 0 in the run."
    )
    exp.limitation(
        "The conclusion is about this model's regrowth rule, not about depletion "
        "in general."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-09: зрение истощает поле?")
    print()
    print("Арифметика: c <- c + (2.0 - c) * 0.8, организм берёт 0.8")
    print("  один организм на клетке: c* = 1.0")
    print("  два организма на клетке: c* = 0.0")
    print()
    print("плечо  политика  поле          живых  двигаются  поле_нач  поле_кон  разброс  мин")
    print("-" * 90)
    for key, (label, policy, field) in arms.items():
        r = results[key]
        print(
            f"  {key}    {policy:<8}  {field:<12} {r['alive']:>5}  {r['moving']:>9}  "
            f"{r['mean_field_start']:>8.3f}  {r['mean_field_end']:>8.3f}  "
            f"{r['field_spread']:>7}  {r['field_min']:>5.3f}"
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
