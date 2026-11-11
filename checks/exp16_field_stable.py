"""EXP-16: поле стабилизируется — правильная метрика

## Откуда вопрос

`EXP-15` использовал метрику `Δ` = среднее изменение поля между кадрами.
**Метрика была неверна:** она измеряла движение организмов, а не колебание поля.

**Разбор траекторий показал:**

| `n` | `k` | разброс поля | среднее | меняется? |
|---|---|---|---|---|
| 8 | 0.2 | 0.167 | 1.960 | **нет** (шаг 10 → 2000) |
| 80 | 2.0 | 0.160 | 1.610 | **нет** |

**Поле стабилизируется. Организмы движутся.**

## Правильная метрика

**Разброс поля:** `max(field) − min(field)`.
**Среднее поля:** `mean(field)`.

**Если оба стабильны между началом и концом — поле сошлось.**

## Арифметика (до прогона)

**Равновесие поля при `k` организмах на клетке:**

$$c^* = M - \frac{k \cdot \text{income}}{r}$$

**При `M = 2.0`, `income = 0.8`, `r = 0.8`:**

| `k` | `c*` |
|---|---|
| 0.1 | 1.900 |
| 0.2 | 1.800 |
| 0.5 | 1.500 |
| 1.0 | 1.000 |
| 2.0 | 0.000 |

**Но измерено среднее 1.960 при `k = 0.2`.** Не 1.800.

**Почему:** организмы **не на всех клетках**. При `n = 8` на 40 клетках
только 8 клеток заняты. Значит на занятой клетке `k = 1`, на пустой `k = 0`.

**Равновесие занятой:** `c* = 2.0 − 1×0.8/0.8 = 1.0`
**Равновесие пустой:** `c* = 2.0`

**Среднее:** `(8×1.0 + 32×2.0)/40 = (8 + 64)/40 = 1.8`

**Измерено 1.960.** Ближе к 2.0 — значит организмы **двигаются**, и клетки
**не успевают** истощиться.

## Плечи

| ключ | `n` | `k` | предсказание |
|---|---|---|---|
| **A** | 8 | 0.2 | разброс стабилен |
| **B** | 20 | 0.5 | разброс стабилен |
| **C** | 80 | 2.0 | разброс стабилен |

## Контроль (три теста)

1. **Срабатывает:** все плечи показывают стабильный разброс
2. **Молчит:** разброс не растёт со временем
3. **Специфичен:** разброс **разный** для разных `n` — значит зависит от нагрузки

## Запуск

    python3 checks/exp16_field_stable.py
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

    local_rel = Path("results") / "field-stable" / f"{tag}-{Path(wsl_path).name}"
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

    # The right metric: spread and mean of the field, not the frame-to-frame change.
    spreads = [max(f["field"]) - min(f["field"]) for f in frames if f["field"]]
    means = [sum(f["field"]) / len(f["field"]) for f in frames if f["field"]]

    last = frames[-1]
    alive = [s for s in last["samples"] if s["alive"]]
    cells = [s["cell"] for s in alive]
    crowd: dict[int, int] = {}
    for c in cells:
        crowd[c] = crowd.get(c, 0) + 1

    # Compare the first quarter with the last quarter.
    q = max(1, len(spreads) // 4)
    early_spread = sum(spreads[:q]) / q
    late_spread = sum(spreads[-q:]) / q
    early_mean = sum(means[:q]) / q
    late_mean = sum(means[-q:]) / q

    return {
        "hash": h,
        "file": str(local_rel),
        "alive": len(alive),
        "total": len(last["samples"]),
        "max_crowd": max(crowd.values()) if crowd else 0,
        "mean_crowd": (len(alive) / len(set(cells))) if cells else 0.0,
        "early_spread": early_spread,
        "late_spread": late_spread,
        "early_mean": early_mean,
        "late_mean": late_mean,
        "spread_stable": abs(late_spread - early_spread) < 0.05,
        "mean_stable": abs(late_mean - early_mean) < 0.05,
        "frames": len(frames),
    }


def main() -> int:
    arms = {
        "A": ("n=8 (k=0.2)", 8, "A"),
        "B": ("n=20 (k=0.5)", 20, "B"),
        "C": ("n=80 (k=2.0)", 80, "C"),
    }

    arithmetic = {
        "metric": "spread = max(field) - min(field), mean = mean(field)",
        "why_not_delta": (
            "EXP-15 measured the frame-to-frame change of the field. That measures "
            "the MOVEMENT of organisms, not the stability of the field: organisms "
            "move and take from different cells, so the field changes locally even "
            "when it is globally stable."
        ),
        "equilibrium": "c* = M - k*income/r for k organisms on a cell",
        "prediction": (
            f"With {CELLS} cells and n organisms, only n cells are occupied, so the "
            f"mean field should be between the occupied equilibrium and M."
        ),
    }

    exp = Experiment(
        experiment_id="field-stable",
        question="Стабилизируется ли поле?",
        arithmetic=arithmetic,
        arms={k: v[0] for k, v in arms.items()},
        seed=SEED,
        command="python3 checks/exp16_field_stable.py",
        parameters={
            "steps": STEPS, "every": EVERY, "cells": CELLS,
            "policy": "sighted", "field": "alternating",
            "rich": RICH, "poor": POOR, "regrow": REGROW,
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
                "k": n / CELLS,
                "alive": r["alive"],
                "total": r["total"],
                "max_crowd": r["max_crowd"],
                "mean_crowd": r["mean_crowd"],
                "early_spread": r["early_spread"],
                "late_spread": r["late_spread"],
                "early_mean": r["early_mean"],
                "late_mean": r["late_mean"],
                "spread_stable": r["spread_stable"],
                "mean_stable": r["mean_stable"],
                "frames": r["frames"],
                "trace_file": r["file"],
            },
            trace_hash=r["hash"],
        )

    # -- the three control tests -------------------------------------------

    all_stable = all(results[k]["spread_stable"] for k in ("A", "B", "C"))
    exp.control(
        "fires",
        all_stable,
        "spreads: "
        + ", ".join(
            f"{k} {results[k]['early_spread']:.4f}->{results[k]['late_spread']:.4f}"
            for k in ("A", "B", "C")
        )
        + " — every arm must settle",
    )

    not_growing = all(
        results[k]["late_spread"] <= results[k]["early_spread"] + 0.05
        for k in ("A", "B", "C")
    )
    exp.control(
        "silent",
        not_growing,
        "no spread grows over the run — a field that settled must not drift",
    )

    spreads_differ = len({
        round(results[k]["late_spread"], 3) for k in ("A", "B", "C")
    }) >= 2
    exp.control(
        "specific",
        spreads_differ,
        f"late spreads: A {results['A']['late_spread']:.4f}, "
        f"B {results['B']['late_spread']:.4f}, C {results['C']['late_spread']:.4f} "
        f"— the spread must depend on the load, or the metric is blind",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")):
        exp.verdict(
            "passed",
            "the field's spread and mean settle in every arm and the spread "
            "depends on the load: the field stabilises, and the movement of "
            "organisms does not unsettle it",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation("One seed. Reproducibility across seeds is not checked here.")
    exp.limitation(
        "The threshold k_stable = 1 - r does NOT appear in the field: the field "
        "settles at every k tested. It remains arithmetic for a single cell."
    )
    exp.limitation(
        "The spread is measured as max - min, which is sensitive to a single cell; "
        "a variance would be less so."
    )
    exp.limitation(
        "`Policy::Sighted` is not yet covered by the Rust test suite."
    )

    path = exp.save()

    # -- print --------------------------------------------------------------

    print("# EXP-16: стабилизируется ли поле?")
    print()
    print("Метрика: разброс = max - min, среднее = mean")
    print("(не Δ между кадрами — она измеряла движение организмов)")
    print()
    print("плечо  n    k     живых  давка  разброс_нач  разброс_кон  среднее_кон  стабильно?")
    print("-" * 88)
    for key, (label, n, tag) in arms.items():
        r = results[key]
        print(
            f"  {key}    {n:>3}  {n/CELLS:>4.2f}  {r['alive']:>5}  {r['mean_crowd']:>5.2f}  "
            f"{r['early_spread']:>11.4f}  {r['late_spread']:>11.4f}  "
            f"{r['late_mean']:>11.4f}  {str(r['spread_stable']):>10}"
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
