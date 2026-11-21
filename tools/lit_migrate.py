"""Migrate the 88 prose `### L-NNN` records into machine blocks — once, idempotently.

Why: the registry is prose, and the machine status used to be derived from a substring of that prose
(`kg/migrate.py`). Two external reviews showed this is how a self-report becomes "strong evidence".
The block below is the machine record; the prose stays untouched as the human record.

Design rules (see docs/BRIEF-NOTES-2026-11-21.md §15 and docs/REVIEW-BACKLOG.md U1):
  * negation wins: "полный текст не читал" is not a full text;
  * a level of `fragment_read`/`full_text_examined` needs a non-empty artifact in `papers/` — otherwise the
    record is downgraded to `abstract_read` with `downgrade_reason`, and the prose is NOT rewritten;
  * every migrated record is `legacy: true` (written before the contract); `kg/lit/baseline.json` holds the
    legacy count so the checker can forbid growth;
  * idempotent: a second run produces byte-identical output.

Usage:
    python3 tools/lit_migrate.py            # report only
    python3 tools/lit_migrate.py --write    # rewrite docs/ELEPHANT-LITERATURE.md
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs" / "ELEPHANT-LITERATURE.md"
PAPERS = ROOT / "papers"
SCHEMA = ROOT / "kg" / "literature-schema.json"

SECTION_RE = re.compile(r"^### (L-\d{3}) · (.+)$", re.M)
BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.S)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s)\]>,;\"]+")
ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5}|[a-z-]+/\d{7})(v\d+)?")
URL_RE = re.compile(r"https?://[^\s)\]>,;\"]+")
PMID_RE = re.compile(r"PMID:?\s*(\d+)")
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
NAME_RE = re.compile(r"\*\*Кто\.\*\*\s*([^.(]+)")

NEGATIVE = ("не читал", "не открыл", "не дост", "не удалось", "не проверял", "не видел")

VIA_BY_HOST = [
    ("ar5iv", "ar5iv"),
    ("arxiv.org", "arxiv"),
    ("pmc.ncbi.nlm.nih.gov", "pmc"),
    ("europepmc.org", "europepmc"),
    ("openalex.org", "openalex"),
    ("doi.org", "publisher"),
    ("zenodo.org", "repository"),
]

LEVELS = ("metadata_only", "abstract_read", "fragment_read", "full_text_examined", "secondary_only")


def level_from_prose(line: str) -> str:
    s = (line or "").lower()
    if any(marker in s for marker in NEGATIVE):
        return "abstract_read" if "аннотац" in s else "secondary_only"
    if "фрагмент" in s:
        return "fragment_read"
    if "полный текст" in s:
        return "full_text_examined"
    if "аннотац" in s:
        return "abstract_read"
    return "secondary_only"


def artifact_for(doi: str | None, arxiv: str | None) -> pathlib.Path | None:
    if not PAPERS.exists():
        return None
    needles = []
    if arxiv:
        needles.append(arxiv)
    if doi:
        needles.append(doi.replace("/", "_"))
    for path in sorted(PAPERS.iterdir()):
        if not path.is_file():
            continue
        for needle in needles:
            if needle and needle in path.name:
                return path
    return None


def via_from_url(url: str | None) -> tuple[str, str | None]:
    if not url:
        return "none", None
    for host, via in VIA_BY_HOST:
        if host in url:
            return via, url
    return "publisher", url


def build_block(lid: str, title: str, body: str) -> dict:
    doi = DOI_RE.search(body)
    arxiv = ARXIV_RE.search(body)
    url = URL_RE.search(body)
    pmid = PMID_RE.search(body)
    checked = re.search(r"\*\*Проверено\.\*\*\s*(.+)", body)
    checked_line = checked.group(1).strip().splitlines()[0] if checked else ""

    level = level_from_prose(checked_line)
    dowgrade = None
    artifact = None
    integrity = None

    if level in ("fragment_read", "full_text_examined"):
        artifact = artifact_for(doi.group(0) if doi else None, arxiv.group(1) if arxiv else None)
        if artifact is not None:
            data = artifact.read_bytes()
            if data:
                integrity = {
                    "artifact": artifact.relative_to(ROOT).as_posix(),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
        if integrity is None:
            dowgrade = "копии текста нет в papers/"
            level = "abstract_read"

    via, via_detail = via_from_url(url.group(0) if url else None)
    if url and via_detail is None:
        via_detail = url.group(0)

    year = YEAR_RE.search(body)
    # «Кто.» begins with the paper title in quotes far more often than with the author, so parse the
    # title first and only then look for a plausible surname after it (1–4 words, no digits).
    paper_title = None
    first_author = None
    who = re.search(r"\*\*Кто\.\*\*\s*(.+)", body)
    if who:
        who_line = who.group(1).strip()
        quoted = re.search(r"«([^»]{5,})»", who_line) or re.search(r'"([^"]{5,})"', who_line)
        if quoted:
            paper_title = quoted.group(1).strip()
            rest = who_line[quoted.end():].strip(" .,;()«»\"")
        else:
            rest = who_line
        candidate = re.split(r"[,();\d]", rest)[0].strip()
        words = candidate.split()
        if 1 <= len(words) <= 4 and not any(ch.isdigit() for ch in candidate):
            first_author = candidate

    block = {
        "L": lid,
        "locator": {
            "doi": doi.group(0).rstrip(".") if doi else None,
            "arxiv": arxiv.group(1) if arxiv else None,
            "arxiv_version": (arxiv.group(2) if arxiv and arxiv.group(2) else None),
            "openalex": None,
            "pmid": pmid.group(1) if pmid else None,
            "url": url.group(0) if url else None,
            "none": not (doi or arxiv or url or pmid),
        },
        "access": {
            "level": level,
            "artifact": integrity["artifact"] if integrity else None,
            "bytes": integrity["bytes"] if integrity else None,
            "sha256": integrity["sha256"] if integrity else None,
            "retrieved_at": None,
            "via": via,
            "via_detail": via_detail,
        },
        "inspection": {"scope": "full" if level == "full_text_examined" else "partial", "reviewed_ranges": []},
        "abstract_sha256": None,
        "bibliographic": {
            "title": (paper_title or title.strip()),
            "year": int(year.group(1)) if year else None,
            "first_author": first_author,
        },
        "legacy": True,
        "legacy_reason": "запись написана до контракта 2026-11-21",
        "downgrade_reason": dowgrade,
    }
    return block


def render(block: dict) -> str:
    return "```json\n" + json.dumps(block, ensure_ascii=False, indent=1, sort_keys=False) + "\n```"


def main(argv: list[str]) -> int:
    write = "--write" in argv
    text = REGISTRY.read_text(encoding="utf-8")
    marks = list(SECTION_RE.finditer(text))
    if not marks:
        print("no ### L-NNN sections found", file=sys.stderr)
        return 2

    out: list[str] = []
    cursor = 0
    levels: dict[str, int] = {}
    downgraded: list[str] = []
    with_artifact = 0
    for i, m in enumerate(marks):
        lid, title = m.group(1), m.group(2)
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        # drop an existing block, so a second run is idempotent
        body_wo = BLOCK_RE.sub("", body, count=1)
        block = build_block(lid, title, body_wo)
        levels[block["access"]["level"]] = levels.get(block["access"]["level"], 0) + 1
        if block["downgrade_reason"]:
            downgraded.append(lid)
        if block["access"]["artifact"]:
            with_artifact += 1

        out.append(text[cursor:m.end()])
        out.append("\n\n")
        out.append(render(block))
        out.append(body_wo if body_wo.startswith("\n") else "\n" + body_wo.lstrip("\n")[:0] + body_wo)
        cursor = end

    out.append(text[cursor:])
    new_text = "".join(out)

    print(f"sections: {len(marks)}")
    print("levels:", ", ".join(f"{k}={v}" for k, v in sorted(levels.items())))
    print(f"with artifact: {with_artifact}; downgraded: {len(downgraded)} ({', '.join(downgraded[:12])}"
          f"{'…' if len(downgraded) > 12 else ''})")
    print(f"schema: {SCHEMA.relative_to(ROOT)}")

    if not write:
        print("dry-run: pass --write to rewrite the registry")
        return 0

    if new_text == text:
        print("already up to date")
        return 0
    REGISTRY.write_text(new_text, encoding="utf-8")
    print("registry rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
