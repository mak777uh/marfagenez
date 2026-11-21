"""The quarantine around literature candidates: the graph must not grow by accident.

Rules:
  C1 every candidate line has candidate_id, key, run_id, status, first_seen;
  C2 candidate keys are unique (no double ingest);
  C3 a candidate never duplicates a literature record already in the registry (by DOI or arXiv id);
  C4 `admitted` candidates name a claim that exists in `kg/nodes.jsonl`, an `L-NNN` that exists in the
     registry, and an `ADM-…` event that exists in `kg/admissions.jsonl`;
  C5 `kg/nodes.jsonl` contains no candidate ids (candidates stay out of the graph);
  C6 rejected tombstones are not re-added as `new` (their key must not appear twice).

Usage:
    python3 checks/candidates_quarantine.py
    python3 checks/candidates_quarantine.py --selftest
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "kg" / "candidates.jsonl"
NODES = ROOT / "kg" / "nodes.jsonl"
ADMISSIONS = ROOT / "kg" / "admissions.jsonl"
REGISTRY = ROOT / "docs" / "ELEPHANT-LITERATURE.md"

REQUIRED = ("candidate_id", "key", "run_id", "status", "first_seen")
STATUSES = {"new", "shortlisted", "admitted", "rejected", "expired"}


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check(candidates_path: pathlib.Path, nodes_path: pathlib.Path,
          admissions_path: pathlib.Path, registry_path: pathlib.Path) -> list[str]:
    errs: list[str] = []
    rows = load_jsonl(candidates_path)
    if not rows:
        return errs

    node_ids = {n["id"] for n in load_jsonl(nodes_path)}
    events = {e.get("event_id") for e in load_jsonl(admissions_path)}
    registry = registry_path.read_text(encoding="utf-8") if registry_path.exists() else ""
    reg_ids = set(re.findall(r"^### (L-\d{3})", registry, re.M))
    reg_keys = set()
    for doi in re.findall(r"10\.\d{4,9}/[^\s)\]>,;\"]+", registry):
        reg_keys.add("doi:" + doi.rstrip(".").lower())
    for arxiv in re.findall(r"arXiv:\s*(\d{4}\.\d{4,5})", registry):
        reg_keys.add("arxiv:" + arxiv)

    seen_keys: dict[str, int] = {}
    for n, row in enumerate(rows, start=1):
        for field in REQUIRED:
            if field not in row:
                errs.append(f"C1 строка {n}: нет поля `{field}`")
        status = row.get("status")
        if status not in STATUSES:
            errs.append(f"C1 строка {n}: статус `{status}` вне перечисления")
        key = row.get("key", "")
        if key in reg_keys:
            errs.append(f"C3 кандидат {row.get('candidate_id')} дублирует запись реестра: {key}")
        seen_keys[key] = seen_keys.get(key, 0) + 1
        if status == "admitted":
            adm = row.get("admitted_as") or {}
            if adm.get("claim") not in node_ids:
                errs.append(f"C4 {row.get('candidate_id')}: claim `{adm.get('claim')}` нет в графе")
            if adm.get("L") not in reg_ids:
                errs.append(f"C4 {row.get('candidate_id')}: L `{adm.get('L')}` нет в реестре")
            if adm.get("event_id") not in events:
                errs.append(f"C4 {row.get('candidate_id')}: события `{adm.get('event_id')}` нет в журнале допуска")

    for key, count in seen_keys.items():
        if count > 1:
            errs.append(f"C2 ключ `{key}` встречается {count} раз")

    cand_ids = {row.get("candidate_id") for row in rows}
    for node_id in node_ids & cand_ids:
        errs.append(f"C5 кандидат `{node_id}` попал в граф")
    return errs


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="quarantine-"))
    registry = tmp / "registry.md"
    registry.write_text("### L-001 · x\n\nDOI 10.1234/reg\n", encoding="utf-8")
    nodes = tmp / "nodes.jsonl"
    nodes.write_text(json.dumps({"id": "C-001"}) + "\n", encoding="utf-8")
    admissions = tmp / "admissions.jsonl"
    admissions.write_text(json.dumps({"event_id": "ADM-0001"}) + "\n", encoding="utf-8")

    def write(name: str, rows: list[dict]) -> pathlib.Path:
        path = tmp / name
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return path

    good = write("good.jsonl", [
        {"candidate_id": "CAND-1", "key": "doi:10.2/new", "run_id": "r", "status": "new",
         "first_seen": "t"},
        {"candidate_id": "CAND-2", "key": "doi:10.3/adm", "run_id": "r", "status": "admitted",
         "first_seen": "t",
         "admitted_as": {"claim": "C-001", "L": "L-001", "event_id": "ADM-0001"}},
    ])
    dup_key = write("dup.jsonl", [
        {"candidate_id": "CAND-1", "key": "doi:10.2/new", "run_id": "r", "status": "new", "first_seen": "t"},
        {"candidate_id": "CAND-2", "key": "doi:10.2/new", "run_id": "r", "status": "new", "first_seen": "t"},
    ])
    dup_reg = write("reg.jsonl", [
        {"candidate_id": "CAND-1", "key": "doi:10.1234/reg", "run_id": "r", "status": "new", "first_seen": "t"},
    ])
    bad_admit = write("bad.jsonl", [
        {"candidate_id": "CAND-1", "key": "doi:10.4/x", "run_id": "r", "status": "admitted", "first_seen": "t",
         "admitted_as": {"claim": "C-999", "L": "L-999", "event_id": "ADM-9999"}},
    ])

    cases = [
        ("чистый карантин", check(good, nodes, admissions, registry), []),
        ("дубль ключа", check(dup_key, nodes, admissions, registry), ["C2"]),
        ("дубль записи реестра", check(dup_reg, nodes, admissions, registry), ["C3"]),
        ("допуск без claim/L/события", check(bad_admit, nodes, admissions, registry), ["C4"]),
    ]
    total, bad = 0, 0
    for name, got, want in cases:
        total += 1
        ok = all(any(w in e for e in got) for w in want) if want else not got
        if not ok:
            bad += 1
            print(f"  FAIL {name}: ждали {want or 'чисто'}, получили {got[:3]}")
        else:
            print(f"  ok   {name}")
    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errs = check(CANDIDATES, NODES, ADMISSIONS, REGISTRY)
    if errs:
        print(f"КАРАНТИН: {len(errs)} нарушений")
        for e in errs[:20]:
            print("  " + e)
        return 1
    rows = load_jsonl(CANDIDATES)
    if rows:
        from collections import Counter

        print("карантин: " + ", ".join(f"{k}={v}" for k, v in sorted(Counter(r.get("status") for r in rows).items())))
    print("карантин кандидатов: нарушений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
