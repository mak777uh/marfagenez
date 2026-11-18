"""List sentences that state a number without saying how sure the number is.

The paper has been audited three times by hand - for agreement with the code, with the data, and with
the degree of confidence. This turns the third audit into a list that can be regenerated, so the next
edit cannot quietly add an unqualified number.

It does not fail the gate: a heuristic that cries wolf gets ignored, and the project has already
learned that lesson twice (`FINDING` check with false orphans, the Lean file count). It prints, a human
reads, and a real problem becomes a finding.

A sentence counts as qualified if it contains any of the words in `QUALIFIERS` - an interval, a share, a
spread, a statement of configuration, or an explicit bound.

    python3 checks/paper_unqualified_numbers.py [n]
"""

from __future__ import annotations

import pathlib
import re
import sys

QUALIFIERS = [
    # intervals and spreads
    "[", "interval", "quartile", "±", "bootstrap", "range", "spread",
    # shares and counts of things
    "%", "of the", "out of", "environments", "runs", "replicates",
    # summaries that already imply a distribution
    "median", "mean", "average", "distribution", "profile",
    # configuration and bounds
    "one economy", "one configuration", "single", "bound", "upper", "at most", "at least",
    "по крайней мере", "приблизительно",
    # explicit honesty markers used in this paper
    "not a law", "does not scale", "does not separate", "no form", "no measurable",
    "not claimed", "is not the reason", "never", "no gain",
    "between", "series", "each",
]

NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?\s?(?:%|×|x)?(?![\w])")


def main(argv: list[str]) -> int:
    limit = int(argv[1]) if len(argv) > 1 else 25
    root = pathlib.Path(__file__).resolve().parent.parent
    text = (root / "docs" / "PAPER-draft.md").read_text(encoding="utf-8")

    # prose only: cut the reference list first (it is headings, so the heading filter below
    # would have hidden the marker), then skip code fences, tables and headings
    if "## References" in text:
        text = text.split("## References")[0]
    lines = [
        line
        for line in text.splitlines()
        if not line.startswith(("|", "    ", "```", "#", "!"))
    ]
    body = " ".join(lines)
    sentences = re.split(r"(?<=[.;:])\s+(?=[A-Z*`])", body)

    flagged = []
    skipped_definition = 0
    for s in sentences:
        if not NUMBER.search(s):
            continue
        low = s.lower()
        if any(q.lower() in low for q in QUALIFIERS):
            continue
        # Definitions are not measurements: `dr = 0.3`, a formula, or a list of parameters
        # carries numbers that need no interval. The first version of this tool flagged 46
        # sentences, most of them of exactly this kind, which is how a report becomes noise.
        if "=" in s or "⇔" in s or "≥" in s or s.count("`") >= 4:
            skipped_definition += 1
            continue
        flagged.append(s.strip())

    for s in flagged[:limit]:
        print(f"- {s}\n")
    print(f"{len(flagged)} sentences carry a number without a qualifier")
    print(f"({skipped_definition} skipped as definitions or formula listings)")
    print("(review by hand; not a gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
