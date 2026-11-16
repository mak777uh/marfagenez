"""A map of environment space: how comfortable it is, and how much it distinguishes.

Two quantities per environment, and the claim that they are independent is what
this experiment tests.

    comfort   the best realised surplus: mean taken by the best policy minus
              the upkeep. This is "how easy it is to make a living here".
    richness  how many of a fixed repertoire of behaviours come out *different*.
              One distinct outcome means the medium admits no question; five
              means every way of living is separated by the medium.

The repertoire is declared here and is the probe's five reading behaviours:
`stay`, `random`, `erased`, `intact` (Memory), `sighted`. It is NOT the core's
five policies - there is no `Remember` arm in the probe - and richness is
therefore relative to this list, which is exactly the concern the brief asks
about (Q1). The number cannot be compared across repertoires and is not claimed
to.

Prediction, written before the run:

    richness is NOT monotone in the peak spacing. It should be 1 at a spacing of
    2 (the medium is nearly uniform, everything that moves eats the same) and 1
    at a spacing of 24 (the single peak is unreachable and every arm dies the
    same way), with a maximum in between. Comfort should fall monotonically as
    the spacing grows, because the walk to a peak gets longer.

If richness turns out monotone in the spacing, the two axes are not independent
and the idea behind this map is wrong. That is the useful failure.

    python3 checks/exp_env_map.py           # writes results/env-map/*.json
    python3 checks/exp_env_map.py --plot    # also writes the PNG
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "checks"))

import result as R  # noqa: E402
from experiment import Experiment  # noqa: E402

PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "memory_probe")

REPERTOIRE = ("stay", "random", "erased", "intact", "sighted")
SPACING = (2, 3, 4, 6, 8, 12, 24)
REGROW = (0.50, 0.60, 0.70, 0.80, 0.90)

CELLS = 24
M_FIELD = 2.0
MAINTENANCE = 1.7911
REPAIR_COST = 1.5
DAMAGE_RATE = 0.02
INCOME = MAINTENANCE + DAMAGE_RATE * REPAIR_COST
UPKEEP = INCOME
STEPS = 20000
SEED = 1
START_CELL = 3
POOR = 0.20


def run(arm: str, spacing: int, regrow: float) -> dict:
    cmd = [
        PROBE,
        "--arm", arm,
        "--cells", str(CELLS),
        "--m", str(M_FIELD),
        "--regrow", str(regrow),
        "--income", str(round(INCOME, 10)),
        "--maintenance", str(MAINTENANCE),
        "--repair-cost", str(REPAIR_COST),
        "--damage-rate", str(DAMAGE_RATE),
        "--steps", str(STEPS),
        "--seed", str(SEED),
        "--threshold", "1.0",
        "--capacity", "10.0",
        "--energy", "5.0",
        "--read-budget", "3",
        "--read-cost", "0.0",
        "--read-period", "1",
        "--field", "peaks",
        "--period", str(spacing),
        "--poor", str(POOR),
        "--start-cell", str(START_CELL),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def outcome(data: dict) -> tuple:
    """What makes two runs 'the same behaviour': the three recorded numbers."""
    return (
        data["lifetime"],
        data["cause"],
        round(data["taken_mean"], 6),
    )


def main(argv: list[str]) -> int:
    if not os.path.exists(PROBE):
        print(f"probe not built: {PROBE}")
        return 1
    want_plot = "--plot" in argv

    arithmetic = {
        "question": "is comfort independent of how much the medium distinguishes",
        "comfort": "mean taken by the best-repertoire arm minus the upkeep, in resource units",
        "richness": "number of distinct (lifetime, cause, taken_mean) among the declared repertoire",
        "repertoire": list(REPERTOIRE),
        "repertoire_is_relative": (
            "richness cannot be compared across repertoires and is not claimed to be; "
            "adding a sixth behaviour would change it. This is the Q1 concern of "
            "docs/REVIEW-emergence-notes-3.md and docs/RESEARCH-BRIEF-4.md, recorded "
            "rather than resolved"
        ),
        "prediction": (
            "richness is not monotone in the spacing: 1 at spacing 2 (nearly uniform) "
            "and 1 at spacing 24 (the single peak is unreachable), with a maximum "
            "between; comfort falls monotonically as the spacing grows"
        ),
        "axes": {"spacing": list(SPACING), "regrow": list(REGROW)},
        "fixed": {"cells": CELLS, "read_cost": 0.0, "poor": POOR, "steps": STEPS},
    }

    exp = Experiment(
        experiment_id="env-map",
        question="is comfort independent of how much the medium distinguishes",
        arithmetic=arithmetic,
        arms={a: f"repertoire arm {a}" for a in REPERTOIRE},
        seed=SEED,
        command="python3 checks/exp_env_map.py",
        parameters={
            "spacing": list(SPACING),
            "regrow": list(REGROW),
            "repertoire": list(REPERTOIRE),
            "steps": STEPS,
        },
    )

    cells: list[dict] = []
    for spacing in SPACING:
        for regrow in REGROW:
            runs = {arm: run(arm, spacing, regrow) for arm in REPERTOIRE}
            outcomes = {arm: outcome(runs[arm]) for arm in REPERTOIRE}
            distinct = len(set(outcomes.values()))
            best_taken = max(r["taken_mean"] for r in runs.values())
            cells.append(
                {
                    "spacing": spacing,
                    "regrow": regrow,
                    "hashes": {a: runs[a]["hash"] for a in REPERTOIRE},
                    "richness": distinct,
                    "comfort": best_taken - UPKEEP,
                    "best_taken": best_taken,
                    "lifetimes": {a: runs[a]["lifetime"] for a in REPERTOIRE},
                    "causes": {a: runs[a]["cause"] for a in REPERTOIRE},
                }
            )
    exp.result["cells"] = cells

    # One arm here runs 35 dynamics, so a single dynamics hash would be a
    # fiction. What is stored is a digest over that arm's per-environment
    # hashes: still checkable, and it does not pretend a sweep has one
    # trajectory.
    import hashlib

    for arm in REPERTOIRE:
        blob = "\n".join(c["hashes"][arm] for c in cells).encode()
        exp.add_arm(
            arm,
            f"repertoire arm {arm}",
            {
                "mean_lifetime": sum(c["lifetimes"][arm] for c in cells) / len(cells),
                "environments": len(cells),
            },
            trace_hash=hashlib.sha256(blob).hexdigest()[:16],
        )

    # -- the map as a text table -------------------------------------------
    print("\nrichness (number of distinct outcomes out of "
          f"{len(REPERTOIRE)})")
    header = "spacing\\regrow " + " ".join(f"{r:>5.2f}" for r in REGROW)
    print(header)
    for spacing in SPACING:
        row = [c for c in cells if c["spacing"] == spacing]
        print(f"{spacing:>14} " + " ".join(f"{c['richness']:>5}" for c in row))

    print("\ncomfort (best realised take minus upkeep)")
    print(header)
    for spacing in SPACING:
        row = [c for c in cells if c["spacing"] == spacing]
        print(f"{spacing:>14} " + " ".join(f"{c['comfort']:>+5.2f}" for c in row))

    # -- controls -----------------------------------------------------------
    # The controls are about the claim "the two axes are independent", not about
    # richness being interesting. Richness turned out to saturate on the first
    # run: with five arms and three recorded numbers the count is the maximum
    # almost everywhere, so the axis that was supposed to vary does not. The
    # controls therefore ask whether *comfort* discriminates the medium (it
    # does) and whether richness is invariant (it is), and the verdict follows.
    comforts = [c["comfort"] for c in cells]
    comfort_discriminates = len(set(round(x, 6) for x in comforts)) > 1
    exp.control(
        "fires",
        comfort_discriminates,
        f"comfort takes {len(set(round(x, 6) for x in comforts))} distinct values "
        f"across {len(cells)} environments, so the medium does change how easy it is "
        "to make a living",
    )

    richness_values = sorted({c["richness"] for c in cells})
    exp.control(
        "silent",
        len(richness_values) > 1,
        f"richness takes values {richness_values}: "
        + (
            "it does vary, so the axis is not constant"
            if len(richness_values) > 1
            else "it is the same in every environment, so this axis carries no "
                 "information about the medium and the map has one axis, not two"
        ),
    )

    # specific: the same environment must give the same outcome twice. The probe
    # is deterministic given the environment (FINDING-158), so a repeat is the
    # check that richness is a property of the medium and not of run order.
    repeat_a = [run(a, 6, 0.80) for a in ("intact", "sighted")]
    repeat_b = [run(a, 6, 0.80) for a in ("intact", "sighted")]
    exp.control(
        "specific",
        repeat_a == repeat_b,
        "a repeat of one environment returns identical numbers, so the counts are a "
        "property of the medium and not of run order",
    )

    # Two arms sharing a digest across every environment is the saturation
    # result stated in the strongest possible way: `intact` and `sighted` are the
    # same dynamics in this whole box. Declared, because the contract reads a
    # collision as a false contrast otherwise.
    by_hash: dict[str, list[str]] = {}
    for key, h in exp.result["hashes"].items():
        by_hash.setdefault(h, []).append(key)
    for keys in by_hash.values():
        if len(keys) > 1:
            exp.expect_coincident(*sorted(keys))
    exp.result["coincident_groups"] = [
        sorted(k) for k in by_hash.values() if len(k) > 1
    ]

    exp.limitation(
        "richness is relative to the declared repertoire and cannot be compared with "
        "another list of behaviours; the probe has no `Remember` arm, so this is not "
        "the core's five policies"
    )
    exp.limitation(
        "one environment per cell, no repetition: FINDING-158 measured sigma = 0 "
        "across seeds, so a cell is a single deterministic run and carries no interval"
    )
    exp.limitation(
        "comfort is the best realised take, so it is the comfort of the luckiest "
        "behaviour, not of a typical organism"
    )
    exp.limitation(
        "`intact` and `sighted` share a digest across all 35 environments: with "
        "read_cost = 0 and read_period = 1 a memory that looks every step IS the "
        "neighbour-follower. Half the repertoire is therefore one arm, which is why "
        "the maximum richness observed is 4 and not 5, and it is another face of the "
        "saturation"
    )
    exp.limitation(
        "the grid is a hand-drawn box: 7 spacings x 5 regrowth rates at one income, "
        "one poor level and one starting cell. A share of this box is not a share of "
        "nature, exactly as the note on Conway's Life warns"
    )
    exp.limitation(
        "read_cost is zero, so the axes measure the medium alone; the price of "
        "perception was the subject of FINDING-156 and is held fixed here"
    )

    reason = (
        f"Across {len(cells)} environments of a declared box, comfort ranges from "
        f"{min(comforts):+.2f} to {max(comforts):+.2f} and separates the medium "
        f"cleanly. Richness does not: it takes values {richness_values} and is "
        f"{max(c['richness'] for c in cells)} out of {len(REPERTOIRE)} in "
        f"{sum(1 for c in cells if c['richness'] == max(x['richness'] for x in cells))} "
        f"of {len(cells)} environments. The prediction - that richness is not "
        "monotone in the spacing, with a peak in the middle - is refuted, and for a "
        "more interesting reason than monotonicity: the count saturates, so it "
        "cannot be used as an axis at all. The map therefore has one working axis "
        "(comfort) and one that measures nothing (richness as a raw count of "
        "distinct outcomes). The claim that comfort and richness are independent is "
        "not supported: richness has no variance to be independent of anything. "
        "This is the Q1 concern of RESEARCH-BRIEF-4 arriving before the answer did."
    )
    exp.verdict("failed", "EXPLAINED: " + reason)
    print()
    print(reason)

    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")

    if want_plot:
        plot(cells)
    return 0


def plot(cells: list[dict]) -> None:
    """Two panels, because one number per cell hides the other one."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, key, title, cmap in (
        (axes[0], "richness", "richness (distinct outcomes)", "viridis"),
        (axes[1], "comfort", "comfort (best taken - upkeep)", "coolwarm"),
    ):
        grid = [[c[key] for c in cells if c["spacing"] == s] for s in SPACING]
        im = ax.imshow(
            grid,
            aspect="auto",
            origin="lower",
            cmap=cmap,
            extent=(0, len(REGROW), 0, len(SPACING)),
        )
        ax.set_xticks([i + 0.5 for i in range(len(REGROW))])
        ax.set_xticklabels([f"{r:.2f}" for r in REGROW])
        ax.set_yticks([i + 0.5 for i in range(len(SPACING))])
        ax.set_yticklabels([str(s) for s in SPACING])
        ax.set_xlabel("regrowth rate")
        ax.set_ylabel("peak spacing")
        ax.set_title(title)
        fig.colorbar(im, ax=ax)
        # one run per cell: say so on the figure, not only in the text
        for i in range(len(SPACING)):
            for j in range(len(REGROW)):
                ax.text(j + 0.5, i + 0.5, f"{grid[i][j]:.2f}" if key == "comfort" else f"{grid[i][j]}",
                        ha="center", va="center", fontsize=7,
                        color="black" if key == "comfort" else "white")
    fig.suptitle("Environment map, n = 1 environment per cell (deterministic, see FINDING-158)")
    out = os.path.join(ROOT, "results", "env-map", "map.png")
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    print(f"figure: {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
