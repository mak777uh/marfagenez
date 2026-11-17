"""Mechanical prose checks on the paper: doubled words and mixed spelling.

A copy editor returns a manuscript for two things this can find without judgement: a word
written twice in a row, and British and American spellings of the same word in one document.
Both are invisible to the author and both are embarrassing in print.

    python3 checks/paper_prose.py
"""

from __future__ import annotations

import pathlib
import re
import sys

# spelling pairs that must not be mixed inside one document
PAIRS = [
    ("behaviour", "behavior"),
    ("modelling", "modeling"),
    ("liquid", "liquid"),
    ("neighbour", "neighbor"),
    ("centre", "center"),
    ("colour", "color"),
    ("analyse", "analyze"),
    ("normalise", "normalize"),
    ("organisation", "organization"),
]

DOUBLED = re.compile(r"\b([A-Za-z]{2,})\s+\1\b", re.IGNORECASE)


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    path = root / "docs" / "PAPER-draft.md"
    if not path.exists():
        print(f"missing {path}")
        return 1
    text = path.read_text(encoding="utf-8")
    bad = 0

    # 1. doubled words, in the prose only: skip tables and code blocks heuristically
    prose_lines = [
        (i + 1, line)
        for i, line in enumerate(text.splitlines())
        if not line.startswith(("|", "    ", "```", "#"))
    ]
    hits = []
    for lineno, line in prose_lines:
        for m in DOUBLED.finditer(line):
            word = m.group(1).lower()
            # a handful of legitimate repetitions exist in English
            if word in {"that", "had", "is", "was"} and line.count(word) > 2:
                continue
            hits.append((lineno, m.group(0)))
    if hits:
        for lineno, frag in hits[:12]:
            print(f"  WRONG doubled word on line {lineno}: {frag!r}")
        bad += len(hits)
    else:
        print("  ok    no doubled words in the prose")

    # 2. mixed spelling
    low = text.lower()
    mixed = []
    for brit, amer in PAIRS:
        if brit == amer:
            continue
        nb = len(re.findall(rf"\b{brit}", low))
        na = len(re.findall(rf"\b{amer}", low))
        if nb and na:
            mixed.append((brit, nb, amer, na))
    if mixed:
        for brit, nb, amer, na in mixed:
            print(f"  WRONG mixed spelling: {brit} x{nb} and {amer} x{na}")
        bad += len(mixed)
    else:
        print("  ok    spelling is consistent within each pair")

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Проза в порядке (по объявленным механическим правилам).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
