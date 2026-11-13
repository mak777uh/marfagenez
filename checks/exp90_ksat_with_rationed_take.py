"""EXP-90: the second occupant is rationed, so `kSat` needs the rationed take.

EXP-89 raised `regrow` from 0.8 to 0.9 at `M = 2.0, t = 0.6, need = 0.6` and the
population went from 80 to 120 on 40 cells -- crowding 2 -> 3. The arithmetic
that predicted 2 cannot explain 3, because it assumed every occupant takes a
full `t`. The second occupant does not take `t`; it takes what the first left.

The corrected arithmetic for `k` occupants on one cell, all standing still:

    first takes  = min(c*, t)
    each further = min(c* - (number of full portions already taken), t)
    survives     = take >= need

With `c* = M + t - t/r` and `t = need` (income equals maintenance, so a
survivor breaks even) the condition for `k` occupants is

    c* - (k-1)*t >= need        <=>        k <= (c* - need)/t + 1 = c*/t

so

    kSat = floor(c*/t)   when need == t

At `M = 2.0, t = 0.6`:

    r = 0.80 -> c* = 1.70 -> kSat = floor(2.833) = 2   -> 80 on 40 cells
    r = 0.90 -> c* = 1.80 -> kSat = floor(3.000) = 3   -> 120
    r = 0.95 -> c* = 1.905 -> kSat = floor(3.175) = 3  -> 120
    M = 3.0, r = 0.80 -> c* = 2.40 -> kSat = 4         -> 160
    M = 3.0, r = 0.90 -> c* = 2.733 -> kSat = 4        -> 160

All five EXP-89 arms match this. This experiment tests the law at a point where
`need != t`, which is where the two candidate formulas disagree:

    kSat_A = floor((M*r - need)/t) + 1        (full portions, then one rationed)
    kSat_B = floor((c*  - need)/t) + 1        (c* is what is actually on the cell)

At `M = 2.0, r = 0.8, t = 0.9, need = 0.6`:

    c*     = 2.0 + 0.9 - 1.125 = 1.775
    kSat_A = floor((1.6 - 0.6)/0.9) + 1 = floor(1.111) + 1 = 2
    kSat_B = floor((1.775 - 0.6)/0.9) + 1 = floor(1.306) + 1 = 2

They agree. At `t = 1.2, need = 0.6`:

    c*     = 2.0 + 1.2 - 1.5 = 1.70
    kSat_A = floor((1.6 - 0.6)/1.2) + 1 = floor(0.833) + 1 = 1
    kSat_B = floor((1.70 - 0.6)/1.2) + 1 = floor(0.917) + 1 = 1

They agree again. At `t = 0.75, need = 0.6`:

    c*     = 2.0 + 0.75 - 0.9375 = 1.8125
    kSat_A = floor((1.6 - 0.6)/0.75) + 1 = floor(1.333) + 1 = 2
    kSat_B = floor((1.8125 - 0.6)/0.75) + 1 = floor(1.617) + 1 = 2

They agree. The two formulas differ only when `c*` and `M*r` fall on opposite
sides of a multiple of `t` -- i.e. when the shortfall `t*(1-r)/r` is comparable
to the distance from `M*r - need` to the next multiple of `t`. That is a narrow
window, and this experiment does not try to hit it. What it does instead is
test the law where it is easy to falsify: vary `t` at fixed `M, r, need` and
require the count to follow `kSat_B`.

`M = 2.0, r = 0.8, need = 0.6`:

    t = 0.60 -> c* = 1.70 -> kSat_B = floor(1.833)+1 = 2
    t = 0.70 -> c* = 1.775-> kSat_B = floor(1.679)+1 = 2
    t = 0.75 -> c* = 1.8125-> kSat_B = floor(1.617)+1 = 2
    t = 0.90 -> c* = 1.775-> kSat_B = floor(1.306)+1 = 2
    t = 1.20 -> c* = 1.70 -> kSat_B = floor(0.917)+1 = 1

So four arms predict 2 and one predicts 1. The `t = 1.2` arm is the one that
moves, and it is the `specific` control: if the count is a real function of the
parameters it must drop to 1 there and nowhere else.
"""

import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")
OUT = os.path.join(ROOT, "results", "EXP-90")


def c_star(m, t, r):
    return m + t - t / r


def ksat_b(m, t, r, need):
    return int((c_star(m, t, r) - need) / t) + 1


def ksat_a(m, t, r, need):
    return int((m * r - need) / t) + 1


def run_trace(args):
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
    return data


def census(frame):
    s = frame["samples"]
    alive = [x for x in s if x["alive"]]
    cells = {}
    for x in alive:
        cells[x["cell"]] = cells.get(x["cell"], 0) + 1
    return {
        "alive": len(alive),
        "crowding": (sum(cells.values()) / len(cells)) if cells else 0.0,
        "max_cell_load": max(cells.values()) if cells else 0,
    }


def arm(t, need, m=2.0, r=0.8, cells=40, n=160, steps=4000, every=1000):
    args = [
        "--policy", "stay",
        "--n", str(n),
        "--cells", str(cells),
        "--steps", str(steps),
        "--every", str(every),
        "--seed", "1",
        "--field", "uniform",
        "--rich", str(m),
        "--poor", str(m),
        "--income", str(t),
        "--maintenance", str(need),
        "--regrow", str(r),
        "--move-cost", "0.0",
        "--read-budget", "0",
        "--layout", "even",
        "--energy", "10.0",
        "--capacity", "10.0",
        "--damage-rate", "0.0",
        "--repair-cost", "1.5",
    ]
    return run_trace(args)


def main():
    m, r, need = 2.0, 0.8, 0.6
    arms = [0.60, 0.70, 0.75, 0.90, 1.20]
    rows = []
    for t in arms:
        d = arm(t, need, m=m, r=r)
        last = census(d["frames"][-1])
        pred_b = ksat_b(m, t, r, need)
        pred_a = ksat_a(m, t, r, need)
        row = {
            "t": t,
            "c_star": round(c_star(m, t, r), 4),
            "kSat_A": pred_a,
            "kSat_B": pred_b,
            "alive": last["alive"],
            "measured_k": last["max_cell_load"],
            "crowding": last["crowding"],
            "hash": d["hash"],
            "path": d["_path"],
        }
        rows.append(row)
        print(json.dumps(row))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(rows, f, indent=1)
    return rows


if __name__ == "__main__":
    main()
