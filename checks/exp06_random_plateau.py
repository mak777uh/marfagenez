"""EXP-06: почему `random` стабилизируется на 21, а не на 0?

## Наблюдение

`random` на 5000 шагах стабилизируется на **21 живом** из 40 и держится
с шага 2050 до 4550.

## Что предсказывала арифметика

Средний баланс за шаг:

```
balance = (2/3) * [0.5*(0.8-0.73) + 0.5*(0.2-0.73)]   # двигается
        + (1/3) * [0.5*(0.8-0.63) + 0.5*(0.2-0.63)]   # стоит
        = -0.1967
```

**Отрицательный.** Значит `random` теряет энергию в среднем.

**Первая гипотеза:** выживут только те, кто на богатых клетках (~20).

**Измерено:** 21 выживший, из них **11 на бедных клетках** (нечётные).

**Гипотеза ложна.**

## Вторая гипотеза

**Средний баланс по ансамблю не определяет судьбу траектории.**

Организм блуждает: попадает на богатую клетку (набирает `+0.07`), потом
на бедную (теряет `−0.53`). Но если он **успевает накопить запас** на богатой,
он переживает бедную.

**Проверка:** если это так, то распределение энергии должно быть
**двухмодальным** — одни на потолке (успели накопить), другие низко.

**И:** если убрать потолок `capacity`, запас станет больше, выживших станет больше.

## Плечи

| ключ | что меняем | предсказание |
|---|---|---|
| **A** | `capacity = 10` (контроль) | 21 выживший, на потолке |
| **B** | `capacity = 100` | **больше** выживших: запас больше |
| **C** | `move_cost = 0.01` | **больше** выживших: движение дешевле |

## Контроль (три теста)

1. **Срабатывает:** B даёт больше выживших, чем A
2. **Молчит:** A даёт ровно 21 (как в наблюдении)
3. **Специфичен:** C даёт больше выживших, но **по другой причине** —
   дешевле движение, а не больше запас. Если бы дело было только в `capacity`,
   C не изменил бы ничего.

## Запуск

    python3 checks/exp06_random_plateau.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
WSL_CORE = "/root/marfagenez/core"

sys.path.insert(0, str(ROOT))
from checks.experiment import Experiment  # noqa: E402

STEPS = 5000
EVERY = 1000
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


def run_arm(capacity: float, move_cost: float) -> dict:
    args = " ".join([
        "--policy random",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {N}",
        f"--cells {CELLS}",
        f"--capacity {capacity}",
        f"--move-cost {move_cost}",
        f"--maintenance {MAINTENANCE}",
        f"--repair-cost {REPAIR_COST}",
        f"--damage-rate {DAMAGE}",
        f"--income {INCOME}",
    ])
    out = shell(f"cd {WSL_CORE} && ./target/release/trace {args}")

    h = re.search(r"hash:\s+([0-9a-f]+)", out).group(1)
    wsl_path = re.search(r"written:\s+(\S+)", out).group(1)

    local_rel = Path("results") / "random-plateau" / Path(wsl_path).name
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
    energies = sorted(round(s["energy"], 3) for s in alive)

    # The plateau: the alive count over the last third of the run.
    tail = data["frames"][len(data["frames"]) * 2 // 3:]
    counts = [sum(1 for s in f["samples"] if s["alive"]) for f in tail]
    plateau = sum(counts) / len(counts) if counts else 0.0

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "energies": energies,
        "plateau": plateau,
        "on_rich": sum(1 for s in alive if s["cell"] % 2 == 0),
        "on_poor": sum(1 for s in alive if s["cell"] % 2 == 1),
    }


def main() -> int:
    arms = {
        "A": ("control (capacity=10, move=0.1)", CAPACITY, MOVE_COST),
        "B": ("capacity=100", 100.0, MOVE_COST),
        "C": ("move_cost=0.01", CAPACITY, 0.01),
    }

    arithmetic = {
        "balance_formula": (
            "(2/3)*[0.5*(income-move-maint-repair) + 0.5*(poor-move-maint-repair)]"
            " + (1/3)*[0.5*(income-maint-repair) + 0.5*(poor-maint-repair)]"
        ),
        "income": INCOME,
        "poor": 0.2,
        "maintenance": MAINTENANCE,
        "repair": DAMAGE * REPAIR_COST,
        "move_cost": MOVE_COST,
        "mean_balance": -0.1967,
        "first_hypothesis": (
            "Mean balance is negative, so random should lose organisms until "
            "only those on rich cells remain (~20)."
        ),
        "measured": "21 alive, 11 of them on POOR cells — the first hypothesis is false.",
        "second_hypothesis": (
            "The ensemble mean does not determine a trajectory's fate. An organism "
            "that banks energy on a rich cell survives the poor cells it wanders into. "
            "If so, raising capacity (B) or lowering move_cost (C) should raise the "
            "plateau."
        ),
    }

    exp = Experiment(
        experiment_id="random-plateau",
        question="Почему random стабилизируется на 21, а не на 0?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp06_random_plateau.py",
        parameters={
            "steps": STEPS, "every": EVERY, "n": N, "cells": CELLS,
            "policy": "random", "maintenance": MAINTENANCE,
            "repair_cost": REPAIR_COST, "damage_rate": DAMAGE,
        },
    )

    results = {}
    for key, (label, cap, mc) in arms.items():
        r = run_arm(cap, mc)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
                "capacity": cap,
                "move_cost": mc,
                "alive": r["alive"],
                "total": r["total"],
                "plateau": r["plateau"],
                "on_rich": r["on_rich"],
                "on_poor": r["on_poor"],
                "energies": r["energies"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    fires = results["B"]["plateau"] > results["A"]["plateau"] + 2.0
    exp.control(
        "fires",
        fires,
        f"B: plateau {results['B']['plateau']:.1f} vs A's {results['A']['plateau']:.1f} "
        f"— raising capacity must raise the plateau",
    )

    silent = abs(results["A"]["plateau"] - 21.0) < 2.0
    exp.control(
        "silent",
        silent,
        f"A: plateau {results['A']['plateau']:.1f} — must match the observed 21",
    )

    specific = (
        results["C"]["plateau"] > results["A"]["plateau"] + 2.0
        and abs(results["C"]["plateau"] - results["B"]["plateau"]) > 2.0
    )
    exp.control(
        "specific",
        specific,
        f"C: plateau {results['C']['plateau']:.1f}, B's {results['B']['plateau']:.1f}, "
        f"A's {results['A']['plateau']:.1f} — cheaper movement must help, but by a "
        f"different amount than more capacity, or the mechanism is not what we think",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            "the plateau rises with capacity and with cheaper movement, by different "
            "amounts: the organism banks energy on rich cells and spends it on poor "
            "ones, so the ensemble mean does not decide a trajectory's fate",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The plateau is measured over the last third of the run; a longer run may "
        "still drift."
    )
    exp.limitation(
        "The first hypothesis (only rich cells survive) was FALSE — 11 of 21 "
        "survivors are on poor cells. Recorded so it is not repeated."
    )
    exp.limitation(
        "The ensemble mean of -0.1967 is a property of the distribution, not of any "
        "one organism."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-06: почему random стабилизируется на 21?")
    print()
    print("Арифметика: средний баланс = -0.1967 (отрицательный)")
    print("Первая гипотеза: выживут только на богатых (~20)")
    print("Измерено: 21 выживший, 11 на БЕДНЫХ — гипотеза ложна")
    print()
    print("плечо  capacity  move  plateau  живых  богатых  бедных  hash")
    print("-" * 72)
    for key, (label, cap, mc) in arms.items():
        r = results[key]
        print(
            f"  {key}    {cap:>8.1f}  {mc:>4.2f}  {r['plateau']:>7.1f}  "
            f"{r['alive']:>5}  {r['on_rich']:>7}  {r['on_poor']:>6}  {r['hash']}"
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
