"""Does every new finding say what it gives the elephant?

`AUTONOMY.md` §1.1a asks, before any experiment: which part of the elephant in `GOAL.md` §1a does this step
add to? Written answers live where the result lives, so each new finding carries a line

    **Слону:** ...

The rule starts on a date, and the check only applies to findings dated on or after it: older findings are
records of how the work went and are not rewritten (the project's cardinal rule about its own past).

    python3 checks/finding_elephant_line.py
"""

from __future__ import annotations

import pathlib
import re
import sys

# findings dated before this day are history and are not rewritten
RULE_DATE = '2026-11-19'
MARKER = '**Слону:**'


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    docs = root / 'docs'
    checked = 0
    missing = []
    for p in sorted(docs.glob('FINDING-*.md')):
        text = p.read_text(encoding='utf-8')
        m = re.search(r'\*\*Дата:\*\*\s*(\d{4}-\d{2}-\d{2})', text)
        if not m:
            continue
        if m.group(1) < RULE_DATE:
            continue
        checked += 1
        if MARKER not in text:
            missing.append(p.name)

    if not checked:
        print(f'  ok    no findings dated {RULE_DATE} or later yet')
        print()
        print('Правило действует на новые находки; пока их нет.')
        return 0

    if missing:
        for name in missing:
            print(f'  WRONG {name} has no «{MARKER}» line (AUTONOMY.md §1.1a)')
        print()
        print(f'РАСХОЖДЕНИЙ: {len(missing)}')
        return 1

    print(f'  ok    all {checked} findings dated {RULE_DATE}+ say what they give the elephant')
    print()
    print('Проверка пройдена.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
