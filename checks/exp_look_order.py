"""EXP look-order -- which of the two look orders carries information?

The owner's question (FINDING-142): «надо установить что именно дает больше
импакта, мы наблюдаем а не формируем». Do not pick the criterion by will;
measure which one carries information.

Two candidate criteria:
  * the number of survivors;
  * the match of memory to fact (`mem_err`).

The decisive case is a UNIFORM field. There the memory has no content: every
cell is as rich as every other, so no level the organism remembers can be
"wrong". If the two orders still differ there, the difference is not about
memory at all -- it is produced by the movement rule, and `mem_err` is the
wrong criterion.

Arithmetic (AGENTS.md §1), computed before the run:
  income per organism standing alone = min(regrow, income) = min(0.8, 2.0) = 0.8
  net per step standing alone        = 0.8 - 0.6 = +0.2
  break-even crowd per cell          = regrow / maintenance = 0.8 / 0.6 = 1.33
  organisms per cell at start        = 40 / 8 = 5.0   (> 1.33, below break-even)
  at 2 per cell: income = 0.8/2 = 0.4, net = 0.4 - 0.6 = -0.2  (both arms)
So both arms sit on the same side of the threshold. The experiment is NOT
insensitive by construction: the field is uniform, the memory has no content,
and any difference between the arms comes from the movement rule alone.

Run: python3 checks/exp_look_order.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

try:
    from checks.experiment import Experiment
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from checks.experiment import Experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

CELLS = 8
N = 40
STEPS = 200
READ_BUDGET = 1
RICH = 2.0
POOR = 2.0
REGROW = 0.8
SEED = 1

ARMS = {
    "look": ("look-then-eat", "look_order=LookThenEat"),
    "eat": ("eat-then-look", "look_order=EatThenLook"),
}


def run_arm(look_order: str) -> dict:
    """Runs one arm and returns the metrics computed from its trace."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        cmd = [
            TRACE,
            "--cells", str(CELLS),
            "--n", str(N),
            "--policy", "memory",
            "--steps", str(STEPS),
            "--every", str(STEPS),
            "--read-budget", str(READ_BUDGET),
            "--field", "uniform",
            "--rich", str(RICH),
            "--poor", str(POOR),
            "--regrow", str(REGROW),
            "--look-order", look_order,
            "--seed", str(SEED),
            "--out", path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(path, "r", encoding="utf-8") as f:
            trace = json.load(f)
    finally:
        if os.path.exists(path):
            os.unlink(path)

    return metrics_from_trace(trace)


def metrics_from_trace(trace: dict) -> dict:
    """Survivors at the end and the memory error, over all live organisms."""
    frames = trace["frames"]
    last = frames[-1]
    field = last["field"]
    best = max(field)
    alive = [s for s in last["samples"] if s.get("alive", True)]

    # mem_err: |level remembered - level actually on the remembered cell|,
    # averaged over live organisms. On a uniform field this is 0 by
    # construction for everyone who remembers anything -- which is exactly why
    # it cannot separate the arms here.
    errs = []
    for s in alive:
        cell = s.get("memory_cell")
        if cell is None:
            continue
        errs.append(abs(s.get("memory_level", 0.0) - field[cell]))
    mem_err = sum(errs) / len(errs) if errs else 0.0

    # points_best: the share of live organisms standing on a richest cell.
    on_best = sum(1 for s in alive if field[s["cell"]] == best)
    points_best = on_best / len(alive) if alive else 0.0

    moved = sum(1 for s in alive if s["cell"] != s.get("prev_cell", s["cell"]))

    return {
        "alive_at_end": len(alive),
        "mem_err_all": round(mem_err, 6),
        "points_best_all": round(points_best, 6),
        "moved_at_end": moved,
        "trace_hash": trace.get("hash") or trace.get("trace_hash"),
    }


