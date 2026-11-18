"""Does the README still describe the model that exists?

The README claims things are *absent* from the model, and those claims go stale the moment a
feature is added. This happened for three rows at once (read price, policy variation, a space of
configurations): the README said "no cost" and "no variation" for fourteen cycles after both had
been built.

No language model and no judgement - two mechanical rules:

  1. every declared feature must be **mentioned** in the README by its code name;
  2. every declared stale phrase must be **gone** from the README.

    python3 checks/readme_features.py
"""

from __future__ import annotations

import pathlib
import sys

# code features that the README must acknowledge by name
FEATURES = [
    ("read_cost", "the price of a look"),
    ("sight_radius", "a window of perception"),
    ("set_policy_mutation", "variation between parent and child"),
    ("birth_cost_per_cell", "birth priced by size"),
    ("ShapeEconomy", "the economy of a shape"),
    ("Pool", "a shared stock"),
    ("fixed_cost", "a cost every form pays once"),
]

# phrases that were true once and must not come back
STALE = [
    "без затрат и без решения",
    "вариации и передачи организации",
    "цена и выбор при чтении среды",
]


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    path = root / "README.md"
    if not path.exists():
        print(f"missing {path}")
        return 1
    text = path.read_text(encoding="utf-8")
    low = text.lower()
    bad = 0

    for symbol, what in FEATURES:
        if symbol.lower() in low:
            print(f"  ok    the README mentions {symbol} ({what})")
        else:
            print(f"  WRONG the README never mentions {symbol} ({what}) - it exists in the code")
            bad += 1

    print()
    for phrase in STALE:
        if phrase.lower() in low:
            print(f"  WRONG stale claim still in the README: {phrase!r}")
            bad += 1
        else:
            print(f"  ok    stale claim gone: {phrase!r}")

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("README описывает ту модель, которая есть.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
