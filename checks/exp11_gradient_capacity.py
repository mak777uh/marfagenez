"""EXP-11: ёмкость на поле с разницей — скопление против расхождения

## Откуда вопрос

`EXP-10` показал: в **однородном** поле ёмкость = число клеток = 40.
Организмы не скапливаются, потому что `sighted` не двигается (все клетки равны).

**Но на поле с разницей** `sighted` **всегда двигается** — соседи разной
богатости. Значит может скапливаться.

## Арифметика (до прогона)

Две гипотезы дают **одинаковое** число для `alternating`:

| гипотеза | рассуждение | ёмкость |
|---|---|---|
| **скопление** | все идут на 20 богатых, `k_max = 2` | 20 × 2 = **40** |
| **расхождение** | все расходятся по 40 клеткам | 40 × 1 = **40** |

**`alternating` не различает гипотезы.** Нужно поле, где они дают разное.

**`gradient`:** все идут вправо, к единственному максимуму.

| гипотеза | рассуждение | ёмкость |
|---|---|---|
| **скопление** | все на правом краю, `k_max = 2` | **2** |
| **расхождение** | расходятся по 40 клеткам | **40** |

**Разница в 20 раз.** `gradient` различает гипотезы.

## Плечи

| ключ | поле | n | предсказание скопления | предсказание расхождения |
|---|---|---|---|---|
| **A** | `uniform` | 80 | 40 | 40 |
| **B** | `alternating` | 80 | 40 | 40 |
| **C** | `gradient` | 80 | **2** | **40** |

## Контроль (три теста)

1. **Срабатывает:** A даёт 40 (как в EXP-10) — контроль работает
2. **Молчит:** B даёт 40 — обе гипотезы согласны, значит тест не различает
3. **Специфичен:** C даёт либо ~2 (скопление), либо ~40 (расхождение) —
   **и это решает вопрос**

## Запуск

    python3 checks/exp11_gradient_capacity.py
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
CELLS = 40
N = 80

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


def run_arm(field: str) -> dict:
    args = " ".join([
        "--policy sighted",
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

    local_rel = Path("results") / "gradient-capacity" / Path(wsl_path).name
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
    crowd: dict[int, int] = {}
    for c in cells:
        crowd[c] = crowd.get(c, 0) + 1

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "survival": len(alive) / len(last["samples"]) if last["samples"] else 0.0,
        "distinct_cells": len(set(cells)),
        "max_crowd": max(crowd.values()) if crowd else 0,
        "mean_crowd": (len(alive) / len(set(cells))) if cells else 0.0,
        "max_cell": max(cells) if cells else 0,
    }


def main() -> int:
    arms = {
        "A": ("uniform (control)", "uniform"),
        "B": ("alternating", "alternating"),
        "C": ("gradient", "gradient"),
    }

    k_max = MAX_RESOURCE * REGROW / INCOME

    arithmetic = {
        "k_max_per_cell": k_max,
        "cells": CELLS,
        "n": N,
        "alternating_does_not_discriminate": (
            f"gathering: 20 rich cells * {k_max} = {20 * k_max}; "
            f"spreading: {CELLS} cells * 1 = {CELLS}. Both give {CELLS}."
        ),
        "gradient_discriminates": (
            f"gathering: 1 best cell * {k_max} = {k_max}; "
            f"spreading: {CELLS} cells * 1 = {CELLS}. A factor of {CELLS / k_max}."
        ),
        "prediction": (
            "If organisms gather, the gradient arm survives about "
            f"{k_max} of {N}. If they spread, it survives about {CELLS}."
        ),
    }

    exp = Experiment(
        experiment_id="gradient-capacity",
        question="Скапливаются ли организмы у единственного максимума?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp11_gradient_capacity.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS, "n": N,
            "policy": "sighted", "maintenance": MAINTENANCE,
            "repair_cost": REPAIR_COST, "damage_rate": DAMAGE,
            "max_resource": MAX_RESOURCE, "regrow": REGROW,
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
                "n": N,
                "alive": r["alive"],
                "total": r["total"],
                "survival": r["survival"],
                "distinct_cells": r["distinct_cells"],
                "max_crowd": r["max_crowd"],
                "mean_crowd": r["mean_crowd"],
                "max_cell": r["max_cell"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    fires = abs(results["A"]["alive"] - 40) <= 4
    exp.control(
        "fires",
        fires,
        f"A (uniform): {results['A']['alive']} alive — must reproduce EXP-10's 40",
    )

    silent = abs(results["B"]["alive"] - 40) <= 6
    exp.control(
        "silent",
        silent,
        f"B (alternating): {results['B']['alive']} alive — both hypotheses predict "
        f"40 here, so this arm cannot discriminate and must not",
    )

    # The discriminating arm: gathering predicts ~2, spreading predicts ~40.
    gathering = results["C"]["alive"] <= 10
    spreading = results["C"]["alive"] >= 25
    specific = gathering or spreading
    exp.control(
        "specific",
        specific,
        f"C (gradient): {results['C']['alive']} alive, max crowd "
        f"{results['C']['max_crowd']} — gathering predicts ~{k_max:.0f}, "
        f"spreading predicts ~{CELLS}",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        kind = "gathering" if gathering else "spreading"
        exp.verdict(
            "passed",
            f"the gradient arm survives {results['C']['alive']} of {N} with a "
            f"maximum crowd of {results['C']['max_crowd']}: organisms {kind}",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The gradient arm's prediction is a two-way choice (gather or spread); an "
        "intermediate outcome would be `void` for the question."
    )
    exp.limitation(
        "`Policy::Sighted` is not yet covered by the Rust test suite."
    )
    exp.limitation(
        "The conclusion is about this model's movement rule, not about crowding in "
        "general."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-11: скапливаются ли организмы у максимума?")
    print()
    print(f"Арифметика: k_max = {k_max} на клетку")
    print(f"  alternating: скопление {20 * k_max:.0f}, расхождение {CELLS} — НЕ РАЗЛИЧАЕТ")
    print(f"  gradient:    скопление {k_max:.0f}, расхождение {CELLS} — РАЗЛИЧАЕТ")
    print()
    print("плечо  поле          живых  выживаемость  клеток  макс_давка  ср_давка  макс_клетка")
    print("-" * 88)
    for key, (label, field) in arms.items():
        r = results[key]
        print(
            f"  {key}    {field:<12} {r['alive']:>5}  {r['survival']:>11.1%}  "
            f"{r['distinct_cells']:>6}  {r['max_crowd']:>10}  {r['mean_crowd']:>8.2f}  "
            f"{r['max_cell']:>11}"
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
