"""Format checks for the paper draft: the invariants that can be enforced by machine.

`docs/PAPER-draft.md` has two guards already: `paper_numbers.py` (the numbers agree with the
model) and `paper_claims.py` (the words do not claim more than the numbers). Both are about
content. This one is about **formats that a journal enforces** and that are easy to get wrong
silently:

    * the abstract must fit in 250 words - most journals count;
    * every figure reference must point at a file that exists, and the figures must be
      numbered in order of appearance;
    * every author-year citation in the text must have an entry in `## References`, and every
      entry must be cited (a bibliography with orphans is the first thing a copy editor
      returns).

    python3 checks/paper_format.py
"""

from __future__ import annotations

import pathlib
import re
import sys

WORD_LIMIT = 250


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    path = root / "docs" / "PAPER-draft.md"
    if not path.exists():
        print(f"missing {path}")
        return 1
    text = path.read_text(encoding="utf-8")
    bad = 0

    # 1. the abstract
    m = re.search(r"## Abstract\n(.*?)\*\*Keywords", text, re.S)
    if not m:
        print("  MISSING: no abstract section")
        bad += 1
    else:
        words = len(m.group(1).split())
        ok = words <= WORD_LIMIT
        print(f"  {'ok   ' if ok else 'WRONG'} abstract length: {words} words (limit {WORD_LIMIT})")
        if not ok:
            bad += 1

    # 2. figure references point at files, and are numbered in order
    refs = re.findall(r"\]\((figures/[a-z0-9_]+\.svg)\)", text)
    missing = [r for r in refs if not (root / "docs" / r).exists()]
    print(f"  {'ok   ' if not missing else 'WRONG'} figure files: {len(refs)} referenced, "
          f"{len(missing)} missing {missing if missing else ''}")
    if missing:
        bad += 1
    captions = re.findall(r"\*Figure (\d+)\.\*", text)
    ordered = captions == [str(i) for i in range(1, len(captions) + 1)]
    print(f"  {'ok   ' if ordered else 'WRONG'} figure captions in order: {captions}")
    if not ordered:
        bad += 1

    # 3. citations and bibliography agree
    #
    # The first version tried to parse author-year citations out of the running text and
    # produced five false orphans, because a bibliography entry spans several authors
    # ("Gray, P. and Scott, S. K.") and a citation may omit the comma ("Riotte-Lambert
    # et al. 2017"). A weaker test that cannot lie: every surname heading an entry must
    # appear somewhere in the body, and every surname used in a parenthetical citation
    # must head an entry.
    parts = text.split("## References")
    if len(parts) != 2:
        print("  MISSING: no References section")
        bad += 1
    else:
        body, refs_text = parts
        surnames = [m.split(",")[0] for m in
                    re.findall(r"^([A-Z][A-Za-z\-]+(?:, [A-Z]\.,?)+(?:\.|$))", refs_text, re.M)]
        surnames += re.findall(r"^([A-Z][A-Za-z\-]+), [A-Z]\.", refs_text, re.M)
        surnames = sorted({s for s in surnames if s})
        uncited = [s for s in surnames if s not in body]
        print(f"  {'ok   ' if not uncited else 'WRONG'} bibliography entries appear in the text: "
              f"{len(surnames)} entries, uncited {uncited if uncited else 'none'}")
        if uncited:
            bad += 1
        cited = sorted({m[0] for m in re.findall(
            r"\(([A-Z][A-Za-z\-]+)(?: et al\.| and [A-Z][A-Za-z\-]+)?,? (\d{4})\)", body)})
        missing = [c for c in cited if c not in refs_text]
        print(f"  {'ok   ' if not missing else 'WRONG'} citations have entries: "
              f"{len(cited)} cited, missing {missing if missing else 'none'}")
        if missing:
            bad += 1

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Формат в порядке (по объявленным правилам).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
