"""EXP-89: does the field that feeds a population also raise its ceiling?

The model has two separate things that both sound like "the medium gets better":

  * `regrow`  -- how fast a cell climbs back toward its own ceiling `M`.
  * `M`       -- the ceiling itself.

FINDING-085 says a fed-on cell settles BELOW its ceiling. So a higher `regrow`
should mean a smaller shortfall, and a higher `M` should mean a higher plateau.
The question this experiment asks is whether the two are interchangeable for
the population: does raising `regrow` buy as many survivors as raising `M` by
the same factor?

Arithmetic before the run (per-cell law, `t` = income, `need` = maintenance):

    c*        = M + t - t/r
    shortfall = M - c* = t*(1-r)/r
    first take = min(c*, t)
    kSat      = floor((M*r - need)/t) + 1

At `M = 2.0, t = 0.6, need = 0.6`:

    r = 0.8 -> c* = 2.0 + 0.6 - 0.75 = 1.85, shortfall 0.15, kSat = 2
    r = 0.9 -> c* = 2.0 + 0.6 - 0.667 = 1.933, shortfall 0.067, kSat = 2
    r = 0.95-> c* = 2.0 + 0.6 - 0.632 = 1.968, shortfall 0.032, kSat = 2

`kSat` does not move between r = 0.8 and r = 0.95, so the population count is
predicted to be INSENSITIVE to `regrow` in this range. That is the `silent`
control. Raising `M` from 2.0 to 3.0 gives kSat = floor((2.4-0.6)/0.6)+1 = 4,
so the `fires` control is the `M` arm.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")
OUT = os.path.join(ROOT, "results", "EXP-89")


def run_trace(args, tag):
    os.makedirs(OUT, exist_ok=True)
    cmd = [TRACE] + args
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("trace failed: %s\n%s" % (cmd, p.stderr))
    path = None
    for line in p.stdout.splitlines():
        if line.startswith("written:"):
            path = line.split(":", 1)[1].strip()
    if path is None:
        raise SystemExit("no written path in:\n" + p.stdout)
    with open(path) as f:
        data = json.load(f)
    data["_path"] = path
    data["_tag"] = tag
    return data


def census(frame):
    s = frame["samples"]
    alive = [x for x in s if x["alive"]]
    cells = {}
    for x in alive:
        cells[x["cell"]] = cells.get(x["cell"], 0) + 1
    crowding = (sum(cells.values()) / len(cells)) if cells else 0.0
    return {
        "alive": len(alive),
        "crowding": crowding,
        "cells_used": len(cells),
        "mean_energy": (sum(x["energy"] for x in alive) / len(alive)) if alive else 0.0,
        "max_cell_load": max(cells.values()) if cells else 0,
    }


def arm(policy, n, cells, steps, every, income, maintenance, regrow, m, move_cost,
        read_budget, layout, seed=1):
    args = [
        "--policy", policy,
        "--n", str(n),
        "--cells", str(cells),
        "--steps", str(steps),
        "--every", str(every),
        "--seed", str(seed),
        "--field", "uniform",
        "--rich", str(m),
        "--poor", str(m),
        "--income", str(income),
        "--maintenance", str(maintenance),
        "--regrow", str(regrow),
        "--move-cost", str(move_cost),
        "--read-budget", str(read_budget),
        "--layout", layout,
        "--energy", "10.0",
        "--capacity", "10.0",
        "--damage-rate", "0.0",
        "--repair-cost", "1.5",
    ]
    return run_trace(args, "%s-M%s-r%s" % (policy, m, regrow))


def main():
    common = dict(policy="stay", n=160, cells=40, steps=4000, every=1000,
                  income=0.6, maintenance=0.6, move_cost=0.0, read_budget=0,
                  layout="even")
    arms = {
        "A_r80_M20": dict(common, regrow=0.8, m=2.0),
        "B_r90_M20": dict(common, regrow=0.9, m=2.0),
        "C_r95_M20": dict(common, regrow=0.95, m=2.0),
        "D_r80_M30": dict(common, regrow=0.8, m=3.0),
        "E_r90_M30": dict(common, regrow=0.9, m=3.0),
    }
    out = {}
    for name, kw in arms.items():
        d = arm(**kw)
        last = census(d["frames"][-1])
        first = census(d["frames"][0])
        out[name] = {
            "params": kw,
            "hash": d["hash"],
            "path": d["_path"],
            "first": first,
            "last": last,
            "field_last": d["frames"][-1]["field"][:4],
        }
        print(name, json.dumps(out[name]["last"]), "field[0:4]",
              out[name]["field_last"])
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


if __name__ == "__main__":
    main()
