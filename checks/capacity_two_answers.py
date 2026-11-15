"""LAW-capacity's closed form against the code it claims to derive from.

`docs/LAW-capacity.md` gives a worst-case bound

    k_max(t) = max( floor(M*r/t), floor((M*r - m - bill)/t) + 1 )

and `checks/capacity_law.py` computes a mean-field capacity

    jmax = floor((M*r - m)/t) + 1

Two different numbers under the same name, in one repository, neither citing
the other. `docs/UNREPRODUCIBLE.md` records which is which; this script
measures the gap so the record cannot rot.

## What this script got wrong, three times

The first version reported a gap of `-9..-357` and blamed it on `capacity()`
returning a **global** count summed over all cells while `k_max` is **per
cell**. The second version divided by `cells` and still came out negative.
The third version -- this one, before the fix -- did the same thing again.

The guess was wrong every time. `capacity()` does **not** depend on `cells`:
it returns `1, 2, 2, 3` for every `cells` in `10, 40, 120`. Dividing by
`cells` made every answer zero, which is why the gap was negative and why it
looked like a real disagreement. The original comparison -- `capacity()`
against `k_max`, no division -- was correct, and the numbers in
`docs/UNREPRODUCIBLE.md` are the ones it measured.

The real defect was in the gate, not the comparison: both earlier versions
printed `NOTE` and returned 0 when the sweep disagreed. A gate that cannot
fail on the thing it measured is the defect `LESSONS.md` calls "a control
that cannot fail is a slogan". The doc meanwhile carried a table that no
longer matched the run, and nothing checked it.

## What it measures now

Three separate questions, each with its own exit code:

1. **The sweep in the doc.** The doc prints the rows it saw. This script
   recomputes them and fails if the doc's numbers are not the computed ones.
   The doc is a claim about a run; a claim that cannot be checked is prose.
2. **The gap on the sweep.** `capacity_law.py` must never come out **below**
   `LAW-capacity.md`: dropping `bill` can only raise the answer, never lower
   it. A violation is a real failure.
3. **The regime the extra term exists for.** There must exist parameter
   points where `bill` moves the floor. If none exist, the term is untested.

Usage:
    python3 checks/capacity_two_answers.py
"""
import contextlib
import io
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "UNREPRODUCIBLE.md"

# `capacity_law.py` prints its sweep at import time. Importing it silently is
# the difference between a check and a wall of output nobody reads twice.
with contextlib.redirect_stdout(io.StringIO()):
    from capacity_law import capacity, jmax  # noqa: E402

#: `docs/LAW-capacity.md` uses damage_rate=0.02, repair_cost=1.5.
BILL = 0.02 * 1.5

#: The sweep this script reports, and the one `docs/UNREPRODUCIBLE.md` prints.
SWEEP = [(cells, M, r) for cells in (10, 40, 120)
         for M, r in ((1.0, 0.8), (2.0, 0.8), (3.0, 0.6), (4.0, 0.8))]


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


def per_cell(cap_global: int, cells: int) -> int:
    """`capacity()` already answers per cell, despite taking `cells`.

    It returns the same number for `cells` in `10, 40, 120`, so dividing by
    `cells` -- as this script did in two earlier versions -- turns every row
    into zero and manufactures a gap that is not there. The parameter only
    enters through the binomial in `alive()`, and on this sweep it does not
    move the answer.
    """
    return cap_global


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


def rows() -> list[tuple[int, float, float, float, int, int]]:
    out = []
    for cells, M, r in SWEEP:
        t = 1.0
        cap = per_cell(capacity(cells, M, r), cells)
        wc = k_max_worst(M, r, t, 0.6)
        out.append((cells, M, r, t, cap, wc))
    return out


#: The table as `docs/UNREPRODUCIBLE.md` prints it: `cells M r t | law | doc | gap`.
DOC_ROW = re.compile(
    r"^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
    re.MULTILINE,
)


def doc_rows() -> list[tuple[int, float, float, float, int, int]]:
    if not DOC.exists():
        return []
    return [
        (int(a), float(b), float(c), float(d), int(e), int(f))
        for a, b, c, d, e, f in DOC_ROW.findall(DOC.read_text(encoding="utf-8"))
    ]


def main() -> int:
    print("cells   M    r    t    | capacity_law.py | LAW-capacity.md | gap")
    print("-" * 74)
    computed = rows()
    for cells, M, r, t, cap, wc in computed:
        print(f"{cells:5} {M:4.1f} {r:4.2f} {t:4.1f} | {cap:15} | {wc:15} | {cap - wc:+5}")

    hits = find_disagreement()
    differ = sum(1 for *_, cap, wc in computed if cap != wc)
    ordered = sum(1 for *_, cap, wc in computed if cap >= wc)

    print()
    print(f"  fires    {differ}/{len(computed)} sweep rows where the two answers differ")
    print(f"  silent   {ordered}/{len(computed)} sweep rows where capacity_law.py >= "
          f"LAW-capacity.md")
    print(f"  specific {len(hits)} parameter points where `bill` moves the floor "
          f"(the regime the extra term exists for)")
    if hits:
        M, r, t, wc, jm = hits[0]
        print(f"           first: M={M:.4f} r={r} t={t} -> doc {wc}, "
              f"capacity_law.py {jm}")

    problems = []

    # 1. The doc must print the numbers the script computes.
    claimed = doc_rows()
    if not claimed:
        problems.append(
            "docs/UNREPRODUCIBLE.md: таблица свипа не найдена -- запись о "
            "расхождении нечего сверять с прогоном"
        )
    elif claimed != computed:
        for want, got in zip(computed, claimed):
            if want != got:
                problems.append(
                    "docs/UNREPRODUCIBLE.md: строка свипа "
                    f"cells={want[0]} M={want[1]} r={want[2]}: в документе "
                    f"{got[4]}/{got[5]}, прогон даёт {want[4]}/{want[5]}"
                )
        if len(claimed) != len(computed):
            problems.append(
                f"docs/UNREPRODUCIBLE.md: {len(claimed)} строк свипа, "
                f"прогон даёт {len(computed)}"
            )

    # 2. Dropping `bill` can only raise the answer.
    if ordered != len(computed):
        problems.append(
            f"capacity_law.py ниже LAW-capacity.md на "
            f"{len(computed) - ordered} строках свипа -- порядок нарушен"
        )

    # 3. The extra term must be exercised somewhere.
    if not hits:
        problems.append(
            "нет ни одной точки, где `bill` двигает пол -- член, ради "
            "которого выведен закон, не проверен"
        )

    print()
    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print(f"OK: документ совпадает с прогоном ({len(computed)} строк),")
    print(f"    порядок держится ({ordered}/{len(computed)}), член `bill`")
    print(f"    двигает пол в {len(hits)} точках.")
    print("    Расхождение на свипе -- не ошибка, а два разных вопроса;")
    print("    какой из них когда применяется, записано в")
    print("    `docs/UNREPRODUCIBLE.md` §1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
