"""The numbers in the docs must match the numbers in the tree.

`docs/PLAN-NEXT.md` §2 A3 records the problem this file exists for: three
documents claimed three different theorem counts (317, 290, 281) and none of
them said which tree they were counting. A number in prose is a claim like any
other, and an unchecked claim drifts.

## What is checked

The **live** claims — the ones a reader would take as a statement about the
tree today. Everything else is a dated record and is skipped.

A file is **frozen** when its name says it is a record of a past state:
`docs/FINDING-*.md`, `docs/SYNTHESIS-*.md`, `LESSONS.md`, `docs/ELIMINATED.md`,
`docs/VISION.md`, `docs/PLAN.md`, `docs/PLAN-EXPERIMENTS.md`,
`docs/MASTER_PLAN.md`. These carry a date and a count from that date; rewriting
them would be falsifying the record. `docs/PLAN-NEXT.md` is frozen too — it is
the plan that *describes* this drift, and its numbers are quotations of the
wrong claims.

A line inside a live file is skipped when it is marked historical by wording:
`HISTORICAL`, `историческ`, `предыдущ`, `previous`, `ранее`, `было`, `→`.

Everything else must match one of the three counts the tree actually gives
(`Medium`, `Legacy`, their sum).

## What is NOT checked

Whether a theorem is *interesting*. `docs/MASTER_PLAN.md` says "198 theorems
are 198 statements, not 198 substantive laws" — a different question, and no
script answers it.

## Why the file count is checked separately

`317 теорем в 66 файлах` was wrong: 66 is the number of `.lean` files under
`laws/`, but 317 = 290 (Medium) + 27 (Legacy), and Medium is 56 files. The
number of files that *contain* the theorems is 64. Counting files and theorems
with the same glob is the mistake; this script counts them with the same
function so they cannot disagree.

Usage:
    python3 checks/log_check.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Files that are a dated record of a past state, not a live claim.
FROZEN = (
    "LESSONS.md",
    "docs/ELIMINATED.md",
    "docs/MASTER_PLAN.md",
    "docs/PLAN.md",
    "docs/PLAN-EXPERIMENTS.md",
    "docs/PLAN-NEXT.md",
    "docs/VISION.md",
)
FROZEN_PREFIX = ("docs/FINDING-", "docs/SYNTHESIS-", "docs/LAW-")

#: Wording that marks a mention as a record of the past, not a live claim.
#: A marker that the gate does not recognise is worse than no marker: the
#: sentence LOOKS annotated and still fails. `на эту дату` is here because it
#: is the wording `laws/README.md` actually uses.
#:
#: `до` and `было` earn their place by the same rule: `PROTOCOL.md` and
#: `docs/CLAIMS.md` describe the state *before* the 2026-11-13 fix ("До
#: 2026-11-13 там лежали 50 файлов", "раньше 35 из 48 ни разу не собирались").
#: Those are the evidence for the fix, not claims about the tree today.
HISTORICAL = (
    "historical", "историческ", "предыдущ", "previous", "ранее", "раньше",
    "было", "до 2026", "датированная запись", "на эту дату", "на ту дату",
    "по состоянию на", "→",
)

#: `317 теорем`, `290 theorems`, `281 теорема`
THEOREM_RE = re.compile(r"\b(\d{2,4})\s*(?:теорем|theorem)", re.IGNORECASE)
#: `66 файлах`, `56 files`
FILE_RE = re.compile(r"\b(\d{2,4})\s*(?:файл|file)", re.IGNORECASE)

#: A count that is part of a name, not a claim about the tree: `11 теорем-
#: тавтологий` names the set that was removed, and `306 теорем` in the same
#: table is `317 − 11` — an arithmetic identity, not a fresh measurement.
#: Flagging those teaches the reader to ignore the gate.
DERIVED_RE = re.compile(r"теорем-тавтолог|тавтологий из", re.IGNORECASE)


def count_theorems(directory: Path) -> tuple[int, int]:
    """(files that contain a theorem, theorems) for one library directory.

    A file with no theorem is not counted: `laws/Medium` has 56 `.lean` files
    but the claim "317 theorems in N files" is about files that carry them.
    """
    with_theorems = 0
    total = 0
    for f in sorted(directory.glob("*.lean")):
        n = 0
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("theorem ") or line.startswith("lemma "):
                n += 1
        if n:
            with_theorems += 1
            total += n
    return with_theorems, total


def live_sorry(directory: Path) -> list[str]:
    """`sorry` that is code, not prose.

    Both current hits in `laws/Medium/FoldPeriodic.lean` are inside the module
    docstring, explaining that a `sorry` was removed. Counting them would make
    the "0 живых sorry" claim permanently false.
    """
    hits = []
    for f in sorted(directory.rglob("*.lean")):
        in_doc = False
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("/-"):
                in_doc = True
            if in_doc:
                if stripped.endswith("-/"):
                    in_doc = False
                continue
            if stripped.startswith("--"):
                continue
            if re.search(r"\bsorry\b", line):
                hits.append(f"{f.relative_to(ROOT)}:{n}: {stripped}")
    return hits


def is_frozen(rel: str) -> bool:
    return rel in FROZEN or rel.startswith(FROZEN_PREFIX)


def markdown_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return [ROOT / p for p in out.stdout.split()]


#: A section is dated when its heading carries a date (`## 15. Из сессии
#: 2026-11-11`) or says so in words. The marker then covers the whole section,
#: not the three lines above the number: a table of six failures cannot carry
#: the marker on every row, and a marker that only works three lines up is a
#: marker nobody will place.
SECTION_DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
SECTION_MARK = "датированная запись"
HEADING_RE = re.compile(r"^#{1,6}\s")


def dated_sections(lines: list[str]) -> list[bool]:
    """Per line: is this line inside a section declared to be a dated record?"""
    inside = []
    dated = False
    for line in lines:
        if HEADING_RE.match(line):
            # A new heading resets the scope; only a heading can open one.
            dated = bool(
                SECTION_DATE_RE.search(line) or SECTION_MARK in line.lower()
            )
        inside.append(dated)
    return inside


def selftest() -> int:
    """fires / silent / specific, done in memory so no file is needed.

    A gate that cannot fail is a slogan. These three cases are the smallest
    ones that would catch the two ways this gate could be wrong: matching
    nothing (fires) and matching everything (silent).
    """
    cases = [
        # (name, line, neighbours, should_flag)
        ("fires: a stale live count", "| 198 теорем Lean | собираются |", [], True),
        ("fires: a stale file count", "**48 файлов. 180 теорем.**", [], True),
        ("silent: the live count", "| 317 теорем Lean | собираются |", [], False),
        ("silent: marked on the line", "Итог *(числа на эту дату)*: 180 теорем", [], False),
        ("silent: marked above", "180 теорем в 48 файлах", ["**2026-11-11** *(числа на эту дату)*"], False),
        ("specific: a theorem count is not a file count", "317 теорем в 63 файлах", [], False),
        ("specific: a file count alone", "48 файлов", [], True),
    ]
    bad = 0
    for name, line, above, should_flag in cases:
        lines = above + [line]
        window = " ".join(lines).lower()
        marked = any(h in window for h in HISTORICAL)
        # The real gate compares against the counts the tree gives; the
        # selftest pins the same numbers so a change in the tree does not
        # silently change what the test means.
        flagged = not marked and (
            any(int(m.group(1)) not in (290, 27, 317) for m in THEOREM_RE.finditer(line))
            or any(int(m.group(1)) not in (56, 7, 63) for m in FILE_RE.finditer(line))
        )
        ok = flagged == should_flag
        if not ok:
            bad += 1
        print(f"  {'OK  ' if ok else 'FAIL'} {name}  (flagged={flagged}, "
              f"marked={marked}, want={should_flag})")
    print()
    print(f"selftest: {len(cases) - bad}/{len(cases)}")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    med_files, med_thm = count_theorems(ROOT / "laws" / "Medium")
    leg_files, leg_thm = count_theorems(ROOT / "laws" / "Legacy")
    total_thm = med_thm + leg_thm
    total_files = med_files + leg_files
    sorries = live_sorry(ROOT / "laws")

    known_thm = {med_thm, leg_thm, total_thm}
    known_files = {med_files, leg_files, total_files}

    print(f"Medium: {med_thm} теорем в {med_files} файлах")
    print(f"Legacy: {leg_thm} теорем в {leg_files} файлах")
    print(f"Всего:  {total_thm} теорем в {total_files} файлах")
    print(f"Живых sorry: {len(sorries)}")
    for s in sorries:
        print(f"    {s}")
    print()

    drift = []
    skipped = 0
    for path in markdown_files():
        rel = path.relative_to(ROOT).as_posix()
        if is_frozen(rel):
            skipped += 1
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        dated = dated_sections(lines)
        for n, line in enumerate(lines, 1):
            # The marker may sit on the line itself or up to two lines above:
            # a wrapped sentence puts "*(числа на эту дату)*" on the first
            # line and the numbers on the next. Looking only at the current
            # line made the marker unusable for exactly the case it is for.
            # `n` is 1-based, so `lines[n - 1]` is the current line and
            # `lines[max(0, n - 3):n]` covers it plus the two above.
            window = " ".join(lines[max(0, n - 3):n]).lower()
            if dated[n - 1] or any(h in window for h in HISTORICAL):
                continue
            if DERIVED_RE.search(line):
                continue
            for m in THEOREM_RE.finditer(line):
                if int(m.group(1)) not in known_thm:
                    drift.append((rel, n, "теорем", int(m.group(1)), line.strip()))
            for m in FILE_RE.finditer(line):
                if int(m.group(1)) not in known_files:
                    drift.append((rel, n, "файлов", int(m.group(1)), line.strip()))

    print(f"Заморожено файлов (датированные записи): {skipped}")
    if not drift:
        print("Живые числа в документации совпадают с деревом.")
        if sorries:
            print("НО: есть живые sorry, а документация обещает 0.")
            return 1
        return 0

    print(f"РАСХОЖДЕНИЙ: {len(drift)}")
    for rel, n, kind, value, text in drift:
        print(f"  {rel}:{n}  {kind} {value}  {text[:90]}")
    # A gate that prints failures and exits 0 is a slogan: `run.sh` reads the
    # exit code, not the transcript.
    return 1


if __name__ == "__main__":
    sys.exit(main())
