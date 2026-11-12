#!/usr/bin/env python3
"""
EXP-21: when `feed=true` and M <= t/r, the cell is eaten to zero.
What happens to the field then?

Arithmetic (written before the run):
  feed=true order is regrow-then-take:
    c1 = c + (M - c) * r        (regrow)
    c2 = c1 - min(c1, k*t)      (take)
  Fixed point on a cell with k organisms: c* = M - k*t/r.

  With n = cells = 8 the organisms spread at random over the cells, so k is
  NOT 1 everywhere. The seed-1 layout is:
    cells 0, 3      : k = 0  ->  c* = M          (never eaten)
    cells 1,2,4,5   : k = 1  ->  c* = M - t/r
    cells 6, 7      : k = 2  ->  c* = M - 2t/r   (floored at 0 when negative)

  With r = 0.5, t = 1.0 (so t/r = 2.0) and 8 cells, mean field =
    (2 * M + 4 * (M - 2.0) + 2 * max(M - 4.0, 0)) / 8

    A: feed=true,  M = 2.0  -> (2*2 + 4*0 + 2*0)/8   =  4/8  = 0.5
    C: feed=true,  M = 4.0  -> (2*4 + 4*2 + 2*0)/8   = 16/8  = 2.0

  B is feed=false: take first, then regrow.
    c1 = c - min(c, k*t)
    c2 = c1 + (M - c1) * r
  The formula c* = M + k*t - k*t/r holds ONLY while c1 > 0, i.e. while the
  cell is not eaten clean. When k*t >= c the cell goes to c1 = 0 and regrows
  to M*r in one step:
    c* = M*r  when k*t >= c*
  With r = 0.5, M = 2.0: M*r = 1.0, and k*t = 2.0 >= 1.0, so a cell with
  k = 2 sits at 1.0, not at 0.0. A cell with k = 1 has c* = M + t - t/r = 1.0
  too, so every occupied cell sits at 1.0 and the empty ones at M = 2.0:
    B -> (2*2 + 6*1)/8 = 10/8 = 1.25

  Prediction: A = 0.5, B = 1.25, C = 2.0.
  The field does not collapse as a whole — it SEGREGATES: cells with k >= 2
  are eaten clean (feed=true) or reset to M*r (feed=false), empty cells sit
  at M untouched, single-occupancy cells sit at M - t/r. The mean is a
  mixture of those values and is not an equilibrium of anything.

Control tests:
  fires    — A must show emptied cells: min(field) < 0.01.
  silent   — B, same M/r/t but feed=false, must keep every cell positive:
             min(field) > 0.5.
  specific — C, feed=true but M > t/r, must keep the single-occupancy cells
             at M - t/r = 2.0 and only empty the k=2 cells; so min(field)
             must be < 0.01 AND the mean must be > 1.0. This separates
             "feed=true" from "feed=true and M <= t/r".
"""
import json
import subprocess
import sys
import pathlib
import hashlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from checks.experiment import Experiment  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIN = ROOT / "core" / "target" / "release" / "trace"


def run(feed, M, r=0.5, t=1.0, n=8, cells=8, steps=40, every=1):
    """One trace run. Returns (samples, hash)."""
    args = [
        str(BIN),
        "--n", str(n),
        "--cells", str(cells),
        "--steps", str(steps),
        "--every", str(every),
        "--policy", "stay",
        "--field", "uniform",
        "--rich", str(M),
        "--poor", str(M),
        "--regrow", str(r),
        "--income", str(t),
        "--maintenance", "0.0",
        "--repair-cost", "0.0",
        "--move-cost", "0.0",
        "--capacity", "1000.0",
        "--energy", "10.0",
        "--seed", "1",
    ]
    if feed:
        args.append("--feed")
    proc = subprocess.run(args, check=True, capture_output=True)
    # The binary prints a short report and writes the frames to
    # results/<policy>/trace-<policy>-<pid>.json. Read the file it names.
    written = None
    for line in proc.stdout.decode().splitlines():
        if line.startswith("written:"):
            written = ROOT / line.split(":", 1)[1].strip()
    if written is None or not written.exists():
        raise RuntimeError(f"trace did not write a file: {proc.stdout!r}")
    raw = written.read_bytes()
    h = hashlib.sha256(raw).hexdigest()[:16]
    return json.loads(raw), h


