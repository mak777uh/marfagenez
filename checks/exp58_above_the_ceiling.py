"""EXP-58: why the field can sit above the static ceiling.

EXP-52 measured 42 survivors at income 1.20 against a ceiling of 40, and 46
at income 1.00 against a ceiling of 80. The two anomalies are on opposite
sides of the same threshold, `income = M*r - need = 1.0`:

  income < 1.0  -> the remainder after the first organism is above need, so a
                   second organism can sustain itself and k_max = 2. The field
                   sits *below* that ceiling.
  income > 1.0  -> the remainder is below need, so k_max = 1 and a second
                   organism cannot sustain itself. The field sits *above* the
                   ceiling, paid for out of stored energy.

This experiment measures the second half: at income 1.20, what do the second
occupants of a doubled cell actually take, and is that below need?

Arithmetic before the run. M = 2.0, r = 0.8, need = 0.6, income = 1.2.
  M*r = 1.6 per cell per step. First organism takes 1.2, leaving 0.4.
  0.4 < need = 0.6, so k_max = 1 + floor((1.6 - 0.6)/1.2) = 1 + 0 = 1.
  Ceiling: 40 cells * 1 = 40 organisms.
  A second organism taking 0.4 loses 0.2 per step; with E_max = 10 it
  survives 10/0.2 = 50 steps before it must leave.
  Prediction: alive > 40, and the second occupant of a doubled cell takes
  below need. If the field held 40 or fewer, the buffer would be buying
  nothing and the claim would be wrong.
"""
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

M = 2.0
R = 0.8
NEED = 0.6
INCOME = 1.2
CELLS = 40
N = 80
STEPS = 200000
EVERY = 1000
SEED = 1
K_MAX = 1 + int((M * R - NEED) // INCOME)
CEILING = CELLS * K_MAX


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

    alive = [sum(1 for s in f["samples"] if s.get("alive")) for f in frames]

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
    occ = Counter(s["cell"] for s in last["samples"] if s.get("alive"))

    # The second occupant of a doubled cell: the one that is not at full
    # energy. The first taker fills up every step and sits at E_max; the
    # second is the one losing energy.
    seconds = []
    for cell, k in occ.items():
        if k < 2:
            continue
        rows = sorted(
            (s for s in last["samples"] if s.get("alive") and s["cell"] == cell),
            key=lambda s: -s["energy"],
        )
        for s in rows[1:]:
            seconds.append({"cell": cell, "energy": s["energy"],
                            "taken": s["taken"], "damage": s["damage"]})

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
        "alive_first": alive[0],
        "alive_last": alive[-1],
        "alive_min": min(alive),
        "alive_max": max(alive),
        "cells_used": len(occ),
        "crowding": dict(Counter(occ.values())),
        "frames": len(frames),
        "stayed": stats(taken["stayed"]),
        "moved": stats(taken["moved"]),
        "seconds": seconds,
        "hash": trace_hash,
    }


