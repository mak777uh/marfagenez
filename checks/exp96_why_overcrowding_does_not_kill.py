"""EXP-96: why overcrowding does not kill.

EXP-95 found that capacity is not C*kSat: at n = 160 on 40 cells with
kSat = 3, all 160 survive. The extra organisms get nothing to eat, so
they should starve. They do not.

Probe (core/examples/tmp_probe.rs) shows why: with income 0.6,
maintenance 0, damage_rate 0, the starving organisms sit at exactly
energy 10.00 -- the spawn energy -- and never move. So `taken` is 0 and
the energy does not change.

Read the code: `Organism::step` does
    energy += taken
    energy -= maintenance_cost
    energy = energy.min(capacity).max(0.0)
    death if energy <= 0

With maintenance_cost = 0 and taken = 0, energy is unchanged: 10.0.
An organism that eats nothing and costs nothing does not die.

So "capacity" in this world is not a survival limit at all: an organism
that never eats lives forever. EXP-95's mismatches are not a wrong law,
they are a world where starvation is impossible.

The survival limit only exists when maintenance_cost > 0. This
experiment measures it with maintenance_cost > 0 and checks that the
capacity is then exactly C*kSat.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / "core" / "target" / "release" / "trace"
OUT = ROOT / "results" / "capacity-law"
OUT.mkdir(parents=True, exist_ok=True)


def measure(cells, n, M, r, t, maintenance, steps=1200):
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
    alive = sum(1 for s in last["samples"] if s["alive"])
    return alive, last["field"][0]


def ksat(M, r, t):
    return int((M * r) // t) + 1


def main():
    print("A. maintenance = 0: nothing starves, capacity is not a limit")
    for n in (40, 120, 160, 240):
        alive, level = measure(40, n, 2.0, 0.8, 0.6, 0.0)
        print(f"  n={n}: alive={alive} level={level:.4f}  (expected {n}: nobody starves)")

    print()
    print("B. maintenance > 0: the surplus starves, capacity = cells*kSat")
    rows = []
    bad = 0
    for cells, n, M, r, t, mc in [
        (40, 40, 2.0, 0.8, 0.6, 0.1),
        (40, 80, 2.0, 0.8, 0.6, 0.1),
        (40, 120, 2.0, 0.8, 0.6, 0.1),
        (40, 160, 2.0, 0.8, 0.6, 0.1),
        (40, 200, 2.0, 0.8, 0.6, 0.1),
        (40, 120, 2.0, 0.8, 1.0, 0.1),
        (40, 160, 2.0, 0.8, 1.0, 0.1),
        (40, 200, 2.0, 0.9, 0.6, 0.1),
        (40, 240, 2.0, 0.9, 0.6, 0.1),
        (40, 240, 3.0, 0.8, 0.6, 0.1),
        (40, 280, 3.0, 0.8, 0.6, 0.1),
    ]:
        alive, level = measure(cells, n, M, r, t, mc)
        ks = ksat(M, r, t)
        cap = cells * ks
        expected = min(n, cap)
        ok = alive == expected
        if not ok:
            bad += 1
        rows.append(dict(cells=cells, n=n, M=M, r=r, t=t, mc=mc, kSat=ks,
                         capacity=cap, measured=alive, ok=ok))
        print(f"  cells={cells} n={n} M={M} r={r} t={t} mc={mc}: kSat={ks} "
              f"capacity={cap} alive={alive} {'OK' if ok else 'MISMATCH'}")

    print()
    print(f"{bad} mismatches out of {len(rows)}")
    (OUT / "summary-starvation.json").write_text(json.dumps(rows, indent=1))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
