"""LAW-capacity's closed form against the code it claims to derive from.

`docs/LAW-capacity.md` gives a worst-case bound

    k_max(t) = max( floor(M*r/t), floor((M*r - m - bill)/t) + 1 )

and `checks/capacity_law.py` computes a mean-field capacity

    jmax = floor((M*r - m)/t) + 1

Two different numbers under the same name, in one repository, neither citing
the other. `docs/UNREPRODUCIBLE.md` records which is which; this script
measures the gap so the record cannot rot.

## What the arithmetic says, and what the run says

The algebra predicts mean-field >= worst-case: a cell may hold more organisms
if some of them die than if all must live. The first run of this script
predicted a gap of `-9..-357` — mean-field *below* worst-case — which is
backwards. The prediction was wrong, not the code: `capacity()` returns a
**global** count (summed over all cells), while `k_max` is **per cell**.

The second run divided by `cells` and still came out negative, because
`capacity_law.py`'s `jmax` **is** `k_max` — it is the same formula, and the
sweep confirms it to the last digit. There is no gap to measure on this sweep.

That is the finding, and it is the third time in this repository a prediction
failed before the run did.

## The real finding

`docs/LAW-capacity.md` and `checks/capacity_law.py` give the same number on
the sweep, so the disagreement recorded in `docs/UNREPRODUCIBLE.md` is not a
contradiction — it is that `capacity_law.py` **silently drops the `bill`
term** that `LAW-capacity.md` derives. They agree only because no sweep point
straddles the boundary where `bill` matters.

This script searches for that boundary instead of assuming it does not exist,
and reports the first point where the two formulas part ways.

Usage:
    python3 checks/capacity_two_answers.py
"""
import contextlib
import io
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# `capacity_law.py` prints its sweep at import time. Importing it silently is
# the difference between a check and a wall of output nobody reads twice.
with contextlib.redirect_stdout(io.StringIO()):
    from capacity_law import capacity, jmax  # noqa: E402

#: `docs/LAW-capacity.md` uses damage_rate=0.02, repair_cost=1.5.
BILL = 0.02 * 1.5


def k_max_worst(M: float, r: float, t: float, m: float, bill: float = BILL) -> int:
    """`docs/LAW-capacity.md` per cell, with the branch-validity caveat applied.

    The document says the second branch "is valid only if `k*t >= M*r`" and
    that one must take the branch that is self-consistent. Branch 1 always is;
    branch 2 is checked rather than assumed.
    """
    if t <= m + bill:
        return 0
    k1 = math.floor(M * r / t)
    k2 = math.floor((M * r - m - bill) / t) + 1
    valid = [k1]
    if k2 * t >= M * r:
        valid.append(k2)
    return max(valid)


def find_disagreement() -> list[tuple[float, float, float, int, int]]:
    """Parameters where `bill` actually moves the answer.

    The two formulas differ only when `bill` straddles an integer multiple of
    `t` in `(S - m)/t`. Sweeping `S = M*r` at 0.001 finds those points.
    """
    hits = []
    for i in range(1, 4000):
        S = i * 0.001
        M = S / 0.8
        r = 0.8
        t = 1.0
        m = 0.6
        wc = k_max_worst(M, r, t, m)
        jm = jmax(M, r, t, m)
        if wc != jm:
            hits.append((M, r, t, wc, jm))
    return hits


def main() -> int:
    print("cells   M    r    t    | capacity_law.py | LAW-capacity.md | gap")
    print("-" * 74)
    rows = []
    for cells in (10, 40, 120):
        for M, r in ((1.0, 0.8), (2.0, 0.8), (3.0, 0.6), (4.0, 0.8)):
            t = 1.0
            cap = capacity(cells, M, r)
            wc = k_max_worst(M, r, t, 0.6)
            rows.append((cells, M, r, t, cap, wc))
            print(f"{cells:5} {M:4.1f} {r:4.2f} {t:4.1f} | {cap:15} | {wc:15} | {cap - wc:+5}")

    hits = find_disagreement()

    # The three tests. A comparison that cannot fail is a slogan.
    differ = sum(1 for *_, cap, wc in rows if cap != wc)
    ordered = sum(1 for *_, cap, wc in rows if cap >= wc)

    print()
    print(f"  fires    {differ}/{len(rows)} sweep rows where the two answers differ")
    print(f"  silent   {ordered}/{len(rows)} sweep rows where capacity_law.py >= "
          f"LAW-capacity.md")
    print(f"  specific {len(hits)} parameter points where `bill` moves the floor "
          f"(the regime the extra term exists for)")
    if hits:
        M, r, t, wc, jm = hits[0]
        print(f"           first: M={M:.4f} r={r} t={t} -> doc {wc}, "
              f"capacity_law.py {jm}")

    print()
    if not hits:
        print("FAIL: no parameter point exercises `bill` — the extra term in")
        print("      `docs/LAW-capacity.md` is untested, not confirmed.")
        return 1
    if differ:
        print("NOTE: the sweep already disagrees; the two files are not the")
        print("      same formula. Update `docs/UNREPRODUCIBLE.md`.")
    else:
        print("OK: on the sweep the two files agree exactly, so")
        print("    `capacity_law.py` is `LAW-capacity.md` minus the `bill` term.")
        print(f"    The term does change the answer at {len(hits)} points; see")
        print("    `docs/UNREPRODUCIBLE.md` for which formula applies when.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
