"""EXP-12: кривая ёмкости — как выживаемость зависит от плотности

## Откуда вопрос

`EXP-11` показал:

| поле | n=80 | выживаемость | давка |
|---|---|---|---|
| `uniform` | 40 | 50% | 1 |
| `alternating` | 76 | 95% | 2 |
| `gradient` | 78 | 97.5% | 2 |

**Вывод был:** движение удваивает ёмкость.

**Но не проверено:** как выживаемость меняется с `n`. Если она падает плавно —
ёмкость размыта. Если резко — есть чёткий порог.

## Арифметика (до прогона)

Ёмкость среды: `C = cells * k_max = 40 * 2 = 80`.

**Модель «жёсткой ёмкости»:**

$$\text{выживших}(n) = \min(n, C)$$

**Предсказание:**

| n | выживших |
|---|---|
| 20 | 20 |
| 40 | 40 |
| 60 | 60 |
| 80 | 80 |
| 100 | **80** |
| 160 | **80** |

**Если модель верна** — выживаемость 100% до `n = 80`, потом падает по `80/n`.

**Если модель неверна** — выживаемость падает раньше, потому что организмы
не распределяются идеально.

## Плечи

Для каждого поля — 4 значения `n`: 20, 40, 60, 80, 100.

**Ключевое плечо:** `alternating`, `n = 100`. Если выживут 80 — ёмкость 80
подтверждена. Если меньше — распределение не идеально.

## Контроль (три теста)

1. **Срабатывает:** при `n = 20` все поля дают 20 из 20 — места хватает
2. **Молчит:** `uniform` при любом `n` даёт ~40 — не двигаются
3. **Специфичен:** `alternating` при `n = 100` даёт больше 40 — двигаются

## Запуск

    python3 checks/exp12_capacity_curve.py
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
MAX_RESOURCE = 2.0
REGROW = 0.8

NS = [20, 40, 60, 80, 100]
FIELDS = ["uniform", "alternating"]


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


def run_arm(field: str, n: int) -> dict:
    args = " ".join([
        "--policy sighted",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {n}",
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

    local_rel = Path("results") / "capacity-curve" / Path(wsl_path).name
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
    }


def main() -> int:
    k_max = MAX_RESOURCE * REGROW / INCOME
    capacity = CELLS * k_max

    arithmetic = {
        "k_max_per_cell": k_max,
        "cells": CELLS,
        "capacity": capacity,
        "hard_capacity_model": "survivors(n) = min(n, capacity)",
        "prediction_uniform": (
            "A uniform field gives no reason to move, so every organism keeps its "
            "own cell: survivors ~ min(n, cells) = min(n, 40)."
        ),
        "prediction_alternating": (
            f"An alternating field makes the organism move, so it can use the second "
            f"place on a cell: survivors ~ min(n, {capacity})."
        ),
    }

    exp = Experiment(
        experiment_id="capacity-curve",
        question="Как выживаемость зависит от плотности?",
        arithmetic=arithmetic,
        arms={
            f"{f}-n{n}": f"{f}, n={n}"
            for f in FIELDS
            for n in NS
        },
        seed=SEED,
        command="python3 checks/exp12_capacity_curve.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS,
            "policy": "sighted", "maintenance": MAINTENANCE,
            "repair_cost": REPAIR_COST, "damage_rate": DAMAGE,
            "max_resource": MAX_RESOURCE, "regrow": REGROW,
            "ns": NS, "fields": FIELDS,
        },
    )

    results: dict[str, dict] = {}
    for field in FIELDS:
        for n in NS:
            key = f"{field}-n{n}"
            r = run_arm(field, n)
            results[key] = r
            exp.add_arm(
                key,
                f"{field}, n={n}",
                {
                    "field": field,
                    "n": n,
                    "alive": r["alive"],
                    "total": r["total"],
                    "survival": r["survival"],
                    "distinct_cells": r["distinct_cells"],
                    "max_crowd": r["max_crowd"],
                    "mean_crowd": r["mean_crowd"],
                    "trace_file": r["file"],
                },
                trace_hash=r["hash"],
            )

    # -- the three control tests -------------------------------------------

    low_density = all(
        results[f"{f}-n20"]["alive"] >= 18 for f in FIELDS
    )
    exp.control(
        "fires",
        low_density,
        f"n=20: uniform {results['uniform-n20']['alive']}/20, "
        f"alternating {results['alternating-n20']['alive']}/20 — at low density "
        f"both fields must keep almost everyone",
    )

    uniform_flat = all(
        abs(results[f"uniform-n{n}"]["alive"] - 40) <= 6 for n in NS
    )
    exp.control(
        "silent",
        uniform_flat,
        f"uniform: "
        + ", ".join(f"n={n}->{results[f'uniform-n{n}']['alive']}" for n in NS)
        + " — a uniform field gives no reason to move, so survivors must stay "
        "near the number of cells",
    )

    alternating_grows = results["alternating-n100"]["alive"] > results["uniform-n100"]["alive"] + 10
    exp.control(
        "specific",
        alternating_grows,
        f"n=100: alternating {results['alternating-n100']['alive']} vs uniform "
        f"{results['uniform-n100']['alive']} — movement must raise the ceiling",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            f"the ceiling is {results['alternating-n100']['alive']} with movement and "
            f"{results['uniform-n100']['alive']} without: movement raises the "
            f"capacity, and the predicted {capacity:.0f} is "
            + ("confirmed" if abs(results['alternating-n100']['alive'] - capacity) <= 10
               else "not reached")
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The hard-capacity model min(n, C) is a model, not a measurement; the "
        "measured curve may be softer."
    )
    exp.limitation(
        "`Policy::Sighted` is not yet covered by the Rust test suite."
    )
    exp.limitation(
        "The conclusion is about this model's movement rule and regrowth, not about "
        "carrying capacity in general."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-12: кривая ёмкости")
    print()
    print(f"Арифметика: k_max = {k_max}, клеток {CELLS}, ёмкость {capacity:.0f}")
    print(f"  модель: выживших = min(n, {capacity:.0f})")
    print()
    print(f"{'n':>5} {'uniform':>10} {'выжив%':>8} {'alternating':>13} {'выжив%':>8} {'давка':>7}")
    print("-" * 60)
    for n in NS:
        u = results[f"uniform-n{n}"]
        a = results[f"alternating-n{n}"]
        print(
            f"{n:>5} {u['alive']:>10} {u['survival']:>7.0%} "
            f"{a['alive']:>13} {a['survival']:>7.0%} {a['mean_crowd']:>7.2f}"
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