def main():
    arithmetic = {
        "cell_yield": f"M*r = {M}*{R} = {M * R}",
        "first_taker": f"takes {INCOME}, leaving {M * R - INCOME}",
        "remainder_vs_need": f"remainder {M * R - INCOME} against need {NEED}: "
                             f"{'below' if M * R - INCOME < NEED else 'at or above'}",
        "k_max": f"1 + floor(({M * R} - {NEED})/{INCOME}) = {K_MAX}",
        "ceiling": f"{CELLS} cells * {K_MAX} = {CEILING} organisms",
        "buffer_life": f"a second organism losing {NEED - (M * R - INCOME):.1f} "
                       f"per step with E_max 10 survives 10/"
                       f"{NEED - (M * R - INCOME):.1f} = "
                       f"{10 / (NEED - (M * R - INCOME)):.0f} steps",
        "threshold": f"the regime flips at income = M*r - need = {M * R - NEED}",
        "prediction": f"alive > {CEILING}, and the second occupant of a doubled "
                      f"cell takes below need {NEED}",
    }

    r = run_arm(INCOME, STEPS)
    print(f"income {INCOME:.2f}  alive {r['alive_first']}..{r['alive_last']}  "
          f"cells {r['cells_used']}  crowding {r['crowding']}  "
          f"frames {r['frames']}  hash {r['hash'][:16]}")
    for kind in ("stayed", "moved"):
        s = r[kind]
        print(f"  {kind}: n={s['n']} mean={s['mean']:.4f} "
              f"p10={s['p10']:.4f} p50={s['p50']:.4f} p90={s['p90']:.4f} "
              f"below_need={s['below_need']} at_need={s['at_need']}")
    print(f"  second occupants: {len(r['seconds'])}")
    for s in r["seconds"]:
        print(f"    cell {s['cell']}: E={s['energy']:.3f} "
              f"taken={s['taken']:.3f} dmg={s['damage']:.3f}")

    exp = Experiment(
        experiment_id="EXP-58",
        question="At income 1.20, where EXP-52 measured 42 survivors against "
                 "a ceiling of 40, what do the second occupants of a doubled "
                 "cell take, and is the excess paid for by stored energy?",
        arithmetic=arithmetic,
        arms={"i1.20": f"income {INCOME:.2f}, {STEPS} steps"},
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

    exp.add_arm(
        key="i1.20",
        label=f"income {INCOME:.2f}",
        metrics={
            "alive_first": r["alive_first"],
            "alive_last": r["alive_last"],
            "alive_min": r["alive_min"],
            "alive_max": r["alive_max"],
            "ceiling": CEILING,
            "crowding": r["crowding"],
            "moved_mean_taken": round(r["moved"]["mean"], 4),
            "moved_below_need": r["moved"]["below_need"],
            "moved_n": r["moved"]["n"],
            "second_occupants": len(r["seconds"]),
            "second_taken": [round(s["taken"], 4) for s in r["seconds"]],
        },
        trace_hash=r["hash"],
    )

    # fires: the field must sit above the ceiling. This is the whole claim;
    # if it held 40 or fewer there would be no excess to explain.
    fires_ok = r["alive_last"] > CEILING
    exp.control(
        "fires",
        fires_ok,
        f"alive {r['alive_last']} (range {r['alive_min']}..{r['alive_max']}) "
        f"against ceiling {CEILING} = {CELLS} cells * k_max {K_MAX}. "
        f"The excess is {r['alive_last'] - CEILING}.",
    )

    # silent: there must be doubled cells to look at. If every cell held one
    # organism the excess would exist without any second occupant, and the
    # mechanism would be something else.
    doubles = r["crowding"].get(2, 0)
    silent_ok = doubles > 0 and r["moved"]["n"] > 100
    exp.control(
        "silent",
        silent_ok,
        f"{doubles} doubled cells at the last frame, {r['moved']['n']} moved "
        f"transitions. A run with no doubled cell would make the second-"
        f"occupant measurement empty.",
    )

    # specific: the second occupant must take below need. The rejected
    # hypothesis is that the second organism takes need or more, which would
    # mean the cell feeds two organisms sustainably and k_max would be 2.
    second_taken = [s["taken"] for s in r["seconds"]]
    specific_ok = bool(second_taken) and all(
        t < NEED - 1e-9 for t in second_taken)
    exp.control(
        "specific",
        specific_ok,
        f"second occupants take {[round(t, 3) for t in second_taken]} against "
        f"need {NEED}. The hypothesis this rejects is that a second organism "
        f"takes need or more, which would make the ceiling 80 instead of 40.",
    )

    if fires_ok and silent_ok and specific_ok:
        exp.verdict(
            "passed",
            f"the field holds {r['alive_last']} against a ceiling of {CEILING}, "
            f"and the excess is paid for by stored energy: the second occupant "
            f"of a doubled cell takes {[round(t, 3) for t in second_taken]} "
            f"against need {NEED}, losing {NEED - (M * R - INCOME):.1f} per "
            f"step out of a buffer of 10. The ceiling is a bound on sustained "
            f"occupancy, not on transient occupancy. The threshold is "
            f"income = M*r - need = {M * R - NEED}: below it a second organism "
            f"breaks even and k_max is 2; above it the buffer is what allows "
            f"the excess",
        )
    else:
        exp.verdict(
            "failed",
            f"fires={fires_ok} (alive {r['alive_last']} vs ceiling {CEILING}), "
            f"silent={silent_ok} ({doubles} doubled cells, "
            f"{r['moved']['n']} moved), specific={specific_ok} "
            f"(second taken {[round(t, 3) for t in second_taken]} vs need {NEED})",
        )

    exp.limitation(
        "One regime (M=2.0, r=0.8, need=0.6, income=1.2, damage_rate=0.02, "
        "E_max=10, sighted with read_budget=3, seed 1). The excess is small "
        "(3 organisms on 40 cells) and its dependence on E_max and on the "
        "number of cells is not measured. `taken` is sampled once per 1000 "
        "steps, so below-need fractions are lower bounds. The mechanism is "
        "inferred from the second occupants of doubled cells at one frame plus "
        "the transition table; individual organisms were not tracked through "
        "a full excursion, so the survival time of about 50 steps is "
        "arithmetic, not a measurement.",
    )

    path = exp.save()
    print(f"\nsaved {path}")


if __name__ == "__main__":
    main()
