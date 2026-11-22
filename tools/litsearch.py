"""One search, three channels, one replayable snapshot.

Runs in WSL and shells out to the Windows side for anything that touches the network (that is the only
side with egress here). Writes `literature/runs/<run_id>.json` plus `literature/runs/<run_id>/raw/…`:

  * the snapshot keeps the **primary inputs** — per-channel ranks — and the derived RRF scores;
  * `checks/litsearch_contract.py` recomputes dedup and RRF from those ranks offline;
  * `--offline --from-run <id>` re-prints a stored ranking without touching the network.

Channels:
  paper-search   — Crossref + arXiv + PubMed + OpenAlex through `paper-search.exe`
  lixplore       — Crossref + arXiv + PubMed + EuropePMC + DOAJ through `lixplore.exe`
  openalex       — relevance ranking straight from the OpenAlex API (curl.exe), key optional

Usage:
    python3 tools/litsearch.py "process-enablement graphs organisational closure" \
        --seeds "organisational closure;autopoiesis" --per-channel 10
    python3 tools/litsearch.py --offline --from-run 2026-11-21T22-40-00Z_ab12cd
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import budget as budget_mod  # noqa: E402
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "literature" / "runs"
K = 60
VENV = pathlib.Path(os.environ.get("LITSEARCH_VENV", "/mnt/c/Users/Admin/.dsh/tools/sci-venv/Scripts"))
CURL = os.environ.get("LITSEARCH_CURL", "/mnt/c/Windows/System32/curl.exe")
KEY_FILE = pathlib.Path(os.environ.get("LITSEARCH_KEY", "/mnt/c/Users/Admin/.dsh/secrets/openalex.key"))


# ---------- helpers ----------

def now_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    return stamp + "_" + os.urandom(3).hex()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def title_norm(title: str) -> str:
    s = (title or "").lower()
    s = re.sub(r"[^a-zа-яё0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def key_of(ids: dict, title: str, year) -> str:
    for field in ("doi", "arxiv", "pmid"):
        value = ids.get(field)
        if value:
            return f"{field}:{str(value).strip().lower() if field == 'doi' else str(value).strip()}"
    return "title:" + title_norm(title) + "#" + str(year or "")


def openalex_key() -> str | None:
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def arxiv_from_url(url: str) -> str | None:
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", url or "")
    return m.group(1) if m else None


# ---------- channels ----------

def channel_paper_search(query: str, n: int) -> tuple[dict, dict]:
    exe = VENV / "paper-search.exe"
    cmd = [str(exe), "search", query, "-s", "crossref,arxiv,pubmed,openalex", "-n", str(n), "--json"]
    started = datetime.now(timezone.utc)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        raw_text = out.stdout
        payload = json.loads(raw_text) if raw_text.strip().startswith("{") else {}
    except Exception as exc:  # noqa: BLE001
        return {"name": "paper-search", "status": "error", "elapsed_ms": 0, "params": {"error": str(exc)},
                "results": []}, {}
    results = []
    for i, paper in enumerate(payload.get("papers", [])[:n], start=1):
        ids = {"doi": paper.get("doi") or None, "arxiv": arxiv_from_url(paper.get("url", "")),
               "openalex": None, "pmid": None}
        results.append({"rank": i, "ids": ids, "title": paper.get("title") or "",
                        "year": int(str(paper.get("published_date") or "0000")[:4] or 0) or None,
                        "score_raw": None, "score_kind": None})
    status = "ok" if results else "empty"
    elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    meta = {"name": "paper-search", "sources": ["crossref", "arxiv", "pubmed", "openalex"],
            "status": status, "elapsed_ms": elapsed, "params": {"n": n},
            "raw_snapshot": None, "raw_sha256": None, "results": results}
    return meta, {"text": raw_text}


def channel_lixplore(query: str, n: int) -> tuple[dict, dict]:
    exe = VENV / "lixplore.exe"
    tmp = pathlib.Path(tempfile.mkstemp(suffix=".json")[1])
    cmd = [str(exe), "-A", "-q", query, "-m", str(n), "-X", "json", "-o", str(tmp)]
    started = datetime.now(timezone.utc)
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        payload = json.loads(tmp.read_text(encoding="utf-8")) if tmp.exists() else []
    except Exception as exc:  # noqa: BLE001
        return {"name": "lixplore", "status": "error", "elapsed_ms": 0, "params": {"error": str(exc)},
                "results": []}, {}
    finally:
        tmp.unlink(missing_ok=True)
    results = []
    for i, paper in enumerate(payload[:n], start=1):
        ids = {"doi": paper.get("doi") or None, "arxiv": arxiv_from_url(paper.get("url", "")),
               "openalex": None, "pmid": None}
        year = paper.get("year")
        results.append({"rank": i, "ids": ids, "title": paper.get("title") or "",
                        "year": int(year) if str(year or "").isdigit() else None,
                        "score_raw": None, "score_kind": None})
    status = "ok" if results else "empty"
    elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    meta = {"name": "lixplore", "sources": ["crossref", "arxiv", "pubmed", "europepmc", "doaj"],
            "status": status, "elapsed_ms": elapsed, "params": {"n": n},
            "raw_snapshot": None, "raw_sha256": None, "results": results}
    return meta, {"text": json.dumps(payload, ensure_ascii=False)[:200000]}


def channel_openalex(query: str, n: int) -> tuple[dict, dict]:
    url = "https://api.openalex.org/works"
    params = ("?search=" + query.replace(" ", "%20") + f"&per_page={n}"
              "&select=id,doi,title,publication_year,cited_by_count")
    key = openalex_key()
    if key:
        params += "&api_key=" + key
    started = datetime.now(timezone.utc)

    # A cached answer costs nothing, so it is checked before the budget: a spent day must not block a
    # replay of a query we already ran.
    cache_name = hashlib.sha256((url + params.replace(key or "", "")).encode("utf-8")).hexdigest()[:32]
    cached = budget_mod.cache_get(cache_name)
    if cached:
        try:
            payload = json.loads(cached["body"])
            results = _openalex_rows(payload, n)
            elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
            meta = {"name": "openalex", "sources": ["openalex"], "status": "ok" if results else "empty",
                    "elapsed_ms": elapsed, "params": {"n": n, "cache_hit": True,
                                                      "cached_at": cached.get("fetched_at")},
                    "raw_snapshot": None, "raw_sha256": None, "results": results}
            return meta, {"text": cached["body"]}
        except Exception:  # noqa: BLE001
            pass

    before = budget_mod.live_budget()
    allow, why = budget_mod.decide(before)
    if not allow:
        return {"name": "openalex", "status": "skipped_budget", "elapsed_ms": 0,
                "params": {"n": n, "reason": why}, "results": []}, {}

    cmd = [CURL, "-sS", "-L", "--compressed", "-m", "60", "-A", "litsearch/1.0", url + params]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        payload = json.loads(out.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"name": "openalex", "status": "error", "elapsed_ms": 0,
                "params": {"error": str(exc)}, "results": []}, {}
    results = _openalex_rows(payload, n)
    status = "ok" if results else "empty"
    elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    budget_mod.cache_put(cache_name, out.stdout)
    after = budget_mod.live_budget()
    if after.get("known") and before.get("known"):
        budget_mod.append_ledger({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endpoint": "/works", "run_id": "inline", "channel": "openalex",
            "budget_before": before.get("daily_remaining_usd"),
            "budget_after": after.get("daily_remaining_usd"),
        })
    meta = {"name": "openalex", "sources": ["openalex"], "status": status, "elapsed_ms": elapsed,
            "params": {"n": n, "key": bool(key), "cache_hit": False}, "raw_snapshot": None,
            "raw_sha256": None, "results": results}
    return meta, {"text": out.stdout}


def _openalex_rows(payload: dict, n: int) -> list[dict]:
    results = []
    for i, work in enumerate((payload.get("results") or [])[:n], start=1):
        doi = (work.get("doi") or "").replace("https://doi.org/", "") or None
        results.append({"rank": i,
                        "ids": {"doi": doi, "arxiv": None,
                                "openalex": (work.get("id") or "").rsplit("/", 1)[-1] or None, "pmid": None},
                        "title": work.get("title") or "",
                        "year": work.get("publication_year"),
                        "score_raw": work.get("cited_by_count"), "score_kind": "api"})
    return results


# ---------- fusion ----------

def fuse(channels: list[dict]) -> tuple[list[dict], list[list[str]], list[dict], bool]:
    scores: dict[str, float] = {}
    ranks: dict[str, dict] = {}
    channels_of: dict[str, list[str]] = {}
    works: dict[str, dict] = {}
    clusters: list[list[str]] = []
    # Same paper under two DOIs (preprint vs journal version) is the same work. The key order
    # doi > arxiv > pmid > title cannot see that, so keys that share title+year are aliased to one.
    alias: dict[str, str] = {}
    by_title: dict[str, str] = {}

    def canonical(key: str, title: str, year) -> str:
        if key in alias:
            return alias[key]
        tkey = title_norm(title) + "#" + str(year or "")
        if tkey in by_title:
            alias[key] = by_title[tkey]
            return by_title[tkey]
        by_title[tkey] = key
        return key

    for ch in channels:
        name = ch["name"]
        seen: dict[str, int] = {}
        for item in ch["results"]:
            key = canonical(key_of(item["ids"], item["title"], item.get("year")),
                            item["title"], item.get("year"))
            seen.setdefault(key, item["rank"])
            works.setdefault(key, {"key": key, "doi": item["ids"].get("doi"),
                                   "arxiv": item["ids"].get("arxiv"),
                                   "openalex": item["ids"].get("openalex"),
                                   "title": item["title"], "year": item.get("year")})
        for key, rank in seen.items():
            scores[key] = scores.get(key, 0.0) + 1.0 / (K + rank)
            ranks.setdefault(key, {})[name] = rank
            channels_of.setdefault(key, []).append(name)
        clusters.append(sorted(seen))
    ranking = [
        {"key": key, "rrf": round(score, 9), "ranks": ranks[key], "channels": sorted(channels_of[key])}
        for key, score in sorted(scores.items(), key=lambda kv: (-round(kv[1], 9), kv[0]))
    ]
    degraded = any(ch["status"] in ("error", "skipped_budget") for ch in channels)
    return ranking, clusters, list(works.values()), degraded


def saturation(cur_ranking: list[dict], prev_snap: dict) -> dict:
    """Marginal novelty of this run against a previous one: the only honest answer to "are we done?".

    `new_frac_top20` and `jaccard_top20` are set-level measures, not "relevance" judgements, so they can be
    recomputed by the contract checker and cannot be gamed by editing prose.
    """
    prev_ranking = (prev_snap.get("fusion") or {}).get("ranking") or []
    cur_top = [row["key"] for row in cur_ranking[:20]]
    prev_top = [row["key"] for row in prev_ranking[:20]]
    prev_all = {row["key"] for row in prev_ranking}
    new_unique = sum(1 for key in cur_top if key not in prev_all)
    inter = len(set(cur_top) & set(prev_top))
    union = len(set(cur_top) | set(prev_top))
    return {
        "prev_run_id": prev_snap.get("run_id"),
        "new_unique": new_unique,
        "new_frac_top20": round(new_unique / max(1, len(cur_top)), 4),
        "jaccard_top20": round(inter / union, 4) if union else None,
    }


def fingerprint(query: str, seeds: list[str], n: int) -> str:
    payload = json.dumps({"q": query, "seeds": seeds, "n": n}, ensure_ascii=False, sort_keys=True)
    return sha_bytes(payload.encode("utf-8"))[:16]


# ---------- main ----------

def main(argv: list[str]) -> int:
    if "--offline" in argv:
        idx = argv.index("--from-run") if "--from-run" in argv else -1
        if idx < 0 or idx + 1 >= len(argv):
            print("usage: --offline --from-run <run_id>", file=sys.stderr)
            return 2
        run_id = argv[idx + 1]
        path = RUNS / f"{run_id}.json"
        if not path.exists():
            print(f"нет снимка {path}", file=sys.stderr)
            return 2
        snap = json.loads(path.read_text(encoding="utf-8"))
        print(f"{snap['run_id']}: {len(snap['fusion']['ranking'])} работ, degraded={snap['degraded']}")
        for i, row in enumerate(snap["fusion"]["ranking"][:10], start=1):
            print(f"{i:2d}. rrf={row['rrf']:.5f} {row['key']} channels={','.join(row['channels'])}")
        return 0

    query = next((a for a in argv if not a.startswith("--")), "")
    if not query:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    seeds: list[str] = []
    if "--seeds" in argv:
        seeds = [s.strip() for s in argv[argv.index("--seeds") + 1].split(";") if s.strip()]
    n = 15
    if "--per-channel" in argv:
        n = int(argv[argv.index("--per-channel") + 1])
    prev_snap = None
    if "--compare" in argv:
        prev_id = argv[argv.index("--compare") + 1]
        prev_path = RUNS / f"{prev_id}.json"
        if not prev_path.exists():
            print(f"нет предыдущего снимка {prev_path}", file=sys.stderr)
            return 2
        prev_snap = json.loads(prev_path.read_text(encoding="utf-8"))

    channels: list[dict] = []
    raws: dict[str, str] = {}
    for fn in (channel_paper_search, channel_lixplore, channel_openalex):
        meta, raw = fn(query, n)
        channels.append(meta)
        raws[meta["name"]] = raw.get("text", "")

    ranking, clusters, works, degraded = fuse(channels)

    run_id = now_id()
    raw_dir = RUNS / run_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for ch in channels:
        text = raws.get(ch["name"], "")
        if not text:
            continue
        path = raw_dir / f"{ch['name']}.json"
        path.write_bytes(text.encode("utf-8"))
        ch["raw_snapshot"] = f"{run_id}/raw/{ch['name']}.json"
        ch["raw_sha256"] = sha_bytes(text.encode("utf-8"))

    snapshot = {
        "schema": "litsearch/v1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "environment": {"repo_commit": git_commit(), "side": "wsl",
                        "tool_versions": {"paper-search": "installed", "lixplore": "installed",
                                          "curl": "windows"}, "semantic_model": None},
        "query": {"text": query, "lang": "en", "seeds": seeds, "fingerprint": fingerprint(query, seeds, n)},
        "channels": channels,
        "dedup": {"method": "doi>arxiv>pmid>title_norm+year; same title+year merged", "clusters": clusters},
        "fusion": {"method": "rrf", "k": K, "weights": {}, "tie_break": "score_desc_key_asc",
                   "ranking": ranking},
        "degraded": degraded,
        "saturation": saturation(ranking, prev_snap) if prev_snap else None,
        "works": works,
    }

    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f"{run_id}.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"run_id: {run_id}")
    for ch in channels:
        print(f"  {ch['name']:<14} {ch['status']:<6} {len(ch['results'])} результатов, {ch['elapsed_ms']} мс")
    print(f"работ после дедупа: {len(works)}; degraded={degraded}")
    print(f"снимок: {out.relative_to(ROOT)}")
    for i, row in enumerate(ranking[:5], start=1):
        title = next((w["title"] for w in works if w["key"] == row["key"]), "")
        print(f"{i:2d}. {row['rrf']:.5f}  {title[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
