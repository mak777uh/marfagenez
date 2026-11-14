"""EXP-05: 9.37 — это потолок или равновесие?

## Откуда вопрос

Наблюдение 2026-11-11: `stay` и `remember` не двигаются с шага 40, и у всех
организмов энергия ровно **9.370**.

Два объяснения:
- **равновесие:** организм нашёл баланс и держится
- **потолок:** организм упёрся в предел, который задаёт модель

## Арифметика (написана ДО прогона, §1)

**Версия 2026-11-13, после переноса clamp в конец шага.**

Старая версия этого файла предсказывала `capacity - maintenance -
damage_rate * repair_cost = 9.37`. Это было верно, пока `min(capacity)`
стоял сразу после дохода. Коммит `b4d116e` перенёс его в конец шага
(иначе `move_cost` стирался потолком, см.
`docs/FINDING-the-cap-is-applied-after-the-spend.md`), и предсказание
перестало соответствовать коду.

Текущий порядок в `Organism::step`:
1. `energy += taken`
2. `energy -= maintenance`
3. `damage += damage_rate`
4. ремонт: `energy -= repaired * repair_cost`
5. `energy = min(energy, capacity)`   <- clamp ПОСЛЕДНИМ

Пока `energy + taken - maintenance - damage_rate*repair_cost >= capacity`,
шаг заканчивается на `capacity`:
```
E_max = capacity
```
Расходы не двигают потолок — они решают, ДОСТИГАЕТ ли организм потолка.
Баланс на богатой клетке (доход 0.8, клетка насыщена) должен быть
положительным, иначе организм умрёт раньше:
```
balance = 0.8 - maintenance - damage_rate * repair_cost
```

При `maintenance = 0.6`, `repair_cost = 1.5`:
```
damage_rate = 0.02 -> balance = +0.17  (потолок достижим)
damage_rate = 0.10 -> balance = +0.05  (потолок достижим, но медленнее)
```

## Плечи

| ключ | что меняем | предсказанный потолок | баланс на богатой |
|---|---|---|---|
| **A** | `capacity = 100.0` | **100.0** | +0.170 |
| **B** | ничего (контроль) | **10.0** | +0.170 |
| **C** | `damage_rate = 0.10` | **10.0** | +0.050 |

## Контроль (§2)

1. **Срабатывает:** A доходит до 100.0 — своего собственного потолка,
   а не просто «выше, чем у B»
2. **Молчит:** B даёт ровно 10.0
3. **Специфичен:** C при впятеро большем `damage_rate` даёт **тот же**
   10.0, что и B. Это и есть подпись механизма: потолок задаёт `capacity`,
   а не расходы. Если бы энергию держало равновесие «доход = расходы», C
   ушёл бы с потолка (баланс +0.05 всё ещё положителен, но запас
   прочности втрое меньше, и любая просадка дохода его бы сбила).

## Почему это специфично

Формула `E_max = capacity` не содержит `damage_rate`, `maintenance` или
`repair_cost`. Поэтому C обязан совпасть с B с точностью до 1e-6, хотя
`damage_rate` у него в пять раз больше. Совпадение — предсказание, а не
отсутствие эффекта: A показывает, что потолок двигается, когда двигают
`capacity`.

Старая версия проверяла обратное — что C сдвинется на
`(0.10-0.02)*1.5 = 0.12`. Она провалилась 2026-11-13 именно потому, что
clamp переехал, а арифметика осталась. Провал был верным: код и текст
разошлись.

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
RICH_INCOME = 0.8

#: Where `trace` writes its JSON, relative to the crate. The file is copied
#: into `results/frozen-ceiling/` below; this is only the staging path.
TRACE_DIR = "results/frozen-ceiling"


def predicted_ceiling(capacity: float) -> float:
    """The arithmetic: where the energy stops.

    With the clamp last, the step ends on `capacity` whenever the income covers
    the spend. The spend does not enter this number — it only decides whether
    the ceiling is reached at all.
    """
    return capacity


def balance_on_rich(damage_rate: float) -> float:
    """Income minus spend on a saturated cell. Must be > 0 to reach the ceiling."""
    return RICH_INCOME - MAINTENANCE - damage_rate * REPAIR_COST


def in_wsl() -> bool:
    """True when we are already inside WSL (no `wsl` wrapper needed)."""
    try:
        with open("/proc/version", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def shell(cmd: str) -> str:
    """Runs a shell command, in WSL if we are there, else through `wsl`."""
    argv = ["bash", "-c", cmd] if in_wsl() else ["wsl", "-e", "bash", "-c", cmd]
    out = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        raise SystemExit(f"command failed:\n{cmd}\n{out.stderr}")
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
        # `trace` no longer picks a path for itself: since the 2026-11-13
        # change the default is to print and write nothing, and it says
        # `written: nothing`. The path has to be asked for.
        f"--out {WSL_CORE}/{TRACE_DIR}/trace-stay.json",
    ])
    out = shell(f"cd {WSL_CORE} && ./target/release/trace {args}")

    m = re.search(r"hash:\s+([0-9a-f]+)", out)
    if not m:
        raise SystemExit(f"no hash in output:\n{out}")
    h = m.group(1)

    # `trace` prints `wrote <path>` on stderr and `written: <path>` on stdout;
    # the default is `written: nothing`, which is not a path.
    f = re.search(r"written:\s+(\S+)", out)
    if not f or f.group(1) == "nothing":
        raise SystemExit(f"trace wrote no file:\n{out}")
    wsl_path = f.group(1)

    # Copy the trace into the repo so the artifact is on disk here.
    local_rel = Path("results") / "frozen-ceiling" / Path(wsl_path).name
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
        "formula": "capacity",
        "formula_note": (
            "The clamp runs LAST in Organism::step (commit b4d116e), so the "
            "step ends on capacity whenever income covers the spend. The spend "
            "does not enter the ceiling; it only decides whether it is reached."
        ),
        "superseded_formula": "capacity - maintenance - damage_rate * repair_cost",
        "superseded_note": (
            "That was correct while min(capacity) ran right after the income. "
            "The 2026-11-13 run of this experiment failed on it: A measured "
            "100.0 not 99.37, B 10.0 not 9.37, C 10.0 not 9.25. The failure was "
            "correct — the code and the text had diverged."
        ),
        "maintenance": MAINTENANCE,
        "repair_cost": REPAIR_COST,
        "rich_income": RICH_INCOME,
        "predicted": {
            key: predicted_ceiling(cap) for key, (_, cap, _) in arms.items()
        },
        "balance_on_rich": {
            key: balance_on_rich(dmg) for key, (_, _, dmg) in arms.items()
        },
        "balance_note": (
            "The balance must stay positive or the organism dies before reaching "
            "the ceiling. At damage_rate=0.10 the balance is +0.05."
        ),
        "steps_to_ceiling": {
            "A": (predicted_ceiling(100.0) - 5.0) / balance_on_rich(DAMAGE_BASE),
            "B": 0.0,
            "C": (predicted_ceiling(CAPACITY) - 5.0) / balance_on_rich(DAMAGE_HIGH),
        },
        "steps_note": (
            "An arm reaches its ceiling only after (ceiling - 5.0) / balance "
            "steps. A needs 559 steps; the run is 1200. C needs 100."
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
                "predicted_ceiling": predicted_ceiling(cap),
                "balance_on_rich": balance_on_rich(dmg),
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

    # Specific: five times the damage rate must NOT move the ceiling. The
    # ceiling is capacity; the spend decides only whether it is reached. A
    # mechanism that held the energy at an income/spend equilibrium would put
    # C below B by (0.10-0.02)*1.5 = 0.12.
    observed_shift = results["B"]["max_energy"] - results["C"]["max_energy"]
    specific = abs(observed_shift) < 1e-6
    exp.control(
        "specific",
        specific,
        f"C: ceiling moved by {observed_shift:.6f} when damage_rate went "
        f"0.02 -> 0.10; the formula says 0.000000 because the clamp is last. "
        f"An income/spend equilibrium would have moved it by "
        f"{(DAMAGE_HIGH - DAMAGE_BASE) * REPAIR_COST:.6f}.",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            "all three arms sit on their capacity; the ceiling is capacity, "
            "not an income/spend equilibrium and not capacity minus the spend",
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
        "arithmetic must be re-derived. It has already changed once (b4d116e)."
    )
    exp.limitation(
        "The ceiling is a property of the model's update order, not of life. "
        "It says nothing about whether an organism SHOULD be able to sit at "
        "its capacity; it says only that this model lets it."
    )
    exp.limitation(
        "The `specific` control cannot distinguish `E_max = capacity` from any "
        "other formula that does not contain the spend. It rules out the "
        "income/spend equilibrium, not every alternative."
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
    return 0 if v["kind"] in ("passed", "void") else 1


if __name__ == "__main__":
    sys.exit(main())
