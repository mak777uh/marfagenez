#!/usr/bin/env python3
"""EXP-53: the two organisms above the bound are the rotation, not the field.

EXP-52 found that at income 1.20 the sighted policy holds 42 organisms where
the corrected capacity law allows 40, and that exactly two cells are
double-occupied at every sample while *which* cells changes every sample. The
reading was that the pair rotates: the second occupant takes less than it
costs, leaves, recovers elsewhere, and another arrives.

That reading is an inference from cell numbers. This experiment tests it by
removing the thing it depends on.

If the 42 is rotation, then an organism that cannot move cannot rotate. It
stays where it is, stays second, keeps taking 0.50 against a cost of 0.63, and
dies. The population should settle at 40 — one per cell, no sharing.

If the 42 is something else — if the field itself can support 42 in some way
the formula missed — then forbidding movement should not remove it.

Arithmetic first (PROTOCOL.md §1).

  cells = 40, M = 2.0, r = 0.8, income = 1.2, maintenance = 0.6,
  damage = 0.02, repair = 1.5.

  cost  = 0.6 + 0.02*1.5 = 0.63
  c*    = M + income - income/r = 2.0 + 1.2 - 1.5 = 1.70

  First organism in a cell takes min(1.70, 1.20) = 1.20, leaving 0.50.
  Second takes min(0.50, 1.20) = 0.50 < cost 0.63 -> loses 0.13 per step.
  From a full energy of 9.37 that is 9.37/0.13 = 72 steps to death.

  So without movement, every double-occupied cell must resolve to one
  occupant within ~72 steps, and the population must fall to at most 40.

  With movement, an organism that is losing can leave and find its own cell.
  The 72-step clock is interrupted, so some surplus survives.

Two hypotheses:
  H1 (rotation):  stay settles at 40 with no sharing; sighted holds more than
                  40 with sharing. The surplus is movement.
  H2 (the field):  stay also holds more than 40, so the surplus is in the
                  field and the formula is wrong about the field, not about
                  movement.

Control tests (PROTOCOL.md §2):
  fires    - the two policies must differ, or nothing is being tested
  silent   - the stay arm must have no double-occupied cell at the end, since
             EXP-52's arithmetic says a permanent second occupant dies within
             ~72 steps and 8000 steps is much longer
  specific - the sighted arm must have double-occupied cells at the end. A
             "sighted differs from stay" control would pass if sighted simply
             had fewer organisms; the claim is specifically that sighted keeps
             the sharing alive, so the sharing has to be there at the end
"""

import json
import os
import subprocess
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment

ROOT = "/root/marfagenez"
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

CELLS = 40
M = 2.0
R = 0.8
INCOME = 1.2
MAINTENANCE = 0.6
DAMAGE = 0.02
REPAIR = 1.5
MOVE = 0.1
RICH = 2.4
POOR = 1.6
STEPS = 8000
SEED = 20250101
N = 160

COST = MAINTENANCE + DAMAGE * REPAIR
CSTAR = M + INCOME - INCOME / R
SECOND_TAKE = min(CSTAR - INCOME, INCOME)
STEPS_TO_DEATH = 9.37 / (COST - SECOND_TAKE) if SECOND_TAKE < COST else float("inf")


