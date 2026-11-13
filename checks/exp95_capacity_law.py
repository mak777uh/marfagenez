"""EXP-95: capacity from the settled level law.

EXP-94 established, on 21 arms and with no mismatch,

    L*(k) = M - k*t*(1-r)/r      if k*t <= M*r
          = M*r                  if k*t >  M*r

and one cell feeds kSat = floor(M*r/t) + 1 organisms (the last one is
rationed and gets only the remainder).

So the capacity of a field of C cells is

    capacity = C * (floor(M*r/t) + 1)

This experiment measures capacity directly and compares.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / "core" / "target" / "release" / "trace"
OUT = ROOT / "results" / "capacity-law"
OUT.mkdir(parents=True, exist_ok=True)


def measure(cells, n, M, r, t, steps=400):
    cmd = [
        str(TRACE),
        "--cells", str(cells),
        "--n", str(n),
        "--policy", "stay",
        "--steps", str(steps),
        "--every", str(steps),
        "--capacity", "1000",
        "--income", str(t),
        "--maintenance", "0",
        "--repair-cost", "1.5",
        "--damage-rate", "0",
        "--move-cost", "0",
        "--energy", "10",
        "--field", "uniform",
        "--rich", str(M),
        "--poor", str(M),
        "--regrow", str(r),
        "--layout", "even",
        "--seed", "1",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT / "core"))
    if res.returncode != 0:
        print("TRACE FAILED", res.returncode, res.stderr[-400:])
        sys.exit(1)
    written = None
    for line in res.stdout.splitlines():
        if line.startswith("written:"):
            written = Path(line.split(":", 1)[1].strip())
    if written is None or not written.is_absolute():
        written = ROOT / "core" / written
    data = json.loads(written.read_text())
    last = data["frames"][-1]
    return sum(1 for s in last["samples"] if s["alive"])


def ksat(M, r, t):
    return int((M * r) // t) + 1


def main():
    grid = [
        # cells, n, M, r, t
        (40, 40, 2.0, 0.8, 0.6),
        (40, 80, 2.0, 0.8, 0.6),
        (40, 120, 2.0, 0.8, 0.6),
        (40, 160, 2.0, 0.8, 0.6),
        (40, 200, 2.0, 0.8, 0.6),
        (40, 40, 2.0, 0.8, 1.0),
        (40, 80, 2.0, 0.8, 1.0),
        (40, 120, 2.0, 0.8, 1.0),
        (40, 40, 2.0, 0.9, 0.6),
        (40, 120, 2.0, 0.9, 0.6),
        (40, 160, 2.0, 0.9, 0.6),
        (40, 200, 2.0, 0.9, 0.6),
        (40, 40, 3.0, 0.8, 0.6),
        (40, 160, 3.0, 0.8, 0.6),
        (40, 200, 3.0, 0.8, 0.6),
        (40, 240, 3.0, 0.8, 0.6),
        (20, 60, 2.0, 0.8, 0.6),
        (20, 80, 2.0, 0.8, 0.6),
        (80, 240, 2.0, 0.8, 0.6),
        (80, 320, 2.0, 0.8, 0.6),
    ]
    rows = []
    bad = 0
    for cells, n, M, r, t in grid:
        alive = measure(cells, n, M, r, t)
        ks = ksat(M, r, t)
        predicted = cells * ks
        expected_alive = min(n, predicted)
        ok = alive == expected_alive
        if not ok:
            bad += 1
        rows.append(dict(cells=cells, n=n, M=M, r=r, t=t, kSat=ks,
                         capacity=predicted, measured=alive, ok=ok))
        print(f"cells={cells} n={n} M={M} r={r} t={t}: kSat={ks} "
              f"capacity={predicted} alive={alive} "
              f"{'OK' if ok else 'MISMATCH'}")

    print()
    print(f"{bad} mismatches out of {len(rows)}")
    (OUT / "summary.json").write_text(json.dumps(rows, indent=1))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
