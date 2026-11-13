"""EXP-93: what the readout is actually reading.

EXP-92 swept `k = 1..4` and `t = 0.2..1.0` at `M = 2.0, r = 0.8` and got a
level that depends on BOTH, in a way no equilibrium of the recurrence

    L' = L + (M - L)*r - sum of takes

can produce. That recurrence says the level is a function of `(k, t)` only
through the sum of takes, and at `k >= 2` with `t >= 0.4` the last occupant is
rationed, which pins `L` at `M*r/(1+r) = 0.8889` independently of `t`. The
measurement gave 1.7, 1.6, 1.6, 1.6 -- never 0.8889.

Before inventing a mechanism, check the simple thing: what does the trace
actually print? `frame["field"]` is the field AFTER the step (the readout is a
camera, not a hand -- PROTOCOL.md). If the level printed is the level after
regrowth and after the takes, then it is `L'`, and the recurrence above applies
to it directly. If the printed level is taken BEFORE the regrowth, the
recurrence is off by one regrowth and the equilibrium is different.

This experiment resolves the order by measuring a single organism on a single
cell for a few steps and comparing the printed level against both candidate
orders computed by hand.

`M = 2.0, r = 0.8, t = 0.6`, one organism, one cell, start at `L = 2.0`:

    order A (take, then regrow):  L' = 2.0 - 0.6 = 1.4 ; regrow -> 1.4 + 0.6*0.8 = 1.88
    order B (regrow, then take):  L' = 2.0 + 0*0.8 = 2.0 ; take 0.6 -> 1.40

The two orders differ at the FIRST step and only there, so a one-step reading
settles it. `--steps 1 --every 1` prints frame 1.
"""

import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")
OUT = os.path.join(ROOT, "results", "EXP-93")


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


def arm(steps, every, t=0.6, m=2.0, r=0.8, n=1, cells=1):
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
    d = arm(5, 1, t=t, m=m, r=r)
    levels = [fr["field"][0] for fr in d["frames"]]
    taken = [fr["samples"][0]["taken"] for fr in d["frames"]]
    print("levels", levels)
    print("taken ", taken)

    # Two hand-computed candidate sequences.
    a = m
    seq_a = []
    for _ in range(5):
        a = a - min(a, t)
        a = a + (m - a) * r
        seq_a.append(round(a, 6))
    b = m
    seq_b = []
    for _ in range(5):
        b = b + (m - b) * r
        b = b - min(b, t)
        seq_b.append(round(b, 6))
    print("order A (take then regrow)", seq_a)
    print("order B (regrow then take)", seq_b)
    row = {
        "levels": levels,
        "taken": taken,
        "order_A": seq_a,
        "order_B": seq_b,
        "hash": d["hash"],
        "path": d["_path"],
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(row, f, indent=1)
    return row


if __name__ == "__main__":
    main()
