"""EXP-98: the crowding law.

Claim. On a cell that the organisms on it empty every step, the cell regrows to
M*r before the next step, so the per-step supply is `supply = M*r`. The
organisms take in index order, each at most `income`. Organism j survives iff
its take is at least `cost = maintenance + damage_rate*repair_cost`. Therefore

    k_max = 0                                              if income < cost or supply < cost
          = floor((supply - cost) / income) + 1             otherwise

and the capacity of a field of `cells` cells is `cells * k_max`.

This is the second limiter the old capacity law was missing. The old law
`C = cells * M*r/income` counts how many full portions the cell holds and
ignores the two cases where nobody can pay at all: when `income` is smaller
than the cost of staying alive, and when the cell cannot even cover one cost.

Controls:
  fires    - the law reproduces the measured k_max on every grid point
  silent   - with income > M the first organism empties the cell, so k_max = 1
             for every M in the grid; the law must say 1, not vary
  specific - raising r must raise k_max and raising the cost must lower it;
             a law that ignores r or cost fails this
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

REPAIR_COST = 1.5


def measure(cells, n, M, r, t, maintenance, damage, steps=1500):
    cmd = [TRACE, "--cells", str(cells), "--n", str(n),
           "--policy", "stay", "--steps", str(steps), "--every", str(steps),
           "--capacity", "1000", "--income", str(t),
           "--maintenance", str(maintenance), "--repair-cost", str(REPAIR_COST),
           "--damage-rate", str(damage), "--move-cost", "0", "--energy", "10",
           "--field", "uniform", "--rich", str(M), "--poor", str(M),
           "--regrow", str(r), "--layout", "even", "--seed", "1"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.join(ROOT, "core"))
    if res.returncode != 0:
        print("TRACE FAILED", res.returncode, res.stderr[-500:])
        sys.exit(1)
    written = None
    for line in res.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
    if written is None or not os.path.isabs(written):
        written = os.path.join(ROOT, "core", written)
    with open(written) as fh:
        data = json.load(fh)
    last = data["frames"][-1]
    return sum(1 for s in last["samples"] if s["alive"]), data["hash"]


def k_max_law(M, r, income, cost):
    if cost <= 0:
        return None
    supply = M * r
    if income < cost or supply < cost:
        return 0
    return int((supply - cost) // income) + 1


GRID = [
    (2.0, 0.8, 0.6, 0.1, 0.0),
    (2.0, 0.8, 0.6, 0.5, 0.0),
    (2.0, 0.8, 0.2, 0.1, 0.0),
    (2.0, 0.8, 0.2, 0.5, 0.0),
    (2.0, 0.8, 1.0, 0.1, 0.0),
    (2.0, 0.8, 1.0, 0.7, 0.0),
    (2.0, 0.5, 0.6, 0.1, 0.0),
    (3.0, 0.8, 0.6, 0.1, 0.0),
    (4.0, 0.8, 0.6, 0.1, 0.0),
    (4.0, 0.8, 0.9, 0.1, 0.0),
    (2.0, 0.9, 0.6, 0.1, 0.0),
    (2.0, 0.8, 0.8, 0.6, 0.02),
    (2.0, 0.8, 0.8, 0.6, 0.00),
    (3.0, 0.6, 0.5, 0.2, 0.0),
    (1.0, 0.8, 0.3, 0.1, 0.0),
]


def main():
    exp = Experiment(
        experiment_id="EXP-98",
        question="What limits how many organisms can live on one cell?",
        arithmetic={
            "supply per cell per step": "M*r (the cell is emptied and regrows once)",
            "cost per step": "maintenance + damage_rate*repair_cost",
            "k_max": "0 if income < cost or M*r < cost, else floor((M*r - cost)/income) + 1",
            "capacity": "cells * k_max",
        },
        arms={"grid": "15 points of (M, r, income, maintenance, damage)"},
        seed=1,
        command="checks/exp98_crowding_law.py",
    )

    rows = []
    bad = 0
    first_hash = None
    for M, r, t, mc, d in GRID:
        cost = mc + d * REPAIR_COST
        pred = k_max_law(M, r, t, cost)
        if pred is None:
            continue
        alive, h = measure(1, pred + 3, M, r, t, mc, d)
        if first_hash is None:
            first_hash = h
        ok = pred == alive
        if not ok:
            bad += 1
        rows.append(dict(M=M, r=r, income=t, maintenance=mc, damage=d,
                         cost=cost, predicted=pred, measured=alive, ok=ok))
        print("M=%.1f r=%.1f income=%.2f cost=%.2f -> law %d measured %d %s" %
              (M, r, t, cost, pred, alive, "ok" if ok else "MISMATCH"))

    exp.add_arm("grid", "one cell, k = law + 3 organisms, 1500 steps",
                {"points": len(rows), "mismatches": bad}, trace_hash=first_hash)

    exp.control("fires", bad == 0,
                "the law reproduces %d of %d grid points" % (len(rows) - bad, len(rows)))

    silent_ok = True
    silent_detail = []
    for M in (1.0, 2.0, 3.0, 4.0):
        pred = k_max_law(M, 0.8, M + 1.0, 0.1)
        alive, _ = measure(1, 4, M, 0.8, M + 1.0, 0.1, 0.0)
        silent_detail.append("M=%g: law %s measured %d" % (M, pred, alive))
        if pred != 1 or alive != 1:
            silent_ok = False
    exp.control("silent", silent_ok, "; ".join(silent_detail))

    # r 0.8 -> 0.9 at M=2, income=0.6: supply 1.6 -> 1.8, floor((1.5)/0.6)+1 = 3
    # and floor((1.7)/0.6)+1 = 3.  Both 3, so that point does not separate a
    # law that uses r from one that ignores it.  Use M=4 instead: 3.2 -> 3.6,
    # floor(3.1/0.6)+1 = 6 and floor(3.5/0.6)+1 = 6.  Also 6.  The floor hides
    # r whenever the step is small, so the separating point has to be chosen
    # where a whole income fits into the difference: M=2, r 0.8 -> 0.5 with
    # income=0.2 gives floor(1.5/0.2)+1 = 8 and floor(0.9/0.2)+1 = 5.
    base = k_max_law(2.0, 0.8, 0.2, 0.1)
    lower_r = k_max_law(2.0, 0.5, 0.2, 0.1)
    higher_cost = k_max_law(2.0, 0.8, 0.2, 0.5)
    spec_ok = (lower_r < base) and (higher_cost < base)
    exp.control("specific", spec_ok,
                "r 0.8->0.5: %d->%d; cost 0.1->0.5: %d->%d (income 0.2)" %
                (base, lower_r, base, higher_cost))

    exp.limitation(
        "Measured on a single cell with `stay` organisms, maintenance > 0, and a cell "
        "that is emptied every step. It says nothing about a field where organisms move "
        "between cells, and nothing when maintenance is 0, where an organism that takes "
        "nothing still does not die."
    )
    exp.verdict("passed" if bad == 0 else "failed",
                "the crowding law holds on all %d grid points" % len(rows)
                if bad == 0 else "%d of %d grid points disagree" % (bad, len(rows)))
    path = exp.save()
    print("\nverdict:", exp._result["verdict"])
    print("written:", path)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
