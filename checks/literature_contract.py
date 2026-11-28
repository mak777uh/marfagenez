"""The literature contract: a record may not claim more than its artifact supports.

Why this file exists
--------------------
`kg/migrate.py` used to promote a record to `verified_agent/strong` on the strength of the phrase
"полный текст" in the registry; the next round of review showed the same hole one storey down (the file
*name* was enough). Both are the same defect: a declaration standing in for a recount. This checker
recounts, and it does so **without importing the migrator** — an independent parser, because a checker that
reuses the code it checks inherits its blindness (that is exactly what `kg/regress.py` does).

Rules (each message names the record):
  R1  exactly one ```json block per `### L-NNN` section, valid JSON
  R2  `L` matches the heading; ids are unique
  R3  locator has at least one of doi/arxiv/openalex/pmid/url, or `none: true` with `legacy: true`
  R4  level is one of the five
  R5  `fragment_read`/`full_text_examined` => artifact exists, `bytes` matches, `sha256` matches
  R6  `scope != full` => reviewed_ranges present (legacy records may have none yet)
  R7  `abstract_read` => `abstract_sha256` + `via != none`; `retrieved_at` may be null only while legacy
  R8  machine level must not exceed the level the prose supports (negation lowers it)
  R9  reverse index: every file in `papers/` maps to a record with `level >= fragment_read`
  R10 the legacy count must not grow beyond `kg/lit/baseline.json`

Usage:
    python3 checks/literature_contract.py
    python3 checks/literature_contract.py --selftest
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
import tempfile

try:  # works both as `python checks/literature_contract.py` and as a package
    from .access_levels import ACCESS_LEVELS, ACCESS_LEVEL_ORDER
except ImportError:  # pragma: no cover - direct script execution
    from access_levels import ACCESS_LEVELS, ACCESS_LEVEL_ORDER

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs" / "ELEPHANT-LITERATURE.md"
PAPERS = ROOT / "papers"
BASELINE = ROOT / "kg" / "lit" / "baseline.json"

SECTION_RE = re.compile(r"^### (L-\d{3}) · (.+)$", re.M)
BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.S)
NEGATIVE = ("не читал", "не открыл", "не дост", "не удалось", "не проверял", "не видел")

LEVELS = list(ACCESS_LEVELS)
LEVEL_ORDER = ACCESS_LEVEL_ORDER

REQUIRED = ("L", "locator", "access", "inspection", "bibliographic", "legacy")


def prose_level(line: str) -> str:
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


def parse_registry(text: str):
    """[(lid, title, body)] — the sections of the registry, prose and block together."""
    marks = list(SECTION_RE.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), m.group(2).strip(), text[m.end():end]))
    return out


def parse_blocks(body: str):
    return [raw for raw in BLOCK_RE.findall(body)]


def checked_line(body: str) -> str:
    m = re.search(r"\*\*Проверено\.\*\*\s*(.+)", body)
    return m.group(1).strip().splitlines()[0] if m else ""


def check_schema(block: dict, lid: str, errs: list[str]) -> None:
    for key in REQUIRED:
        if key not in block:
            errs.append(f"{lid}: R4 нет обязательного поля `{key}`")
            return
    if block["L"] != lid:
        errs.append(f"{lid}: R2 в блоке указан `{block.get('L')}`")
    loc = block.get("locator") or {}
    if not isinstance(loc, dict):
        errs.append(f"{lid}: R4 `locator` не объект")
        return
    has = any(loc.get(k) for k in ("doi", "arxiv", "openalex", "pmid", "url"))
    if not has and not (loc.get("none") is True and block.get("legacy") is True):
        errs.append(f"{lid}: R3 нет локатора и нет `none: true` с `legacy: true`")
    acc = block.get("access") or {}
    level = acc.get("level")
    if level not in LEVELS:
        errs.append(f"{lid}: R4 уровень `{level}` вне перечисления")
        return
    insp = block.get("inspection") or {}
    if insp.get("scope") not in ("full", "partial"):
        errs.append(f"{lid}: R4 `inspection.scope` = `{insp.get('scope')}`")


def check_artifact(block: dict, lid: str, errs: list[str]) -> None:
    acc = block.get("access") or {}
    level = acc.get("level")
    if level not in ("fragment_read", "full_text_examined"):
        return
    rel = acc.get("artifact")
    if not rel:
        errs.append(f"{lid}: R5 уровень `{level}` без артефакта")
        return
    path = ROOT / rel
    if not path.is_file():
        errs.append(f"{lid}: R5 артефакта нет: {rel}")
        return
    data = path.read_bytes()
    if not data:
        errs.append(f"{lid}: R5 артефакт пуст: {rel}")
        return
    if acc.get("bytes") != len(data):
        errs.append(f"{lid}: R5 размер не совпадает: в блоке {acc.get('bytes')}, на диске {len(data)}")
    digest = hashlib.sha256(data).hexdigest()
    if acc.get("sha256") != digest:
        errs.append(f"{lid}: R5 sha256 не совпадает: в блоке {str(acc.get('sha256'))[:12]}…, на диске {digest[:12]}…")
    ranges = (block.get("inspection") or {}).get("reviewed_ranges") or []
    if (block.get("inspection") or {}).get("scope") != "full" and not ranges and not block.get("legacy"):
        errs.append(f"{lid}: R6 `scope: partial` без reviewed_ranges")
    lines = data.count(b"\n") + 1
    for rng in ranges:
        if rng.get("type") == "lines":
            to = rng.get("to")
            if not isinstance(to, int) or to > lines:
                errs.append(f"{lid}: R6 диапазон строк за границей артефакта ({to} > {lines})")
        elif rng.get("type") in ("page", "section"):
            if not str(rng.get("from") or "").strip() and not str(rng.get("to") or "").strip():
                errs.append(f"{lid}: R6 пустой диапазон {rng.get('type')}")


def check_abstract(block: dict, lid: str, errs: list[str]) -> None:
    acc = block.get("access") or {}
    if acc.get("level") != "abstract_read":
        return
    if not block.get("abstract_sha256") and not block.get("legacy"):
        errs.append(f"{lid}: R7 `abstract_read` без `abstract_sha256`")
    if acc.get("via") in (None, "none") and not block.get("legacy"):
        errs.append(f"{lid}: R7 `abstract_read` без `via`")
    if not acc.get("retrieved_at") and not block.get("legacy"):
        errs.append(f"{lid}: R7 `abstract_read` без `retrieved_at`")


def check_prose(block: dict, body: str, lid: str, errs: list[str]) -> None:
    machine = (block.get("access") or {}).get("level")
    prose = prose_level(checked_line(body))
    if machine in LEVEL_ORDER and LEVEL_ORDER[machine] > LEVEL_ORDER[prose]:
        errs.append(f"{lid}: R8 уровень `{machine}` выше того, что поддерживает проза (`{prose}`)")

def check_duplicate_doi(records: dict, errs: list[str]) -> None:
    """One paper, one canonical record. Duplicates are allowed only as pointers (`duplicate_of`)."""
    by_doi: dict[str, list[tuple[str, str | None]]] = {}
    for lid, block in records.items():
        doi = ((block.get("locator") or {}).get("doi") or "").strip().lower()
        if doi:
            by_doi.setdefault(doi, []).append((lid, block.get("duplicate_of")))
    for doi, entries in by_doi.items():
        canon = [lid for lid, dup in entries if not dup]
        if len(canon) == 1:
            continue
        if not canon:
            errs.append(f"R12 DOI `{doi}`: нет канонической записи, все помечены `duplicate_of`")
            continue
        errs.append(f"R12 DOI `{doi}` зарегистрирован несколько раз без `duplicate_of`: {', '.join(canon)}")


def check_reverse(records: dict, errs: list[str]) -> None:
    if not PAPERS.exists():
        errs.append("R9 нет каталога papers/")
        return
    anchors = set()
    for lid, block in records.items():
        acc = block.get("access") or {}
        art = acc.get("artifact")
        if art and acc.get("level") in ("fragment_read", "full_text_examined"):
            anchors.add(pathlib.PurePosixPath(art).name)
    for path in sorted(PAPERS.iterdir()):
        if path.is_file() and path.name not in anchors:
            errs.append(f"R9 файл `papers/{path.name}` не привязан ни к одной записи уровня fragment_read+")


def check_legacy(records: dict, errs: list[str]) -> None:
    legacy = sum(1 for b in records.values() if b.get("legacy"))
    baseline = 0
    if BASELINE.exists():
        baseline = int(json.loads(BASELINE.read_text(encoding="utf-8")).get("legacy", 0))
    print(f"legacy: {legacy} (baseline {baseline})")
    if legacy > baseline:
        errs.append(f"R10 legacy-записей больше baseline: {legacy} > {baseline} (новые записи обязаны иметь локатор и уровень)")


def run(registry: pathlib.Path, papers: pathlib.Path, baseline: pathlib.Path) -> list[str]:
    global REGISTRY, PAPERS, BASELINE
    REGISTRY, PAPERS, BASELINE = registry, papers, baseline
    if not registry.exists():
        return [f"нет реестра {registry}"]
    text = registry.read_text(encoding="utf-8")
    sections = parse_registry(text)
    if not sections:
        return ["R1 в реестре нет секций `### L-NNN`"]

    errs: list[str] = []
    records: dict[str, dict] = {}
    for lid, _title, body in sections:
        blocks = parse_blocks(body)
        if len(blocks) != 1:
            errs.append(f"{lid}: R1 блоков {len(blocks)}, нужен ровно один")
            if not blocks:
                continue
        try:
            block = json.loads(blocks[0])
        except json.JSONDecodeError as exc:
            errs.append(f"{lid}: R1 блок не разбирается как JSON ({exc.lineno}:{exc.colno})")
            continue
        if lid in records:
            errs.append(f"{lid}: R2 повтор записи")
            continue
        records[lid] = block
        check_schema(block, lid, errs)
        check_artifact(block, lid, errs)
        check_abstract(block, lid, errs)
        check_prose(block, body, lid, errs)

    check_duplicate_doi(records, errs)
    check_reverse(records, errs)
    check_legacy(records, errs)
    print(f"записей: {len(records)} из {len(sections)} секций")
    return errs


SELFTEST_CASES = [
    ("full без артефакта", "full", None, "R5"),
    ("артефакт не совпадает по sha", "full", "badsa", "R5"),
    ("проза «не читал», уровень full", "negated_full", None, "R8"),
    ("нет локатора и нет none", "noloc", None, "R3"),
    ("два блока в секции", "twoblocks", None, "R1"),
    ("абстракт без отпечатка", "abstract_no_sha", None, "R7"),
    ("сирота в papers/", "orphan", None, "R9"),
]


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="lit-contract-"))
    papers = tmp / "papers"
    papers.mkdir()
    good_art = papers / "arXiv-0000.00000-good.txt"
    good_art.write_text("line one\nline two\n", encoding="utf-8")
    digest = hashlib.sha256(good_art.read_bytes()).hexdigest()
    size = good_art.stat().st_size

    def block(lid="L-001", level="full_text_examined", artifact=good_art, sha=digest, bytes_=size,
              locator=None, legacy=False, abstract_sha=None, scope="full", ranges=None):
        return {
            "L": lid,
            "locator": locator or {"doi": "10.1234/abcde", "arxiv": None, "arxiv_version": None,
                                   "openalex": None, "pmid": None, "url": None, "none": False},
            "access": {"level": level,
                       "artifact": artifact.name if artifact else None,
                       "bytes": bytes_ if artifact else None,
                       "sha256": sha if artifact else None,
                       "retrieved_at": None, "via": "arxiv", "via_detail": "x"},
            "inspection": {"scope": scope, "reviewed_ranges": ranges or []},
            "abstract_sha256": abstract_sha,
            "bibliographic": {"title": "t", "year": 2025, "first_author": "A"},
            "legacy": legacy, "legacy_reason": None, "downgrade_reason": None,
        }

    def registry(cases: list[tuple[str, str, dict | None, int]]) -> str:
        parts = []
        for i, (_name, prose, blk, nblocks) in enumerate(cases, start=1):
            lid = f"L-{i:03d}"
            blk = dict(blk) if blk else None
            if blk is not None:
                blk["L"] = lid
                if blk["access"]["artifact"]:
                    blk["access"]["artifact"] = f"papers/{blk['access']['artifact']}"
            body = f"\n\n**Проверено.** {prose}\n\n" + (("```json\n" + json.dumps(blk) + "\n```\n") * nblocks if blk else "")
            parts.append(f"### {lid} · title {i}{body}")
        return "".join(parts)

    total = 0
    bad = 0
    for name, prose, blk, want in SELFTEST_CASES:
        if name == "full без артефакта":
            b = block(artifact=None)
            cases_text = registry([(name, "**полный текст**", b, 1)])
        elif name == "артефакт не совпадает по sha":
            b = block(sha="0" * 64)
            cases_text = registry([(name, "**полный текст**", b, 1)])
        elif name == "проза «не читал», уровень full":
            b = block()
            cases_text = registry([(name, "**аннотация** (полный текст не читал)", b, 1)])
        elif name == "нет локатора и нет none":
            b = block(locator={"doi": None, "arxiv": None, "arxiv_version": None, "openalex": None,
                               "pmid": None, "url": None, "none": False})
            cases_text = registry([(name, "**полный текст**", b, 1)])
        elif name == "два блока в секции":
            b = block()
            cases_text = registry([(name, "**полный текст**", b, 2)])
        elif name == "абстракт без отпечатка":
            b = block(level="abstract_read", artifact=None)
            b["access"]["via"] = "none"
            b["access"]["retrieved_at"] = "2026-11-21T00:00:00Z"
            cases_text = registry([(name, "**аннотация**", b, 1)])
        elif name == "сирота в papers/":
            (papers / "arXiv-9999.99999-orphan.txt").write_text("x", encoding="utf-8")
            b = block()
            cases_text = registry([(name, "**полный текст**", b, 1)])
        else:
            continue

        reg = tmp / f"registry-{total}.md"
        reg.write_text(cases_text, encoding="utf-8")
        errors = run(reg, papers, tmp / "no-baseline.json")
        total += 1
        hit = any(want in e for e in errors)
        if not hit:
            bad += 1
            print(f"  FAIL {name}: ждали {want}, получили {errors}")
        else:
            print(f"  ok   {name} -> {want}")

    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errors = run(REGISTRY, PAPERS, BASELINE)
    if errors:
        print(f"ЛИТЕРАТУРНЫЙ КОНТРАКТ: {len(errors)} нарушений")
        for err in errors[:40]:
            print("  " + err)
        if len(errors) > 40:
            print(f"  … и ещё {len(errors) - 40}")
        return 1
    print("контракт литературы: нарушений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
