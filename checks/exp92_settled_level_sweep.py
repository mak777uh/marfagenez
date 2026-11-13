"""EXP-92: the level a fed-on cell settles at, as a function of the crowding.

EXP-91 measured three points and got 1.85 / 1.70 / 1.60 at `k = 1, 2, 3` with
`M = 2.0, r = 0.8, t = 0.6`. This experiment turns those three points into a
law by sweeping `k` and by sweeping `t`, and by making the prediction BEFORE
the run from the recurrence

    L' = L + (M - L)*r - sum_{i=1..k} min(L - (taken so far), t)

The equilibrium condition is `(M - L)*r = sum of takes`. Writing
`g = (M - L)*r` for the regrowth, the takes are `min(L, t)` then
`min(L - t, t)` and so on, so for `k` occupants

    L >= k*t  ->  g = k*t                    (nobody rationed)
    L <  k*t  ->  g = L                     (the last one takes the rest)

The second case is the one the measurements live in: `g = L` means
`(M - L)*r = L`, i.e.

    L = M*r/(1 + r)

independent of `t` and of `k`. That is why 1.70 and 1.60 came out so close at
`k = 2` and `k = 3` -- and it predicts that the level stays at `M*r/(1+r)`
for every `k` at which the last occupant is rationed, i.e. every `k` with
`k*t > M*r/(1+r)`.

At `M = 2.0, r = 0.8`: `M*r/(1+r) = 1.6/1.8 = 0.8889`. With `t = 0.6` that
means `k > 1.48`, i.e. every `k >= 2` should settle at 0.8889. The measurement
gave 1.70 and 1.60 instead, so the prediction is wrong and the run is worth
doing: the disagreement is large and in one direction.

What the measurement actually suggests is that the take is capped by `t` but
the regrowth is not the only thing feeding the cell -- the organisms also
regrow it, or the take is smaller than `min(L, t)`. The sweep below separates
the two by varying `t` at fixed `k`.
"""

import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")
OUT = os.path.join(ROOT, "results", "EXP-92")


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


def arm(k, t, m=2.0, r=0.8, cells=40, steps=2000, every=500):
    args = [
        "--policy", "stay",
        "--n", str(k * cells),
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


def predict(k, t, m=2.0, r=0.8):
    """Solve `(M - L)*r = sum of k takes` by bisection on L."""
    lo, hi = 0.0, m
    for _ in range(200):
        mid = (lo + hi) / 2.0
        left = mid
        takes = 0.0
        for _ in range(k):
            got = min(left, t)
            takes += got
            left -= got
        g = (m - mid) * r
        if g > takes:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def main():
    m, r = 2.0, 0.8
    rows = []
    for t in (0.2, 0.4, 0.6, 0.8, 1.0):
        for k in (1, 2, 3, 4):
            d = arm(k, t, m=m, r=r)
            last = d["frames"][-1]
            levels = last["field"]
            alive = [x for x in last["samples"] if x["alive"]]
            row = {
                "t": t,
                "k": k,
                "alive": len(alive),
                "level": round(sum(levels) / len(levels), 6),
                "spread": round(max(levels) - min(levels), 6),
                "pred": round(predict(k, t, m, r), 6),
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
