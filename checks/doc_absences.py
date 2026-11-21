#!/usr/bin/env python3
"""doc_absences.py -- every doc sentence that claims something is absent.

Why: twice in one series a doc comment described the code wrongly ("inheritance is not implemented",
"a good formula is `capacity - maintenance - dr*rc`"). Both times the lie was found by an outside reviewer,
not by the project. This script turns luck into a standing watchlist: it prints each doc claim of absence
with its file and line, and says whether the claim is covered by a test that pins the behaviour.

It does not decide whether a claim is true -- that needs a reader. It decides only that the list is
enumerated, so the next reviewer starts from the list instead of from zero.

Usage:
    python3 checks/doc_absences.py            # the list, grouped by file
    python3 checks/doc_absences.py --count    # just the number
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "core" / "src"
TESTS = ROOT / "core" / "tests"

# Phrases that assert absence or impossibility about the code, not about the world.
PATTERNS = [
    r"\bnot implemented\b",
    r"\bis not implemented\b",
    r"\bno (?:gene|inheritance|variation|effect|support)\b",
    r"\bnever (?:used|stored|read|cleared|reset|changes)\b",
    r"\bdoes not (?:exist|happen|change|affect|store|read)\b",
    r"\bis ignored\b",
    r"\bhas no effect\b",
    r"\bcannot (?:be|have|change|affect|influence)\b",
]
ABSENCE = re.compile("|".join(PATTERNS), re.IGNORECASE)

# Two different kinds of sentence, and only the first one needs a test against the code.
# A **feature** claim says the code does not do a thing; a **design** claim says why a measurement or a
# comparison is impossible (the trace must record X, otherwise arms cannot be compared). Auditing them
# with one rule is how "cannot be compared" ends up treated as a missing feature.
FEATURE = re.compile(
    r"not implemented|no (?:gene|inheritance|variation|support|effect)|never (?:used|stored|read|cleared|reset)|"
    r"is ignored|has no effect|does not (?:exist|happen|store|read)",
    re.IGNORECASE,
)


def kind(text):
    return "feature" if FEATURE.search(text) else "design"

# A claim is "pinned" when a test file mentions the feature keyword. Deliberately coarse: the script is a
# watchlist, not a proof.
PIN_HINTS = {
    "inheritance": ["births.rs"],
    "policy": ["births.rs", "off_positions.rs"],
    "birth": ["births.rs"],
    "read": ["off_positions.rs"],
    "sight": ["off_positions.rs"],
    "claims": ["off_positions.rs"],
    "order": ["order_protocol.rs"],
    "room": ["room_isotropy.rs"],
}


def main(argv):
    found = []
    for path in sorted(CORE.rglob("*.rs")):
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            stripped = line.lstrip()
            if not (stripped.startswith("//!") or stripped.startswith("///")):
                continue
            if ABSENCE.search(line):
                found.append((path.relative_to(ROOT).as_posix(), i, line.strip()))
    if "--count" in argv:
        print(len(found))
        return 0
    by_file = {}
    kinds = {"feature": 0, "design": 0}
    for f, i, text in found:
        by_file.setdefault(f, []).append((i, text, kind(text)))
        kinds[kind(text)] += 1
    print("утверждений об отсутствии в докбуках core/: " + str(len(found)))
    unpinned = 0
    hinted = 0
    for f, rows in sorted(by_file.items()):
        print()
        print(f)
        for i, text, k in rows:
            hint = ""
            low = text.lower()
            for key, tests in PIN_HINTS.items():
                if key in low:
                    present = [t for t in tests if (TESTS / t).exists()]
                    # A keyword match is a pointer for the reader, not a verdict: the script cannot
                    # know whether the test really pins this sentence.
                    hint = ("  → рядом тест: " + ", ".join(present) + " (проверить вручную)") if present else ""
                    if not present:
                        unpinned += 1
                    else:
                        hinted += 1
                    break
            print("  %4d  [%s] %s%s" % (i, k, text[:110], hint))
    print()
    print("по смыслу: заявление о возможности — " + str(kinds["feature"]) +
          " · про измерение/сравнение — " + str(kinds["design"]))
    print("подсказка есть у " + str(hinted) + " из " + str(len(found)) +
          " · утверждений без подсказки: " + str(len(found) - hinted - unpinned))
    print("«Рядом тест» значит только, что в тестах есть ключевое слово: проверять всё равно человеку.")
    print("Правило: утверждение об отсутствии либо проверено тестом, либо помечено как непроверенное.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
