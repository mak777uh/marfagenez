"""Do any of the JS checks use `Math.random`?

`docs/PLAN-NEXT.md` D-4 was filed because `checks/audit.js` used `Math.random`, so two runs of the
same audit could disagree and neither could be reproduced. The seed was added; this keeps it.

    python3 checks/no_unseeded_random.py
"""

from __future__ import annotations

import pathlib
import re
import sys


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    targets = list((root / "checks").glob("*.js")) + list((root / "scripts").glob("*.js"))
    hits = []
    for p in targets:
        text = p.read_text(encoding="utf-8")
        # strip line comments so that a note about the old defect does not count as the defect
        code = "\n".join(line.split("//")[0] for line in text.splitlines())
        for m in re.finditer(r"Math\s*\.\s*random\s*\(", code):
            line = code[: m.start()].count("\n") + 1
            hits.append((p.name, line))

    if not hits:
        print(f"  ok    no Math.random in {len(targets)} JS checks")
        print()
        print("Проверка пройдена: JS-проверки детерминированы.")
        return 0

    for name, line in hits:
        print(f"  WRONG {name}:{line} uses Math.random")
    print()
    print(f"РАСХОЖДЕНИЙ: {len(hits)}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
