"""EXP-54: the surplus above the field bound is bought with cheap movement.

EXP-53 removed movement and the surplus vanished (42 -> 40). That showed the
surplus needs movement, but not what movement costs. This sweeps the price.

The question is not "how many can the field hold" -- EXP-52 showed the field
holds 40 and that the formula is an upper bound, not an achieved value. The
question is: the two organisms above the bound are alive, so someone is paying
for them. Who, and how much?

Arithmetic first.

  c*      = M + income - income/r = 2.0 + 1.2 - 1.5 = 1.70
  cost    = maintenance + damage*repair = 0.6 + 0.02*1.5 = 0.63
  net     = income - cost = 1.2 - 0.63 = 0.57 per step, alone on a cell

  first taker on a cell:  min(c*, income) = 1.20   -> net +0.57
  second taker:           min(c* - 1.20, income) = 0.50 -> net -0.13

A second occupant loses 0.13/step. From full energy 9.37 it dies in
9.37/0.13 = 72 steps if it stays. EXP-53 ran 8000 steps = 111 such lifetimes
and still had two second occupants, so they are not staying: they rotate.

A rotation costs move_cost per move. For a rotating second occupant to break
even it must spend less on moving than it loses by sharing. That gives a
threshold in move_cost, and the threshold is what this measures.

Prediction, stated before the run:

  P1  surplus falls to 0 at some move_cost strictly between 0.1 and 0.6
      (0.1 keeps it, 0.6 does not -- measured in the exploratory runs).
  P2  the fall is a step, not a slope: the surplus is an integer count of
      organisms, so it cannot be 1.4. Either a second occupant survives or
      it does not.
  P3  a sighted organism that cannot see its neighbours cannot move, so the
      surplus must be 0 whenever the policy degenerates to stay. This is the
      control that makes "movement causes the surplus" falsifiable: if the
      surplus survived with no movement, the whole account above is wrong.

P2 is the one that can embarrass the account. A step would mean the surplus
is a yes/no fact about whether rotation pays; a slope would mean the surplus
is a population equilibrium that happens to land on small integers here, and
the "two organisms" reading of EXP-53 would be a coincidence of parameters.

What this does not prove: that the two organisms are the same two organisms
from step to step (samples carry no id), or that the surplus is stable over
seeds. Both are recorded as limitations.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from checks.experiment import Experiment

CORE = Path(__file__).resolve().parent.parent / "core"
TRACE = CORE / "target" / "release" / "trace"

# Fixed for every arm. Only move_cost and read_budget move.
BASE = [
    "--seed", "20250101",
    "--n", "160",
    "--cells", "40",
    "--capacity", "10",
    "--damage-rate", "0.02",
    "--income", "1.2",
    "--maintenance", "0.6",
    "--repair-cost", "1.5",
    "--field", "uniform",
    "--rich", "2.4",
    "--poor", "1.6",
    "--regrow", "0.8",
    "--memory-life", "100000",
]

STEPS = 8000
BOUND = 40  # cells; the field holds one organism per cell at the bound


def run_arm(policy, move_cost, read_budget, steps=STEPS):
    """Run one arm and return the last frame's summary."""
    cmd = [
        str(TRACE),
        "--policy", policy,
        "--steps", str(steps),
        "--every", str(steps),
        *BASE,
        "--move-cost", str(move_cost),
        "--read-budget", str(read_budget),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=CORE)
    if out.returncode != 0:
        raise RuntimeError(
            f"trace failed for {policy} mc={move_cost} rb={read_budget}:\n{out.stderr}"
        )

    written = None
    digest = None
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
        elif line.startswith("hash:"):
            digest = line.split(":", 1)[1].strip()
    path = CORE / written
    data = json.loads(path.read_text())
    frame = data["frames"][-1]
    samples = frame["samples"]
    alive = [s for s in samples if s["alive"]]
    cells = {}
    for s in alive:
        cells[s["cell"]] = cells.get(s["cell"], 0) + 1
    return {
        "policy": policy,
        "move_cost": move_cost,
        "read_budget": read_budget,
        "alive": len(alive),
        "occupied": len(cells),
        "doubles": sum(1 for v in cells.values() if v > 1),
        "max_per_cell": max(cells.values()) if cells else 0,
        "moved": sum(1 for s in alive if s["direction"] != 0),
        "surplus": len(alive) - BOUND,
        "hash": digest,
        "file": written,
    }