def run_arm(policy):
    cmd = [
        TRACE,
        "--policy", policy,
        "--steps", str(STEPS),
        "--every", str(STEPS),
        "--seed", str(SEED),
        "--n", str(N),
        "--cells", str(CELLS),
        "--capacity", "10",
        "--damage-rate", str(DAMAGE),
        "--income", str(INCOME),
        "--maintenance", str(MAINTENANCE),
        "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--field", "uniform",
        "--rich", str(RICH),
        "--poor", str(POOR),
        "--regrow", str(R),
        "--memory-life", "100000",
        "--read-budget", "3",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(f"trace failed for {policy}:\n{out.stderr}")

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
    samples = frames[-1]["samples"] if frames else []
    alive = [s for s in samples if s.get("alive")]
    occ = collections.Counter(s["cell"] for s in alive)
    hist = collections.Counter(occ.values())
    return {
        "alive": len(alive),
        "occupied": len(occ),
        "doubles": hist.get(2, 0),
        "triples_or_more": sum(v for k, v in hist.items() if k >= 3),
        "max_per_cell": max(occ.values()) if occ else 0,
        "hash": trace_hash,
    }


def main():
    arithmetic = {
        "cost": f"maintenance + damage*repair = {MAINTENANCE} + "
                f"{DAMAGE}*{REPAIR} = {COST}",
        "equilibrium": f"c* = M + income - income/r = {M} + {INCOME} - "
                       f"{INCOME}/{R} = {CSTAR}",
        "first_take": f"min(c*, income) = min({CSTAR}, {INCOME}) = {INCOME}",
        "left_after_first": f"c* - income = {CSTAR - INCOME}",
        "second_take": f"min({CSTAR - INCOME}, {INCOME}) = {SECOND_TAKE}",
        "second_net": f"{SECOND_TAKE} - {COST} = {SECOND_TAKE - COST} per step",
        "steps_to_death": f"9.37 / {COST - SECOND_TAKE} = "
                          f"{STEPS_TO_DEATH:.1f} steps",
        "prediction_stay": f"every double resolves within "
                           f"{STEPS_TO_DEATH:.0f} steps, so after {STEPS} steps "
                           f"at most {CELLS} survive, with no sharing",
        "prediction_sighted": "a losing organism can leave before the clock "
                              "runs out, so some surplus survives",
    }

    stay = run_arm("stay")
    sighted = run_arm("sighted")

    print(f"stay    alive {stay['alive']:<4} occupied {stay['occupied']:<3} "
          f"doubles {stay['doubles']} max {stay['max_per_cell']} "
          f"hash {stay['hash'][:16]}")
    print(f"sighted alive {sighted['alive']:<4} occupied {sighted['occupied']:<3} "
          f"doubles {sighted['doubles']} max {sighted['max_per_cell']} "
          f"hash {sighted['hash'][:16]}")

    exp = Experiment(
        experiment_id="EXP-53",
        question="Is the surplus above the capacity bound the rotation of the "
                 "losing position, or a property of the field the formula "
                 "missed?",
        arithmetic=arithmetic,
        arms={"stay": "policy stay", "sighted": "policy sighted"},
        seed=SEED,
        command=" ".join([TRACE, f"--cells {CELLS}", f"--n {N}",
                          f"--steps {STEPS}", f"--income {INCOME}",
                          f"--maintenance {MAINTENANCE}",
                          f"--field uniform"]),
        parameters={
            "cells": CELLS, "M": M, "regrow": R, "income": INCOME,
            "maintenance": MAINTENANCE, "damage_rate": DAMAGE,
            "repair_cost": REPAIR, "move_cost": MOVE, "rich": RICH,
            "poor": POOR, "steps": STEPS, "n": N,
        },
    )

    for key, r in (("stay", stay), ("sighted", sighted)):
        exp.add_arm(
            key=key,
            label=f"policy {key}",
            metrics={
                "alive": r["alive"],
                "occupied_cells": r["occupied"],
                "double_occupied": r["doubles"],
                "max_per_cell": r["max_per_cell"],
            },
            trace_hash=r["hash"],
        )

    fires_ok = stay["alive"] != sighted["alive"] or stay["doubles"] != sighted["doubles"]
    exp.control(
        "fires",
        fires_ok,
        f"stay alive {stay['alive']} doubles {stay['doubles']}; sighted alive "
        f"{sighted['alive']} doubles {sighted['doubles']}",
    )

    silent_ok = stay["doubles"] == 0 and stay["max_per_cell"] <= 1
    exp.control(
        "silent",
        silent_ok,
        f"stay has {stay['doubles']} double-occupied cells and max "
        f"{stay['max_per_cell']} per cell; arithmetic says a permanent second "
        f"occupant takes {SECOND_TAKE} against cost {COST} and dies in "
        f"{STEPS_TO_DEATH:.0f} steps, and the run is {STEPS} steps",
    )

    specific_ok = sighted["doubles"] > 0
    exp.control(
        "specific",
        specific_ok,
        f"sighted has {sighted['doubles']} double-occupied cells at the end. "
        f"The claim is not merely that sighted differs from stay but that it "
        f"keeps sharing alive; a sighted run with no sharing would fail this",
    )

    if silent_ok and specific_ok and fires_ok and stay["alive"] <= CELLS:
        exp.verdict(
            "passed",
            f"the surplus is movement: forbidding movement settles the "
            f"population at {stay['alive']} with no sharing, while sighted "
            f"holds {sighted['alive']} with {sighted['doubles']} cells shared. "
            f"The {sighted['alive'] - stay['alive']} extra organisms exist only "
            f"because a losing organism can leave before its "
            f"{STEPS_TO_DEATH:.0f}-step clock runs out",
        )
    else:
        exp.verdict(
            "failed",
            f"stay alive {stay['alive']} doubles {stay['doubles']}, sighted "
            f"alive {sighted['alive']} doubles {sighted['doubles']}; "
            f"stay should have settled at most {CELLS} with no sharing",
        )

    exp.limitation(
        "One seed, one field kind (uniform), one income (1.20), 8000 steps. "
        "The rotation itself is not timed here: EXP-52 sampled every 1000 steps "
        "and saw thirteen different organisms in sixteen second-occupant "
        "positions, but a rotation faster than one sample cannot be resolved "
        "from that data. The claim is that the surplus requires movement, not "
        "that it is exactly 2 for all parameters. Nothing here says whether "
        "the surplus grows or shrinks with move_cost, read_budget or n."
    )

    path = exp.save()
    print(f"\nsaved {path}")
    print(f"verdict: {exp.result['verdict']['kind']}")


if __name__ == "__main__":
    main()
