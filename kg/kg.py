#!/usr/bin/env python3
"""kg.py — claim-centric knowledge graph for this repository.

Source of truth: kg/claims.jsonl (append-only, one claim per line).
Generated: kg/INDEX.md (human), kg/graph.json (machine).

Commands:
  build                 rebuild INDEX.md and graph.json
  map                   status counts and the busiest claims
  find <text>           full-text search over claims
  show C-00N            one claim with its evidence and relations
  expand C-00N [N]      neighbourhood of a claim (default 1 hop)
  contradictions        refutes-pairs and same-text-different-status pairs
  trace C-00N           evidence path from a claim
  check                 validate the file

Usage: python3 kg/kg.py <command> [args]
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIMS = ROOT / "claims.jsonl"
INDEX = ROOT / "INDEX.md"
GRAPH = ROOT / "graph.json"

EPISTEMIC = {"hypothesis", "established", "contested", "replicated", "refuted", "bounded"}
PROVENANCE = {"extracted", "verified_agent", "human_confirmed"}
RELATIONS = {"supports", "refutes", "qualifies", "extends", "replicates", "supersedes", "same_as", "shared_evidence"}
EVIDENCE_KINDS = {"experiment", "literature", "formula", "result", "prediction"}


def load():
    claims = []
    with CLAIMS.open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                claims.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"claims.jsonl line {n}: {exc}")
    return claims


def validate(claims):
    problems = []
    seen = set()
    for c in claims:
        cid = c.get("id", "?")
        if cid in seen:
            problems.append(f"{cid}: duplicate id")
        seen.add(cid)
        if not c.get("text"):
            problems.append(f"{cid}: empty text")
        if c.get("epistemic") not in EPISTEMIC:
            problems.append(f"{cid}: bad epistemic {c.get('epistemic')!r}")
        if c.get("provenance") not in PROVENANCE:
            problems.append(f"{cid}: bad provenance {c.get('provenance')!r}")
        if not isinstance(c.get("context"), dict) or not c["context"]:
            problems.append(f"{cid}: empty context")
        for e in c.get("evidence", []):
            if e.get("kind") not in EVIDENCE_KINDS:
                problems.append(f"{cid}: bad evidence kind {e.get('kind')!r}")
        for r in c.get("relations", []):
            if r.get("type") not in RELATIONS:
                problems.append(f"{cid}: bad relation type {r.get('type')!r}")
    return problems


def build(claims):
    by_id = {c["id"]: c for c in claims}
    edges = []
    for c in claims:
        for r in c.get("relations", []):
            edges.append({"from": c["id"], "to": r["target"], "type": r["type"], "note": r.get("note", "")})
    GRAPH.write_text(json.dumps({"claims": claims, "edges": edges}, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")

    lines = ["# kg/INDEX.md — граф утверждений (генерируется из claims.jsonl)", "",
             "**Не править руками.** Источник: `kg/claims.jsonl`. Пересборка: `python3 kg/kg.py build`.", "",
             f"утверждений: **{len(claims)}**, связей: **{len(edges)}**", "",
             "| id | утверждение | статус | происхождение | доказательств |", "|---|---|---|---|---|"]
    for c in claims:
        text = c["text"] if len(c["text"]) <= 110 else c["text"][:107] + "…"
        lines.append(f"| {c['id']} | {text} | {c['epistemic']} | {c['provenance']} | {len(c.get('evidence', []))} |")
    lines += ["", "## Связи", ""]
    for e in edges:
        lines.append(f"- {e['from']} —{e['type']}→ {e['to']}" + (f"  ({e['note']})" if e["note"] else ""))
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"built: {len(claims)} claims, {len(edges)} edges -> {INDEX.name}, {GRAPH.name}")


def cmd_map(claims):
    print(f"claims: {len(claims)}")
    print("by epistemic:", dict(Counter(c["epistemic"] for c in claims)))
    print("by provenance:", dict(Counter(c["provenance"] for c in claims)))
    deg = Counter()
    for c in claims:
        deg[c["id"]] += len(c.get("relations", []))
    print("busiest:", deg.most_common(5))
    no_ev = [c["id"] for c in claims if not c.get("evidence")]
    print("without evidence:", no_ev)


def cmd_find(claims, needle):
    n = needle.lower()
    hits = [c for c in claims if n in c["text"].lower() or n in json.dumps(c.get("context", {}), ensure_ascii=False).lower()]
    for c in hits:
        print(f"{c['id']} [{c['epistemic']}/{c['provenance']}] {c['text']}")
    if not hits:
        print("nothing found")


def cmd_show(claims, cid):
    for c in claims:
        if c["id"] == cid:
            print(json.dumps(c, ensure_ascii=False, indent=2))
            return
    print(f"{cid}: not found")


def cmd_expand(claims, cid, hops=1):
    by_id = {c["id"]: c for c in claims}
    seen = {cid}
    frontier = {cid}
    for _ in range(hops):
        nxt = set()
        for c in claims:
            for r in c.get("relations", []):
                if c["id"] in frontier or r["target"] in frontier:
                    nxt.add(c["id"])
                    nxt.add(r["target"])
        frontier = nxt - seen
        seen |= nxt
    for i in sorted(seen):
        if i in by_id:
            print(f"{i} [{by_id[i]['epistemic']}] {by_id[i]['text']}")


def cmd_contradictions(claims):
    by_id = {c["id"]: c for c in claims}
    found = False
    for c in claims:
        for r in c.get("relations", []):
            if r["type"] == "refutes":
                found = True
                tgt = by_id.get(r["target"], {})
                print(f"REFUTES: {c['id']} -> {r['target']}")
                print(f"   claim : {c['text']}")
                print(f"   target: {tgt.get('text', '(missing)')}")
                print(f"   note  : {r.get('note', '')}")
    for c in claims:
        if c["epistemic"] == "refuted":
            found = True
            print(f"REFUTED: {c['id']} {c['text']}")
    if not found:
        print("no contradictions recorded")


def cmd_trace(claims, cid):
    for c in claims:
        if c["id"] == cid:
            print(f"{cid}: {c['text']}")
            for e in c.get("evidence", []):
                print(f"  evidence [{e['kind']}] {e['ref']}: {e.get('strength', '')}")
            if not c.get("evidence"):
                print("  (no evidence)")
            return
    print(f"{cid}: not found")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    claims = load()
    cmd = argv[1]
    if cmd == "build":
        problems = validate(claims)
        if problems:
            print("validation problems:")
            for p in problems:
                print("  ", p)
            return 1
        build(claims)
    elif cmd == "check":
        problems = validate(claims)
        print("OK" if not problems else "\n".join(problems))
        return 0 if not problems else 1
    elif cmd == "map":
        cmd_map(claims)
    elif cmd == "find":
        cmd_find(claims, " ".join(argv[2:]))
    elif cmd == "show":
        cmd_show(claims, argv[2])
    elif cmd == "expand":
        cmd_expand(claims, argv[2], int(argv[3]) if len(argv) > 3 else 1)
    elif cmd == "contradictions":
        cmd_contradictions(claims)
    elif cmd == "trace":
        cmd_trace(claims, argv[2])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
