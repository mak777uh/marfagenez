"""A small reader for the paper draft: does the text claim more than the numbers?

`docs/PAPER-draft.md` is written from findings, and the risk is a sentence that reads
stronger than the measurement behind it. This checks a declared list of phrases that
have already been caught once - each was too strong when written and was softened in
cycle 118 - so they cannot come back unnoticed.

It is not a grammar checker and not a style rule. It is a list of our own past
overstatements, which is the only kind this project can know about.

    python3 checks/paper_claims.py
"""

from __future__ import annotations

import pathlib
import sys

# phrase -> what it overstated
BANNED = {
    "decides who lives": "one economy is not a general claim about survival",
    "dominates the ecological parameter": "a ranking of mechanisms was never measured",
    "is always written by us": "true of this code, not of models in general",
    "the reason was always the same": "a summary of four cases stated as a proof",
    "proves that memory": "one contrast cannot prove a negative about memory",
    "memory is useless": "the project's own prohibition (docs/NOT-CLAIMED.md)",
    "emergent structure": "transport is programmed; see the review prohibitions",
    "shows that emergence": "nothing here is emergent, and §7 says so",
}

REQUIRED = [
    "Not that anything here is emergent",
    "care cannot be posed",
    "so what selection sees is distance to a known place",
]


def main(argv: list[str]) -> int:
    path = pathlib.Path(__file__).resolve().parent.parent / "docs" / "PAPER-draft.md"
    if not path.exists():
        print(f"missing {path}")
        return 1
    text = path.read_text(encoding="utf-8")
    low = " ".join(text.lower().split())

    bad = 0
    for phrase, why in BANNED.items():
        n = low.count(phrase.lower())
        if n:
            print(f"  OVERSTATEMENT: {phrase!r} occurs {n}x - {why}")
            bad += n
        else:
            print(f"  ok: no {phrase!r}")

    print()
    for phrase in REQUIRED:
        if phrase.lower() in low:
            print(f"  ok: the draft still says {phrase!r}")
        else:
            print(f"  MISSING: the draft no longer says {phrase!r}")
            bad += 1

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Текст не заявляет больше, чем измерено (по объявленному списку).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
