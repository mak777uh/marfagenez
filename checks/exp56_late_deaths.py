"""EXP-56: who dies late, and what kills it?

EXP-55 found that at E_max 8 the surplus decays: +2 at 1000/3000/5000 steps,
0 at 8000. Two late deaths at steps 3578 and 6804. E_max 9 keeps +2.

The mechanism is unknown. The old trace could not say which organism died,
because a Sample carried no identity and a death had to be guessed from
(cell, energy) -- which fails exactly when two organisms share a cell, the
case worth measuring. Samples now carry `slot`, stable for the whole run.

ARITHMETIC FIRST (before any run).

Stable energy at the top of the population is E_max - 1.63, where 1.63 is the
peak net spend per step measured in EXP-55:

    E_max 8  -> 6.37?  no: measured 7.370, so the spend there is 0.63
    E_max 9  -> 8.370, spend 0.63
    E_max 10 -> 9.370, spend 0.63

So the top organism holds E_max - 0.63. At E_max 8 that is 7.370, and a
second occupant loses 0.130/step while it waits. 7.370 / 0.130 = 56.7 steps.
The longest double occupancy measured in EXP-55 was 25 steps. So a death by
starvation while queued needs a queue of 57 steps, and none was seen.

That means the late deaths are probably NOT starvation in a queue. Two other
candidates the arithmetic can separate:

  H1 the organism is alone on a poor cell and its income is below its spend.
     Poor cell income 1.60, spend 0.63 + 0.10 move = 0.73, so income exceeds
     spend and it cannot starve alone. H1 predicts no death. REJECT by
     arithmetic.
  H2 the organism is one of two on a rich cell, and the queue is long because
     the population is dense. Needs 57 steps of queue. Not seen. REJECT by
     arithmetic unless the measurement contradicts it.
  H3 damage, not energy. The sample carries `damage`. If damage climbs to the
     death threshold the organism dies with energy left. This is the only
     candidate the arithmetic does not already reject.

So P1: the late deaths happen with energy well above zero.
    P2: at the moment of death the organism shares its cell, or it does not --
        the slot id settles which.
    P3: damage at death is at the death threshold.

Controls:
  fires    -- the run must reproduce the decay: surplus 0 at 8000 steps for
              E_max 8, +2 for E_max 9. If the decay does not appear, the
              experiment is void, because there is no death to explain.
  silent   -- E_max 10 must have no late deaths at all.
  specific -- the deaths must be late (step > 1000), not the initial collapse
              at steps 8-25. A death at step 12 is a different phenomenon and
              must not be counted as the one under study.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment import Experiment

ARITHMETIC = {
    "top_energy_at_Emax8": 7.370,
    "per_step_spend": 0.63,
    "second_occupant_loss": 0.130,
    "queue_steps_needed": round(7.370 / 0.130, 1),
    "longest_queue_measured": 25,
    "poor_cell_income": 1.60,
    "move_cost": 0.10,
    "alone_on_poor_net": round(1.60 - 0.63 - 0.10, 4),
    "prediction": "H1 and H2 rejected by arithmetic; H3 (damage) is the only survivor",
}

STEPS = 8000
# The parameters are stated in full rather than left to defaults: the defaults
# in core/src/organism.rs are M = 1.1, which is not the field EXP-55 measured.
BASE = [
    "--n", "160",
    "--cells", "40",
    "--capacity", None,  # filled per arm
    "--damage-rate", "0.02",
    "--income", "1.2",
    "--maintenance", "0.6",
    "--repair-cost", "1.5",
    "--field", "uniform",
    "--rich", "2.4",
    "--poor", "1.6",
    "--regrow", "0.8",
    "--move-cost", "0.10",
    "--read-budget", "3",
    "--steps", str(STEPS),
    "--every", "1",
    "--seed", "20250101",
    "--policy", "sighted",
]


def run_arm(exp, emax, label):
    """Run one E_max arm and return its late deaths with full context."""
    import subprocess
    import json

    args = list(BASE)
    args[args.index(None)] = str(emax)
    cmd = ["cargo", "run", "--release", "--quiet", "--bin", "trace", "--"] + args
    cwd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"{label}: trace failed\n{out.stderr[-2000:]}")
    # trace writes the JSON to results/<policy>/trace-<policy>-<stamp>.json and
    # prints a summary on stdout, so the path is read from the summary.
    written = [
        line.split(":", 1)[1].strip()
        for line in out.stdout.splitlines()
        if line.startswith("written:")
    ]
    if not written:
        raise SystemExit(f"{label}: no 'written:' line\n{out.stdout[-2000:]}")
    data = json.load(open(os.path.join(cwd, written[0])))
    frames = data["frames"]
    last = frames[-1]
    alive = [s for s in last["samples"] if s["alive"]]

    # Rebuild each slot's history. A slot that was alive and is now not alive
    # died. The frame before the death carries the state that caused it.
    deaths = []
    prev = None
    for f in frames:
        if prev is not None:
            for s_prev, s_now in zip(prev["samples"], f["samples"]):
                if s_prev["alive"] and not s_now["alive"]:
                    # who else was on that cell in the frame before
                    mates = [
                        t["slot"]
                        for t in prev["samples"]
                        if t["alive"] and t["cell"] == s_prev["cell"] and t["slot"] != s_prev["slot"]
                    ]
                    deaths.append({
                        "step": f["step"],
                        "slot": s_prev["slot"],
                        "cell": s_prev["cell"],
                        "energy": round(s_prev["energy"], 6),
                        "damage": round(s_prev["damage"], 6),
                        "taken": round(s_prev["taken"], 6),
                        "direction": s_prev["direction"],
                        "mates_on_cell": mates,
                        "energy_now": round(s_now["energy"], 6),
                    })
        prev = f

    late = [d for d in deaths if d["step"] > 1000]
    # field level on the cell of each late death
    for d in late:
        d["field_at_death"] = round(frames[-1]["field"][d["cell"]], 6)
    return {
        "label": label,
        "emax": emax,
        "hash": data["hash"],
        "alive": len(alive),
        "surplus": len(alive) - 40,
        "deaths_total": len(deaths),
        "deaths_early": len(deaths) - len(late),
        "deaths_late": len(late),
        "late": late,
        "top_energy": round(max((s["energy"] for s in alive), default=0.0), 6),
        "min_energy": round(min((s["energy"] for s in alive), default=0.0), 6),
    }


def main():
    exp = Experiment(
        experiment_id="EXP-56",
        question="What kills the late deaths at E_max 8, and why is the mechanism not starvation?",
        arithmetic=ARITHMETIC,
        arms={
            "8": "capacity=8",
            "9": "capacity=9",
            "10": "capacity=10",
        },
        seed=20250101,
        command="python3 checks/exp56_late_deaths.py",
        parameters={
            "n": 160, "cells": 40, "rich": 2.4, "poor": 1.6, "regrow": 0.8,
            "move_cost": 0.10, "read_budget": 3, "steps": STEPS, "every": 1,
            "policy": "sighted",
        },
    )

    arms = {}
    for emax in (8, 9, 10):
        arms[emax] = run_arm(exp, emax, f"E_max {emax}")
        a = arms[emax]
        print(f"E_max {emax}: alive {a['alive']}  surplus {a['surplus']:+d}  "
              f"deaths {a['deaths_total']} (early {a['deaths_early']}, "
              f"late {a['deaths_late']})  top {a['top_energy']:.3f}")
        for d in a["late"]:
            print(f"    late death step {d['step']} slot {d['slot']} cell {d['cell']} "
                  f"energy {d['energy']:.3f} damage {d['damage']:.3f} "
                  f"taken {d['taken']:.3f} mates {d['mates_on_cell']}")
        exp.add_arm(
            str(emax),
            f"capacity={emax}",
            {
                "alive": a["alive"],
                "surplus": a["surplus"],
                "deaths_total": a["deaths_total"],
                "deaths_late": a["deaths_late"],
                "top_energy": a["top_energy"],
                "late": a["late"],
            },
            trace_hash=a["hash"],
        )

    # Control fires: the decay must be reproduced.
    fires = arms[8]["surplus"] == 0 and arms[9]["surplus"] == 2
    exp.control(
        "fires", fires,
        f"surplus at 8000 steps: E_max 8 -> {arms[8]['surplus']:+d}, "
        f"E_max 9 -> {arms[9]['surplus']:+d}; the decay must be reproduced "
        f"(0 and +2) for there to be a death to explain",
    )

    # Control silent: E_max 10 must have no late deaths.
    silent = arms[10]["deaths_late"] == 0
    exp.control(
        "silent", silent,
        f"E_max 10 has {arms[10]['deaths_late']} late deaths; the arm where the "
        f"surplus is stable must show the effect absent",
    )

    # Control specific: deaths under study are late.
    late = [d for a in arms.values() for d in a["late"]]
    specific = all(d["step"] > 1000 for d in late) and len(late) > 0
    exp.control(
        "specific", specific,
        f"{len(late)} counted deaths, earliest step "
        f"{min((d['step'] for d in late), default='none')}; the initial collapse "
        f"at steps 8-25 is a different phenomenon and must not be counted",
    )

    limitation = (
        "Single seed (20250101), single geometry (n 160, cells 40, rich 2.4, poor 1.6, "
        "regrow 0.8). The slot id is stable within a run but says nothing about "
        "lineage: a slot is a position in the array, not a parent-child relation. "
        "Frames are sampled every step, so the per-death state is the step before the "
        "death. What is still missing is the reason the organism was in that state: the "
        "trace records where it was and what it held, not which decision it took or why, "
        "so a death can be described but not yet explained."
    )
    exp.limitation(limitation)

    if not late:
        exp.verdict("void", "no late deaths reproduced, so there is nothing to explain")
    else:
        with_energy = [d for d in late if d["energy"] > 0.5]
        shared = [d for d in late if d["mates_on_cell"]]
        if len(with_energy) == len(late):
            exp.verdict(
                "passed",
                f"P1 holds: all {len(late)} late deaths happen with energy above 0.5 "
                f"(min {min(d['energy'] for d in late):.3f}), so they are not starvation "
                f"in the ordinary sense. P2: {len(shared)} of {len(late)} died while "
                f"sharing a cell. "
                + ("Sharing is universal, so the queue is the context. " if len(shared) == len(late)
                   else "Not all died sharing a cell, so queueing is not the whole story. ")
                + "The energy and damage at death are recorded per death; the mechanism "
                "is named only where the numbers name it.",
            )
        else:
            exp.verdict(
                "failed",
                f"P1 refuted: {len(late) - len(with_energy)} of {len(late)} late deaths "
                f"happen with energy at or below 0.5, i.e. starvation after all. The "
                f"arithmetic that rejected H1/H2 is wrong.",
            )

    path = exp.save()
    print(f"\nsaved {path}")


if __name__ == "__main__":
    main()
