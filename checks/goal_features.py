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


PARTS = ("хобот", "ноги", "желудок", "кожа", "память", "стадо")


def scan(root: pathlib.Path, rel: str, src: str) -> list[tuple[int, str, str]]:
    path = root / rel
    if not path.exists():
        return []
    missing = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        # outside GOAL and POSITIVE the same table sits among other prose; scanning the whole
        # README flagged `awk` and `LICENSE`, which are not model fields
        if rel == "README.md" and not (
            line.startswith("| **") and any(part in line.lower() for part in PARTS)
        ):
            continue
        for m in re.finditer(r"`([A-Za-z_][A-Za-z_0-9]{2,})`", line):
            name = m.group(1)
            if name in SKIP or name in src:
                continue
            # a commit hash, or a short all-caps symbol from a chemical notation
            if re.fullmatch(r"[0-9a-f]{7,40}", name):
                continue
            if name.isupper() and len(name) <= 5:
                continue
            # The removal marker must be CLOSE to the name. A line-wide test excused a bogus
            # field on any row that happened to say "нет" somewhere - and the row about the
            # skin says exactly that, so the guard was blind on its own main case.
            near = line[max(0, m.start() - 60): m.end() + 60].lower()
            if any(marker in near for marker in REMOVAL):
                continue
            missing.append((i, name, line.strip()[:80]))
    return missing


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    contract_files = ["result.py", "contract.py", "experiment.py", "dispatcher.py"]
    src = "\n".join(
        p.read_text(encoding="utf-8")
        for p in list((root / "core" / "src").rglob("*.rs"))
        + [root / "checks" / n for n in contract_files if (root / "checks" / n).exists()]
    )

    # the same table lives in both documents, and it went stale in both
    documents = ["GOAL.md", "POSITIVE.md", "README.md"]
    total = 0
    for rel in documents:
        missing = scan(root, rel, src)
        if not missing:
            print(f"  ok    every field named in {rel} exists in core/src")
        for i, name, text in missing:
            print(f"  WRONG {rel}:{i} names `{name}`, which core/src does not have")
            print(f"        {text}")
            total += 1

    print()
    if total:
        print(f"РАСХОЖДЕНИЙ: {total}")
        return 1
    print("Документы о слоне описывают ту модель, которая есть.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
