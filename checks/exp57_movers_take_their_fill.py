"""EXP-57: what does a moving organism actually eat?

The FINDING `capacity-is-a-network-property.md` claims that the population
exceeds the static per-cell count because a cell's output is shared in time
rather than pinned to fixed organisms. The first version of that claim said
movers average about 0.68 of `need`, inferred from endpoint values. Measuring
the walk instead gave 0.959, so the claim was rewritten. This experiment is
the measurement, so the number is reproducible and not a note in a document.

Question: at income 1.00, where EXP-52 measured 52 survivors against a static
bound of 40, what do movers and stayers actually take, and how often does an
organism fall below `need`?

Arithmetic before the run. M = 2.0, r = 0.8, need = 0.6, income = 1.0.
  M*r = 1.6 per cell per step. One organism takes 1.0, leaving 0.6.
  A second organism in the same step gets at most 0.6, which equals need.
  Total food 40 * 1.6 = 64 per step; 46 organisms need 46 * 0.6 = 27.6.
  So food is not the binding constraint at 46, and a mover that arrives
  first takes the full 1.0. Prediction: movers average well above need,
  and the fraction of steps below need is small but non-zero.
"""
import json
import os
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

M = 2.0
R = 0.8
NEED = 0.6
INCOME = 1.0
CELLS = 40
N = 80
STEPS = 400000
EVERY = 1000
SEED = 1


