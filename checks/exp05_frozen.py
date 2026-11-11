"""EXP-05: 9.37 — это потолок или равновесие?

## Откуда вопрос

Наблюдение 2026-11-11: `stay` и `remember` не двигаются с шага 40, и у всех
организмов энергия ровно **9.370**.

Два объяснения:
- **равновесие:** организм нашёл баланс и держится
- **потолок:** организм упёрся в `capacity - maintenance - repair`

## Арифметика (написана ДО прогона, §1)

`Organism::step` каждый шаг:
1. `energy = min(energy + taken, capacity)`
2. `energy -= maintenance`
3. `damage += damage_rate`
4. ремонт: `energy -= repaired * repair_cost`

Если `energy + taken >= capacity`, то после шага:
```
energy = capacity - maintenance - damage_rate * repair_cost
```

При `capacity = 10.0`, `maintenance = 0.6`, `damage_rate = 0.02`,
`repair_cost = 1.5`:
```
E_max = 10.0 - 0.6 - 0.02 * 1.5 = 10.0 - 0.6 - 0.03 = 9.37
```

**Совпадает с наблюдением 9.370.** Значит это потолок.

## Плечи

| ключ | что меняем | предсказанный потолок | баланс на богатой |
|---|---|---|---|
| **A** | `capacity = 100.0` | **99.37** | +0.170 |
| **B** | ничего (контроль) | **9.37** | +0.170 |
| **C** | `damage_rate = 0.10` | **9.25** | +0.050 |

## Контроль (§2)

1. **Срабатывает:** A даёт энергию > 9.37 (потолок сдвинулся вверх)
2. **Молчит:** B даёт ровно 9.37 (как в наблюдении)
3. **Специфичен:** C даёт 9.25, а не 9.37 — значит дело именно в формуле
   `capacity - maintenance - damage*repair`, а не в чём-то ещё

## Почему это специфично

Если бы энергия зависела от чего-то другого (например, от поля), то
изменение `damage_rate` не сдвинуло бы её на предсказанную величину.
Сдвиг ровно на `(0.10 - 0.02) * 1.5 = 0.12` — это подпись формулы.

## Запуск

    python3 checks/exp05_frozen.py

**Требует WSL.** Windows-линковка Rust сломана (undefined reference to
`GetHostNameW`), поэтому бинарь собирается и запускается в WSL.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"

#: Where the Rust crate lives inside WSL.
WSL_CORE = "/root/marfagenez/core"
WSL_BIN = f"{WSL_CORE}/target/release/trace"

sys.path.insert(0, str(ROOT))
from checks.experiment import Experiment  # noqa: E402

STEPS = 1200
EVERY = 500
SEED = 20250101
N = 40
CELLS = 40

CAPACITY = 10.0
MAINTENANCE = 0.6
REPAIR_COST = 1.5
DAMAGE_BASE = 0.02
DAMAGE_HIGH = 0.10


def predicted_ceiling(capacity: float, damage_rate: float) -> float:
    """The arithmetic: where the energy stops."""
    return capacity - MAINTENANCE - damage_rate * REPAIR_COST


def wsl(cmd: str) -> str:
    """Runs a shell command in WSL and returns its stdout."""
    out = subprocess.run(
        ["wsl", "-e", "bash", "-c", cmd],
        capture_output=True, text=True, timeout=300,
    )
    if out.returncode != 0:
        raise SystemExit(f"WSL command failed:\n{cmd}\n{out.stderr}")
    return out.stdout


def run_arm(capacity: float, damage_rate: float) -> dict:
    """Runs one arm in WSL and returns its hash, trace file, and energy."""
    args = " ".join([
        "--policy stay",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {N}",
        f"--cells {CELLS}",
        f"--capacity {capacity}",
        f"--damage-rate {damage_rate}",
        f"--maintenance {MAINTENANCE}",
        f"--repair-cost {REPAIR_COST}",
    ])
    out = wsl(f"cd {WSL_CORE} && ./target/release/trace {args}")

    m = re.search(r"hash:\s+([0-9a-f]+)", out)
    if not m:
        raise SystemExit(f"no hash in output:\n{out}")
    h = m.group(1)

    f = re.search(r"written:\s+(\S+)", out)
    if not f:
        raise SystemExit(f"no file in output:\n{out}")
    wsl_path = f.group(1)

    # Copy the trace out of WSL into the repo so the artifact is on disk here.
    local_rel = Path("results") / "frozen-ceiling" / Path(wsl_path).name
    local_abs = ROOT / local_rel
    local_abs.parent.mkdir(parents=True, exist_ok=True)
    wsl(f"cp {WSL_CORE}/{wsl_path} /mnt/c/Users/Admin/Documents/Qoder/"
        f"2026-10-18/82ab86cd/marfagenez/{local_rel.as_posix()}")

    data = json.loads(local_abs.read_text(encoding="utf-8"))
    last = data["frames"][-1]
    alive = [s for s in last["samples"] if s["alive"]]
    energies = sorted({round(s["energy"], 4) for s in alive})
    mean_e = sum(s["energy"] for s in alive) / len(alive) if alive else 0.0

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "energies": energies,
        "mean_energy": mean_e,
        "max_energy": max(energies) if energies else 0.0,
    }


def main() -> int:
    arms = {
        "A": ("capacity=100.0", 100.0, DAMAGE_BASE),
        "B": ("control (capacity=10.0)", CAPACITY, DAMAGE_BASE),
        "C": ("damage_rate=0.10", CAPACITY, DAMAGE_HIGH),
    }

    arithmetic = {
        "formula": "capacity - maintenance - damage_rate * repair_cost",
        "maintenance": MAINTENANCE,
        "repair_cost": REPAIR_COST,
        "predicted": {
            key: predicted_ceiling(cap, dmg) for key, (_, cap, dmg) in arms.items()
        },
        "balance_on_rich": {
            key: 0.8 - MAINTENANCE - dmg * REPAIR_COST
            for key, (_, _, dmg) in arms.items()
        },
        "balance_note": (
            "The balance must stay positive or the organism dies before reaching "
            "the ceiling. At damage_rate=0.10 the balance is +0.05."
        ),
        "steps_to_ceiling": {
            "A": (predicted_ceiling(100.0, DAMAGE_BASE) - 5.0) / (0.8 - MAINTENANCE - DAMAGE_BASE * REPAIR_COST),
            "B": 0.0,
            "C": (predicted_ceiling(CAPACITY, DAMAGE_HIGH) - 5.0) / (0.8 - MAINTENANCE - DAMAGE_HIGH * REPAIR_COST),
        },
        "steps_note": (
            "An arm reaches its ceiling only after (ceiling - 5.0) / balance steps. "
            "A needed 555 steps; the first run used 500 and stopped at 90.0, short "
            "of 99.37. The run is now 1200 steps."
        ),
    }

    exp = Experiment(
        experiment_id="frozen-ceiling",
        question="9.37 — это потолок или равновесие?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp05_frozen.py",
        parameters={
            "steps": STEPS, "every": EVERY, "n": N, "cells": CELLS,
            "policy": "stay", "maintenance": MAINTENANCE,
            "repair_cost": REPAIR_COST,
        },
    )

    results = {}
    for key, (label, cap, dmg) in arms.items():
        r = run_arm(cap, dmg)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
                "capacity": cap,
                "damage_rate": dmg,
                "alive": r["alive"],
                "total": r["total"],
                "mean_energy": r["mean_energy"],
                "max_energy": r["max_energy"],
                "energies": r["energies"],
                "predicted_ceiling": predicted_ceiling(cap, dmg),
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    pred = arithmetic["predicted"]

    # The control must fire because the arm REACHED its ceiling, not merely
    # because the energy grew. An earlier version of this experiment checked
    # `A > 9.37`, which was true at 90.0 while the arm had not yet reached its
    # own ceiling of 99.37 — the control fired for the wrong reason.
    fires = abs(results["A"]["max_energy"] - pred["A"]) < 1e-6
    exp.control(
        "fires",
        fires,
        f"A: max energy {results['A']['max_energy']:.4f} vs its own predicted "
        f"ceiling {pred['A']:.4f} — must have REACHED the ceiling, not merely "
        f"grown past B's",
    )

    silent = abs(results["B"]["max_energy"] - pred["B"]) < 1e-6
    exp.control(
        "silent",
        silent,
        f"B: max energy {results['B']['max_energy']:.4f} vs predicted "
        f"{pred['B']:.4f} — must match",
    )

    shift = pred["B"] - pred["C"]
    observed_shift = results["B"]["max_energy"] - results["C"]["max_energy"]
    specific = abs(observed_shift - shift) < 1e-6
    exp.control(
        "specific",
        specific,
        f"C: ceiling moved by {observed_shift:.6f}, the formula predicts "
        f"{shift:.6f} (= (0.10-0.02)*1.5). A different mechanism would not "
        f"move by exactly this amount.",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            "all three arms sit on the predicted ceilings; the ceiling is "
            "capacity - maintenance - damage_rate*repair_cost, not an equilibrium",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "One policy (`stay`). `remember` and `random` are not tested in this run."
    )
    exp.limitation(
        "The formula is read off `Organism::step`; if that code changes, the "
        "arithmetic must be re-derived."
    )
    exp.limitation(
        "The ceiling is a property of the model's update order, not of life."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-05: потолок или равновесие?")
    print()
    print(f"Арифметика: {arithmetic['formula']}")
    print()
    print("плечо  capacity  damage  предсказано  измерено  живых  hash")
    print("-" * 68)
    for key, (label, cap, dmg) in arms.items():
        r = results[key]
        print(
            f"  {key}    {cap:>8.1f}  {dmg:>6.2f}  {pred[key]:>11.4f}"
            f"  {r['max_energy']:>8.4f}  {r['alive']:>3}/{r['total']:<3}  {r['hash']}"
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
