"""EXP-17: перенаселение — держится ли ёмкость?

## Откуда вопрос

`EXP-12`–`EXP-14` подтвердили: `C = cells * M*r/income = 80`.

**Но проверено только до `n = 100`.** При `n = 120`, `160` — что будет?

## Арифметика (до прогона)

| `n` | `k = n/cells` | лишних |
|---|---|---|
| 40 | 1.0 | 0 |
| 80 | 2.0 | 0 |
| 100 | 2.5 | 20 |
| 120 | 3.0 | 40 |
| 160 | 4.0 | 80 |

**Предсказание:** при `n > 80` выживут ровно **80**, лишние умрут.

**Давка на выживших:** `80/40 = 2.0` = `k_max`.

## Плечи

| ключ | `n` | предсказание |
|---|---|---|
| **A** | 80 | 80 живых, давка 2.0 |
| **B** | 120 | **80** живых, давка 2.0 |
| **C** | 160 | **80** живых, давка 2.0 |

## Контроль (три теста)

1. **Срабатывает:** A даёт 80 (как в `EXP-14`)
2. **Молчит:** B и C не дают больше 80 — ёмкость держится
3. **Специфичен:** B и C дают **ровно 80**, а не 40 или 100

## Запуск

    python3 checks/exp17_overcrowding.py
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
POOR = 0.2
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


def run_arm(n: int, tag: str) -> dict:
    args = " ".join([
        "--policy sighted",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {n}",
        f"--cells {CELLS}",
        "--field alternating",
        f"--rich {RICH}",
        f"--poor {POOR}",
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

    local_rel = Path("results") / "overcrowding" / f"{tag}-{Path(wsl_path).name}"
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
        "distinct_cells": len(set(cells)),
        "max_crowd": max(crowd.values()) if crowd else 0,
        "mean_crowd": (len(alive) / len(set(cells))) if cells else 0.0,
    }


def main() -> int:
    arms = {
        "A": ("n=80 (at capacity)", 80, "A"),
        "B": ("n=120 (over)", 120, "B"),
        "C": ("n=160 (over)", 160, "C"),
    }

    k_max = RICH * REGROW / INCOME
    capacity = CELLS * k_max

    arithmetic = {
        "k_max": k_max,
        "capacity": capacity,
        "prediction": (
            f"At or below n = {capacity:.0f} every organism finds a place; above "
            f"it exactly {capacity:.0f} survive and the rest die. The survivors "
            f"should sit at a crowding of {k_max:.1f}."
        ),
        "why": (
            "A cell holds k_max organisms without being drained. With more "
            "organisms than cells * k_max there are not enough places, so the "
            "surplus dies."
        ),
    }

    exp = Experiment(
        experiment_id="overcrowding",
        question="Держится ли ёмкость при перенаселении?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp17_overcrowding.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS,
            "policy": "sighted", "field": "alternating",
            "rich": RICH, "poor": POOR, "regrow": REGROW,
            "maintenance": MAINTENANCE, "repair_cost": REPAIR_COST,
            "damage_rate": DAMAGE,
        },
    )

    results: dict[str, dict] = {}
    for key, (label, n, tag) in arms.items():
        r = run_arm(n, tag)
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

    fires = abs(results["A"]["alive"] - capacity) <= 6
    exp.control(
        "fires",
        fires,
        f"A (n=80): {results['A']['alive']} alive vs capacity {capacity:.0f} — "
        f"at capacity every organism must find a place",
    )

    silent = (
        results["B"]["alive"] <= capacity + 6
        and results["C"]["alive"] <= capacity + 6
    )
    exp.control(
        "silent",
        silent,
        f"B (n=120): {results['B']['alive']}, C (n=160): {results['C']['alive']} "
        f"— neither may exceed the capacity of {capacity:.0f}",
    )

    specific = (
        abs(results["B"]["alive"] - capacity) <= 8
        and abs(results["C"]["alive"] - capacity) <= 8
    )
    exp.control(
        "specific",
        specific,
        f"B and C both settle at about {capacity:.0f}, not at 40 or at n — the "
        f"ceiling is the capacity, not the number of cells or the number of organisms",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            f"the capacity holds under overcrowding: n=120 and n=160 both settle "
            f"at {results['B']['alive']} and {results['C']['alive']}, against a "
            f"predicted {capacity:.0f}",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The run is 3000 steps; a longer run might let the surplus linger before "
        "dying."
    )
    exp.limitation(
        "The capacity is measured at the end, not tracked over time, so a slow "
        "decline would look the same as a stable ceiling."
    )
    exp.limitation(
        "`Policy::Sighted` is not yet covered by the Rust test suite."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-17: держится ли ёмкость при перенаселении?")
    print()
    print(f"Арифметика: k_max = {k_max}, C = {capacity:.0f}")
    print()
    print("плечо  n    живых  выжив%  клеток  макс_давка  ср_давка")
    print("-" * 62)
    for key, (label, n, tag) in arms.items():
        r = results[key]
        print(
            f"  {key}    {n:>3}  {r['alive']:>5}  {r['alive']/r['total']:>6.0%}  "
            f"{r['distinct_cells']:>6}  {r['max_crowd']:>10}  {r['mean_crowd']:>8.2f}"
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
