"""EXP-10: ёмкость клетки и почему гибнут организмы

## Откуда вопрос

`EXP-09`: `sighted` на `alternating` даёт 40 из 40 живых, `remember` — 39 из 40.
`EXP-07`: `sighted` на `uniform` — 32 из 40 живых.

**Почему гибнут 8 из 40 в однородном поле?**

## Арифметика (до прогона)

Клетка с `k` организмами: `t = k * income`, равновесие `c* = M - t/r`.

**Ёмкость клетки** — сколько организмов она прокормит при `c* ≥ 0`:

k_max = M * r / income

При `M = 2.0`, `r = 0.8`, `income = 0.8`:

$$k_{\max} = \frac{2.0 \times 0.8}{0.8} = 2$$

**40 клеток × 2 = 80 организмов.** Организмов 40 — места хватает вдвое.

**Значит гибель не от ёмкости.**

## Гипотеза

Гибнут те, кто **стартовал на бедной клетке** и **не успел дойти** до богатой,
потому что бедная клетка даёт `0.2`, а тратит организм `0.63` за шаг.

**Время до смерти:** `energy / (0.63 - 0.2) = 5.0 / 0.43 ≈ 11.6` шагов.

**За 11 шагов** организм должен дойти до богатой клетки. При `sighted` он идёт
в сторону лучшего соседа — это 1 шаг. **Успевает.**

**Но в однородном поле** все клетки `0.8`. Организм берёт `min(0.8, 0.8) = 0.8`,
тратит `0.63` — **баланс +0.17**. Живёт.

**Тогда почему гибнут 8?**

## Плечи

| ключ | политика | поле | предсказание |
|---|---|---|---|
| **A** | `sighted` | uniform | 32 живых (как в EXP-07) |
| **B** | `sighted` | uniform, `n = 20` | **больше** живых: меньше давки |
| **C** | `sighted` | uniform, `n = 80` | **меньше** живых: давка |

## Контроль (три теста)

1. **Срабатывает:** C даёт меньше живых, чем A — давка убивает
2. **Молчит:** A даёт 32, как в EXP-07
3. **Специфичен:** B даёт больше живых, но **не 20** — значит дело в давке,
   а не просто в числе

## Запуск

    python3 checks/exp10_capacity.py
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


def run_arm(n: int) -> dict:
    args = " ".join([
        "--policy sighted",
        "--read-budget 3",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {n}",
        f"--cells {CELLS}",
        "--field uniform",
        "--rich 2.0 --poor 0.2",
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

    local_rel = Path("results") / "capacity" / Path(wsl_path).name
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
    crowd = {}
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
    }


def main() -> int:
    arms = {
        "A": ("n=40 (control)", 40),
        "B": ("n=20", 20),
        "C": ("n=80", 80),
    }

    k_max = MAX_RESOURCE * REGROW / INCOME

    arithmetic = {
        "equilibrium": "c* = M - t/r, t = k * income",
        "capacity_formula": "k_max = M * r / income",
        "k_max": k_max,
        "total_capacity": k_max * CELLS,
        "note": (
            f"k_max = {MAX_RESOURCE} * {REGROW} / {INCOME} = {k_max}. "
            f"{CELLS} cells hold {k_max * CELLS} organisms. With 40 organisms there "
            f"is twice the room needed, so death cannot be from cell capacity."
        ),
        "hypothesis": (
            "If deaths come from crowding, then n=20 should lose fewer and n=80 "
            "should lose more, both relative to n=40."
        ),
    }

    exp = Experiment(
        experiment_id="capacity",
        question="Почему гибнут организмы, если ёмкости хватает вдвое?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp10_capacity.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS,
            "policy": "sighted", "field": "uniform",
            "maintenance": MAINTENANCE, "repair_cost": REPAIR_COST,
            "damage_rate": DAMAGE, "max_resource": MAX_RESOURCE,
            "regrow": REGROW,
        },
    )

    results = {}
    for key, (label, n) in arms.items():
        r = run_arm(n)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
                "n": n,
                "alive": r["alive"],
                "total": r["total"],
                "survival": r["alive"] / r["total"] if r["total"] else 0.0,
                "distinct_cells": r["distinct_cells"],
                "max_crowd": r["max_crowd"],
                "mean_crowd": r["mean_crowd"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    fires = results["C"]["survival"] < results["A"]["survival"]
    exp.control(
        "fires",
        fires,
        f"C (n=80): {results['C']['alive']}/{results['C']['total']} = "
        f"{results['C']['survival']:.1%} vs A (n=40): {results['A']['survival']:.1%} "
        f"— crowding must lower survival",
    )

    silent = abs(results["A"]["alive"] - 32) <= 2
    exp.control(
        "silent",
        silent,
        f"A: {results['A']['alive']} alive — must match EXP-07's 32",
    )

    specific = (
        results["B"]["survival"] > results["A"]["survival"]
        and results["B"]["alive"] < 20
    )
    exp.control(
        "specific",
        specific,
        f"B (n=20): {results['B']['alive']}/{results['B']['total']} = "
        f"{results['B']['survival']:.1%} vs A's {results['A']['survival']:.1%} — "
        f"less crowding must help, but not perfectly (some still die)",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            "survival falls as crowding rises and rises as crowding falls, so the "
            "deaths come from crowding, not from cell capacity",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The capacity formula k_max = M*r/income assumes all organisms on a cell "
        "take the full income every step; a moving organism takes less."
    )
    exp.limitation(
        "A uniform field is degenerate: there is no best cell, so the sighted "
        "organism has nothing to prefer and the crowding is the only variable."
    )
    exp.limitation(
        "The conclusion is about this model's regrowth rule, not about carrying "
        "capacity in general."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-10: ёмкость клетки")
    print()
    print(f"Арифметика: k_max = M*r/income = {MAX_RESOURCE}*{REGROW}/{INCOME} = {k_max}")
    print(f"  {CELLS} клеток вмещают {k_max * CELLS} организмов")
    print(f"  организмов 40 — места хватает вдвое")
    print()
    print("плечо  n    живых  выживаемость  клеток  макс_давка  ср_давка  hash")
    print("-" * 76)
    for key, (label, n) in arms.items():
        r = results[key]
        print(
            f"  {key}    {n:>3}  {r['alive']:>5}  {r['alive']/r['total']:>11.1%}  "
            f"{r['distinct_cells']:>6}  {r['max_crowd']:>10}  {r['mean_crowd']:>8.2f}  {r['hash']}"
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
