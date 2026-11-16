"""Every number the paper draft quotes, re-measured against the model.

The most dangerous error in a paper written from a project's own notes is a number
that is remembered better than it was measured. This script does not trust the
findings: it re-runs the probe and compares against the tables in
`docs/PAPER-draft.md`.

Covered: section 4.1 (per-step boundary across four world sizes), 4.2 (full boundary
on two branches), 4.3 (realised surplus on a depleting lattice).

    python3 checks/paper_numbers.py

Exit code 1 on any mismatch, so it can be a gate.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "memory_probe")


def run(**kw) -> dict:
    cmd = [PROBE]
    for key, value in kw.items():
        flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            cmd += [flag, "on" if value else "off"]
        else:
            cmd += [flag, str(value)]
    cmd += ["--steps", "20000", "--threshold", "1.0", "--seed", "1"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def lifetime(**kw) -> int:
    return int(run(**kw)["lifetime"])


BASE = dict(
    m=2.0,
    regrow=0.99,
    maintenance=1.7911,
    repair_cost=1.5,
    damage_rate=0.02,
    capacity=10.0,
    energy=5.0,
    read_budget=3,
    read_cost=0.0,
    read_period=1,
    field="uniform",
    period=6,
    poor=0.5,
    start_cell=0,
    arm="stay",
)


def check(results: list[tuple[str, int, int]]) -> int:
    bad = 0
    for label, got, want in results:
        if got == want:
            print(f"  ok    {label}: {got}")
        else:
            print(f"  WRONG {label}: measured {got}, paper says {want}")
            bad += 1
    return bad


def main(argv: list[str]) -> int:
    if not os.path.exists(PROBE):
        print(f"probe not built: {PROBE}")
        return 1

    print("4.1 per-step boundary, four world sizes")
    res = []
    for n in (12, 24, 48, 96):
        for income, want in ((1.70, 42), (1.78, 124), (1.8211, 20000), (1.94, 20000)):
            got = lifetime(cells=n, income=income, **BASE)
            res.append((f"N={n} income={income}", got, want))
    bad = check(res)

    print("4.2 full boundary, two branches (dr = 0.3, s = 0.1, income 1.8911)")
    res = []
    for cap, want_live in ((1.0, {0.30, 0.33, 0.35, 0.40}), (0.2, {0.30, 0.33})):
        for rc in (0.30, 0.33, 0.35, 0.40, 0.45):
            got = lifetime(
                cells=24,
                m=2.0,
                regrow=0.99,
                maintenance=1.7911,
                damage_rate=0.3,
                income=1.8911,
                capacity=cap,
                repair_cost=rc,
                energy=5.0,
                read_budget=3,
                read_cost=0.0,
                read_period=1,
                field="uniform",
                period=6,
                poor=0.5,
                start_cell=0,
                arm="stay",
            )
            if rc in want_live:
                res.append((f"capacity={cap} rc={rc} alive", got, 20000))
            elif got >= 20000:
                print(f"  WRONG capacity={cap} rc={rc}: paper says dead, measured {got}")
                bad += 1
            else:
                print(f"  ok    capacity={cap} rc={rc} dead at {got}")
    bad += check(res)

    print("4.3 realised surplus on a peaked lattice (nominal income 3.0)")
    real = dict(BASE, m=3.0, income=3.0, regrow=0.99, field="peaks", period=2, start_cell=1)
    res = []
    for rc, poor, want in (
        (1.5, 1.838, 3440),
        (1.5, 1.8395, 20000),
        (2.0, 1.846, 1459),
        (2.0, 1.8496, 20000),
    ):
        got = lifetime(
            cells=24,
            m=3.0,
            regrow=0.99,
            maintenance=1.7911,
            damage_rate=0.02,
            income=3.0,
            capacity=10.0,
            repair_cost=rc,
            energy=5.0,
            read_budget=3,
            read_cost=0.0,
            read_period=1,
            field="peaks",
            period=2,
            poor=poor,
            start_cell=1,
            arm="stay",
        )
        res.append((f"rc={rc} poor={poor}", got, want))
    bad += check(res)

    if bad:
        print(f"\nРАСХОЖДЕНИЙ: {bad}")
        return 1
    print("\nВсе числа статьи сверены с моделью, расхождений 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