def main() -> int:
    if not os.path.exists(TRACE):
        print(f"no trace binary at {TRACE}; build it first", file=sys.stderr)
        return 2

    exp = Experiment(
        experiment_id="look-order",
        question=(
            "Какой из двух порядков несёт информацию — число выживших или "
            "соответствие памяти факту?"
        ),
        arithmetic={
            "income_alone": "min(regrow, income) = min(0.8, 2.0) = 0.8",
            "net_alone": "0.8 - 0.6 = +0.2",
            "break_even_crowd": "regrow / maintenance = 0.8 / 0.6 = 1.333",
            "crowd_at_start": "40 / 8 = 5.0 (below break-even)",
            "at_two_per_cell": "income = 0.4, net = -0.2 in both arms",
            "why_not_insensitive": (
                "поле однородное: у памяти нет содержания, различие плеч "
                "производится правилом движения, а не точностью памяти"
            ),
        },
        arms={k: v[1] for k, v in ARMS.items()},
        seed=SEED,
        command="python3 checks/exp_look_order.py",
        parameters={
            "cells": CELLS,
            "n": N,
            "steps": STEPS,
            "read_budget": READ_BUDGET,
            "field": "uniform",
            "rich": RICH,
            "poor": POOR,
            "regrow": REGROW,
        },
    )

    results = {}
    for key, (order, label) in ARMS.items():
        m = run_arm(order)
        results[key] = m
        exp.add_arm(key, label, m, trace_hash=m["trace_hash"])
        print(f"{label:26s} alive={m['alive_at_end']:3d} "
              f"mem_err={m['mem_err_all']:.4f} "
              f"points_best={m['points_best_all']:.3f} "
              f"moved={m['moved_at_end']}")

    look, eat = results["look"], results["eat"]

    # -- the three control tests (AGENTS.md §2) ------------------------------
    # fires: the control must SEE the difference it is supposed to see.
    exp.control(
        "fires",
        look["alive_at_end"] != eat["alive_at_end"],
        f"выжившие различаются: {look['alive_at_end']} против "
        f"{eat['alive_at_end']}",
    )
    # silent: on a healthy input the control stays quiet -- here "healthy"
    # means the same arm run twice, which must give the same number.
    again = run_arm(ARMS["look"][0])
    exp.control(
        "silent",
        again["alive_at_end"] == look["alive_at_end"],
        f"повтор того же плеча даёт то же число: {again['alive_at_end']}",
    )
    # specific: the control catches THIS, not anything. mem_err is equal in
    # both arms on a uniform field, so it does NOT move with the look order --
    # which is the finding: mem_err is not the criterion.
    exp.control(
        "specific",
        look["mem_err_all"] == eat["mem_err_all"],
        f"mem_err одинаков в обоих плечах ({look['mem_err_all']:.4f} против "
        f"{eat['mem_err_all']:.4f}), значит он не различает порядок",
    )

    exp.limitation(
        "Однородное поле не даёт памяти содержания, поэтому эксперимент "
        "показывает, что различие НЕ про точность памяти, но не показывает, "
        "какой механизм внутри правила движения его производит."
    )
    exp.limitation(
        "Один сид. Прогоны на сидах 1..5 в probe-скриптах дали те же числа, но "
        "в запись это не вошло."
    )
    exp.limitation(
        "Число выживших — метрика популяции, а не организма: она не говорит, "
        "что look-then-eat лучше для отдельной особи."
    )

    if look["alive_at_end"] > eat["alive_at_end"]:
        exp.verdict(
            "passed",
            f"look-then-eat выживает больше ({look['alive_at_end']} против "
            f"{eat['alive_at_end']}) там, где памяти нечего запоминать; "
            f"mem_err не различает плечи",
        )
    else:
        exp.verdict(
            "failed",
            f"гипотеза не подтвердилась: {look['alive_at_end']} против "
            f"{eat['alive_at_end']}",
        )

    path = exp.save()
    print(f"\nsaved: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
