"""A calculation before any code: what signal does a sensory rule actually have?

`docs/WHERE-WE-ARE.md` states the limit that matters: an organism in this model compares
**one neighbour**, so a medium can reward **returning** but cannot reward **searching**.
That was an observation from experiments. This turns it into arithmetic.

The question is not about survival but about **signal**: standing on a cell, does a rule
point anywhere at all? On a line with rich islands every `s` cells and a poor sea between
them, compute for every position:

  * what a neighbour rule (`Sighted`) does: step to the richer of the two neighbours, or
    stay when they tie;
  * what a windowed rule would do: step toward the best cell within radius `k`;
  * whether the chosen step is toward the nearest island (`+`), away from it (`-`), or
    nothing (`0`, a tie).

    python3 checks/perception_signal.py

The claim it tests, declared before the run: with a neighbour rule the sea is **silent** -
both neighbours are equal on the flat bottom, so the rule has no signal at all except at
the island edges - and a windowed rule has a signal everywhere the island is within `k`.
If that holds, "searching" is not a matter of better behaviour but of **available signal**,
and no policy can search in a world that does not provide one.
"""

from __future__ import annotations

import sys

CELLS = 24
ISLAND_PERIOD = 8
RICH = 3.0
POOR = 1.65


def field() -> list[float]:
    return [RICH if i % ISLAND_PERIOD == 0 else POOR for i in range(CELLS)]


def neighbours(i: int) -> tuple[int, int]:
    return (i - 1) % CELLS, (i + 1) % CELLS


def nearest_island(i: int) -> int:
    best, best_d = None, None
    for j in range(CELLS):
        if field()[j] == RICH:
            d = min((i - j) % CELLS, (j - i) % CELLS)
            if best_d is None or d < best_d:
                best, best_d = j, d
    return best


def sign_toward(start: int, target: int) -> int:
    """+1 if a +1 step gets closer to target, -1 if a -1 step does, 0 if equidistant."""
    d_plus = min((start + 1 - target) % CELLS, (target - start - 1) % CELLS)
    d_minus = min((start - 1 - target) % CELLS, (target - start + 1) % CELLS)
    if d_plus < d_minus:
        return 1
    if d_minus < d_plus:
        return -1
    return 0


def neighbour_decision(i: int) -> int:
    f = field()
    left, right = neighbours(i)
    if f[left] == f[right]:
        return 0
    return 1 if f[right] > f[left] else -1


def windowed_decision(i: int, k: int) -> int:
    f = field()
    best_j, best_v, best_d = None, -1.0, None
    for d in range(-k, k + 1):
        j = (i + d) % CELLS
        if f[j] > best_v:
            best_j, best_v, best_d = j, f[j], d
    if best_d is None or best_d == 0:
        return 0
    return 1 if best_d > 0 else -1


def tally(decisions: list[tuple[int, int]]) -> dict[str, int]:
    out = {"toward": 0, "away": 0, "silent": 0}
    for step, target_sign in decisions:
        if step == 0:
            out["silent"] += 1
        elif step == target_sign:
            out["toward"] += 1
        else:
            out["away"] += 1
    return out


def main(argv: list[str]) -> int:
    f = field()
    print(f"line of {CELLS} cells, rich island every {ISLAND_PERIOD} cells")
    print("levels:", " ".join(f"{v:.2f}" for v in f))
    print()

    neighbour = [(neighbour_decision(i), sign_toward(i, nearest_island(i))) for i in range(CELLS)]
    n = tally(neighbour)
    print(f"neighbour rule: toward {n['toward']:2}, away {n['away']:2}, "
          f"silent {n['silent']:2} of {CELLS}")
    # Silence on an island is correct - there is nowhere better to go. What matters is
    # silence in the sea, where a searching form would need the signal.
    sea = [i for i in range(CELLS) if f[i] != RICH]
    sea_silent = sum(1 for i in sea if neighbour_decision(i) == 0)
    silent_share = sea_silent / len(sea)
    print(f"  silent share of the sea: {silent_share:.0%} ({sea_silent} of {len(sea)} cells) "
          f"- no signal at all on the flat bottom")

    rows = []
    for k in (1, 2, 3, 4):
        dec = [(windowed_decision(i, k), sign_toward(i, nearest_island(i))) for i in range(CELLS)]
        t = tally(dec)
        rows.append((k, t))
        print(f"windowed k={k}: toward {t['toward']:2}, away {t['away']:2}, "
              f"silent {t['silent']:2} of {CELLS}")

    print()
    bad = 0
    checks = [
        ("the neighbour rule is silent on the flat sea (share > 40%)",
         silent_share > 0.40, f"{silent_share:.0%}"),
        ("a window of half the spacing has a signal in every sea cell",
         all(windowed_decision(i, 4) != 0 for i in sea),
         sum(1 for i in sea if windowed_decision(i, 4) == 0)),
        ("the windowed rule is never wrong more often than right",
         all(t["away"] <= t["toward"] for _, t in rows), [(k, t["away"], t["toward"]) for k, t in rows]),
    ]
    for label, ok, val in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}  [{val}]")
        bad += 0 if ok else 1
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Расчёт пройден: сигнал neighbour-правила отсутствует на плоском дне.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
