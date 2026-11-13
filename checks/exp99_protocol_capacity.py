# -*- coding: utf-8 -*-
"""Is the capacity of a cell a property of the *protocol* of distribution?

The claim under test (from outside this project):

    Sequential distribution (index order, `min(income, rest)`) and
    proportional distribution (softmax: everyone divides one normalised unit)
    give different integer laws for how many organisms a cell can hold, so
    capacity is a property of the protocol, not of the resource or the eater.

The sequential half is already measured: EXP-98 gives

    k_max = floor((M*r - cost)/income) + 1

This experiment tests the second half by building a proportional cell in the
same Rust core and running the same grid through both.

The proportional cell, defined so that the only difference from the sequential
one is *who gets what*:

    w_j    = 1 for every organism on the cell      (no advantage, Delta = 0)
    share_j = income * w_j / sum_k w_k             (all organisms, alive or not)
    take_j  = min(share_j, cell_before_sharing)
    cell   -= take_j                               (applied simultaneously)

With Delta = 0 the share is `income/k` for each of `k` organisms. Organism j
survives iff `income/k >= cost`, i.e. `k <= income/cost`, so

    k_max_prop = floor(income / cost)

and the field capacity is `cells * floor(income/cost)`. This depends on
`income` and `cost` and not on `M` or `r` at all -- because in a proportional
split the sum of the shares is fixed at `income` however rich the cell is.
That is the structural difference the claim points at, and it is a *prediction*
that can fail: if the measured k_max moves with `M`, the proportional cell is
not proportional.

Controls:
  fires    - the proportional law reproduces the measured k_max on the grid
  silent   - with income < cost, k_max = 0 under both protocols: a cell that
             cannot pay one organism's cost pays nobody, whatever the protocol
  specific - the two protocols disagree on at least one point of the grid;
             a law that gave the same answer everywhere would be measuring the
             resource, not the protocol
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

REPAIR_COST = 1.5


def measure(cells, n, M, r, t, maintenance, damage, protocol, steps=1500):
    cmd = [TRACE, "--cells", str(cells), "--n", str(n),
           "--policy", "stay", "--steps", str(steps), "--every", str(steps),
           "--capacity", "1000", "--income", str(t),
           "--maintenance", str(maintenance), "--repair-cost", str(REPAIR_COST),
           "--damage-rate", str(damage), "--move-cost", "0", "--energy", "10",
           "--field", "uniform", "--rich", str(M), "--poor", str(M),
           "--regrow", str(r), "--layout", "even", "--seed", "1",
           "--share", protocol]
    res = subprocess.run(cmd, capture_output=True, text=True,
                         cwd=os.path.join(ROOT, "core"))
    if res.returncode != 0:
        print("TRACE FAILED", res.returncode, res.stderr[-800:])
        sys.exit(1)
    written = None
    for line in res.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
    if written is None or not os.path.isabs(written):
        written = os.path.join(ROOT, "core", written)
    with open(written) as fh:
        data = json.load(fh)
    last = data["frames"][-1]
    return sum(1 for s in last["samples"] if s["alive"]), data["hash"]


def k_seq(M, r, income, cost):
    supply = M * r
    if cost <= 0:
        return None
    if income < cost or supply < cost:
        return 0
    return int((supply - cost) // income) + 1


def k_prop(M, r, income, cost):
    if cost <= 0:
        return None
    if income < cost:
        return 0
    return int(income // cost)


GRID = [
    (2.0, 0.8, 0.6, 0.1, 0.0),
    (2.0, 0.8, 0.6, 0.3, 0.0),
    (2.0, 0.8, 0.6, 0.5, 0.0),
    (2.0, 0.8, 0.2, 0.1, 0.0),
    (2.0, 0.8, 1.0, 0.1, 0.0),
    (3.0, 0.8, 0.6, 0.1, 0.0),
    (4.0, 0.8, 0.6, 0.1, 0.0),
    (2.0, 0.5, 0.6, 0.1, 0.0),
    (2.0, 0.9, 0.6, 0.1, 0.0),
    (2.0, 0.8, 0.8, 0.6, 0.02),
]


def main():
    exp = Experiment(
        experiment_id="EXP-99",
        question="Does the protocol of distribution change how many organisms a cell holds?",
        arithmetic={
            "sequential k_max": "0 if income<cost or M*r<cost else floor((M*r-cost)/income)+1",
            "proportional k_max": "0 if income<cost else floor(income/cost)",
            "why they differ": "sequential sums k portions of up to `income`; "
                               "proportional splits one `income` among k",
        },
        arms={"sequential": "index order, min(income, rest)",
              "proportional": "share = income/k, applied simultaneously"},
        seed=1,
        command="checks/exp99_protocol_capacity.py",
    )

    rows = []
    bad_prop = 0
    bad_seq = 0
    disagree = 0
    first_seq_hash = None
    first_prop_hash = None
    for M, r, t, mc, d in GRID:
        cost = mc + d * REPAIR_COST
        ks = k_seq(M, r, t, cost)
        kp = k_prop(M, r, t, cost)
        if ks is None or kp is None:
            continue
        n = max(ks, kp) + 3
        a_s, h_s = measure(1, n, M, r, t, mc, d, "sequential")
        a_p, h_p = measure(1, n, M, r, t, mc, d, "proportional")
        if first_seq_hash is None:
            first_seq_hash, first_prop_hash = h_s, h_p
        ok_s = ks == a_s
        ok_p = kp == a_p
        bad_seq += 0 if ok_s else 1
        bad_prop += 0 if ok_p else 1
        disagree += 1 if a_s != a_p else 0
        rows.append(dict(M=M, r=r, income=t, cost=cost, seq_law=ks, seq_meas=a_s,
                         prop_law=kp, prop_meas=a_p, ok=ok_s and ok_p))
        print("M=%.1f r=%.1f income=%.2f cost=%.2f | seq %d/%d %s | prop %d/%d %s" %
              (M, r, t, cost, ks, a_s, "ok" if ok_s else "MISMATCH",
               kp, a_p, "ok" if ok_p else "MISMATCH"))

    exp.add_arm("sequential", "index order, one cell, k = max(laws)+3",
                {"points": len(rows), "mismatches": bad_seq},
                trace_hash=first_seq_hash)
    exp.add_arm("proportional", "share = income/k, one cell, same k",
                {"points": len(rows), "mismatches": bad_prop},
                trace_hash=first_prop_hash)

    exp.control("fires", bad_prop == 0 and bad_seq == 0,
                "sequential %d/%d, proportional %d/%d" %
                (len(rows) - bad_seq, len(rows), len(rows) - bad_prop, len(rows)))

    silent_ok = True
    detail = []
    for M, r in ((2.0, 0.8), (4.0, 0.8)):
        for proto in ("sequential", "proportional"):
            a, _ = measure(1, 4, M, r, 0.1, 0.5, 0.0, proto)
            detail.append("%s M=%g: %d" % (proto, M, a))
            if a != 0:
                silent_ok = False
    exp.control("silent", silent_ok,
                "income 0.1 < cost 0.5 kills everyone under both protocols: " +
                ", ".join(detail))

    exp.control("specific", disagree > 0,
                "the two protocols give different survivor counts on %d of %d "
                "grid points" % (disagree, len(rows)))

    exp.limitation(
        "Measured on one cell, `stay`, maintenance > 0, Delta = 0 (no organism has "
        "an advantage over another). A proportional cell with an advantage would "
        "need a weight per organism, and the law would then depend on the ratio "
        "of weights, not on k alone. Nothing here says which protocol is the more "
        "faithful picture of attention; it says only that the two give different "
        "integer laws on the same resource and the same eater."
    )
    exp.verdict("passed" if (bad_prop == 0 and bad_seq == 0 and disagree > 0) else "failed",
                "sequential %d/%d, proportional %d/%d, protocols disagree on %d points" %
                (len(rows) - bad_seq, len(rows), len(rows) - bad_prop, len(rows), disagree))
    path = exp.save()
    print("\nverdict:", exp._result["verdict"])
    print("written:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
