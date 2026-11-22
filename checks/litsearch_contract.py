"""A search snapshot is replayable: deduplication and RRF are recomputed from the stored ranks.

The rule the whole repository is built on: a derived number is not data, it is a claim. The snapshot keeps
the primary inputs (per-channel ranks) and this checker recomputes the fusion from them, offline. A ranking
edited by hand without touching the ranks therefore fails.

Rules:
  R1 schema and required fields;
  R2 dedup keys recompute from ids (doi -> arxiv -> pmid -> title_norm+year);
  R3 RRF recomputes (k=60, stored weights) and matches the stored ranking and scores;
  R4 `channels` per work matches the channels whose results contain it;
  R5 `degraded` is true iff some channel has status `error` or `skipped_budget`;
  R6 `raw_snapshot` exists and its sha256 matches;
  R7 `saturation.prev_run_id` points to an existing snapshot in literature/runs/.

Usage:
    python3 checks/litsearch_contract.py literature/runs/<run>.json
    python3 checks/litsearch_contract.py --selftest
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "literature" / "runs"

K = 60
TIE = "score_desc_key_asc"


def title_norm(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-zа-яё0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def key_of(ids: dict, title: str, year) -> str:
    doi = (ids or {}).get("doi")
    if doi:
        return "doi:" + str(doi).strip().lower()
    arxiv = (ids or {}).get("arxiv")
    if arxiv:
        return "arxiv:" + str(arxiv).strip()
    pmid = (ids or {}).get("pmid")
    if pmid:
        return "pmid:" + str(pmid).strip()
    return "title:" + title_norm(title) + "#" + str(year or "")


def recompute(snap: dict) -> tuple[list[str], dict[str, float], dict[str, list[str]], dict[str, str]]:
    """Return (ranking keys, rrf scores, channels per key, key per work) from channel ranks alone."""
    weights = snap.get("fusion", {}).get("weights") or {}
    scores: dict[str, float] = {}
    channels: dict[str, set] = {}
    key_by_raw: dict[str, str] = {}
    alias: dict[str, str] = {}
    by_title: dict[str, str] = {}
    method = (snap.get("dedup") or {}).get("method") or ""
    merge_titles = "merged" in method

    def canonical(key: str, title: str, year) -> str:
        if not merge_titles:
            return key
        if key in alias:
            return alias[key]
        tkey = title_norm(title) + "#" + str(year or "")
        if tkey in by_title:
            alias[key] = by_title[tkey]
            return by_title[tkey]
        by_title[tkey] = key
        return key

    for ch in snap.get("channels", []):
        name = ch.get("name")
        w = float(weights.get(name, 1.0))
        seen: set[str] = set()
        for item in sorted(ch.get("results", []), key=lambda r: r.get("rank", 0)):
            key = canonical(key_of(item.get("ids") or {}, item.get("title", ""), item.get("year")),
                            item.get("title", ""), item.get("year"))
            key_by_raw[str(item.get("rank")) + "|" + item.get("title", "")] = key
            if key in seen:
                continue
            seen.add(key)
            scores[key] = scores.get(key, 0.0) + w / (K + int(item.get("rank", 1)))
            channels.setdefault(key, set()).add(name)
    ranking = sorted(scores.items(), key=lambda kv: (-round(kv[1], 9), kv[0]))
    return [k for k, _ in ranking], dict(scores), {k: sorted(v) for k, v in channels.items()}, key_by_raw


def check(path: pathlib.Path, runs_dir: pathlib.Path) -> list[str]:
    errs: list[str] = []
    try:
        snap = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"R1 снапшот не разбирается: {exc}"]

    for field in ("schema", "run_id", "created_at", "environment", "query", "channels", "dedup", "fusion", "degraded", "works"):
        if field not in snap:
            errs.append(f"R1 нет поля `{field}`")
    if errs:
        return errs
    if snap["schema"] != "litsearch/v1":
        errs.append(f"R1 схема `{snap['schema']}` вместо `litsearch/v1`")
    if (snap.get("fusion") or {}).get("k") != K:
        errs.append(f"R3 k={snap['fusion'].get('k')} вместо {K}")
    if (snap.get("fusion") or {}).get("tie_break") != TIE:
        errs.append(f"R3 tie_break={snap['fusion'].get('tie_break')} вместо {TIE}")

    keys, scores, channels, _ = recompute(snap)
    stored = snap.get("fusion", {}).get("ranking") or []
    stored_keys = [r.get("key") for r in stored]
    if stored_keys != keys:
        errs.append("R3 порядок в `fusion.ranking` не пересчитывается из рангов каналов")
    for row in stored:
        key = row.get("key")
        want = scores.get(key)
        if want is None:
            errs.append(f"R3 ключ `{key}` не следует ни из одного канала")
            continue
        got = row.get("rrf")
        if got is None or abs(float(got) - want) > 1e-9:
            errs.append(f"R3 `{key}`: rrf={got} вместо {round(want, 9)}")
        row_chans = sorted(row.get("channels") or [])
        if row_chans != channels.get(key, []):
            errs.append(f"R4 `{key}`: каналы {row_chans} вместо {channels.get(key, [])}")

    degraded = any((c.get("status") in ("error", "skipped_budget")) for c in snap.get("channels", []))
    if bool(snap.get("degraded")) != degraded:
        errs.append(f"R5 degraded={snap.get('degraded')}, а каналы дают {degraded}")

    for ch in snap.get("channels", []):
        rel = ch.get("raw_snapshot")
        if not rel:
            continue
        raw = path.parent / rel
        if not raw.is_file():
            errs.append(f"R6 нет сырого ответа канала `{ch.get('name')}`: {rel}")
            continue
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        if ch.get("raw_sha256") != digest:
            errs.append(f"R6 sha сырого ответа `{ch.get('name')}` не совпадает")

    sat = snap.get("saturation") or {}
    prev = sat.get("prev_run_id")
    if prev:
        if not (runs_dir / f"{prev}.json").is_file():
            errs.append(f"R7 предыдущего прогона нет в literature/runs/: {prev}")
    return errs


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="litsearch-"))
    runs = tmp / "runs"
    runs.mkdir()
    (tmp / "raw-a.json").write_text("[]", encoding="utf-8")
    raw_sha = hashlib.sha256(b"[]").hexdigest()

    def snapshot(rrf_override=None, degraded=False, prev=None, raw_sha_=raw_sha):
        channels = [
            {"name": "paper-search", "status": "ok", "elapsed_ms": 10, "params": {},
             "raw_snapshot": "raw-a.json", "raw_sha256": raw_sha_,
             "results": [
                 {"rank": 1, "ids": {"doi": "10.1/a"}, "title": "A paper", "year": 2020},
                 {"rank": 2, "ids": {"doi": "10.1/b"}, "title": "B paper", "year": 2021},
             ]},
            {"name": "semantic", "status": "ok", "elapsed_ms": 20, "params": {},
             "results": [
                 {"rank": 1, "ids": {"doi": "10.1/b"}, "title": "B paper", "year": 2021},
                 {"rank": 2, "ids": {"doi": "10.1/c"}, "title": "C paper", "year": 2019},
             ]},
        ]
        snap = {"schema": "litsearch/v1", "run_id": "2026-11-21T22-00-00Z_abcdef",
                "created_at": "2026-11-21T22:00:00Z",
                "environment": {"repo_commit": "x", "side": "windows", "tool_versions": {}},
                "query": {"text": "q", "lang": "en", "seeds": [], "fingerprint": "0" * 16},
                "channels": channels,
                "dedup": {"method": "doi>arxiv>pmid>title_norm+year", "clusters": []},
                "fusion": {"method": "rrf", "k": 60, "weights": {}, "tie_break": TIE, "ranking": []},
                "degraded": degraded,
                "saturation": {"prev_run_id": prev} if prev else None,
                "works": []}
        keys, scores, chans, _ = recompute(snap)
        snap["fusion"]["ranking"] = [
            {"key": k, "rrf": (rrf_override if rrf_override is not None and k.endswith("10.1/b") else round(scores[k], 9)),
             "ranks": {}, "channels": chans[k]}
            for k in keys
        ]
        return snap

    def write(name, snap):
        path = tmp / f"{name}.json"
        path.write_text(json.dumps(snap), encoding="utf-8")
        return path

    cases = []

    good = write("good", snapshot())
    cases.append(("чистый снапшот проходит", check(good, runs), []))

    bad_rrf = write("bad_rrf", snapshot(rrf_override=0.5))
    cases.append(("rrf подправлен без рангов", check(bad_rrf, runs), ["R3"]))

    bad_deg = write("bad_deg", snapshot(degraded=True))
    cases.append(("degraded врёт", check(bad_deg, runs), ["R5"]))

    bad_raw = write("bad_raw", snapshot(raw_sha_="0" * 64))
    cases.append(("sha сырого ответа не тот", check(bad_raw, runs), ["R6"]))

    bad_prev = write("bad_prev", snapshot(prev="nope"))
    cases.append(("нет предыдущего прогона", check(bad_prev, runs), ["R7"]))

    total, bad = 0, 0
    for name, got, want in cases:
        total += 1
        ok = all(any(w in e for e in got) for w in want) if want else not got
        if not ok:
            bad += 1
            print(f"  FAIL {name}: ждали {want or 'чисто'}, получили {got}")
        else:
            print(f"  ok   {name}")
    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    if not argv:
        targets = sorted(RUNS.glob("*.json")) if RUNS.exists() else []
        if not targets:
            print("снимков нет: литературных прогонов ещё не было")
            return 0
    else:
        targets = [pathlib.Path(a) for a in argv]
    bad = 0
    for path in targets:
        errs = check(path, path.parent)
        if errs:
            bad += 1
            print(f"{path.name}: {len(errs)} нарушений")
            for e in errs[:12]:
                print("  " + e)
    if bad:
        return 1
    print(f"снимки поиска: {len(targets)} проверено, нарушений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
