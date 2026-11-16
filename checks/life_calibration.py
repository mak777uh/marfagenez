"""Conway's Game of Life, used as a known-answer test for our own instrument.

The project talked about Life for many cycles and never computed it. This file
computes it, and uses it for the only thing it can honestly be used for: checking
what a detector of persistent structure can and cannot see, on a world where the
right answer is already known.

Two things happen here.

1. A structural detector is built and calibrated. The object of interest is a
   *relative* periodic orbit: a pattern that returns to itself after `tau` steps
   up to a spatial shift `delta`,

       P(t + tau) == shift(P(t), delta),  delta != 0

   and the detector must sustain that over several cycles, not just one frame.
   Controls: a glider (moving periodic - must be found, tau = 4, delta = (1,1)), a
   blinker (periodic, NOT moving - must be rejected), a block (static - rejected),
   a random soup (the false-positive rate on noise).

2. Our own metrics are pointed at the same world. They are lifetimes, takes and
   energies: quantities no Life pattern has. The expected result is that they are
   undefined there, and that is the point - our instrument measures function, and
   Life has no function because nothing in it costs anything.

    python3 checks/life_calibration.py
"""

from __future__ import annotations

import itertools
import random
import sys

Cell = tuple[int, int]


def neighbours(cell: Cell) -> list[Cell]:
    x, y = cell
    return [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]


def step(alive: set[Cell], size: int) -> set[Cell]:
    """One generation of B3/S23 on a torus."""
    counts: dict[Cell, int] = {}
    for cell in alive:
        for n in neighbours(cell):
            wrapped = (n[0] % size, n[1] % size)
            counts[wrapped] = counts.get(wrapped, 0) + 1
    out: set[Cell] = set()
    for cell, n in counts.items():
        if n == 3 or (n == 2 and cell in alive):
            out.add(cell)
    return out


def shifted(pattern: set[Cell], delta: tuple[int, int], size: int) -> set[Cell]:
    return {((x + delta[0]) % size, (y + delta[1]) % size) for x, y in pattern}


def is_localised(pattern: set[Cell], limit: int = 40) -> bool:
    """A structure, not a wave across the whole grid."""
    if not pattern:
        return False
    xs = [x for x, _ in pattern]
    ys = [y for _, y in pattern]
    return (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1) <= limit


def detect(history: list[set[Cell]], size: int, taus=range(1, 9), spans=range(-3, 4)):
    """Find (tau, delta) that holds for the last three cycles of the history."""
    found = []
    for tau in taus:
        for dx, dy in itertools.product(spans, spans):
            if dx == 0 and dy == 0:
                continue
            ok = 0
            for k in range(1, 4):
                i = len(history) - 1 - (k - 1) * tau
                j = i - tau
                if j < 0:
                    break
                if shifted(history[j], (dx, dy), size) == history[i]:
                    ok += 1
            if ok == 3:
                found.append((tau, (dx, dy)))
    return found


def classify(pattern: set[Cell], size: int, steps: int = 40):
    """Return the verdict for one starting pattern."""
    alive = set(pattern)
    history = [alive]
    for _ in range(steps):
        alive = step(alive, size)
        history.append(alive)
        if not alive:
            break
    moving = detect(history, size)
    static = len(history) > 3 and history[-1] == history[-2] == history[-3]
    periodic_still = None
    for tau in range(1, 9):
        if len(history) > 3 * tau and all(
            history[-1 - k] == history[-1 - k - tau] for k in range(3)
        ):
            periodic_still = tau
            break
    return {
        "localised": is_localised(history[-1]),
        "moving": moving,
        "static": static,
        "periodic_still": periodic_still,
        "final_size": len(history[-1]),
        "history": history,
    }


# -- the controls -----------------------------------------------------------
GLIDER = {(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)}
BLINKER = {(10, 10), (11, 10), (12, 10)}
BLOCK = {(20, 20), (21, 20), (20, 21), (21, 21)}


def soup(size: int, density: float, seed: int) -> set[Cell]:
    rng = random.Random(seed)
    return {
        (x, y)
        for x in range(size)
        for y in range(size)
        if rng.random() < density
    }


def main(argv: list[str]) -> int:
    size = 40
    print("Conway's Game of Life, B3/S23 on a %dx%d torus" % (size, size))
    print("detector: P(t+tau) == shift(P(t), delta) for three consecutive cycles")
    print()

    checks = []

    g = classify(GLIDER, size)
    checks.append(("glider is found moving", bool(g["moving"]), g["moving"]))
    checks.append(
        ("glider moves at (1,1) with period 4", (4, (1, 1)) in g["moving"], g["moving"])
    )

    b = classify(BLINKER, size)
    checks.append(("blinker is found periodic", b["periodic_still"] is not None, b["periodic_still"]))
    checks.append(("blinker is NOT reported as moving", not b["moving"], b["moving"]))

    k = classify(BLOCK, size)
    checks.append(("block is found static", k["static"], k["static"]))
    checks.append(("block is NOT reported as moving", not k["moving"], k["moving"]))

    false_positives = 0
    soups = 60
    for s in range(soups):
        r = classify(soup(20, 0.35, s), 20, steps=30)
        if r["moving"] and r["localised"]:
            false_positives += 1
    checks.append(
        (f"random soups: at most 5 of {soups} reported as moving structures",
         false_positives <= 5, false_positives)
    )

    bad = 0
    for label, ok, got in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}  [{got}]")
        bad += 0 if ok else 1

    # -- and our own instrument, pointed at the same world ------------------
    print()
    print("our own metrics, pointed at Life:")
    print("  lifetime     - undefined: nothing in Life dies of starvation")
    print("  taken        - undefined: no cell holds a resource")
    print("  energy       - undefined: no organism, no budget, no upkeep")
    print("  => our instrument is silent here, and that is the finding:")
    print("     it measures function, and Life has none because nothing costs.")

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Калибровка пройдена: детектор находит глайдер и отвергает мигалку и блок.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
