"""EXP-94: the settled level law.

Prediction (derived from the order take-all-then-regrow-once):

    L*(k) = M - k*t*(1-r)/r      if k*t <= M*r
          = M*r                  if k*t >  M*r

and the number of organisms one cell can feed is

    kSat = floor(M*r/t) + 1

Test it on a grid of (M, r, t, k) that includes both branches.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / "core" / "target" / "release" / "trace"
OUT = ROOT / "results" / "settled-law"
OUT.mkdir(parents=True, exist_ok=True)


def predict(M, r, t, k):
    if k * t <= M * r:
        return M - k * t * (1.0 - r) / r
    return M * r


def measure(M, r, t, k, cells=1, steps=400):
    cmd = [
        str(TRACE),
        "--cells", str(cells),
        "--n", str(k),
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
    return last["field"][0], sum(1 for s in last["samples"] if s["alive"])


def main():
    rows = []
    grid = [
        (2.0, 0.8, 0.6, 1), (2.0, 0.8, 0.6, 2), (2.0, 0.8, 0.6, 3),
        (2.0, 0.8, 0.6, 4), (2.0, 0.8, 0.6, 5),
        (2.0, 0.8, 1.0, 1), (2.0, 0.8, 1.0, 2), (2.0, 0.8, 1.0, 3),
        (2.0, 0.8, 0.2, 1), (2.0, 0.8, 0.2, 4), (2.0, 0.8, 0.2, 8),
        (3.0, 0.8, 0.6, 1), (3.0, 0.8, 0.6, 3), (3.0, 0.8, 0.6, 4),
        (3.0, 0.8, 0.6, 5),
        (2.0, 0.5, 0.6, 1), (2.0, 0.5, 0.6, 2), (2.0, 0.5, 0.6, 3),
        (2.0, 0.9, 0.6, 1), (2.0, 0.9, 0.6, 2), (2.0, 0.9, 0.6, 3),
    ]
    bad = 0
    for M, r, t, k in grid:
        level, alive = measure(M, r, t, k)
        p = predict(M, r, t, k)
        ok = abs(level - p) < 1e-6
        if not ok:
            bad += 1
        rows.append((M, r, t, k, level, p, alive, ok))
        print(f"M={M} r={r} t={t} k={k}: level={level:.6f} predicted={p:.6f} "
              f"alive={alive} {'OK' if ok else 'MISMATCH'}")

    print()
    print(f"{bad} mismatches out of {len(rows)}")
    (OUT / "summary.json").write_text(json.dumps(
        [{"M": a, "r": b, "t": c, "k": d, "level": e, "predicted": f,
          "alive": g, "ok": h} for a, b, c, d, e, f, g, h in rows], indent=1))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
