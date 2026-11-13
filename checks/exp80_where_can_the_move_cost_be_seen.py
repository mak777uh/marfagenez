"""EXP-80: `move_cost` is invisible from energy. Where does it go?

EXP-79 tried to charge `move_cost` in a unit test and found that it cannot be
seen:

    C: sighted on a poor cell, move_cost 0.00, one step -> energy 10.0
    D: sighted on a poor cell, move_cost 0.05, one step -> energy 10.0
                                                          difference 0.00

The move happened (C's assertion that the cell changed passed). The charge did
not. So the question is not "is the cost charged" -- EXP-72 asked that from the
mean energy and got a difference that did not separate either -- it is "what
can see it".

## Three candidates, and only one of them is a bug

  H1. The charge is not there at all. `Life::advance` reads
      `if direction != 0 && r.organism.spend(r.move_cost)`
      (`core/src/life.rs:441`), and `Organism::spend` subtracts from `energy`.
      If it were not there, `move_cost` would be a parameter that does nothing.

  H2. The charge is there and the cap erases it. `Organism::step` ends with
      `self.energy = self.energy.min(world.capacity).max(0.0)`
      (`core/src/organism.rs:182`). Both arms start at 10.0 with
      `capacity = 10.0`. The free arm pays 0.05 move cost, then eats
      `min(1.35, 1.0) = 1.0`, pays maintenance 0.6 and repair 0.075, and ends
      at 10.0 - 0.05 + 1.0 - 0.6 - 0.075 = 10.275, capped to 10.0. The paid arm
      ends at 10.225, capped to 10.0. **The cap hides the difference.**

  H3. The charge is real and visible only when the cap does not bind.

H2 is the arithmetic, and it is checkable before any run: the surplus per step
is

    income - maintenance - damage*repair = 1.0 - 0.6 - 0.075 = 0.325

so an organism at the cap stays at the cap whatever `move_cost` is, as long as
`move_cost < 0.325`. The cap is not a bug; it is the design
(`docs/FINDING-the-cap-is-applied-after-the-spend.md`). But it means **every
arm in this project that reads energy at the cap is blind to `move_cost`**, and
that is a large fraction of them.

The way to see the charge is to start BELOW the cap and stop before reaching
it. Start at 1.0 with `capacity = 10.0`, run 100 steps: an organism that never
moves gains `0.325` per step and reaches `1.0 + 32.5` = 33.5, capped to 10.0.
Still capped. Run 10 steps: `1.0 + 3.25 = 4.25`, not capped. A moving organism
pays `move_cost` per move, so at 10 steps the difference is `10 * move_cost`
times the move fraction.

## The arms

  A. `move_cost = 0.00`, 10 steps, start energy 1.0, `Policy::Sighted` on an
     alternating field: energy after 10 steps.
  B. `move_cost = 0.05`, same: energy after 10 steps.
  C. `move_cost = 0.30`, same: energy after 10 steps.
  D. `move_cost = 0.00`, 10 steps, `Policy::Stay`: the no-move reference.

Prediction, if the charge is real and nothing else changes:

    E(D) - E(A) = 0                      (both never move)
    E(D) - E(B) = 10 * 0.05 * f          (f = move fraction, 0 < f <= 1)
    E(D) - E(C) = 10 * 0.30 * f

with `f` the same in B and C if the policy's decision does not depend on
energy -- and it does not: `Sighted` looks at the field, not at its own energy
(`core/src/life.rs:405-436`). So the ratio

    (E(D) - E(C)) / (E(D) - E(B)) = 0.30 / 0.05 = 6.00

is a prediction with no free parameter, and it is the specific test: it says
the cost is linear in `move_cost` and charged once per move, not once per step
and not clipped.

## Controls

  fires:    E(D) - E(B) must be strictly positive. If it is zero the charge is
            absent, and every energy reading at the cap is meaningless.
  silent:   E(D) - E(A) must be exactly zero. `move_cost = 0` must cost nothing.
  specific: the ratio must be 6.00 within tolerance. If it is 1.00 the charge
            is per step, not per move; if it is 30.00 the charge is quadratic;
            if it is 0.00 the charge saturates.

## What this does not prove

It does not say how many steps a moving organism actually moves -- that is `f`,
and `f` is measured, not predicted. It does not say the charge is applied
before or after eating within the step; only that it is applied once.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from checks.experiment import Experiment  # noqa: E402

CORE = os.path.join(ROOT, "core")
TRACE = os.path.join(CORE, "target", "release", "trace")

CELLS = 4
RICH = 2.4
POOR = 1.6
REGROW = 0.8
INCOME = 1.0
MAINT = 0.6
DAMAGE = 0.05
REPAIR = 1.5
CAP = 10.0
START = 1.0
STEPS = 10
SEED = 1

SURPLUS = INCOME - MAINT - DAMAGE * REPAIR


def run(policy, move_cost, label):
    trace_dir = os.path.join(CORE, "results", policy)
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", policy,
        "--steps", str(STEPS), "--every", "1",
        "--seed", str(SEED),
        "--n", "1", "--cells", str(CELLS), "--layout", "even",
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", str(move_cost),
        "--energy", str(START),
        "--field", "alternating", "--rich", str(RICH), "--poor", str(POOR),
        "--regrow", str(REGROW), "--memory-life", "100000",
    ]
    if policy == "sighted":
        cmd += ["--read-budget", "3"]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("%s: trace failed: %s" % (label, out.stderr[-1200:]))
    digest = None
    for line in out.stdout.splitlines():
        if line.startswith("hash:"):
            digest = line.split(":", 1)[1].strip()
    after = [os.path.join(trace_dir, f) for f in os.listdir(trace_dir)
             if f not in before]
    if not after:
        raise RuntimeError("%s: no new trace" % label)
    path = max(after, key=os.path.getmtime)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    energies = [fr["samples"][0]["energy"] for fr in data["frames"]]
    cells = [fr["samples"][0]["cell"] for fr in data["frames"]]
    moves = sum(1 for a, b in zip(cells, cells[1:]) if a != b)
    alive = [fr["samples"][0]["alive"] for fr in data["frames"]]
    return {
        "hash": digest,
        "label": label,
        "policy": policy,
        "move_cost": move_cost,
        "energy_start": energies[0],
        "energy_end": energies[-1],
        "energies": energies,
        "cells": cells,
        "moves": moves,
        "alive_end": alive[-1],
    }


def main():
    exp = Experiment(
        experiment_id="EXP-80",
        question="`move_cost` is invisible from energy at the cap. Where can it "
                 "be seen, and is it charged once per move?",
        arithmetic={
            "surplus_per_step": SURPLUS,
            "cap": CAP,
            "start": START,
            "steps": STEPS,
            "uncapped_gain": START + SURPLUS * STEPS,
            "capped": START + SURPLUS * STEPS >= CAP,
            "predicted_ratio_0p30_over_0p05": 0.30 / 0.05,
            "note": "at the cap the surplus 0.325 per step swamps any move_cost "
                    "below 0.325, so every energy reading at the cap is blind "
                    "to move_cost. Starting at 1.0 and stopping at 10 steps "
                    "keeps the arm below the cap.",
        },
        arms={
            "A": "sighted, move_cost 0.00, 10 steps from 1.0",
            "B": "sighted, move_cost 0.05, 10 steps from 1.0",
            "C": "sighted, move_cost 0.30, 10 steps from 1.0",
            "D": "stay,    move_cost 0.00, 10 steps from 1.0",
        },
        seed=SEED,
        command="python3 checks/exp80_where_can_the_move_cost_be_seen.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "regrow": REGROW,
            "income": INCOME, "maintenance": MAINT, "damage_rate": DAMAGE,
            "repair_cost": REPAIR, "capacity": CAP, "start_energy": START,
            "steps": STEPS,
        },
    )

    rows = {}
    for key, policy, mc in (("A", "sighted", 0.0), ("B", "sighted", 0.05),
                            ("C", "sighted", 0.30), ("D", "stay", 0.0)):
        r = run(policy, mc, key)
        rows[key] = r
        print("  %s policy=%-8s mc=%.2f E0=%.4f E_end=%.4f moves=%d alive=%s"
              % (key, policy, mc, r["energy_start"], r["energy_end"],
                 r["moves"], r["alive_end"]))
        print("     energies %s" % " ".join("%.4f" % e for e in r["energies"]))

    for key, r in rows.items():
        exp.add_arm(
            key,
            "%s, move_cost %.2f, %d steps from %.2f"
            % (r["policy"], r["move_cost"], STEPS, START),
            {
                "energy_start": r["energy_start"],
                "energy_end": r["energy_end"],
                "moves": r["moves"],
                "alive_end": r["alive_end"],
                "cells": r["cells"],
            },
            trace_hash=r["hash"],
        )
        exp.add_series(key, list(range(STEPS + 1)), r["energies"])

    gap_b = rows["D"]["energy_end"] - rows["B"]["energy_end"]
    gap_c = rows["D"]["energy_end"] - rows["C"]["energy_end"]
    gap_a = rows["D"]["energy_end"] - rows["A"]["energy_end"]
    ratio = gap_c / gap_b if abs(gap_b) > 1e-12 else None

    exp.control(
        "fires",
        gap_b > 1e-9,
        "E(stay, mc 0.00) - E(sighted, mc 0.05) = %.6f. It must be strictly "
        "positive: the charge has to be visible below the cap." % gap_b,
    )
    exp.control(
        "silent",
        abs(gap_a) < 1e-12,
        "E(stay, mc 0.00) - E(sighted, mc 0.00) = %.6f. A free move must cost "
        "nothing, so this must be exactly zero." % gap_a,
    )
    exp.control(
        "specific",
        ratio is not None and abs(ratio - 6.0) < 0.05,
        "gap(0.30) / gap(0.05) = %s, predicted %.2f. The charge must be linear "
        "in move_cost and applied once per move: a ratio of 1.00 would mean "
        "once per step, 30.00 would mean quadratic, 0.00 would mean saturated."
        % ("undefined" if ratio is None else "%.4f" % ratio, 0.30 / 0.05),
    )

    if gap_b > 1e-9 and abs(gap_a) < 1e-12 and ratio is not None \
            and abs(ratio - 6.0) < 0.05:
        exp.verdict(
            "passed",
            "`move_cost` is charged once per move and is linear in it: the gap "
            "against the stay arm is %.4f at move_cost 0.05 and %.4f at 0.30, "
            "a ratio of %.3f against a prediction of 6.00 with no free "
            "parameter. It was invisible in EXP-79 because both arms started "
            "at the cap and the surplus %.3f per step swamped a charge of "
            "0.05. The lesson is about the instrument, not the model: any arm "
            "that reads energy at the cap cannot see move_cost."
            % (gap_b, gap_c, ratio, SURPLUS),
        )
    elif gap_b <= 1e-9:
        exp.verdict(
            "failed",
            "the gap between the stay arm and the moving arm is %.6f even below "
            "the cap, so `move_cost` is not charged at all. Every reading in "
            "this project that used move_cost as a treatment is void."
            % gap_b,
        )
    else:
        exp.verdict(
            "failed",
            "the charge is visible but not linear: gap 0.05 -> %.4f, gap 0.30 "
            "-> %.4f, ratio %s against 6.00. The cost is not once per move."
            % (gap_b, gap_c, "undefined" if ratio is None else "%.4f" % ratio),
        )

    exp.limitation(
        "The move fraction `f` is measured, not predicted. The ratio 6.00 holds "
        "only if `f` is the same at move_cost 0.05 and 0.30, which it is here "
        "because `Sighted` decides on the field and not on its own energy. A "
        "policy that reads its own energy would break the ratio."
    )
    exp.limitation(
        "Ten steps on a four-cell ring. A longer run reaches the cap and the "
        "charge disappears again, so this measures the charge and not its "
        "long-run effect."
    )
    exp.limitation(
        "This does not say whether the charge is applied before or after "
        "eating inside the step. It says it is applied once."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
