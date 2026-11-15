#!/usr/bin/env python3
"""Sweep the capacity boundary of the two share protocols.

One process, one binary, all points. Writes JSON rows to stdout (and a file).

Usage:
    python3 sweep_capacity.py [--steps 1500] [--out FILE]

Each row: M, r, income, n, protocol, alive, taken (per-slot), energies, field, hash.
"""
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
SEED = 1


def run(n, M, r, protocol, steps, income=INCOME, maintenance=MAINTENANCE):
    args = [
        TRACE,
        "--cells", "1",
        "--n", str(n),
        "--policy", "stay",
        "--steps", str(steps),
        "--every", str(steps),
        "--capacity", str(CAPACITY),
        "--income", str(income),
        "--maintenance", str(maintenance),
        "--repair-cost", str(REPAIR_COST),
        "--damage-rate", str(DAMAGE),
        "--move-cost", "0",
        "--energy", str(ENERGY),
        "--field", "uniform",
        "--rich", str(M),
        "--poor", str(M),
        "--regrow", str(r),
        "--layout", "even",
        "--seed", str(SEED),
        "--share", protocol,
        "--out", "-",
    ]
    p = subprocess.run(args, cwd=CORE, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"trace failed ({p.returncode}) for n={n} M={M} r={r} {protocol}: {p.stderr[-400:]}")
    raw = p.stdout
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < 0:
        raise RuntimeError(f"no JSON in trace stdout for n={n} M={M} r={r} {protocol}")
    d = json.loads(raw[start:end + 1])
    f = d["frames"][-1]
    samples = f["samples"]
    return {
        "M": M,
        "r": r,
        "income": income,
        "maintenance": maintenance,
        "cost": round(maintenance + DAMAGE * REPAIR_COST, 6),
        "n": n,
        "protocol": protocol,
        "alive": sum(1 for s in samples if s["alive"]),
        "taken": [round(s["taken"], 6) for s in samples],
        "energies": [round(s["energy"], 3) for s in samples],
        "field": [round(x, 6) for x in f["field"]],
        "hash": d["hash"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--out", default=os.path.join(ROOT, ".dsh-switchman", "sweep_capacity.json"))
    ap.add_argument("--quick", action="store_true", help="only n=1..6, for a smoke test")
    a = ap.parse_args()

    if not os.path.isfile(TRACE):
        sys.exit(f"missing binary: {TRACE}")

    grid = [(2.0, 0.5), (2.0, 0.8), (2.0, 0.95),
            (3.0, 0.5), (3.0, 0.8), (3.0, 0.95),
            (4.0, 0.8), (4.0, 0.95)]
    ns = list(range(1, 7)) if a.quick else list(range(1, 25))

    rows = []
    for (M, r) in grid:
        for proto in ("sequential", "proportional"):
            for n in ns:
                row = run(n, M, r, proto, a.steps)
                rows.append(row)
                print(f"M={M} r={r} {proto:12s} n={n:2d} alive={row['alive']:2d} "
                      f"taken={row['taken'][:3]}", flush=True)

    with open(a.out, "w") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nwrote {a.out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
