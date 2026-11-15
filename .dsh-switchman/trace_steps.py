import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")
TRACE = os.path.join(CORE, "target", "release", "trace")

REPAIR_COST = 1.5
DAMAGE = 0.02
MAINTENANCE = 0.1
INCOME = 2.0
CAPACITY = 1000.0
ENERGY = 10.0


def run(n, M, r, protocol, steps, seed, every):
    args = [
        TRACE, "--cells", "1", "--n", str(n), "--policy", "stay",
        "--steps", str(steps), "--every", str(every),
        "--capacity", str(CAPACITY), "--income", str(INCOME),
        "--maintenance", str(MAINTENANCE), "--repair-cost", str(REPAIR_COST),
        "--damage-rate", str(DAMAGE), "--move-cost", "0", "--energy", str(ENERGY),
        "--field", "uniform", "--rich", str(M), "--poor", str(M),
        "--regrow", str(r), "--layout", "even", "--seed", str(seed),
        "--share", protocol, "--out", "-",
    ]
    p = subprocess.run(args, cwd=CORE, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("trace failed: " + p.stderr[-300:])
    raw = p.stdout
    d = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    frames = d["frames"]
    return frames, d["hash"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=17)
    ap.add_argument("--M", type=float, default=3.0)
    ap.add_argument("--r", type=float, default=0.8)
    ap.add_argument("--proto", default="proportional")
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    frames, h = run(a.n, a.M, a.r, a.proto, a.steps, a.seed, a.every)
    print("hash", h, "frames", len(frames))
    for f in frames[:40]:
        alive = sum(1 for s in f["samples"] if s["alive"])
        e = [round(s["energy"], 3) for s in f["samples"][:6]]
        t = [round(s["taken"], 4) for s in f["samples"][:6]]
        print("step %4d alive %2d field %s E %s taken %s"
              % (f["step"], alive, [round(x, 4) for x in f["field"]], e, t))


if __name__ == "__main__":
    main()
