"""Is a recorded hash comparable to a freshly computed one?

## The defect this exists for

`Trace::compute_hash` changed after some records were written: `prev_cell` was
mixed into the sample hash, so `results/standing-is-a-uniform-third/` holds
`40bd71fa379e135a` while the binary at `HEAD` gives `f94d3b830971a9e8` for the
same arm. AGENTS.md §5 -- "two arms with the same hash are one arm" -- is true
*inside one version of the function*. Across versions it silently means
nothing, because the same sixteen hex digits no longer measure the same thing.

So every record now carries `hash_version`, and this script is the machine that
makes the field mean something:

| outcome | meaning |
|---|---|
| `ok` | the record carries a version, and it is the current one |
| `stale` | the record carries a version, but another one -- it is legal history, and it must not be compared to a newer record; the list is printed |
| `unversioned` | the field is absent: the record was written before versioning existed |

`stale` is not a failure. A record from version 1 is a true statement about
version 1. The failure is a *silent* mixture, and the two ways it can happen are
both caught here:

1. **A new record without a version.** `docs/hash-unversioned.txt` fixes the
   set of unversioned records as of the commit that introduced this gate. A path
   that appears in `results/` but not in that file is a failure -- otherwise the
   defect could grow quietly, one new experiment at a time.
2. **A listed path that is gone.** The list may only shrink; when a record is
   deleted or re-recorded with a version, its line must be removed in the same
   commit. A frozen list that outlives its files is a list nobody reads.

It also cross-checks the constant itself: the regexp below reads
`HASH_VERSION` out of `core/src/trace.rs` and compares it with
`checks/result.py`'s `HASH_VERSION_PY`. Two readers that must agree turn a
convention into a check.

## What this does not do

It does not recompute old hashes. Nothing can: the old function is not in the
tree. It only refuses to let the two be compared by accident.

## Usage

    python3 checks/hash_version.py
    python3 checks/hash_version.py --selftest
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
TRACE_RS = ROOT / "core" / "src" / "trace.rs"
DOC = ROOT / "docs" / "hash-unversioned.txt"

#: The declaration in `core/src/trace.rs`. Deliberately the strictest shape:
#: a commented-out or renamed constant must not satisfy it.
VERSION_RE = re.compile(r'^pub const HASH_VERSION: &str = "([^"]+)";$', re.MULTILINE)


def rust_version(trace_rs: Path) -> str | None:
    """`HASH_VERSION` as declared in the Rust source, or `None`."""
    try:
        text = Path(trace_rs).read_text(encoding="utf-8")
    except OSError:
        return None
    m = VERSION_RE.search(text)
    return m.group(1) if m else None


def python_version() -> str:
    """`HASH_VERSION_PY` from `checks/result.py` (which reads the same file)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from checks import result

    return result.HASH_VERSION_PY


def classify(results_dir: Path, version: str) -> tuple[list[str], list[tuple[str, str]], list[str], list[str]]:
    """Splits every recorded run into (ok, stale, unversioned, unreadable)."""
    ok: list[str] = []
    stale: list[tuple[str, str]] = []
    unversioned: list[str] = []
    unreadable: list[str] = []
    for path in sorted(Path(results_dir).rglob("run-*.json")):
        rel = path.relative_to(Path(results_dir).parent).as_posix()
        if "_archive" in Path(rel).parts:
            # `results/_archive/` holds records from before the contract itself.
            # They are history, not evidence -- the same rule `contract.py`
            # applies -- so versioning them would say something we cannot check.
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            unreadable.append(rel)
            continue
        got = data.get("hash_version")
        if got is None:
            unversioned.append(rel)
        elif got == version:
            ok.append(rel)
        else:
            stale.append((rel, str(got)))
    return ok, stale, unversioned, unreadable


def read_list(doc: Path) -> set[str]:
    """The frozen unversioned set, one repo-relative path per line."""
    try:
        text = Path(doc).read_text(encoding="utf-8")
    except OSError:
        return set()
    return {line.strip() for line in text.splitlines() if line.strip()}


