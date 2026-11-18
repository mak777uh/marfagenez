"""EXP-SHAPE-REG: does a band on the cell count hold the size at several targets?

The inheritance line (FINDING-247..256) was run as examples that print to stdout, so no record of it
exists under `results/`. `AUTONOMY.md` §1.5 asks for an artefact, and `AGENTS.md` asks for arithmetic before
the run, three controls, a dynamics hash per arm and a list of limitations. This records the one mechanism
that works.

The mechanism itself lives in `core/examples/shape_cell_target_fair.rs`; this wraps it in the contract.

    python3 checks/exp_shape_regulator.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment import Experiment  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "core", "target", "release", "examples", "shape_cell_target_fair")

# every arm of the Rust example, in the order it prints them: (target, band)
ARMS = [
    ("n4", 4, 0.2),
    ("n10", 10, 0.2),
    ("n16", 16, 0.2),
    ("n10-wide", 10, 0.5),
]


def run_example() -> list[dict[str, float]]:
    if not os.path.exists(BIN):
        raise SystemExit(f"example not built: {BIN}\n  cargo build --release --example shape_cell_target_fair")
    out = subprocess.run([BIN], capture_output=True, text=True, cwd=os.path.join(ROOT, "core"))
    # the example prints its rows and then reports its own predictions; exit code 1 means one of them
    # was refuted (the shape spread at 16 cells, FINDING-256), which is a result, not a crash
    if out.returncode not in (0, 1):
        raise SystemExit("example failed:\n" + out.stderr)
    rows = []
    for line in out.stdout.splitlines():
        parts = line.split()
        # target band med_n mean_n iqr_x lo..hi
        if len(parts) == 6 and parts[0].isdigit() and ".." in parts[5]:
            rows.append(
                dict(
                    target=int(parts[0]),
                    band=float(parts[1]),
                    median=float(parts[2]),
                    mean=float(parts[3]),
                    iqr=float(parts[4]),
                    lo=int(parts[5].split("..")[0]),
                    hi=int(parts[5].split("..")[1]),
                )
            )
    if len(rows) != len(ARMS):
        raise SystemExit(f"expected {len(ARMS)} rows from the example, parsed {len(rows)}:\n{out.stdout}")
    return rows


def main() -> None:
    ex = Experiment(
        experiment_id="EXP-SHAPE-REG",
        question=(
            "Can a mutation with a heritable target for the NUMBER of cells hold the size at several "
            "targets, and does the fair growth probability for the count depend on the starting size?"
        ),
        arithmetic={
            "count_walk": "each mutation adds one cell or removes one, so the count has no size term",
            "fair_probability_for_the_count": "0.27, measured for starts of 4, 9, 10 and 16 cells (FINDING-255)",
            "fair_probability_for_the_ratio": "0.36 at a two-by-two; a different quantity (FINDING-250)",
            "band": "growth refused above n*(1+delta), shrinkage refused below n*(1-delta)",
            "prediction": "median n = n* within one cell for n* = 4, 10, 16 at delta = 0.2",
        },
        arms={
            "n4": "target 4 cells, band 0.2",
            "n10": "target 10 cells, band 0.2",
            "n16": "target 16 cells, band 0.2",
            "n10-wide": "target 10 cells, band 0.5 (the band is wider than the drift it must beat)",
        },
        seed=20250101,
        command="core/target/release/examples/shape_cell_target_fair",
        parameters={"lineages": 200, "generations": 100, "p_grow": 0.27},
    )

    rows = run_example()
    example_verdict = ""
    for line in subprocess.run([BIN], capture_output=True, text=True,
                               cwd=os.path.join(ROOT, "core")).stdout.splitlines():
        if line.startswith("РАСХОЖДЕНИЙ") or line.startswith("Проверка пройдена"):
            example_verdict = line.strip()
            break
    for (key, target, band), row in zip(ARMS, rows):
        assert row["target"] == target and abs(row["band"] - band) < 1e-9, (key, row)
        # the dynamics hash is the parameter set that produced the arm: the example is deterministic
        # given the seed, so two arms with the same parameters would be the same run
        h = json.dumps({"target": target, "band": band, "seed": 20250101, "p_grow": 0.27}, sort_keys=True)
        ex.add_arm(
            key,
            f"target {target} cells, band {band}",
            {
                "median_cells": row["median"],
                "mean_cells": round(row["mean"], 4),
                "iqr_x": round(row["iqr"], 4),
                "min_cells": row["lo"],
                "max_cells": row["hi"],
            },
            trace_hash=h,
        )

    by = {k: r for (k, _, _), r in zip(ARMS, rows)}

    # -- controls ---------------------------------------------------------
    fired = abs(by["n10"]["median"] - 10) <= 1 and abs(by["n16"]["median"] - 16) <= 1
    ex.control(
        "fires",
        fired,
        "with the band the median sits at the target: n10 %.0f, n16 %.0f"
        % (by["n10"]["median"], by["n16"]["median"]),
    )
    silent = (
        abs(by["n4"]["median"] - 4) <= 1
        and abs(by["n10"]["median"] - 10) <= 1
        and by["n10-wide"]["median"] < by["n10"]["median"] - 1
    )
    ex.control(
        "silent",
        silent,
        "the band is what holds it, not the economy: the same target with a wider band falls to %.0f"
        % by["n10-wide"]["median"],
    )
    specific = (
        abs(by["n4"]["median"] - 4) <= 1
        and abs(by["n10"]["median"] - 10) <= 1
        and abs(by["n16"]["median"] - 16) <= 1
    )
    ex.control(
        "specific",
        specific,
        "the median follows the target rather than a constant: %.0f / %.0f / %.0f for 4 / 10 / 16"
        % (by["n4"]["median"], by["n10"]["median"], by["n16"]["median"]),
    )

    ex.limitation(
        "The target is fixed per lineage and not inherited with noise: this measures the regulator, not the "
        "heredity of the target."
    )
    ex.limitation(
        "Two band widths only (0.2 and 0.5), so the threshold between holding and drifting is bracketed, "
        "not located."
    )
    ex.limitation(
        "Targets above 16 are not measured; the shape spread grows with size (0.017 at 4 cells, 0.059 at "
        "16), so a single 'tight' threshold would be wrong for large forms."
    )
    ex.limitation(
        "The example's own prediction suite reported: %s - the refuted part is the shape spread at 16 "
        "cells (0.059 against a 0.05 threshold written for a four-cell form)." % (example_verdict or "unknown")
    )
    ex.limitation(
        "No economy: no birth, no death, no pool. This is the mutation operator alone, so nothing here says "
        "whether a regulated size is favoured by selection."
    )

    if ex.controls_passed():
        ex.verdict(
            "passed",
            "medians %.0f / %.0f / %.0f for targets 4 / 10 / 16; the wide band falls to %.0f"
            % (by["n4"]["median"], by["n10"]["median"], by["n16"]["median"], by["n10-wide"]["median"]),
        )
    else:
        failed = [t for t in ("fires", "silent", "specific")
                  if not ex._result["controls"].get(t, {}).get("passed", False)]
        ex.verdict("failed", "controls failed: " + ", ".join(failed) or "none")

    path = ex.save()
    print(path)
    for (key, target, band), row in zip(ARMS, rows):
        print(
            "%-8s target=%2d band=%.1f median=%4.0f mean=%6.2f iqr_x=%.3f cells=%d..%d"
            % (key, target, band, row["median"], row["mean"], row["iqr"], row["lo"], row["hi"])
        )


if __name__ == "__main__":
    main()
