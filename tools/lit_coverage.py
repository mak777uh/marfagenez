"""Coverage of the literature registry: what each record can actually support.

Documents should cite these numbers instead of remembering them (the repository has already been bitten
twice by descriptive counts drifting in prose). Offline: reads the registry blocks and `papers/`.

Usage:
    python3 tools/lit_coverage.py            # print
    python3 tools/lit_coverage.py --write    # write literature/coverage.json
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs" / "ELEPHANT-LITERATURE.md"
PAPERS = ROOT / "papers"
OUT = ROOT / "literature" / "coverage.json"

SECTION_RE = re.compile(r"^### (L-\d{3}) · (.+)$", re.M)
BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.S)


def main(argv: list[str]) -> int:
    text = REGISTRY.read_text(encoding="utf-8")
    marks = list(SECTION_RE.finditer(text))
    levels: dict[str, int] = {}
    total = 0
    with_locator = 0
    with_artifact = 0
    with_abstract_sha = 0
    legacy = 0
    no_locator: list[str] = []
    downgraded: list[str] = []
    for i, m in enumerate(marks):
        lid = m.group(1)
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        blocks = BLOCK_RE.findall(body)
        if len(blocks) != 1:
            continue
        try:
            block = json.loads(blocks[0])
        except json.JSONDecodeError:
            continue
        total += 1
        level = (block.get("access") or {}).get("level")
        levels[level] = levels.get(level, 0) + 1
        loc = block.get("locator") or {}
        has_loc = any(loc.get(k) for k in ("doi", "arxiv", "openalex", "pmid", "url"))
        with_locator += bool(has_loc)
        if not has_loc:
            no_locator.append(lid)
        with_artifact += bool((block.get("access") or {}).get("artifact"))
        with_abstract_sha += bool(block.get("abstract_sha256"))
        legacy += bool(block.get("legacy"))
        if block.get("downgrade_reason"):
            downgraded.append(lid)

    papers = sorted(p.name for p in PAPERS.iterdir() if p.is_file()) if PAPERS.exists() else []
    report = {
        "records": total,
        "sections": len(marks),
        "by_level": dict(sorted(levels.items())),
        "with_locator": with_locator,
        "without_locator": len(no_locator),
        "without_locator_ids": no_locator,
        "with_artifact": with_artifact,
        "with_abstract_sha256": with_abstract_sha,
        "legacy": legacy,
        "downgraded": downgraded,
        "papers_files": len(papers),
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if "--write" in argv:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"written {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