def run(results_dir: Path, doc: Path, trace_rs: Path, version_py: str) -> int:
    """The whole gate. Returns 0 for green, 1 for red."""
    problems: list[str] = []

    version_rust = rust_version(trace_rs)
    if version_rust is None:
        problems.append(
            f"{trace_rs}: no `pub const HASH_VERSION: &str = \"...\";` found -- "
            "the hash has no version, so no recorded hash can be compared"
        )
        version = version_py
    else:
        version = version_rust
        if version_rust != version_py:
            problems.append(
                f"hash version disagrees: core/src/trace.rs says {version_rust!r}, "
                f"checks/result.py says {version_py!r}. The record would be "
                "written with one number and checked against another"
            )

    ok, stale, unversioned, unreadable = classify(results_dir, version)
    for rel in unreadable:
        problems.append(f"{rel}: cannot be read as JSON, so its version is unknown")

    listed = read_list(doc)
    new_unversioned = sorted(set(unversioned) - listed)
    vanished = sorted(listed - set(unversioned))

    print(f"hash version: core/src/trace.rs = {version!r}, checks/result.py = {version_py!r}")
    print(
        f"records outside results/_archive/: {len(ok) + len(stale) + len(unversioned) + len(unreadable)}"
    )
    print(f"  ok          {len(ok)}")
    print(f"  stale       {len(stale)}")
    print(f"  unversioned {len(unversioned)}  (frozen list: {len(listed)})")
    if unreadable:
        print(f"  unreadable  {len(unreadable)}")

    if stale:
        print()
        print("stale -- versioned, but with another hash function. Not a failure:")
        print("these records are true about their own version and must never be")
        print("compared with a current hash.")
        for rel, got in stale:
            print(f"  {rel}  ({got})")

    if new_unversioned:
        problems.append(
            f"{len(new_unversioned)} record(s) carry no hash_version and are not "
            "in docs/hash-unversioned.txt -- the defect is growing again, not "
            "being frozen:"
        )
        for rel in new_unversioned[:20]:
            problems.append(f"    {rel}")
        if len(new_unversioned) > 20:
            problems.append(f"    ... and {len(new_unversioned) - 20} more")

    if vanished:
        problems.append(
            f"{len(vanished)} path(s) in docs/hash-unversioned.txt are no longer "
            "unversioned records in the tree -- the list may only shrink, and it "
            "was not shrunk:"
        )
        for rel in vanished[:20]:
            problems.append(f"    {rel}")
        if len(vanished) > 20:
            problems.append(f"    ... and {len(vanished) - 20} more")

    if problems:
        print()
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print()
    print("OK: every record is either versioned at the current version or listed")
    print("as written before versioning existed; the list matches the tree.")
    return 0


# ---------------------------------------------------------------------------
# Selftest: the five cases the gate must tell apart, in memory.

def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _case(records: dict[str, dict | None], listed: list[str], version_py: str | None = None) -> int:
    """Builds a throwaway tree and runs the gate against it."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        results = base / "results"
        for rel, data in records.items():
            p = base / rel
            if data is None:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("{not json", encoding="utf-8")
            else:
                _write(p, data)
        doc = base / "hash-unversioned.txt"
        doc.write_text("\n".join(listed) + ("\n" if listed else ""), encoding="utf-8")
        trace = base / "trace.rs"
        trace.write_text('pub const HASH_VERSION: &str = "2-prev-cell";\n', encoding="utf-8")
        return run(results, doc, trace, version_py or "2-prev-cell")


def selftest() -> int:
    cases: list[tuple[str, int, int]] = []

    cases.append((
        "ok: versioned record at the current version",
        _case({"results/e/run-1.json": {"hash_version": "2-prev-cell"}}, []),
        0,
    ))
    cases.append((
        "stale: versioned record from another version",
        _case({"results/e/run-1.json": {"hash_version": "1-prev-cell"}}, []),
        0,
    ))
    cases.append((
        "unversioned: no field, frozen in the list",
        _case({"results/e/run-1.json": {"seed": 1}}, ["results/e/run-1.json"]),
        0,
    ))
    cases.append((
        "new unversioned: no field, not in the list",
        _case({"results/e/run-1.json": {"seed": 1}}, []),
        1,
    ))
    cases.append((
        "missing file: listed path is gone",
        _case({"results/e/run-1.json": {"hash_version": "2-prev-cell"}},
              ["results/e/run-gone.json"]),
        1,
    ))
    cases.append((
        "version mismatch: rust and python disagree",
        _case({"results/e/run-1.json": {"hash_version": "2-prev-cell"}}, [],
              version_py="1-prev-cell"),
        1,
    ))
    cases.append((
        "unreadable record: version unknown",
        _case({"results/e/run-1.json": None}, []),
        1,
    ))

    bad = 0
    for name, got, want in cases:
        mark = "ok " if got == want else "BAD"
        print(f"  {mark} {name}: got {got}, want {want}")
        if got != want:
            bad += 1
    print()
    if bad:
        print(f"SELFTEST FAILED: {bad} case(s)")
        return 1
    print(f"SELFTEST OK: {len(cases)} cases")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    # The selftest's own runs print; keep the real run quiet about the import
    # path manipulation and loud about the verdict.
    return run(RESULTS, DOC, TRACE_RS, python_version())


if __name__ == "__main__":
    sys.exit(main())