def main():
    sweep_costs = (0.10, 0.15, 0.18, 0.20, 0.30, 0.60)

    exp = Experiment(
        experiment_id="EXP-54",
        question=(
            "EXP-53 showed the two organisms above the 40-cell bound need movement. "
            "Does the surplus disappear when movement becomes expensive, and does it "
            "disappear as a step or as a slope?"
        ),
        arithmetic={
            "c_star": "M + income - income/r = 2.0 + 1.2 - 1.5 = 1.70",
            "cost": "maintenance + damage*repair = 0.6 + 0.02*1.5 = 0.63",
            "net_alone": "income - cost = 1.2 - 0.63 = +0.57 per step",
            "first_taker": "min(c*, income) = 1.20 -> +0.57 per step",
            "second_taker": "min(c* - 1.20, income) = 0.50 -> -0.13 per step",
            "death_if_staying": "9.37 / 0.13 = 72 steps",
            "bound": "40 cells, one organism each",
            "prediction_P1": "surplus 0 at some move_cost in (0.1, 0.6)",
            "prediction_P2": "the fall is a step, not a slope",
            "prediction_P3": "no sight -> no movement -> no surplus",
        },
        arms={
            "sweep": "sighted, move_cost in " + str(list(sweep_costs)),
            "blind": "sighted, read_budget 1 (no neighbour visible)",
            "seeing": "sighted, read_budget 3",
        },
        seed=20250101,
        command="python3 checks/exp54_surplus_price.py",
        parameters={
            "steps": STEPS,
            "bound": BOUND,
            "base": BASE,
        },
    )

    # --- Arm 1: sweep the price of movement -------------------------------
    sweep = []
    for mc in sweep_costs:
        arm = run_arm("sighted", mc, 3)
        sweep.append(arm)
        print(
            f"  move_cost {mc:4.2f}  alive {arm['alive']:3d}  doubles {arm['doubles']}  "
            f"moved {arm['moved']:3d}  surplus {arm['surplus']:+d}"
        )

    # --- Arm 2: no movement ------------------------------------------------
    # read_budget 1 reads only the cell underfoot, so no neighbour is ever
    # seen and `best > here` is never true: the organism cannot move. The
    # trace binary refuses read_budget 0 for sighted (it would be a silent
    # stay), so 1 is the smallest budget that still runs.
    blind = run_arm("sighted", 0.10, 1)
    print(
        f"  read_budget 1  alive {blind['alive']:3d}  doubles {blind['doubles']}  "
        f"moved {blind['moved']:3d}  surplus {blind['surplus']:+d}"
    )

    # The same organism, allowed to see, at the same price.
    seeing = run_arm("sighted", 0.10, 3)
    print(
        f"  read_budget 3  alive {seeing['alive']:3d}  doubles {seeing['doubles']}  "
        f"moved {seeing['moved']:3d}  surplus {seeing['surplus']:+d}"
    )

    # Arms that share a hash are one arm (PROTOCOL §5). Above move_cost 0.18
    # every price gives the identical trajectory -- the system is frozen, so
    # the price has stopped doing anything. That is a result, not a duplicate
    # to hide: it is recorded as the set of prices that collapse to one arm.
    by_hash = {}
    for arm in sweep:
        by_hash.setdefault(arm["hash"], []).append(arm)
    collapsed = {}
    for digest, group in by_hash.items():
        costs = [a["move_cost"] for a in group]
        first = group[0]
        key = f"mc{first['move_cost']:.2f}"
        collapsed[key] = costs
        exp.add_arm(
            key,
            f"sighted, move_cost {first['move_cost']:.2f}, read_budget 3"
            + (f" (identical trajectory at move_cost {costs[1:]})" if len(costs) > 1 else ""),
            {
                "alive": first["alive"],
                "occupied": first["occupied"],
                "doubles": first["doubles"],
                "max_per_cell": first["max_per_cell"],
                "moved": first["moved"],
                "surplus": first["surplus"],
                "same_trajectory_as": costs[1:],
            },
            trace_hash=digest,
        )
    print(f"\n  distinct trajectories across the sweep: {len(by_hash)} of {len(sweep)}")
    for key, costs in collapsed.items():
        if len(costs) > 1:
            print(f"    {key} and move_cost {costs[1:]} are one arm")
    exp.add_arm(
        "blind",
        "sighted, read_budget 1 (neighbours invisible, cannot move)",
        {
            "alive": blind["alive"],
            "occupied": blind["occupied"],
            "doubles": blind["doubles"],
            "moved": blind["moved"],
            "surplus": blind["surplus"],
        },
        trace_hash=blind["hash"],
    )
    # `seeing` is the same run as the move_cost 0.10 arm: same policy, same
    # price, same budget. Recorded once, under its own name, only if its hash
    # is new. If it repeats, the repeat is the evidence that the arm is
    # reproducible -- and a repeat is not a second arm (§5).
    if seeing["hash"] == sweep[0]["hash"]:
        print(
            "\n  read_budget 3 at move_cost 0.10 reproduces the mc0.10 arm exactly "
            "(same hash): the arm is reproducible, and is recorded once"
        )
    else:
        exp.add_arm(
            "seeing",
            "sighted, read_budget 3, same price as blind",
            {
                "alive": seeing["alive"],
                "occupied": seeing["occupied"],
                "doubles": seeing["doubles"],
                "moved": seeing["moved"],
                "surplus": seeing["surplus"],
            },
            trace_hash=seeing["hash"],
        )

    # --- Controls ----------------------------------------------------------
    # fires: the survivor count must change across the sweep. A sweep in which
    # every arm gives 42 would mean move_cost is not reaching the organism.
    counts = {a["alive"] for a in sweep}
    exp.control(
        "fires",
        len(counts) > 1,
        f"alive counts across the sweep: {sorted(counts)}",
    )

    # silent: with no sight there is no direction, so nothing moves. If the
    # blind arm moved, `direction` is being set somewhere other than the
    # sighted branch and the whole attribution is wrong.
    exp.control(
        "silent",
        blind["moved"] == 0,
        f"blind arm moved {blind['moved']} organisms; expected 0",
    )

    # specific: the blind arm must still hold 40, not fewer. A blind organism
    # is a staying organism, and staying is the case the field bound is about.
    # If blindness cost lives, the drop would be about perception, not movement,
    # and the surplus could not be attributed to movement at all.
    exp.control(
        "specific",
        blind["alive"] == BOUND,
        f"blind arm alive {blind['alive']}; expected exactly the bound {BOUND}",
    )

    # --- Verdict -----------------------------------------------------------
    p1 = sweep[0]["surplus"] > 0 and sweep[-1]["surplus"] == 0
    surpluses = sorted({a["surplus"] for a in sweep})
    p2 = surpluses in ([0], [0, 2])
    p3 = blind["surplus"] == 0 and seeing["surplus"] > 0

    if p1 and p2 and p3:
        verdict = "passed"
        note = (
            "The surplus is a step, not a slope: it is 2 while movement is cheap "
            "and 0 once it is not, with nothing in between. Removing sight removes "
            "movement and the surplus with it, at the same price, so the surplus is "
            "bought by movement and not by the field."
        )
    elif not p3:
        verdict = "failed"
        note = (
            "The surplus survived without movement, so it is not bought by movement. "
            "The EXP-53 reading -- that the two extra organisms exist because a "
            "losing organism can leave before its clock runs out -- is not supported."
        )
    elif not p2:
        verdict = "failed"
        note = (
            f"The surplus changes gradually across the sweep ({surpluses}), so it is "
            "a population equilibrium rather than a yes/no fact about rotation. The "
            "clean 'two organisms' reading of EXP-53 would then be an accident of "
            "these parameters."
        )
    else:
        verdict = "failed"
        note = f"Predictions did not hold: p1={p1} p2={p2} p3={p3}."

    exp.limitation(
        "Samples carry no organism id, so the two second occupants cannot be "
        "followed as individuals; 'rotation' is inferred from the cell index "
        "changing between samples, not from identity."
    )
    exp.limitation(
        "One seed (20250101) only. The surplus is not shown to be stable across "
        "seeds, and EXP-52 already found a different surplus (53 vs 40) at "
        "income 1.0, so this threshold belongs to income 1.2 and is not a field "
        "constant."
    )
    exp.limitation(
        "The trace binary refuses read_budget 0 for sighted, so 'no movement' was "
        "produced by read_budget 1, which also removes the organism's view of the "
        "cell underfoot. Blindness and immobility are not separated here."
    )
    exp.limitation(
        "The sweep is coarse: six prices. The threshold is bracketed to (0.15, 0.20) "
        "but not located, and the claim that the fall is a step rests on no arm "
        "landing between 2 and 0."
    )

    exp.verdict(verdict, note)
    path = exp.save()
    print(f"\n{verdict}: {note}")
    print(f"saved {path}")


if __name__ == "__main__":
    main()
