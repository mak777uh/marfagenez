"""Lists the longest sentences in the paper, so they can be read one at a time.

Long sentences are where non-native constructions hide, and a rejected manuscript usually has a
few of them. This does not judge them; it only puts them in front of a reader, longest first.

    python3 checks/paper_long_sentences.py [n]
"""

from __future__ import annotations

import pathlib
import re
import sys


def main(argv: list[str]) -> int:
    n = int(argv[1]) if len(argv) > 1 else 12
    root = pathlib.Path(__file__).resolve().parent.parent
    path = root / "docs" / "PAPER-draft.md"
    text = path.read_text(encoding="utf-8")

    # keep line numbers for reference, drop tables and code
    lines = [
        (i + 1, line)
        for i, line in enumerate(text.splitlines())
        if not line.startswith(("|", "    ", "```", "#", "!"))
    ]
    body = " ".join(line for _, line in lines)
    sentences = re.split(r"(?<=[.:])\s+(?=[A-Z*`])", body)
    scored = []
    for s in sentences:
        words = len(s.split())
        if words >= 35:
            scored.append((words, s.strip()))
    scored.sort(reverse=True)

    for words, s in scored[:n]:
        print(f"[{words:>3} words] {s}\n")
    print(f"{len(scored)} sentences of 35+ words")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
