"""Add a literature record from a real source — no invented DOIs, no invented abstracts.

The registry is prose plus a machine block; a new record must satisfy the same contract as the old ones
(`checks/literature_contract.py`), which means: a locator, a level, `via`, `retrieved_at`, and for
`abstract_read` an `abstract_sha256`. That hash is what lets a later audit notice that the publisher changed
the abstract, without keeping a copy of text we may not redistribute.

Normalisation of the abstract before hashing (must stay stable):
    reconstruct from the inverted index by position, join tokens with a single space, NFC,
    collapse runs of whitespace to one space, strip ends, keep case.

Usage:
    python3 tools/lit_new.py --doi 10.1162/artl_a_00165 --note "минимальные условия стационарного роста"
    python3 tools/lit_new.py --doi 10.1016/0303-2647(86)90008-0 --note "самоподдержание как динамика"
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs" / "ELEPHANT-LITERATURE.md"
CACHE = ROOT / "literature" / "cache"
KEY_FILE = pathlib.Path(os.environ.get("LITSEARCH_KEY", "/mnt/c/Users/Admin/.dsh/secrets/openalex.key"))
CURL = os.environ.get("LITSEARCH_CURL", "/mnt/c/Windows/System32/curl.exe")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_key() -> str | None:
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def fetch(doi: str) -> dict:
    url = "https://api.openalex.org/works/https://doi.org/" + doi
    params = "?select=id,doi,title,publication_year,authorships,abstract_inverted_index,primary_location"
    key = read_key()
    if key:
        params += "&api_key=" + key
    cache = CACHE / ("meta-" + hashlib.sha256((url + params.replace(key or "", "")).encode()).hexdigest()[:32] + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    out = subprocess.run([CURL, "-sS", "-L", "--compressed", "-m", "60", "-A", "lit_new/1.0", url + params],
                         capture_output=True, text=True, timeout=90)
    data = json.loads(out.stdout)
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def abstract_text(inverted: dict | None) -> str | None:
    if not inverted:
        return None
    positions: list[tuple[int, str]] = []
    for token, places in inverted.items():
        for place in places:
            positions.append((int(place), token))
    text = " ".join(token for _, token in sorted(positions))
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def next_id(text: str) -> str:
    ids = [int(m) for m in re.findall(r"^### L-(\d{3})", text, re.M)]
    return f"L-{max(ids) + 1:03d}"


def main(argv: list[str]) -> int:
    if "--doi" not in argv:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    doi = argv[argv.index("--doi") + 1].strip()
    note = argv[argv.index("--note") + 1] if "--note" in argv else ""

    data = fetch(doi)
    if not data.get("id"):
        print(f"OpenAlex не знает DOI {doi}", file=sys.stderr)
        return 1

    title = data.get("title") or ""
    year = data.get("publication_year")
    authors = [a.get("author", {}).get("display_name", "") for a in (data.get("authorships") or [])]
    author_line = "; ".join(a for a in authors[:6] if a)
    abstract = abstract_text(data.get("abstract_inverted_index"))
    abstract_sha = hashlib.sha256(abstract.encode("utf-8")).hexdigest() if abstract else None
    level = "abstract_read" if abstract else "metadata_only"

    text = REGISTRY.read_text(encoding="utf-8")
    lid = next_id(text)
    retrieved = now()

    block = {
        "L": lid,
        "locator": {
            "doi": doi.lower(),
            "arxiv": None,
            "arxiv_version": None,
            "openalex": (data.get("id") or "").rsplit("/", 1)[-1] or None,
            "pmid": None,
            "url": "https://doi.org/" + doi,
            "none": False,
        },
        "access": {
            "level": level,
            "artifact": None,
            "bytes": None,
            "sha256": None,
            "retrieved_at": retrieved,
            "via": "openalex",
            "via_detail": "api.openalex.org/works/https://doi.org/" + doi,
        },
        "inspection": {"scope": "partial", "reviewed_ranges": []},
        "abstract_sha256": abstract_sha,
        "bibliographic": {"title": title, "year": year, "first_author": authors[0] if authors else None},
        "legacy": False,
        "legacy_reason": None,
        "downgrade_reason": None,
    }

    prose = [
        "",
        f"### {lid} · {title}",
        "",
        "```json",
        json.dumps(block, ensure_ascii=False, indent=1),
        "```",
        "",
        f"**Кто.** {title} ({year}). {author_line}",
        f"**Ссылка.** https://doi.org/{doi}",
        f"**Проверено.** **{'аннотация' if abstract else 'метаданные'}** OpenAlex, "
        f"{retrieved}, отпечаток {'есть' if abstract else 'нет'}; фрагмент не читался.",
        f"**Утверждение.** {note or '—'}",
        "**Что даёт нам.** — (суждение не сделано).",
        "",
    ]
    REGISTRY.write_text(text.rstrip() + "\n" + "\n".join(prose), encoding="utf-8")
    print(f"{lid}: {title[:80]}")
    print(f"  level={level}, abstract_sha256={(abstract_sha or '—')[:12]}, retrieved_at={retrieved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
