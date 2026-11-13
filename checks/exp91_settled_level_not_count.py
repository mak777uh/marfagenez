"""EXP-91: the level a fed-on cell settles at, when the population is capped by
the initial placement rather than by the field.

EXP-89 and EXP-90 measured the SURVIVAL count, which is an integer and hides
the continuous law. Here the population is small enough that nobody dies, so
the field level can be read directly.

The per-cell law with `k` standing occupants taking `min(level, t)` in turn and
the field regrowing toward `M` by `r` once per step:

    L' = L + (M - L)*r - sum of the k takes

At equilibrium `L' = L`, so

    (M - L)*r = sum of takes                          (*)

For `k = 1` and `L >= t`: `(M - L)*r = t`, i.e. `L = M - t/r`.
That is the OLD formula, and it is wrong here only because the old formula was
applied to the wrong quantity: it is the level the cell settles at when exactly
one organism eats a full portion every step.

For `k = 2` with `M = 2.0, r = 0.8, t = 0.6`:

    guess L = 1.70: takes = 0.6 + min(1.10, 0.6) = 1.2
                    (M - L)*r = 0.3*0.8 = 0.24  != 1.2   -> L must be higher
    guess L = 1.25: takes = 0.6 + min(0.65, 0.6) = 1.2
                    (M - L)*r = 0.75*0.8 = 0.60 != 1.2
    guess L = 0.50: takes = 0.5 + 0 = 0.5
                    (M - L)*r = 1.5*0.8 = 1.2   != 0.5

So with `k = 2` and `t = 0.6` the cell cannot hold two full portions from the
regrowth: the regrowth at any level `L` is `0.8*(2 - L)`, which equals `1.2`
only at `L = 0.5`, where the cell has only `0.5` to give. The consistent point
is where the second organism is rationed:

    L - t = 0.8*(2 - L) - t   ->   L = 0.8*(2 - L)   ->   L = 1.6/1.8 = 0.8889
    takes = 0.6 + 0.2889 = 0.8889,  regrowth = 0.8*(2 - 0.8889) = 0.8889  OK

So `k = 2` at `t = 0.6` settles at `L = M*r/(1+r) = 0.8889`, and the second
organism takes `0.2889` against a need of `0.6` -- it starves. That is exactly
why EXP-90 measured `k = 2` and not 3: the cell settles at a level that feeds
one and a third organisms, not two.

Prediction for this experiment: with `n = 40` on 40 cells (one per cell) the
level settles at `M - t/r`; with `n = 80` (two per cell) it settles at
`M*r/(1+r)`. The second number is the `fires` control -- it is below the first
and below `t + need`.
"""

import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")
OUT = os.path.join(ROOT, "results", "EXP-91")


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


def arm(n, cells=40, t=0.6, m=2.0, r=0.8, steps=2000, every=500):
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
        "--maintenance", "0.0",
        "--regrow", str(r),
        "--move-cost", "0.0",
        "--read-budget", "0",
        "--layout", "even",
        "--energy", "10.0",
        "--capacity", "1000.0",
        "--damage-rate", "0.0",
        "--repair-cost", "1.5",
    ]
    return run_trace(args)


def main():
    m, r, t = 2.0, 0.8, 0.6
    pred1 = m - t / r
    pred2 = m * r / (1.0 + r)
    rows = []
    for n in (40, 80, 120):
        d = arm(n, t=t, m=m, r=r)
        last = d["frames"][-1]
        levels = last["field"]
        alive = [x for x in last["samples"] if x["alive"]]
        row = {
            "n": n,
            "alive": len(alive),
            "level_min": round(min(levels), 6),
            "level_max": round(max(levels), 6),
            "level_mean": round(sum(levels) / len(levels), 6),
            "pred_one": round(pred1, 6),
            "pred_two": round(pred2, 6),
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
