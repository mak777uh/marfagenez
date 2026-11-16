"""`K`, the damage clock, against `ceil(1/dr)`.

Step 3 of `core/src/organism.rs` is

    self.damage = (self.damage + world.damage_rate).min(1.0);

so the number of steps from `damage = 0` to death by damage is

    clock(dr) = min { k : fl_sum_k(dr) >= 1.0 }

where `fl_sum_k(dr)` is `dr` added to itself `k` times **in that order**, each
addition rounded. `FINDING-148` measured `K = 11` at `dr = 0.1` where
`ceil(1/dr) = 10`, and `FINDING-149` carried the measured `K` into the boundary
of life without saying where the two numbers part. This script says where.

Three controls, each with its own verdict:

1. **fires** -- on the decimal grid `dr = k/10000`, `k = 1..10000`, the
   divergences must exist and must be exactly the set of reciprocals `1/n` that
   the grid contains. A different list (or none) is red: the mechanism would
   then not be the clock.
2. **silent** -- on random doubles the two answers must agree. The regression
   this rules out is a `clock` that stopped accumulating and computes
   `dr * k` instead: that agrees with `ceil(1/dr)` everywhere, including at the
   reciprocals, where the model does not.
3. **specific** -- the divergence must be a property of the **running sum**,
   not of `dr`. The same number of additions with exact rounding (`math.fsum`)
   or with a different association (pairwise tree) must give `ceil(1/dr)` back.
   Reversing a list of identical terms is bit-identical and proves nothing, so
   the control changes the association and not the order of the reads.

Usage:
    python3 checks/damage_clock.py
    python3 checks/damage_clock.py --selftest

Exit code 0 only when all three controls pass.
"""
import math
import random
import sys

#: The grid `FINDING-148` and `FINDING-149` drew their `dr` from.
GRID = 10000

#: The divergences on `k/10000`, as `k`. These are exactly `GRID/n` for
#: `n in {10, 80, 400, 2000, 2500, 5000, 10000}`: the reciprocals the grid
#: contains. `0.001 = 1000/10000` is **not** in the list -- `1000` additions of
#: `0.001` overshoot `1.0` and `K = 1000 = ceil(1/dr)` there.
EXPECTED_K = frozenset({1, 2, 4, 5, 25, 125, 1000})

#: Random draws for `silent` and the seed they come from. The seed is fixed so
#: a failure is reproducible; the count is small because this script runs in
#: `run.sh all` on every gate.
RANDOM_DRAWS = 2000
RANDOM_SEED = 20261116


def clock(dr):
    """Steps to death by damage, repeating step 3 of the model literally."""
    damage = 0.0
    steps = 0
    while True:
        steps += 1
        damage = min(damage + dr, 1.0)
        if damage >= 1.0:
            return steps


def predicted(dr):
    """`ceil(1.0/dr)` -- one division and one `ceil`, each of them rounded."""
    return math.ceil(1.0 / dr)


def clock_exact(dr):
    """The same sum with exact rounding. Divergence should disappear here."""
    steps = 0
    while True:
        steps += 1
        if min(math.fsum([dr] * steps), 1.0) >= 1.0:
            return steps


def _pairwise_insert(buckets, dr):
    """Adds one more copy of `dr` to a binary-counter tree of partial sums."""
    carry = dr
    level = 0
    while level < len(buckets) and buckets[level] is not None:
        carry = buckets[level] + carry
        buckets[level] = None
        level += 1
    if level == len(buckets):
        buckets.append(carry)
    else:
        buckets[level] = carry


def _pairwise_total(buckets):
    total = 0.0
    for value in reversed(buckets):
        if value is not None:
            total += value
    return total


def clock_pairwise(dr):
    """The same multiset of terms, summed with a different association."""
    buckets = []
    steps = 0
    while True:
        steps += 1
        _pairwise_insert(buckets, dr)
        if min(_pairwise_total(buckets), 1.0) >= 1.0:
            return steps


def fires():
    """On the decimal grid the divergences must be exactly the reciprocals."""
    found = {}
    for k in range(1, GRID + 1):
        dr = k / GRID
        measured = clock(dr)
        formula = predicted(dr)
        if measured != formula:
            found[k] = (measured, formula)
    keys = frozenset(found)
    problems = []
    if keys != EXPECTED_K:
        problems.append(
            "grid divergences %s, expected %s"
            % (sorted(keys), sorted(EXPECTED_K))
        )
    for k, (measured, formula) in sorted(found.items()):
        if GRID % k != 0:
            problems.append(
                "k=%d (%r) is not a reciprocal on the grid" % (k, k / GRID)
            )
        if measured != formula + 1:
            problems.append(
                "k=%d (%r): K=%d, ceil=%d -- not the off-by-one the clock makes"
                % (k, k / GRID, measured, formula)
            )
    detail = ", ".join(
        "%r: K=%d" % (k / GRID, found[k][0]) for k in sorted(found)
    )
    return keys == EXPECTED_K and not problems, (
        7 if not problems else len(problems)
    ), detail, problems