def main():
    exp = Experiment(
        experiment_id="exp21-feed-collapse",
        question=(
            "When feed=true and M <= t/r the equilibrium c* = M - t/r is "
            "non-positive. Does the field collapse, and is the collapse "
            "caused by feed=true or by the parameters?"
        ),
        arithmetic={
            "order_feed_true": "c1 = c + (M-c)*r ; c2 = c1 - min(c1, k*t)",
            "order_feed_false": "c1 = c - min(c, k*t) ; c2 = c1 + (M-c1)*r",
            "fixed_point_feed_true": "c* = M - k*t/r",
            "fixed_point_feed_false": "c* = M + k*t - k*t/r while c1 > 0, else c* = M*r",
            "r": 0.5,
            "t": 1.0,
            "t_over_r": 2.0,
            "layout_seed_1": {"k0": 2, "k1": 4, "k2": 2},
            "A_mean_formula": "(2*M + 4*(M - 2.0) + 2*max(M - 4.0, 0)) / 8",
            "B_mean_formula": "(2*M + 6*M*r) / 8",
            "A_feed_true_M_2.0_mean": 0.5,
            "B_feed_false_M_2.0_mean": 1.25,
            "C_feed_true_M_4.0_mean": 2.0,
        },
        arms={
            "A": "feed=true,  M=2.0 (= t/r) -> predicted field 0.0",
            "B": "feed=false, M=2.0         -> predicted field 1.0",
            "C": "feed=true,  M=4.0 (> t/r) -> predicted field 2.0",
        },
        seed=1,
        command="python3 checks/exp21_feed_collapse.py",
        parameters={"n": 8, "cells": 8, "steps": 40, "every": 1,
                    "policy": "stay", "field": "uniform"},
    )

    sA, hA = run(feed=True, M=2.0)
    sB, hB = run(feed=False, M=2.0)
    sC, hC = run(feed=True, M=4.0)

    def stats(s):
        f = s["frames"][-1]["field"]
        return sum(f) / len(f), min(f), max(f)

    meanA, minA, maxA = stats(sA)
    meanB, minB, maxB = stats(sB)
    meanC, minC, maxC = stats(sC)

    exp.add_arm("A", "feed=true, M=2.0=t/r",
                {"mean_field": meanA, "min_field": minA, "max_field": maxA},
                trace_hash=hA)
    exp.add_arm("B", "feed=false, M=2.0",
                {"mean_field": meanB, "min_field": minB, "max_field": maxB},
                trace_hash=hB)
    exp.add_arm("C", "feed=true, M=4.0>t/r",
                {"mean_field": meanC, "min_field": minC, "max_field": maxC},
                trace_hash=hC)

    exp.control("fires", minA < 0.01,
                f"A: min field {minA:.6f} < 0.01 — cells with k>=2 are eaten clean")
    exp.control("silent", minB > 0.5,
                f"B: min field {minB:.6f} > 0.5 — same M=2.0, r=0.5, t=1.0, "
                f"feed=false keeps every cell alive")
    exp.control("specific", (minC < 0.01) and (meanC > 1.0),
                f"C: min field {minC:.6f} < 0.01 and mean {meanC:.6f} > 1.0 — "
                f"feed=true with M=4.0 > t/r still empties the k=2 cells but "
                f"keeps the rest at M - t/r = 2.0")

    ok = (minA < 0.01) and (minB > 0.5) and (minC < 0.01) and (meanC > 1.0)
    exp.verdict(
        "passed" if ok else "failed",
        (f"A mean={meanA:.4f} min={minA:.4f}; B mean={meanB:.4f} min={minB:.4f}; "
         f"C mean={meanC:.4f} min={minC:.4f}. The field does not collapse as a "
         "whole — it SEGREGATES: cells with k >= 2 are eaten clean, empty cells "
         "sit at M untouched, single-occupancy cells sit at M - t/r. The mean is "
         "a mixture of those three values and is not an equilibrium.")
        if ok else
        (f"A mean={meanA:.4f} min={minA:.4f}; B mean={meanB:.4f} min={minB:.4f}; "
         f"C mean={meanC:.4f} min={minC:.4f} — prediction did not hold."),
    )

    exp.limitation(
        "The layout (which cells hold 0, 1 or 2 organisms) is set by the seed "
        "and by Policy::Stay. A moving population would redistribute k every "
        "step, and the per-cell fixed point M - k*t/r would then be a moving "
        "target, not an equilibrium. This experiment does not exercise that."
    )
    exp.limitation(
        "This shows what happens to the FIELD. It does not show what happens to "
        "the organisms: maintenance=0 and move-cost=0 here, so an organism on a "
        "cleared cell pays nothing for staying and nothing for moving. Whether a "
        "population survives on a segregated field is a separate question."
    )

    out = exp.save()
    print(json.dumps({"saved": str(out),
                      "A": {"mean": meanA, "min": minA, "max": maxA},
                      "B": {"mean": meanB, "min": minB, "max": maxB},
                      "C": {"mean": meanC, "min": minC, "max": maxC},
                      "hashes": [hA, hB, hC]}, indent=2))


if __name__ == "__main__":
    main()
