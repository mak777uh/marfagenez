"""Does GOAL.md name symbols the model does not have?

GOAL.md is the document that answers "what do we already understand about the elephant". Its table
pointed at `structure` for six days after the field was removed, and nothing noticed, because GOAL
has no guard: it carries few numbers, so the numeric checks pass over it.

No judgement is needed for the machine part of this: an identifier in backticks either exists in
`core/src` or it does not. A name that does not exist is allowed only on a line that says so -
"удалён", "нет", "removed" - which is how a removed field is supposed to be mentioned.

    python3 checks/goal_features.py
"""

from __future__ import annotations

import pathlib
import re
import sys

# words that are prose or Rust syntax rather than model fields
SKIP = {
    "World", "Life", "Field", "N", "k", "n", "r", "t", "M", "dr", "rc", "s", "p", "f",
    "o", "x", "k_max", "1", "0",
}
REMOVAL = ("удалён", "удален", "нет", "removed", "не существует", "уже нет")


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    goal = root / "GOAL.md"
    if not goal.exists():
        print("  SKIP no GOAL.md")
        return 0

    src = "\n".join(
        p.read_text(encoding="utf-8")
        for p in list((root / "core" / "src").rglob("*.rs"))
    )

    lines = goal.read_text(encoding="utf-8").splitlines()
    missing = []
    for i, line in enumerate(lines, 1):
        if "удалён" in line.lower() or "удален" in line.lower():
            continue
        for name in re.findall(r"`([A-Za-z_][A-Za-z_0-9]{2,})`", line):
            if name in SKIP:
                continue
            if name in src:
                continue
            low = line.lower()
            if any(marker in low for marker in REMOVAL):
                continue
            missing.append((i, name, line.strip()[:80]))

    if not missing:
        print(f"  ok    every field named in GOAL.md exists in core/src")
        print()
        print("GOAL описывает ту модель, которая есть.")
        return 0

    for i, name, text in missing:
        print(f"  WRONG GOAL.md:{i} names `{name}`, which core/src does not have")
        print(f"        {text}")
    print()
    print(f"РАСХОЖДЕНИЙ: {len(missing)}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