def silent():
    """Random doubles: the clock and `ceil(1/dr)` must agree."""
    rng = random.Random(RANDOM_SEED)
    problems = []
    draws = 0
    while draws < RANDOM_DRAWS:
        dr = rng.random()
        if dr <= 0.0:
            continue
        draws += 1
        measured = clock(dr)
        formula = predicted(dr)
        if measured != formula:
            problems.append(
                "%r: K=%d, ceil=%d" % (dr, measured, formula)
            )
            if len(problems) >= 5:
                break
    return not problems, draws - len(problems), "%d draws" % draws, problems


def specific():
    """The seven grid divergences vanish under exact or regrouped addition."""
    problems = []
    checked = 0
    for k in sorted(EXPECTED_K):
        dr = k / GRID
        running = clock(dr)
        exact = clock_exact(dr)
        regrouped = clock_pairwise(dr)
        formula = predicted(dr)
        checked += 1
        if running != formula + 1:
            problems.append(
                "%r: running sum gives K=%d, expected %d"
                % (dr, running, formula + 1)
            )
        if exact != formula:
            problems.append(
                "%r: exact sum gives K=%d, ceil=%d -- the divergence is not "
                "the running sum" % (dr, exact, formula)
            )
        if regrouped != formula:
            problems.append(
                "%r: regrouped sum gives K=%d, ceil=%d -- the divergence is "
                "not the association" % (dr, regrouped, formula)
            )
    detail = "%d/%d reciprocals: running K=ceil+1, exact and regrouped K=ceil" % (
        checked - len(problems),
        checked,
    )
    return not problems, checked, detail, problems


def main(argv):
    if "--selftest" in argv:
        return selftest()

    failures = 0
    print("damage clock: K = min{k : fl_sum_k(dr) >= 1.0} vs ceil(1.0/dr)")
    print()
    for name, control in (("fires", fires), ("silent", silent),
                          ("specific", specific)):
        ok, count, detail, problems = control()
        print("  %-8s %-4s  %s" % (name, "ok" if ok else "FAIL", detail))
        if not ok:
            failures += 1
            for problem in problems[:8]:
                print("           %s" % problem)
            print()

    # The number 148 measured, restated as a check: at dr = 0.1 the running sum
    # does not reach 1.0 in ten steps. This is the one point FINDING-148 saw.
    if clock(0.1) != 11 or predicted(0.1) != 10:
        failures += 1
        print("  %-8s %-4s  dr=0.1: K=%d, ceil=%d"
              % ("case", "FAIL", clock(0.1), predicted(0.1)))
    else:
        print("  %-8s %-4s  dr=0.1: K=11, ceil=10 (the point FINDING-148 saw)"
              % ("case", "ok"))

    print()
    if failures:
        print("ЕСТЬ РАСХОЖДЕНИЯ: контролей провалено %d" % failures)
        return 1
    print("ВСЁ СОГЛАСОВАНО: расхождения есть, и они -- последовательное сложение")
    return 0


def selftest():
    """The controls must be able to fail. Each case breaks one assumption."""
    cases = []

    # 1. A grid where the clock is a multiplication agrees with the formula
    #    everywhere: `fires` must go red on the empty set.
    saved = globals()["clock"]
    try:
        globals()["clock"] = lambda dr: math.ceil(1.0 / dr)
        ok, _, _, _ = fires()
        cases.append(("fires sees a clock without accumulation", ok is False))
        ok, _, _, _ = specific()
        cases.append(("specific sees a clock without accumulation", ok is False))
    finally:
        globals()["clock"] = saved

    # 2. A grid that differs from the reciprocals is red even when it is
    #    non-empty: the list itself is part of the claim.
    saved = EXPECTED_K
    try:
        globals()["EXPECTED_K"] = frozenset({3, 7})
        ok, _, _, _ = fires()
        cases.append(("fires compares the set, not just its size", ok is False))
    finally:
        globals()["EXPECTED_K"] = saved

    # 3. `silent` must be able to fail: a clock that is always a step late
    #    disagrees on every draw.
    saved = globals()["clock"]
    try:
        globals()["clock"] = lambda dr: math.ceil(1.0 / dr) + 1
        ok, _, _, _ = silent()
        cases.append(("silent sees a wrong clock", ok is False))
    finally:
        globals()["clock"] = saved

    bad = [name for name, passed in cases if not passed]
    for name, passed in cases:
        print("  %-6s %s" % ("ok" if passed else "FAIL", name))
    print()
    if bad:
        print("САМОПРОВЕРКА ПРОВАЛЕНА: %d из %d" % (len(bad), len(cases)))
        return 1
    print("САМОПРОВЕРКА ПРОЙДЕНА: %d из %d" % (len(cases), len(cases)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
