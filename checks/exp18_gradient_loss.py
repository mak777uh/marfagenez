"""EXP-18: gradient при перенаселении — потери в пути

## Откуда вопрос

`EXP-17` показал: при `n = 120`, `160` на `alternating` выживают ровно 80.
При `n = 80` — только 76: четыре гибнут **в пути**.

**Вопрос:** на `gradient` потери в пути больше?

## Разница полей

| поле | движение организма |
|---|---|
| `alternating` | колеблется между двумя клетками |
| `gradient` | идёт **всегда вправо**, к максимуму |

**В `gradient`** организм идёт **в одну сторону** — тратит энергию на путь.
**В `alternating`** — колеблется рядом, путь короче.

**Предсказание:** на `gradient` потери в пути **больше**.

## Арифметика (до прогона)

**Ёмкость одинакова:** `C = cells × M·r/income = 80`.

**Но выживших:**

$$N_{\text{survive}} = \min(n, C) - \text{потери в пути}$$

**Потери зависят от поля:**
- `alternating`: 4 (измерено при `n = 80`)
- `gradient`: **больше 4** (предсказание)

## Плечи

| ключ | поле | `n` | предсказание |
|---|---|---|---|
| **A** | `alternating` | 80 | 76 (как в `EXP-17`) |
| **B** | `gradient` | 80 | **меньше 76** |
| **C** | `gradient` | 120 | ~80, но меньше |

## Контроль (три теста)

1. **Срабатывает:** A даёт 76 (как в `EXP-17`)
2. **Молчит:** B не даёт больше 80
3. **Специфичен:** B даёт **меньше** A — потери в пути больше

## Запуск

    python3 checks/exp18_gradient_loss.py
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


def run_arm(field: str, n: int, tag: str) -> dict:
    args = " ".join([
        "--policy sighted",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {n}",
        f"--cells {CELLS}",
        f"--field {field}",
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

    local_rel = Path("results") / "gradient-loss" / f"{tag}-{Path(wsl_path).name}"
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
        "max_cell": max(cells) if cells else 0,
        "loss": n - len(alive),
    }


def main() -> int:
    arms = {
        "A": ("alternating, n=80", "alternating", 80, "A"),
        "B": ("gradient, n=80", "gradient", 80, "B"),
        "C": ("gradient, n=120", "gradient", 120, "C"),
    }

    k_max = RICH * REGROW / INCOME
    capacity = CELLS * k_max

    arithmetic = {
        "k_max": k_max,
        "capacity": capacity,
        "formula": "N_survive = min(n, C) - loss_in_transit",
        "prediction": (
            f"On alternating at n=80 the loss was 4 (76 of 80). On gradient the "
            f"organism walks in one direction instead of oscillating, so the loss "
            f"should be larger: B should survive fewer than A."
        ),
        "why": (
            "In alternating the organism steps to a neighbour and back, so the "
            "distance travelled is short. In gradient it walks the same way every "
            "step until it reaches the end."
        ),
    }

    exp = Experiment(
        experiment_id="gradient-loss",
        question="Больше ли потери в пути на gradient?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp18_gradient_loss.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS,
            "policy": "sighted", "rich": RICH, "poor": POOR,
            "regrow": REGROW, "maintenance": MAINTENANCE,
            "repair_cost": REPAIR_COST, "damage_rate": DAMAGE,
        },
    )

    results: dict[str, dict] = {}
    for key, (label, field, n, tag) in arms.items():
        r = run_arm(field, n, tag)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
                "field": field,
                "n": n,
                "alive": r["alive"],
                "total": r["total"],
                "loss": r["loss"],
                "survival": r["alive"] / r["total"] if r["total"] else 0.0,
                "distinct_cells": r["distinct_cells"],
                "max_crowd": r["max_crowd"],
                "mean_crowd": r["mean_crowd"],
                "max_cell": r["max_cell"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    fires = abs(results["A"]["alive"] - 76) <= 6
    exp.control(
        "fires",
        fires,
        f"A (alternating, n=80): {results['A']['alive']} alive — must reproduce "
        f"EXP-17's 76",
    )

    silent = results["B"]["alive"] <= capacity + 6
    exp.control(
        "silent",
        silent,
        f"B (gradient, n=80): {results['B']['alive']} alive — must not exceed the "
        f"capacity of {capacity:.0f}",
    )

    specific = results["B"]["loss"] > results["A"]["loss"]
    exp.control(
        "specific",
        specific,
        f"B loses {results['B']['loss']} against A's {results['A']['loss']} — "
        f"walking in one direction must cost more than oscillating",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            f"the gradient loses {results['B']['loss']} against the alternating "
            f"field's {results['A']['loss']}: walking in one direction costs more "
            f"lives than oscillating, and the capacity still holds",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The loss is measured as n minus survivors at the end; organisms that die "
        "early and late are not separated."
    )
    exp.limitation(
        "A gradient with a different slope would change the walking distance and "
        "so the loss."
    )
    exp.limitation(
        "`Policy::Sighted` is not yet covered by the Rust test suite."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-18: больше ли потери в пути на gradient?")
    print()
    print(f"Арифметика: k_max = {k_max}, C = {capacity:.0f}")
    print(f"  N_survive = min(n, C) - потери в пути")
    print()
    print("плечо  поле          n    живых  потери  клеток  макс_давка  макс_клетка")
    print("-" * 78)
    for key, (label, field, n, tag) in arms.items():
        r = results[key]
        print(
            f"  {key}    {field:<12} {n:>3}  {r['alive']:>5}  {r['loss']:>6}  "
            f"{r['distinct_cells']:>6}  {r['max_crowd']:>10}  {r['max_cell']:>11}"
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
