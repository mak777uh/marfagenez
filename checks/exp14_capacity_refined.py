"""EXP-14: уточнение формулы ёмкости — клетка должна кормить

## Откуда вопрос

`EXP-13` подтвердил формулу `C = cells * M*r/income` при `k_max = 1` и `k_max = 2`.
При `M = 4.0` предсказано `C = 160`, но измерено только `>= 100`.

## Уточнение арифметики

**Прежняя формула** `k_max = M*r/income` отвечает на вопрос:
> При каком `k` равновесие `c* = 0`?

**Но организм берёт `min(income, c)`.** Если `c* < income`, он получает
**меньше** дохода и **голодает**.

**Правильное условие:** `c* >= income`, то есть клетка кормит **полностью**.

$$M - \frac{k \cdot \text{income}}{r} \geq \text{income}$$

$$k \leq \frac{(M - \text{income}) \cdot r}{\text{income}}$$

**При `M = 2.0`, `income = 0.8`, `r = 0.8`:**

$$k \leq \frac{(2.0 - 0.8) \times 0.8}{0.8} = 1.2$$

**Значит `k_max = 1`**, а не 2!

**Но `EXP-12` измерил давку 2 при `M = 2.0`.** Значит организмы **выживают**
и при `c* < income` — просто получают меньше.

## Две ёмкости

| ёмкость | условие | при `M=2.0` | при `M=4.0` |
|---|---|---|---|
| **полного кормления** | `c* >= income` | 1 | 3 |
| **выживания** | `c* >= 0` | 2 | 4 |

**`EXP-12` измерил ёмкость выживания** — 2 на клетку.

## Плечи

| ключ | `M` | `n` | предсказание выживания | предсказание полного кормления |
|---|---|---|---|---|
| **A** | 2.0 | 100 | 80 | 40 |
| **B** | 4.0 | 200 | 160 | 120 |
| **C** | 4.0 | 200, uniform | 40 | 40 |

## Контроль (три теста)

1. **Срабатывает:** A даёт ~80 (ёмкость выживания при `M=2.0`)
2. **Молчит:** C даёт ~40 (uniform, не двигаются)
3. **Специфичен:** B даёт **либо 160, либо 120** — это решает, какая формула верна

## Запуск

    python3 checks/exp14_capacity_refined.py
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
REGROW = 0.8


def in_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def shell(cmd: str) -> str:
    argv = ["bash", "-c", cmd] if in_wsl() else ["wsl", "-e", "bash", "-c", cmd]
    out = subprocess.run(argv, capture_output=True, text=True, timeout=900)
    if out.returncode != 0:
        raise SystemExit(f"command failed:\n{cmd}\n{out.stderr}")
    return out.stdout


def run_arm(field: str, n: int, rich: float, poor: float) -> dict:
    args = " ".join([
        "--policy sighted",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {n}",
        f"--cells {CELLS}",
        f"--field {field}",
        f"--rich {rich}",
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

    local_rel = Path("results") / "capacity-refined" / Path(wsl_path).name
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

    # How many survivors are at the energy ceiling (well fed) vs below it.
    energies = [s["energy"] for s in alive]
    at_ceiling = sum(1 for e in energies if e >= 9.36)

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "survival": len(alive) / len(last["samples"]) if last["samples"] else 0.0,
        "distinct_cells": len(set(cells)),
        "max_crowd": max(crowd.values()) if crowd else 0,
        "mean_crowd": (len(alive) / len(set(cells))) if cells else 0.0,
        "at_ceiling": at_ceiling,
        "mean_energy": (sum(energies) / len(energies)) if energies else 0.0,
    }


def main() -> int:
    arms = {
        "A": ("alternating, M=2.0, n=100", "alternating", 100, 2.0, 0.2),
        "B": ("alternating, M=4.0, n=200", "alternating", 200, 4.0, 0.5),
        "C": ("uniform, M=4.0, n=200", "uniform", 200, 4.0, 0.5),
    }

    def survive_k(m: float) -> float:
        return m * REGROW / INCOME

    def feed_k(m: float) -> float:
        return max(0.0, (m - INCOME) * REGROW / INCOME)

    arithmetic = {
        "survival_capacity": "k_survive = M * r / income (equilibrium c* = 0)",
        "feeding_capacity": "k_feed = (M - income) * r / income (equilibrium c* = income)",
        "why_two": (
            "The organism takes min(income, c). If c* < income it gets less than "
            "the full income and lives below the energy ceiling, but it lives. So "
            "there are two capacities: how many can survive at all, and how many "
            "are fully fed."
        ),
        "predictions": {
            "A": {
                "survive": CELLS * survive_k(2.0),
                "feed": CELLS * feed_k(2.0),
            },
            "B": {
                "survive": CELLS * survive_k(4.0),
                "feed": CELLS * feed_k(4.0),
            },
            "C": {
                "survive": CELLS,
                "feed": CELLS,
            },
        },
    }

    exp = Experiment(
        experiment_id="capacity-refined",
        question="Ёмкость выживания или ёмкость полного кормления?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp14_capacity_refined.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS,
            "policy": "sighted", "maintenance": MAINTENANCE,
            "repair_cost": REPAIR_COST, "damage_rate": DAMAGE,
            "regrow": REGROW, "income": INCOME,
        },
    )

    results: dict[str, dict] = {}
    for key, (label, field, n, rich, poor) in arms.items():
        r = run_arm(field, n, rich, poor)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
                "field": field,
                "n": n,
                "rich": rich,
                "poor": poor,
                "alive": r["alive"],
                "total": r["total"],
                "survival": r["survival"],
                "distinct_cells": r["distinct_cells"],
                "max_crowd": r["max_crowd"],
                "mean_crowd": r["mean_crowd"],
                "at_ceiling": r["at_ceiling"],
                "mean_energy": r["mean_energy"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    pred = arithmetic["predictions"]

    # -- the three control tests -------------------------------------------

    fires = abs(results["A"]["alive"] - pred["A"]["survive"]) <= 10
    exp.control(
        "fires",
        fires,
        f"A: {results['A']['alive']} alive vs predicted survival capacity "
        f"{pred['A']['survive']:.0f} — must reproduce EXP-12's 80",
    )

    silent = results["C"]["alive"] <= CELLS + 5
    exp.control(
        "silent",
        silent,
        f"C (uniform): {results['C']['alive']} alive — a uniform field gives no "
        f"reason to move, so the ceiling must stay at the number of cells ({CELLS})",
    )

    # The discriminating arm: 160 (survival) vs 120 (feeding).
    near_survive = abs(results["B"]["alive"] - pred["B"]["survive"]) <= 15
    near_feed = abs(results["B"]["alive"] - pred["B"]["feed"]) <= 15
    specific = near_survive or near_feed
    exp.control(
        "specific",
        specific,
        f"B: {results['B']['alive']} alive, {results['B']['at_ceiling']} at the "
        f"energy ceiling — survival capacity predicts {pred['B']['survive']:.0f}, "
        f"feeding capacity predicts {pred['B']['feed']:.0f}",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        which = (
            "survival capacity" if near_survive else
            "feeding capacity" if near_feed else "neither"
        )
        exp.verdict(
            "passed",
            f"B survives {results['B']['alive']} of 200 with "
            f"{results['B']['at_ceiling']} at the energy ceiling: the measured "
            f"ceiling is the {which}",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The two capacities differ only when M > income; at M = 2.0 they are 2 and "
        "1.2, close enough that the measurement may not separate them."
    )
    exp.limitation(
        "`at_ceiling` uses a 9.36 threshold, which is the ceiling at these "
        "parameters; a different capacity parameter would move it."
    )
    exp.limitation(
        "The conclusion is about this model's take rule min(income, c), not about "
        "feeding in general."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-14: ёмкость выживания или полного кормления?")
    print()
    print("Арифметика:")
    print("  k_survive = M*r/income          (равновесие c* = 0)")
    print("  k_feed    = (M-income)*r/income (равновесие c* = income)")
    print()
    print("плечо  поле          M      n   живых  выжив%  давка  на_потолке  ср.энергия")
    print("-" * 88)
    for key, (label, field, n, rich, poor) in arms.items():
        r = results[key]
        print(
            f"  {key}    {field:<12} {rich:>3.1f}  {n:>4}  {r['alive']:>5}  "
            f"{r['survival']:>6.0%}  {r['mean_crowd']:>5.2f}  {r['at_ceiling']:>10}  "
            f"{r['mean_energy']:>10.3f}"
        )
    print()
    print("Предсказания:")
    for key in ("A", "B", "C"):
        print(
            f"  {key}: выживание {pred[key]['survive']:.0f}, "
            f"полное кормление {pred[key]['feed']:.0f}, "
            f"измерено {results[key]['alive']}"
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
