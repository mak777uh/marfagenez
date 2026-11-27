"""Do the documents' numbers match the tree?

Three times in three cycles a document was found to state something that had stopped being true:
the README denied features that existed, section 9.7 denied a space of configurations that existed,
and PROTOCOL described a gate of four checks while the gate ran twenty-eight. Each was fixed by hand
and guarded in its own way.

This is the generalisation: the countable facts that documents state - tests, findings, figures,
checks - are compared with the tree here, in one place, for every document that states them.

The test count is taken from `#[test]` in the sources rather than from a run: it is deterministic,
costs nothing, and the run itself is already a separate gate step.

    python3 checks/doc_numbers.py
"""

from __future__ import annotations

import pathlib
import re
import sys

DOCS = [
    "README.md",
    "PROTOCOL.md",
    "AGENTS.md",
    "NOT-CLAIMED.md",
    "docs/CLAIMS.md",
    "docs/LAWS.md",
    "docs/MODEL.md",
    "docs/WHERE-WE-ARE.md",
    "docs/PAPER-draft.md",
]

# a claim is "N <unit>" in Russian or English
UNITS = {
    "тест": "tests",
    "test": "tests",
    "находк": "findings",
    "finding": "findings",
    "проверк": "checks",
    "check": "checks",
    "фигур": "figures",
    "figure": "figures",
    "теорем": "theorems",
    "theorem": "theorems",
}

# numbers above this in a document are almost always data, not a count of artefacts
MAX_ARTEFACT = 5000


def count_theorems(root: pathlib.Path) -> int:
    """Theorem and lemma declarations under `laws/`."""
    total = 0
    for p in (root / "laws").rglob("*.lean"):
        if ".lake" in p.parts:
            continue
        total += len(
            re.findall(r"^(theorem|lemma) ", p.read_text(encoding="utf-8"), re.MULTILINE)
        )
    return total


def count_tests(root: pathlib.Path) -> int:
    n = 0
    for p in list((root / "core" / "src").rglob("*.rs")) + list(
        (root / "core" / "tests").rglob("*.rs")
    ):
        n += p.read_text(encoding="utf-8").count("#[test]")
    return n


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    real = {
        "tests": count_tests(root),
        "findings": len(list((root / "docs").glob("FINDING-*.md"))),
        "figures": len(list((root / "docs" / "figures").glob("*.svg")))
        if (root / "docs" / "figures").exists()
        else 0,
        "theorems": count_theorems(root),
        "checks": len(
            set(re.findall(r"checks/([a-z_0-9]+\.py)", (root / "run.sh").read_text(encoding="utf-8")))
        ),
    }
    print("tree:", ", ".join(f"{k} {v}" for k, v in real.items()))
    print()

    bad = 0
    for rel in DOCS:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for num_s, unit_word in re.findall(
            # `tests whether` / `tests if` are verbs, not counts
            r"\b(\d{1,4})\s+(тест\w*|test\w*\b(?!\s+(?:whether|if|that))|находк\w*|finding\w*|проверк\w*|check\w*|фигур\w*|figure\w*)",
            text,
            re.IGNORECASE,
        ):
            num = int(num_s)
            if num > MAX_ARTEFACT:
                continue
            key = None
            low = unit_word.lower()
            for stem, kind in UNITS.items():
                if low.startswith(stem):
                    key = kind
                    break
            if key is None:
                continue
            if num != real[key]:
                # a document may quote a historical number deliberately; require the word
                # "на тот момент" / "at that time" next to it to let it pass
                window = text[max(0, text.find(f"{num_s} {unit_word}") - 60):][:160].lower()
                if "на тот момент" in window or "at that time" in window:
                    continue
                print(f"  WRONG {rel}: claims {num} {unit_word} but the tree has {real[key]} {key}")
                bad += 1

    # The Lean file count is ambiguous by nature: the gate counts `laws/Medium` and
    # `laws/Legacy` (64 files), of which 63 contain theorems. A document may state either
    # number, but only next to a phrase that says which it means, so this checks the
    # construction "N файл" only when it follows "теорем" or is followed by "с теоремами".
    medium = len(list((root / "laws" / "Medium").glob("*.lean")))
    legacy = len(list((root / "laws" / "Legacy").glob("*.lean")))
    lean_all = medium + legacy
    lean_with = 0
    for sub in ("Medium", "Legacy"):
        for p_ in (root / "laws" / sub).glob("*.lean"):
            if re.search(r"^(theorem|lemma) ", p_.read_text(encoding="utf-8"), re.MULTILINE):
                lean_with += 1
    print(f"      lean: {lean_all} files in Medium+Legacy ({medium}+{legacy}), "
          f"{lean_with} with theorems")
    for rel in DOCS:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        patterns = [
            r"теорем\w*\s+в\s+(\d{1,4})\s+файл",
            r"(\d{1,4})\s+файл\w*\s+с\s+теорем",
            r"теорем\w*\s+в\s+(\d{1,4})\s+файлах",
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                num = int(m.group(1))
                if num not in (lean_all, lean_with):
                    print(f"  WRONG {rel}: claims {num} Lean files but the tree has "
                          f"{lean_all} ({lean_with} with theorems)")
                    bad += 1

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Числа в документах совпадают с деревом.")
    return 0


if __name__ == "__main__":
    result = main(sys.argv)
    import subprocess
    root = pathlib.Path(__file__).resolve().parents[1]
    live_check = subprocess.run(
        [sys.executable, str(root / "tools" / "live_numbers.py"), "--check"],
        cwd=root,
        check=False,
    )
    if result == 0:
        result = live_check.returncode
    sys.exit(result)
