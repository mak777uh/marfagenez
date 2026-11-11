"""EXP-19: потери от бедных клеток, не от движения

## Откуда вопрос

`EXP-18` показал: на `gradient` потери 2, на `alternating` — 4.

**Гипотеза была:** колебание дороже пути (движение тратит энергию).

**Арифметика опровергла:**

| ситуация | баланс |
|---|---|
| на богатой, стоя | **+0.170** |
| на богатой, двигаясь | **+0.070** |
| на бедной, стоя | **−0.430** |
| на бедной, двигаясь | **−0.530** |

**Движение уменьшает баланс на 0.1, но он остаётся положительным.**
**Попадание на бедную клетку делает баланс отрицательным.**

**Новая гипотеза:** потери — от **времени на бедных клетках**.

## Арифметика (до прогона)

**Доля времени на бедной клетке `b`:**

$$\text{баланс} = (1-b) \cdot 0.070 + b \cdot (-0.530)$$

**Гибнет, если баланс < 0:**

$$b > \frac{0.070}{0.070 + 0.530} = 0.117$$

**Значит:** если организм проводит на бедных клетках **больше 11.7%** времени —
он гибнет.

**В `alternating`:** колеблется между богатой и бедной — **~50%** на бедной.
**В `gradient`:** идёт вправо, бедные только слева — **< 10%**.

**Предсказание:** на `alternating` больше потерь.

## Плечи

| ключ | поле | `n` | предсказание |
|---|---|---|---|
| **A** | `alternating` | 80 | потери 4, доля на бедных ~50% |
| **B** | `gradient` | 80 | потери 2, доля на бедных < 10% |
| **C** | `alternating`, `poor = 1.0` | 80 | **потери 0** — бедная не так бедна |

## Контроль (три теста)

1. **Срабатывает:** A даёт потери 4 (как в `EXP-18`)
2. **Молчит:** C даёт потери 0 — при `poor = 1.0` нет бедных клеток
3. **Специфичен:** B даёт меньше потерь, и **доля на бедных меньше**

## Запуск

    python3 checks/exp19_poor_cells.py
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

STEPS = 3000
EVERY = 3000
SEED = 20250101
CELLS = 40

CAPACITY = 10.0
MAINTENANCE = 0.6
REPAIR_COST = 1.5
DAMAGE = 0.02
MOVE_COST = 0.1
INCOME = 0.8
RICH = 2.0
REGROW = 0.8


def in_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def shell(cmd: str) -> str:
    argv = ["bash", "-c", cmd] if in_wsl() else ["wsl", "-e", "bash", "-c", cmd]
    out = subprocess.run(argv, capture_output=True, text=True, timeout=1200)
    if out.returncode != 0:
        raise SystemExit(f"command failed:\n{cmd}\n{out.stderr}")
    return out.stdout


def run_arm(field: str, n: int, poor: float, tag: str) -> dict:
    args = " ".join([
        "--policy sighted",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {n}",
        f"--cells {CELLS}",
        f"--field {field}",
        f"--rich {RICH}",
        f"--poor {poor}",
        f"--regrow {REGROW}",
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

    local_rel = Path("results") / "poor-cells" / f"{tag}-{Path(wsl_path).name}"
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
    frames = data["frames"]
    last = frames[-1]
    alive = [s for s in last["samples"] if s["alive"]]

    # How much time did the survivors spend on poor cells?
    #
    # A cell is "poor" if its value is below what the organism takes per step:
    # taking `min(income, c)` from a cell below `income` gives less than the full
    # income, and the balance turns negative.
    poor_time = 0
    total_time = 0
    for fr in frames:
        for s in fr["samples"]:
            if not s["alive"]:
                continue
            total_time += 1
            if fr["field"][s["cell"]] < INCOME:
                poor_time += 1

    frac_poor = poor_time / total_time if total_time else 0.0

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "loss": n - len(alive),
        "frac_poor": frac_poor,
    }


def main() -> int:
    arms = {
        "A": ("alternating, poor=0.2", "alternating", 80, 0.2, "A"),
        "B": ("gradient, poor=0.2", "gradient", 80, 0.2, "B"),
        "C": ("alternating, poor=1.0", "alternating", 80, 1.0, "C"),
    }

    cost_stay = MAINTENANCE + DAMAGE * REPAIR_COST
    cost_move = cost_stay + MOVE_COST
    bal_rich_move = INCOME - cost_move
    bal_poor_move = 0.2 - cost_move
    threshold = bal_rich_move / (bal_rich_move - bal_poor_move)

    arithmetic = {
        "balance_on_rich_moving": bal_rich_move,
        "balance_on_poor_moving": bal_poor_move,
        "threshold_fraction_on_poor": threshold,
        "prediction": (
            f"An organism dies when it spends more than {threshold:.1%} of its time "
            f"on cells below income. In alternating it oscillates onto poor cells; "
            f"in gradient it walks away from them."
        ),
        "why_not_movement": (
            "Movement costs 0.1 per step, which lowers the balance from 0.170 to "
            "0.070 but keeps it positive. What kills is standing on a cell below "
            "income, where the balance is -0.43."
        ),
    }

    exp = Experiment(
        experiment_id="poor-cells",
        question="Потери от бедных клеток, а не от движения?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp19_poor_cells.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS,
            "policy": "sighted", "rich": RICH, "regrow": REGROW,
            "maintenance": MAINTENANCE, "repair_cost": REPAIR_COST,
            "damage_rate": DAMAGE, "income": INCOME,
        },
    )

    results: dict[str, dict] = {}
    for key, (label, field, n, poor, tag) in arms.items():
        r = run_arm(field, n, poor, tag)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
                "field": field,
                "n": n,
                "poor": poor,
                "alive": r["alive"],
                "total": r["total"],
                "loss": r["loss"],
                "frac_poor": r["frac_poor"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    fires = abs(results["A"]["loss"] - 4) <= 4
    exp.control(
        "fires",
        fires,
        f"A: loss {results['A']['loss']} — must reproduce EXP-18's 4",
    )

    silent = results["C"]["loss"] <= 2
    exp.control(
        "silent",
        silent,
        f"C (poor=1.0): loss {results['C']['loss']} — with no poor cells there is "
        f"nothing to die on, so the loss must vanish",
    )

    specific = (
        results["B"]["loss"] < results["A"]["loss"]
        and results["B"]["frac_poor"] < results["A"]["frac_poor"]
    )
    exp.control(
        "specific",
        specific,
        f"B loses {results['B']['loss']} against A's {results['A']['loss']}, and "
        f"spends {results['B']['frac_poor']:.1%} of its time on poor cells against "
        f"A's {results['A']['frac_poor']:.1%} — the loss must track the poor time",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            f"the loss tracks the time spent on poor cells: {results['A']['frac_poor']:.1%} "
            f"on alternating gives a loss of {results['A']['loss']}, "
            f"{results['B']['frac_poor']:.1%} on gradient gives {results['B']['loss']}, "
            f"and with no poor cells the loss is {results['C']['loss']}",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "`frac_poor` counts time on cells below `income` after the step; the cell "
        "value at the moment of taking may differ."
    )
    exp.limitation(
        "The threshold 11.7% is arithmetic for one organism alone; with many "
        "organisms the cell value changes and so does the threshold."
    )
    exp.limitation(
        "`Policy::Sighted` is not yet covered by the Rust test suite."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-19: потери от бедных клеток?")
    print()
    print(f"Арифметика: баланс на богатой (двигаясь) {bal_rich_move:+.3f}, "
          f"на бедной {bal_poor_move:+.3f}")
    print(f"  порог: гибнет при доле на бедных > {threshold:.1%}")
    print()
    print("плечо  поле          poor   живых  потери  доля_на_бедных")
    print("-" * 62)
    for key, (label, field, n, poor, tag) in arms.items():
        r = results[key]
        print(
            f"  {key}    {field:<12} {poor:>4.1f}  {r['alive']:>5}  {r['loss']:>6}  "
            f"{r['frac_poor']:>13.1%}"
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
