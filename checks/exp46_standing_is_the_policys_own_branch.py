# -*- coding: utf-8 -*-
"""EXP-46: standing does not depend on density.

EXP-45 tried to reproduce the earlier claim "at n=80 84.6% stand still, at n=8
0.0% stand still" and got 0.3194 and 0.3688 - the opposite, and nearly equal.

The old numbers came from a different configuration (the FINDING used
`--policy remember` and a 500-step alternating field).  The honest reading of
EXP-45 is narrower: under the `random` policy on a uniform field, standing is
about 1/3 at both densities, which is exactly the `direction == 0` branch of
`Policy::Random` (`core/src/life.rs:344`: `u < 1/3 -> -1`, `u < 2/3 -> 0`,
else `+1`).

So the question is not "does density change standing" but "is standing simply
the policy's own stay probability".  Test it directly: measure the fraction of
`direction == 0` for `random` at several densities and compare with 1/3.  If it
is 1/3 everywhere, the old 84.6% / 0.0% pair was a property of `remember`, not
of density, and the FINDING that claimed otherwise has to be corrected.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"

BASE = ["--steps", "400", "--every", "10", "--cells", "120", "--capacity", "10",
        "--damage-rate", "0.2", "--income", "1", "--maintenance", "0.1",
        "--repair-cost", "0.5", "--move-cost", "0.05", "--energy", "5",
        "--field", "uniform", "--seed", "1"]


def run(extra):
    out = subprocess.run([str(BIN)] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def stand_still(r):
    frames = r["frames"][len(r["frames"]) // 2:]
    tot = still = 0
    for f in frames:
        for s in f["samples"]:
            if s["alive"]:
                tot += 1
                if s["direction"] == 0:
                    still += 1
    return round(still / tot, 4) if tot else None


def main():
    arms = {}
    for policy in ("random", "remember"):
        for n in (8, 80):
            r = run(["--policy", policy, "--n", str(n)])
            arms[f"{policy}_n{n}"] = {"stand_still": stand_still(r), "hash": r["hash"]}
            print(f"{policy} n {n}: {arms[f'{policy}_n{n}']['stand_still']}")

    exp = Experiment(
        experiment_id="standing-is-the-policys-own-branch",
        question="Стояние — свойство политики или плотности?",
        arithmetic={
            "random": "u<1/3 -> -1, u<2/3 -> 0, else +1, so p(stay) = 1/3",
            "old_claim": "n=80 84.6% still, n=8 0.0% still (remember, alternating field)",
            "exp45": "random on uniform: 0.3194 at n=80, 0.3688 at n=8",
        },
        arms={k: k for k in arms},
        seed=1,
        command="python3 checks/exp46_standing_is_the_policys_own_branch.py",
        parameters={"cells": 120, "steps": 400, "every": 10, "capacity": 10,
                    "damage_rate": 0.2, "income": 1, "maintenance": 0.1,
                    "repair_cost": 0.5, "move_cost": 0.05, "energy": 5,
                    "field": "uniform"},
    )
    for key, a in arms.items():
        exp.add_arm(key, key, {"stand_still": a["stand_still"]}, trace_hash=a["hash"])

    rnd = [arms[f"random_n{n}"]["stand_still"] for n in (8, 80)]
    rem = [arms[f"remember_n{n}"]["stand_still"] for n in (8, 80)]

    # Control 1 (fires): the two policies differ - otherwise the policy is not
    # what decides standing and the whole reading collapses.
    exp.control("fires", abs(rnd[0] - rem[0]) > 0.2,
                f"n=8: random {rnd[0]} vs remember {rem[0]}")

    # Control 2 (silent): density does not move `random` off its own branch.
    exp.control("silent", abs(rnd[0] - rnd[1]) < 0.1,
                f"random: n=8 {rnd[0]} vs n=80 {rnd[1]}")

    # Control 3 (specific): `random` stands still about 1/3 of the time.
    exp.control("specific", all(abs(x - 1 / 3) < 0.06 for x in rnd),
                f"random stand still {rnd} vs 1/3 = 0.333")

    exp.limitation(
        "uniform field only; the old 84.6%/0.0% pair came from `remember` on an "
        "alternating field, and this experiment does not re-run that configuration"
    )
    ok = abs(rnd[0] - rem[0]) > 0.2 and abs(rnd[0] - rnd[1]) < 0.1 \
        and all(abs(x - 1 / 3) < 0.06 for x in rnd)
    exp.verdict("passed" if ok else "failed",
                "стояние задаёт ветка политики (1/3 у random), а не плотность")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
