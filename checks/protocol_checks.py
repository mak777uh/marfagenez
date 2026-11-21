"""Does PROTOCOL.md list the checks that `run.sh all` actually runs?

`PROTOCOL.md` §12 tells a reader what "verified" means, and it named three checks while the gate
ran twenty-eight. A reader following the protocol would have believed the gate was smaller than it
is - the same staleness that made the README deny features that existed.

Two mechanical rules:

  1. every `checks/*.py` invoked by `run.sh` must be named in `PROTOCOL.md`;
  2. a declared list of the nine **judging** checks must be named with a one-line description,
     because those are the ones a reader needs to know by name.

    python3 checks/protocol_checks.py
"""

from __future__ import annotations

import pathlib
import re
import sys

JUDGES = [
    "contract.py",
    "log_check.py",
    "hash_version.py",
    "paper_numbers.py",
    "paper_claims.py",
    "paper_format.py",
    "paper_prose.py",
    "readme_features.py",
    "life_calibration.py",
]


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    run = (root / "run.sh").read_text(encoding="utf-8")
    proto = (root / "PROTOCOL.md").read_text(encoding="utf-8")

    invoked = sorted(set(re.findall(r"checks/([a-z_0-9]+\.(?:py|sh|js))", run)))
    named = set(re.findall(r"checks/([a-z_0-9]+\.(?:py|sh|js))", proto))

    bad = 0
    missing = [c for c in invoked if c not in named]
    if missing:
        print(f"  WRONG {len(missing)} checks run by the gate are not named in PROTOCOL.md:")
        for c in missing[:20]:
            print(f"          {c}")
        bad += len(missing)
    else:
        print(f"  ok    all {len(invoked)} checks run by the gate are named in PROTOCOL.md")

    absent_judges = [c for c in JUDGES if c not in named]
    if absent_judges:
        print(f"  WRONG judging checks absent from PROTOCOL.md: {absent_judges}")
        bad += len(absent_judges)
    else:
        print(f"  ok    all {len(JUDGES)} judging checks are named")

    # AGENTS.md states how many rules it has, and `run.sh agents` requires exactly that many
    # sections. The count in the prose drifted once (five written, six present), so it is checked
    # against both the file and the gate.
    agents = root / "AGENTS.md"
    if agents.exists():
        text = agents.read_text(encoding="utf-8")
        have = sorted(int(m) for m in re.findall(r"^## §(\d+)", text, re.MULTILINE))
        required = sorted(
            int(m) for m in re.findall(r"for s in ([\d\s]+); do", run)
            for m in m.split()
        )
        stated = re.findall(r"\b([а-яё]+)\s+правил", text, re.IGNORECASE)
        words = {
            "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
            "четыре": 4, "три": 3,
        }
        if have != required:
            print(f"  WRONG AGENTS.md has sections {have} but the gate requires {required}")
            bad += 1
        else:
            print(f"  ok    AGENTS.md sections match the gate: {have}")
        if stated:
            word = stated[0].lower()
            n = words.get(word)
            if n is not None and n != len(have):
                print(f"  WRONG AGENTS.md says «{word} правил» but has {len(have)} sections")
                bad += 1
            elif n is not None:
                print(f"  ok    the stated rule count matches: «{word}» = {len(have)}")

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("PROTOCOL описывает тот гейт, который есть.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