def run_arm(income, steps):
    cmd = [
        TRACE,
        "--policy", "sighted",
        "--field", "uniform",
        "--cells", str(CELLS),
        "--n", str(N),
        "--steps", str(steps),
        "--every", str(EVERY),
        "--seed", str(SEED),
        "--maintenance", str(NEED),
        "--rich", str(M),
        "--poor", str(M),
        "--income", str(income),
        "--read-budget", "3",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(f"trace failed for income={income}:\n{out.stderr}")

    written, trace_hash = None, ""
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
        elif line.startswith("hash:"):
            trace_hash = line.split(":", 1)[1].strip()
    if written is None:
        raise SystemExit(f"trace printed no `written:` line:\n{out.stdout}")

    with open(os.path.join(ROOT, written)) as f:
        data = json.load(f)

    frames = data.get("frames") or []
    if len(frames) < 2:
        raise SystemExit(f"need at least two frames, got {len(frames)}")

    taken = defaultdict(list)
    for prev, cur in zip(frames, frames[1:]):
        pmap = {s["slot"]: s for s in prev["samples"] if s.get("alive")}
        for c in cur["samples"]:
            if not c.get("alive"):
                continue
            p = pmap.get(c["slot"])
            if p is None:
                continue
            kind = "stayed" if c["cell"] == p["cell"] else "moved"
            taken[kind].append(c["taken"])

    last = frames[-1]
    alive = sum(1 for s in last["samples"] if s.get("alive"))
    used = len({s["cell"] for s in last["samples"] if s.get("alive")})

    def stats(xs):
        if not xs:
            return {"n": 0}
        xs_sorted = sorted(xs)
        n = len(xs)
        return {
            "n": n,
            "mean": sum(xs) / n,
            "min": xs_sorted[0],
            "max": xs_sorted[-1],
            "p10": xs_sorted[n // 10],
            "p50": xs_sorted[n // 2],
            "p90": xs_sorted[9 * n // 10],
            "below_need": sum(1 for x in xs if x < NEED - 1e-9),
            "at_need": sum(1 for x in xs if abs(x - NEED) <= 1e-9),
        }

    return {
        "alive": alive,
        "cells_used": used,
        "frames": len(frames),
        "stayed": stats(taken["stayed"]),
        "moved": stats(taken["moved"]),
        "hash": trace_hash,
    }


def main():
    arithmetic = {
        "cell_yield": f"M*r = {M}*{R} = {M * R}",
        "first_taker": f"takes min(income, yield) = min({INCOME}, {M * R}) = {INCOME}",
        "second_taker": f"gets at most {M * R} - {INCOME} = {M * R - INCOME}, "
                        f"which equals need {NEED}",
        "total_food": f"cells * M*r = {CELLS} * {M * R} = {CELLS * M * R} per step",
        "total_need": f"n_alive * need; at 46 that is {46 * NEED}",
        "static_bound": f"k_max = 1 + floor(({M * R} - {NEED})/{INCOME}) = "
                        f"{1 + int((M * R - NEED) // INCOME)}, so {CELLS} organisms",
        "total_food_bound": f"cells * M*r / need = {CELLS * M * R / NEED:.1f}",
        "prediction": "movers average well above need; the fraction of steps "
                      "below need is small but non-zero",
    }

    rows = {}
    for income in (INCOME,):
        rows[f"i{income:.2f}"] = run_arm(income, STEPS)
        r = rows[f"i{income:.2f}"]
        print(f"income {income:.2f}  alive {r['alive']}  cells {r['cells_used']}  "
              f"frames {r['frames']}  hash {r['hash'][:16]}")
        for kind in ("stayed", "moved"):
            s = r[kind]
            print(f"  {kind}: n={s['n']} mean={s['mean']:.4f} "
                  f"p10={s['p10']:.4f} p50={s['p50']:.4f} p90={s['p90']:.4f} "
                  f"below_need={s['below_need']} at_need={s['at_need']}")

    exp = Experiment(
        experiment_id="EXP-57",
        question="At income 1.00, where the population exceeds the static "
                 "per-cell count, what do movers actually take, and how often "
                 "does an organism fall below need?",
        arithmetic=arithmetic,
        arms={"i1.00": f"income {INCOME:.2f}, {STEPS} steps"},
        seed=SEED,
        command=" ".join([TRACE, "--policy sighted", "--field uniform",
                          f"--cells {CELLS}", f"--n {N}", f"--steps {STEPS}",
                          f"--every {EVERY}", f"--maintenance {NEED}",
                          f"--rich {M}", f"--poor {M}",
                          f"--income {INCOME}", "--read-budget 3"]),
        parameters={
            "cells": CELLS, "M": M, "regrow": R, "need": NEED,
            "income": INCOME, "steps": STEPS, "every": EVERY, "n": N,
        },
    )

    for key, r in rows.items():
        exp.add_arm(
            key=key,
            label=f"income {INCOME:.2f}",
            metrics={
                "alive": r["alive"],
                "cells_used": r["cells_used"],
                "moved_n": r["moved"]["n"],
                "moved_mean_taken": round(r["moved"]["mean"], 4),
                "moved_below_need": r["moved"]["below_need"],
                "stayed_n": r["stayed"]["n"],
                "stayed_mean_taken": round(r["stayed"]["mean"], 4),
                "stayed_below_need": r["stayed"]["below_need"],
            },
            trace_hash=r["hash"],
        )

    r = rows[f"i{INCOME:.2f}"]
    moved = r["moved"]
    stayed = r["stayed"]

    static_bound = CELLS * (1 + int((M * R - NEED) // INCOME))

    # fires: the phenomenon to explain is a field that sits *below* its
    # ceiling. The first version of this control asserted the opposite
    # (alive > bound) because I had computed k_max = 1 instead of 2; the
    # control failed, which is how the arithmetic error was caught. It now
    # asserts the claim the note actually makes: 46 against a ceiling of 80.
    fires_ok = r["alive"] < static_bound
    exp.control(
        "fires",
        fires_ok,
        f"alive {r['alive']} against ceiling {static_bound}; the field is "
        f"{static_bound - r['alive']} below the ceiling. If this were 0 there "
        f"would be no gap to explain.",
    )

    # silent: movers must be distinguishable from stayers, otherwise the
    # "moved" category is not capturing movement and the split is meaningless.
    silent_ok = moved["n"] > 100 and stayed["n"] > 0
    exp.control(
        "silent",
        silent_ok,
        f"moved n={moved['n']}, stayed n={stayed['n']} over {r['frames']} "
        f"frames. A run where nothing moved would make the comparison empty.",
    )

    # specific: the claim is "movers eat their fill, they do not scrape the
    # remainder". The failure mode is movers averaging near need. This control
    # fails if the mean is within 0.1 of need, which is the prediction the
    # first version of the FINDING made (0.68).
    specific_ok = moved["mean"] > NEED + 0.2
    exp.control(
        "specific",
        specific_ok,
        f"moved mean taken {moved['mean']:.4f} against need {NEED}. "
        f"The rejected hypothesis was a mean near 0.68 (need + 0.08); "
        f"this control fails if the mean is within 0.2 of need, so it could "
        f"have confirmed that hypothesis and did not.",
    )

    if fires_ok and silent_ok and specific_ok:
        exp.verdict(
            "passed",
            f"the field sits {static_bound - r['alive']} below its ceiling: "
            f"{r['alive']} organisms on {r['cells_used']} cells against "
            f"k_max*{CELLS} = {static_bound}. Movers average "
            f"{moved['mean']:.4f} of taken against need {NEED}, and only "
            f"{moved['below_need']} of {moved['n']} sampled transitions fall "
            f"below need, so the gap is not organisms scraping remainders — "
            f"they eat their fill and the ceiling is missed for another "
            f"reason. The first version of this claim said movers average "
            f"0.68 and that the population exceeded the ceiling; both were "
            f"wrong and are retracted in the FINDING",
        )
    else:
        exp.verdict(
            "failed",
            f"fires={fires_ok} (alive {r['alive']} vs ceiling {static_bound}), "
            f"silent={silent_ok} (moved {moved['n']}, stayed {stayed['n']}), "
            f"specific={specific_ok} (moved mean {moved['mean']:.4f} vs need "
            f"{NEED})",
        )

    exp.limitation(
        "One regime (M 2.0, r 0.8, need 0.6, income 1.0, damage_rate 0.02, "
        "default move_cost), one seed, sighted with read_budget 3, 400000 "
        "steps sampled every 1000. The `taken` table samples the walk once per "
        "thousand steps, so a bad value on an unsampled step is not counted "
        "and the below-need count is a lower bound. `moved` is defined as a "
        "change of cell between consecutive frames, so an organism that leaves "
        "and returns between two frames is counted as `stayed`. Nothing here "
        "measures where movers go or whether they revisit cells, and nothing "
        "here says the total-food bound cells*M*r/need is achievable — 46 is "
        "far below 106 and what blocks the rest is not known."
    )

    path = exp.save()
    print(f"\nsaved {path}")
    print(f"verdict: {exp.result['verdict']['kind']}")


if __name__ == "__main__":
    main()
