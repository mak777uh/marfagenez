"""EXP-97: which organism starves, and why the count is 120 not 160.

EXP-96 B: with maintenance 0.1 > 0, the surplus dies, but the number
that survives is 120 where kSat predicts 160 (M=2, r=0.9, t=0.6) and
160 where kSat predicts 200 (M=3, r=0.8, t=0.6).

Both wrong cases are the ones where the third/fourth/fifth organism
on a cell is *rationed*: it gets less than t. A rationed organism
pays maintenance out of the remainder and loses energy every step.
So the rationed organism starves, and the survivors are only the ones
that get the full t.

That gives

    kFull = floor(M*r/t)     (organisms per cell that get the full t)
    capacity = cells * kFull

Check: M=2, r=0.8, t=0.6 -> floor(1.6/0.6) = 2 -> 80.  But EXP-96
measured 120 at those settings.  So kFull is not it either.

The order matters. Organisms are stepped in slot order, and the cell
is emptied by the first kFull of them. The (kFull+1)-th gets the
remainder. But the regrow happens after all of them, so the remainder
is not zero: at the fixed point the cell holds L*, and the first
kFull take t each, leaving L* - kFull*t for the rest.

At the fixed point with k = kSat organisms, L* = M*r (the cell empties
every step). So the remainder for the (kFull+1)-th is
    M*r - kFull*t  =  remainder of the division
and it is constant. With M=2, r=0.8, t=0.6: 1.6 - 1.2 = 0.4.

The rationed organism gets 0.4 per step and pays 0.1 maintenance,
so it gains 0.3 per step. It does NOT starve. It grows.

So the rationed organism survives, and capacity should be
cells * kSat = 120. Which is what was measured at M=2, r=0.8.

Then why 120 and not 160 at M=2, r=0.9? kSat = floor(1.8/0.6)+1 = 4.
Remainder = 1.8 - 3*0.6 = 0.0. The fourth organism gets 0.0, pays
0.1, and dies. So the capacity is

    capacity = cells * (kFull + [remainder > maintenance_cost])

i.e. the last, rationed organism survives only if its ration covers
its maintenance.

M=2, r=0.8, t=0.6: kFull=2, remainder 0.4 > 0.1 -> 3 per cell -> 120.
M=2, r=0.9, t=0.6: kFull=3, remainder 0.0 < 0.1 -> 3 per cell -> 120.
M=3, r=0.8, t=0.6: kFull=4, remainder 0.0 < 0.1 -> 4 per cell -> 160.
M=2, r=0.8, t=1.0: kFull=1, remainder 0.6 > 0.1 -> 2 per cell -> 80.

All four match EXP-96 B. This experiment tests the rule on a fresh
grid it was not fitted to.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / "core" / "target" / "release" / "trace"
OUT = ROOT / "results" / "capacity-law"
OUT.mkdir(parents=True, exist_ok=True)


def measure(cells, n, M, r, t, maintenance, steps=1500):
    cmd = [
        str(TRACE),
        "--cells", str(cells),
        "--n", str(n),
        "--policy", "stay",
        "--steps", str(steps),
        "--every", str(steps),
        "--capacity", "1000",
        "--income", str(t),
        "--maintenance", str(maintenance),
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


def capacity_per_cell(M, r, t, mc):
    full = int((M * r) // t)
    remainder = M * r - full * t
    return full + (1 if remainder > mc else 0)


def main():
    grid = [
        # M, r, t, mc
        (2.0, 0.8, 0.6, 0.1),
        (2.0, 0.8, 0.6, 0.3),
        (2.0, 0.9, 0.6, 0.1),
        (3.0, 0.8, 0.6, 0.1),
        (2.0, 0.8, 1.0, 0.1),
        (2.0, 0.8, 1.0, 0.5),
        (2.0, 0.8, 0.2, 0.1),
        (2.0, 0.5, 0.6, 0.1),
        (4.0, 0.8, 0.6, 0.1),
        (4.0, 0.8, 0.9, 0.1),
    ]
    rows = []
    bad = 0
    for M, r, t, mc in grid:
        cells = 20
        k = capacity_per_cell(M, r, t, mc)
        n = cells * (k + 2)
        alive = measure(cells, n, M, r, t, mc)
        predicted = cells * k
        ok = alive == predicted
        if not ok:
            bad += 1
        rows.append(dict(M=M, r=r, t=t, mc=mc, per_cell=k,
                         capacity=predicted, measured=alive, ok=ok))
        print(f"M={M} r={r} t={t} mc={mc}: per_cell={k} capacity={predicted} "
              f"alive={alive} {'OK' if ok else 'MISMATCH'}")

    print()
    print(f"{bad} mismatches out of {len(rows)}")
    (OUT / "summary-per-cell.json").write_text(json.dumps(rows, indent=1))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
