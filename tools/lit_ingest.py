"""Literature candidates live in a quarantine, not in the graph.

A search run produces candidates; a candidate becomes evidence only by an explicit act that names the claim
it supports, the literature record it rests on, and a rationale. Nothing here touches `kg/nodes.jsonl`:
`find` does not filter anything today (there is no `lifecycle` field in the schema), so a candidate that
slipped into the graph would change navigation immediately.

Files:
    literature/inbox/<run_id>.json   raw candidates of one run (written on ingest)
    kg/candidates.jsonl              the quarantine: one line per candidate, append-only, status field
    kg/admissions.jsonl              the existing hash-chained journal, reused for literature admissions

Usage:
    python3 tools/lit_ingest.py ingest --from-run <run_id> [--top 20]
    python3 tools/lit_ingest.py list [--status new]
    python3 tools/lit_ingest.py admit <candidate_id> --claim C-001 --L L-060 --why "…" [--action supports]
    python3 tools/lit_ingest.py reject <candidate_id> --why "…"
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "literature" / "runs"
INBOX = ROOT / "literature" / "inbox"
CANDIDATES = ROOT / "kg" / "candidates.jsonl"
ADMISSIONS = ROOT / "kg" / "admissions.jsonl"
NODES = ROOT / "kg" / "nodes.jsonl"
REGISTRY = ROOT / "docs" / "ELEPHANT-LITERATURE.md"
TTL_DAYS = 30


# ---------- helpers ----------

def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def node_ids() -> set[str]:
    return {n["id"] for n in load_jsonl(NODES)}


def registry_ids() -> set[str]:
    if not REGISTRY.exists():
        return set()
    return set(re.findall(r"^### (L-\d{3})", REGISTRY.read_text(encoding="utf-8"), re.M))


def registry_keys() -> set[str]:
    """Keys already covered by a literature record: ingesting them would be a duplicate, not a candidate."""
    if not REGISTRY.exists():
        return set()
    text = REGISTRY.read_text(encoding="utf-8")
    keys = set()
    for doi in re.findall(r"10\.\d{4,9}/[^\s)\]>,;\"]+", text):
        keys.add("doi:" + doi.rstrip(".").lower())
    for arxiv in re.findall(r"arXiv:\s*(\d{4}\.\d{4,5})", text):
        keys.add("arxiv:" + arxiv)
    return keys


def key_of(work: dict) -> str:
    for field in ("doi", "arxiv"):
        value = work.get(field)
        if value:
            return f"{field}:{str(value).strip().lower() if field == 'doi' else value}"
    title = re.sub(r"[^a-zа-яё0-9 ]+", " ", (work.get("title") or "").lower())
    return "title:" + re.sub(r"\s+", " ", title).strip()


def append_candidate(row: dict) -> None:
    CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATES.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def rewrite_candidates(rows: list[dict]) -> None:
    CANDIDATES.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows),
        encoding="utf-8",
    )


def admission_event(claim_id: str, action: str, rationale: str, evidence: list[str]) -> dict:
    lines = load_jsonl(ADMISSIONS)
    prev = lines[-1].get("event_hash", "") if lines else ""
    event = {
        "event_id": "ADM-" + f"{len(lines) + 1:04d}",
        "node_id": claim_id,
        "action": action,
        "rationale": rationale,
        "evidence_ids": evidence,
        "actor": "owner",
        "rules_version": "admit-v1-literature",
        "graph_hash": hashlib.sha256(str(sorted(node_ids())).encode()).hexdigest()[:16],
        "prev_hash": prev,
        "at": now(),
    }
    event["event_hash"] = hashlib.sha256(
        json.dumps(event, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    ADMISSIONS.parent.mkdir(parents=True, exist_ok=True)
    with ADMISSIONS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


# ---------- verbs ----------

def ingest(run_id: str, top: int) -> int:
    snap_path = RUNS / f"{run_id}.json"
    if not snap_path.exists():
        print(f"нет снимка {snap_path}", file=sys.stderr)
        return 2
    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    ranking = (snap.get("fusion") or {}).get("ranking") or []
    works = (snap.get("works") or [])
    by_key = {w["key"]: w for w in works}

    existing = load_jsonl(CANDIDATES)
    rejected = {row["key"] for row in existing if row.get("status") in ("rejected", "expired")}
    known = {row["key"] for row in existing} | registry_keys()
    added = 0
    inbox: list[dict] = []

    for row in ranking[:top]:
        key = row["key"]
        if key in known or key in rejected:
            continue
        work = by_key.get(key) or {"key": key, "title": "", "doi": None, "arxiv": None, "year": None}
        candidate = {
            "candidate_id": "CAND-" + hashlib.sha256(key.encode()).hexdigest()[:10],
            "key": key,
            "title": work.get("title") or "",
            "year": work.get("year"),
            "doi": work.get("doi"),
            "arxiv": work.get("arxiv"),
            "run_id": run_id,
            "rrf": row.get("rrf"),
            "channels": row.get("channels") or [],
            "status": "new",
            "first_seen": now(),
            "last_seen": now(),
            "admitted_as": None,
            "note": "",
        }
        append_candidate(candidate)
        inbox.append(candidate)
        added += 1

    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / f"{run_id}.json").write_text(
        json.dumps({"run_id": run_id, "added": added, "candidates": inbox}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(f"кандидатов добавлено: {added} (в карантине всего {len(existing) + added})")
    print(f"inbox: literature/inbox/{run_id}.json")
    return 0


def list_candidates(status: str | None) -> int:
    rows = load_jsonl(CANDIDATES)
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if not rows:
        print("карантин пуст" + (f" для статуса {status}" if status else ""))
        return 0
    for row in rows:
        print(f"{row['candidate_id']:<16} {row['status']:<9} {str(row.get('year')):<5} "
              f"{(row.get('title') or '')[:70]}")
    print(f"всего: {len(rows)}")
    return 0


def admit(candidate_id: str, claim: str, lid: str, why: str, action: str, dry: bool = False) -> int:
    rows = load_jsonl(CANDIDATES)
    target = next((r for r in rows if r["candidate_id"] == candidate_id), None)
    if target is None:
        print(f"нет кандидата {candidate_id}", file=sys.stderr)
        return 2
    if not why or len(why) < 10:
        print("отказ: нужна причина не короче 10 символов", file=sys.stderr)
        return 1
    if claim not in node_ids():
        print(f"отказ: нет узла {claim}", file=sys.stderr)
        return 1
    if lid not in registry_ids():
        print(f"отказ: нет записи {lid} в реестре литературы", file=sys.stderr)
        return 1
    if target.get("status") == "admitted":
        print("отказ: кандидат уже допущён", file=sys.stderr)
        return 1

    if dry:
        print(f"[dry-run] {candidate_id} -> {claim} через {lid}: условия выполнены, журнал не тронут")
        return 0
    event = admission_event(claim, action, why, [lid])
    target["status"] = "admitted"
    target["admitted_as"] = {"claim": claim, "L": lid, "event_id": event["event_id"], "at": event["at"]}
    for row in rows:
        if row["candidate_id"] == candidate_id:
            row.update(target)
    rewrite_candidates(rows)
    print(f"допущен: {candidate_id} -> {claim} через {lid} ({event['event_id']})")
    return 0


def reject(candidate_id: str, why: str) -> int:
    rows = load_jsonl(CANDIDATES)
    target = next((r for r in rows if r["candidate_id"] == candidate_id), None)
    if target is None:
        print(f"нет кандидата {candidate_id}", file=sys.stderr)
        return 2
    target["status"] = "rejected"
    target["note"] = why
    target["last_seen"] = now()
    rewrite_candidates(rows)
    print(f"отклонён: {candidate_id} ({why[:60]})")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 2
    verb, rest = argv[0], argv[1:]
    if verb == "ingest":
        if "--from-run" not in rest:
            print("usage: ingest --from-run <run_id> [--top N]", file=sys.stderr)
            return 2
        run_id = rest[rest.index("--from-run") + 1]
        top = int(rest[rest.index("--top") + 1]) if "--top" in rest else 20
        return ingest(run_id, top)
    if verb == "list":
        status = rest[rest.index("--status") + 1] if "--status" in rest else None
        return list_candidates(status)
    if verb == "admit":
        cid = next((a for a in rest if a.startswith("CAND-")), "")
        claim = rest[rest.index("--claim") + 1] if "--claim" in rest else ""
        lid = rest[rest.index("--L") + 1] if "--L" in rest else ""
        why = rest[rest.index("--why") + 1] if "--why" in rest else ""
        action = rest[rest.index("--action") + 1] if "--action" in rest else "supports"
        return admit(cid, claim, lid, why, action, "--dry-run" in rest)
    if verb == "reject":
        cid = next((a for a in rest if a.startswith("CAND-")), "")
        why = rest[rest.index("--why") + 1] if "--why" in rest else ""
        return reject(cid, why)
    print(f"неизвестный глагол {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
