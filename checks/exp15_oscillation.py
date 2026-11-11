"""EXP-15: третий порог в реальном прогоне — колеблется ли поле?

## Откуда вопрос

`Regimes.lean` доказал два режима. Численная проверка показала третий порог:

$$\text{cellStepRationed}(c) - c^* = (c - c^*)(1 - r - k)$$

**Устойчиво при `k < 1 − r`.**

При `r = 0.8`: `k < 0.2`.

**Но это арифметика одной клетки.** В реальном прогоне организмы двигаются,
и `k` меняется.

## Арифметика (до прогона)

**Три порога при `M=2.0`, `r=0.8`, `income=0.8`:**

| порог | формула | значение |
|---|---|---|
| устойчивости | `1 − r` | **0.2** |
| полного кормления | `(M−income)·r/income` | **1.2** |
| выживания | `M·r/income` | **2.0** |

**При 40 клетках:**

| `n` | `k = n/40` | режим |
|---|---|---|
| 4 | 0.1 | **устойчиво** |
| 8 | 0.2 | **граница** |
| 20 | 0.5 | **колебания** |
| 80 | 2.0 | **сильные колебания** |

## Метрика

**Изменение поля между кадрами:**

$$\Delta = \frac{1}{\text{cells}} \sum_i |c_i(t+1) - c_i(t)|$$

**Сходящееся:** `Δ → 0`.
**Колеблющееся:** `Δ` не убывает.

## Плечи

| ключ | `n` | `k` | предсказание |
|---|---|---|---|
| **A** | 4 | 0.1 | `Δ → 0` (устойчиво) |
| **B** | 8 | 0.2 | граница |
| **C** | 20 | 0.5 | `Δ` не убывает |
| **D** | 80 | 2.0 | `Δ` большая |

## Контроль (три теста)

1. **Срабатывает:** A показывает затухание (`Δ` в конце < `Δ` в начале)
2. **Молчит:** A не колеблется (`Δ` мала)
3. **Специфичен:** D колеблется сильнее A — и **порог между ними**

## Запуск

    python3 checks/exp15_oscillation.py
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
EVERY = 10
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
    out = subprocess.run(argv, capture_output=True, text=True, timeout=900)
    if out.returncode != 0:
        raise SystemExit(f"command failed:\n{cmd}\n{out.stderr}")
    return out.stdout


def run_arm(n: int) -> dict:
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

    local_rel = Path("results") / "oscillation" / Path(wsl_path).name
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

    # The change of the field between consecutive frames.
    deltas = []
    for a, b in zip(frames, frames[1:]):
        fa, fb = a["field"], b["field"]
        if not fa or not fb or len(fa) != len(fb):
            continue
        d = sum(abs(x - y) for x, y in zip(fa, fb)) / len(fa)
        deltas.append(d)

    last = frames[-1]
    alive = [s for s in last["samples"] if s["alive"]]
    cells = [s["cell"] for s in alive]
    crowd: dict[int, int] = {}
    for c in cells:
        crowd[c] = crowd.get(c, 0) + 1

    # Early and late change, to see whether the change decays.
    k = len(deltas)
    early = sum(deltas[: max(1, k // 5)]) / max(1, k // 5) if deltas else 0.0
    late = sum(deltas[-max(1, k // 5):]) / max(1, k // 5) if deltas else 0.0

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "max_crowd": max(crowd.values()) if crowd else 0,
        "mean_crowd": (len(alive) / len(set(cells))) if cells else 0.0,
        "mean_delta": (sum(deltas) / len(deltas)) if deltas else 0.0,
        "early_delta": early,
        "late_delta": late,
        "decays": late < early * 0.5,
        "frames": len(frames),
    }


def main() -> int:
    arms = {
        "A": ("n=4 (k=0.1)", 4),
        "B": ("n=8 (k=0.2)", 8),
        "C": ("n=20 (k=0.5)", 20),
        "D": ("n=80 (k=2.0)", 80),
    }

    k_stable = 1 - REGROW
    k_feed = (RICH - INCOME) * REGROW / INCOME
    k_max = RICH * REGROW / INCOME

    arithmetic = {
        "thresholds": {
            "k_stable": k_stable,
            "k_feed": k_feed,
            "k_max": k_max,
        },
        "metric": "mean |c_i(t+1) - c_i(t)| over the field",
        "prediction": (
            f"Below k_stable = {k_stable} the field change must decay; above it "
            f"the change must not decay. With {CELLS} cells, k = n/{CELLS}, so "
            f"n = {int(k_stable * CELLS)} is the boundary."
        ),
        "note": (
            "This is a single-cell arithmetic applied to a field where organisms "
            "move, so k is not exactly n/cells. The boundary may shift."
        ),
    }

    exp = Experiment(
        experiment_id="oscillation",
        question="Колеблется ли поле выше третьего порога?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp15_oscillation.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS,
            "policy": "sighted", "field": "alternating",
            "rich": RICH, "poor": POOR, "regrow": REGROW,
            "maintenance": MAINTENANCE, "repair_cost": REPAIR_COST,
            "damage_rate": DAMAGE,
        },
    )

    results: dict[str, dict] = {}
    for key, (label, n) in arms.items():
        r = run_arm(n)
        results[key] = r
        exp.add_arm(
            key,
            label,
            {
                "n": n,
                "k": n / CELLS,
                "alive": r["alive"],
                "total": r["total"],
                "max_crowd": r["max_crowd"],
                "mean_crowd": r["mean_crowd"],
                "mean_delta": r["mean_delta"],
                "early_delta": r["early_delta"],
                "late_delta": r["late_delta"],
                "decays": r["decays"],
                "frames": r["frames"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    fires = results["A"]["decays"]
    exp.control(
        "fires",
        fires,
        f"A (k=0.1): change {results['A']['early_delta']:.5f} -> "
        f"{results['A']['late_delta']:.5f} — below the threshold the change must decay",
    )

    silent = results["A"]["late_delta"] < 0.01
    exp.control(
        "silent",
        silent,
        f"A: late change {results['A']['late_delta']:.5f} — a stable field must "
        f"stop changing",
    )

    specific = results["D"]["late_delta"] > results["A"]["late_delta"] * 5
    exp.control(
        "specific",
        specific,
        f"D (k=2.0): late change {results['D']['late_delta']:.5f} against A's "
        f"{results['A']['late_delta']:.5f} — above the threshold the change must "
        f"persist",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        # Where does the change stop decaying?
        boundary = None
        for key in ("A", "B", "C", "D"):
            if not results[key]["decays"]:
                boundary = key
                break
        exp.verdict(
            "passed",
            f"the field change decays at k=0.1 and persists at k=2.0; the first arm "
            f"that does not decay is {boundary or 'none'}, against a predicted "
            f"boundary at k={k_stable:.2f}",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The threshold k_stable = 1 - r is arithmetic for ONE cell; in a field the "
        "organisms move and k is not exactly n/cells, so the boundary may shift."
    )
    exp.limitation(
        "The metric is the mean absolute change of the field; a different metric "
        "might place the boundary elsewhere."
    )
    exp.limitation(
        "`Policy::Sighted` is not yet covered by the Rust test suite."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-15: колеблется ли поле выше третьего порога?")
    print()
    print(f"Арифметика: k_stable = 1-r = {k_stable:.2f}, "
          f"k_feed = {k_feed:.2f}, k_max = {k_max:.2f}")
    print(f"  при {CELLS} клетках граница при n = {int(k_stable * CELLS)}")
    print()
    print("плечо  n    k     живых  давка  Δ_начало  Δ_конец  затухает?")
    print("-" * 68)
    for key, (label, n) in arms.items():
        r = results[key]
        print(
            f"  {key}    {n:>3}  {n/CELLS:>4.2f}  {r['alive']:>5}  {r['mean_crowd']:>5.2f}  "
            f"{r['early_delta']:>9.5f}  {r['late_delta']:>8.5f}  {str(r['decays']):>9}"
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
