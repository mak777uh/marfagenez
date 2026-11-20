#!/usr/bin/env python3
"""kg.py — agent-friendly knowledge graph for this repository.

Generated store: kg/nodes.jsonl (one node per line; REBUILT from the corpora by kg/migrate.py).
Source of truth: kg/claims.jsonl + docs/ELEPHANT-LITERATURE.md + results/*/run-*.json. Never hand-edit
nodes.jsonl: the next migrate overwrites it.
Generated:       kg/meta.json (the map), kg/graph.json, kg/INDEX.md.

Node kinds: claim | formula | experiment | dataset | definition | question
Edges:      supports | refutes | qualifies | extends | replicates | supersedes | same_as | predicted_by

Commands
  build                 validate, then rebuild meta.json, graph.json, INDEX.md
  map                   the map: counts, communities, frontier, verbs
  check                 validate against the invariants (code, not opinion)
  find <text>           search nodes
  show <id>             one node
  expand <id> [k]       neighbourhood
  trace <id>            evidence of a node
  chain <id>            claim -> formula -> experiment -> data
  formula <id>          signature: latex, units, what checks it
  contradictions        explicit refutes, plus refuted nodes
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

KG = Path(__file__).resolve().parent
ROOT = KG.parent
NODES = KG / "nodes.jsonl"
META = KG / "meta.json"
GRAPH = KG / "graph.json"
INDEX = KG / "INDEX.md"

KINDS = {"claim", "formula", "experiment", "dataset", "definition", "question"}
EPISTEMIC = {"hypothesis", "established", "contested", "replicated", "refuted", "bounded"}
PROVENANCE = {"extracted", "verified_agent", "human_confirmed"}
RELATIONS = {"supports", "refutes", "qualifies", "extends", "replicates", "supersedes", "same_as", "predicted_by"}


def load():
    if not NODES.exists():
        raise SystemExit("kg/nodes.jsonl missing: run python3 kg/migrate.py")
    out = []
    for i, line in enumerate(NODES.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"nodes.jsonl line {i}: {exc}")
    return out



def resolve_refs(nodes):
    """Resolve every `evidence` reference to something real.

    Three acceptance routes, in order:
      1. a node id in the graph (`C-`, `F-`, `L-`, `X-`);
      2. a path that exists on disk (`docs/...`, `results/...`);
      3. an alias: `EXP-22` matches the run nodes whose text names it, `FINDING-317` matches the finding file.

    Returns (resolved_by_kind, unresolved) where unresolved is a list of (node_id, kind, ref).
    A reference that resolves to nothing is a hole in the graph, not a formatting detail -- it is reported,
    and `check --refs` turns the report into a failure.
    """
    by_id = {n["id"] for n in nodes}
    exp_aliases = {}
    for n in nodes:
        if n.get("kind") != "experiment":
            continue
        text = n.get("text") or ""
        head = text.split(" run ")[0].strip()
        if head:
            exp_aliases.setdefault(head, []).append(n["id"])
        src = (n.get("data") or {}).get("source") or ""
        stem = src.rsplit("/", 1)[-1].replace(".json", "")
        if stem:
            exp_aliases.setdefault(stem, []).append(n["id"])
    import glob as _glob
    resolved = {}
    unresolved = []
    for n in nodes:
        for ev in n.get("evidence") or []:
            ref = ev.get("ref") or ""
            kind = ev.get("kind") or "?"
            ok = False
            if ref in by_id or ref in exp_aliases:
                ok = True
            elif "/" in ref and (ROOT / ref).exists():
                ok = True
            elif ref.startswith("FINDING-"):
                num = ref.split("-")[1] if "-" in ref else ""
                ok = bool(_glob.glob(str(ROOT / "docs" / ("FINDING-" + num + "*.md"))))
            if ok:
                resolved[kind] = resolved.get(kind, 0) + 1
            else:
                unresolved.append((n["id"], kind, ref))
    return resolved, unresolved

def invariants(nodes):
    problems = []
    ids = {n["id"] for n in nodes}
    if len(ids) != len(nodes):
        problems.append("duplicate ids")
    text_seen = {}
    for n in nodes:
        nid = n.get("id", "?")
        if n.get("kind") not in KINDS:
            problems.append(f"{nid}: kind {n.get('kind')!r}")
        if n.get("epistemic") not in EPISTEMIC:
            problems.append(f"{nid}: bad epistemic")
        if n.get("provenance") not in PROVENANCE:
            problems.append(f"{nid}: bad provenance")
        if not n.get("context"):
            problems.append(f"{nid}: empty context")
        if n.get("epistemic") == "established" and not n.get("evidence"):
            problems.append(f"{nid}: established without evidence")
        if n.get("epistemic") == "established" and n.get("provenance") == "extracted":
            problems.append(f"{nid}: established but only extracted")
        if n.get("kind") == "formula":
            math = n.get("math") or {}
            checked = (math.get("checked") or {}).get("kind", "none")
            if checked != "none" and not math.get("units"):
                problems.append(f"{nid}: checked formula without units")
        for r in n.get("relations", []):
            if r.get("type") not in RELATIONS:
                problems.append(f"{nid}: relation {r.get('type')!r}")
            if str(r.get("target", "")).startswith(("C-", "F-")) and r["target"] not in ids:
                problems.append(f"{nid}: dangling relation -> {r['target']}")
        key = n.get("text", "")[:80]
        if key:
            if key in text_seen and n.get("kind") == "claim":
                problems.append(f"{nid}: duplicate text with {text_seen[key]}")
            text_seen.setdefault(key, nid)
    refuted = {n["id"] for n in nodes if n.get("epistemic") == "refuted"}
    for n in nodes:
        for r in n.get("relations", []):
            if r.get("type") == "supports" and r.get("target") in refuted:
                problems.append(f"{n['id']}: supports a refuted node {r['target']}")
    return problems


def build(nodes):
    problems = invariants(nodes)
    if problems:
        print("INVARIANT VIOLATIONS:")
        for p in problems:
            print("  ", p)
        return 1
    kinds = Counter(n["kind"] for n in nodes)
    epistemic = Counter(n["epistemic"] for n in nodes)
    provenance = Counter(n["provenance"] for n in nodes)
    edges = [{"from": n["id"], "to": r["target"], "type": r["type"]}
             for n in nodes for r in n.get("relations", [])]
    refuted = {m["id"] for m in nodes if m["epistemic"] == "refuted"}
    refuted_referenced = sorted({r["target"] for n in nodes for r in n.get("relations", [])
                                 if r["type"] in ("supports", "extends", "qualifies")
                                 and r["target"] in refuted})
    frontier = {
        "without_evidence": sorted(n["id"] for n in nodes if not n.get("evidence")),
        "extracted_only": sorted(n["id"] for n in nodes if n.get("provenance") == "extracted"),
        "refuted_still_referenced": refuted_referenced,
        "contested": sorted(n["id"] for n in nodes if n.get("epistemic") == "contested"),
    }
    communities = [
        {"id": "K1", "label": "цена и бюджет", "hubs": ["C-001", "C-002"]},
        {"id": "K2", "label": "замыкание и выживание", "hubs": ["C-003", "C-006", "F-022", "F-024"]},
        {"id": "K3", "label": "порог и его форма", "hubs": ["C-005", "C-007", "F-003", "F-029"]},
        {"id": "K4", "label": "формулы", "hubs": sorted(n["id"] for n in nodes if n["kind"] == "formula")[:5]},
        {"id": "K5", "label": "прогоны", "hubs": sorted(n["id"] for n in nodes if n["kind"] == "experiment")[:5]},
    ]
    meta = {
        "schema": "kg/2",
        "built_at": "2026-11-20",
        "counts": {"total": len(nodes), "by_kind": dict(kinds), "by_epistemic": dict(epistemic),
                   "by_provenance": dict(provenance), "edges": len(edges)},
        "invariants": [
            "every node has non-empty context",
            "established implies at least one evidence item",
            "established cannot have provenance=extracted",
            "a checked formula declares units for its symbols",
            "no dangling C-/F- references",
            "ids are unique",
            "claims do not repeat another claim's text",
            "a refuted node is never the target of supports",
        ],
        "communities": communities,
        "frontier": frontier,
        "verbs": ["map", "find", "show", "expand", "trace", "chain", "formula", "contradictions", "check"],
        "hashes": {"graph": hashlib.sha256(json.dumps(nodes, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]},
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    GRAPH.write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# kg/INDEX.md — карта графа (генерируется)", "",
             f"узлов: **{len(nodes)}**, рёбер: **{len(edges)}**", "",
             "| kind | сколько |", "|---|---|"]
    for k, v in sorted(kinds.items()):
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Фронтир", "",
              f"- без свидетельств: **{len(frontier['without_evidence'])}**",
              f"- только извлечено: **{len(frontier['extracted_only'])}**",
              f"- опровергнуто, но цитируется: **{len(refuted_referenced)}**",
              "", "## Глаголы", "",
              ", ".join(meta["verbs"]), ""]
    INDEX.write_text("\n".join(lines), encoding="utf-8")
    print(f"built: {len(nodes)} nodes, {len(edges)} edges")
    print("by kind:", dict(kinds))
    print("frontier:", {k: len(v) for k, v in frontier.items()})
    return 0


def refs_report(nodes, strict):
    resolved, unresolved = resolve_refs(nodes)
    print("ссылки свидетельств: разрешено " + str(sum(resolved.values())) + ", не разрешено " + str(len(unresolved)))
    for kind, count in sorted(resolved.items()):
        print("  ok        " + kind + ": " + str(count))
    for nid, kind, ref in unresolved[:15]:
        print("  висит     " + nid + " -> " + kind + ":" + ref)
    if len(unresolved) > 15:
        print("  ... ещё " + str(len(unresolved) - 15))
    if strict and unresolved:
        print("FAIL: " + str(len(unresolved)) + " ссылок не разрешаются")
        return 1
    if unresolved:
        print("NOTE: ссылки выше -- дыры в графе; строгий режим: kg.py check --refs")
    return 0

def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    nodes = load()
    by_id = {n["id"]: n for n in nodes}
    cmd = argv[1]

    if cmd == "build":
        return build(nodes)

    if cmd == "check":
        strict_refs = "--refs" in argv
        problems = invariants(nodes)
        print("OK" if not problems else "\n".join(problems))
        bad = refs_report(nodes, "--refs" in argv)
        if problems:
            return 1
        return 1 if bad else 0

    if cmd == "map":
        if not META.exists():
            print("no meta.json: run build")
            return 1
        meta = json.loads(META.read_text(encoding="utf-8"))
        print(f"nodes: {meta['counts']['total']}  edges: {meta['counts']['edges']}")
        print("by kind:", meta["counts"]["by_kind"])
        print("by epistemic:", meta["counts"]["by_epistemic"])
        print("frontier:", {k: len(v) for k, v in meta["frontier"].items()})
        print("communities:", [c["label"] for c in meta["communities"]])
        return 0

    if cmd == "find":
        needle = " ".join(argv[2:]).lower()
        hits = [n for n in nodes if needle in n.get("text", "").lower()]
        for n in hits[:20]:
            print(f"{n['id']} [{n['kind']}/{n['epistemic']}] {n['text'][:110]}")
        print(f"({len(hits)} hits)")
        return 0

    if cmd == "show":
        n = by_id.get(argv[2])
        if not n:
            print(f"{argv[2]}: not found")
            return 1
        print(json.dumps(n, ensure_ascii=False, indent=2))
        return 0

    if cmd == "expand":
        start = argv[2]
        hops = int(argv[3]) if len(argv) > 3 else 1
        seen = {start}
        frontier = {start}
        for _ in range(hops):
            nxt = set()
            for n in nodes:
                for r in n.get("relations", []):
                    if n["id"] in frontier:
                        nxt.add(r["target"])
                    if r["target"] in frontier:
                        nxt.add(n["id"])
                for e in n.get("evidence", []):
                    ref = str(e.get("ref", ""))
                    if ref in frontier:
                        nxt.add(n["id"])
                    if n["id"] in frontier and ref.startswith(("C-", "F-", "X-")):
                        nxt.add(ref)
            frontier = nxt - seen
            seen |= nxt
        for i in sorted(seen):
            n = by_id.get(i)
            if n:
                print(f"{i} [{n['kind']}/{n['epistemic']}] {n['text'][:100]}")
        return 0

    if cmd == "trace":
        n = by_id.get(argv[2])
        if not n:
            print(f"{argv[2]}: not found")
            return 1
        print(f"{n['id']}: {n['text']}")
        for e in n.get("evidence", []):
            print(f"  evidence [{e['kind']}] {e['ref']} ({e.get('strength', '?')})")
        return 0

    if cmd == "chain":
        n = by_id.get(argv[2])
        if not n:
            print(f"{argv[2]}: not found")
            return 1
        print(f"claim  {n['id']}: {n['text']}")
        for e in n.get("evidence", []):
            print(f"-> {e['kind']:12} {e['ref']}")
            m = by_id.get(str(e["ref"]))
            if m:
                for e2 in m.get("evidence", []):
                    print(f"   -> {e2['kind']:10} {e2['ref']}")
        return 0

    if cmd == "formula":
        n = by_id.get(argv[2])
        if not n or n.get("kind") != "formula":
            print(f"{argv[2]}: not a formula node")
            return 1
        math = n.get("math", {})
        print(f"{n['id']}: {n['text']}")
        print("latex:", (math.get("latex") or "").splitlines()[:3])
        print("units:", math.get("units"))
        print("checked:", math.get("checked"))
        return 0

    if cmd == "contradictions":
        found = False
        for n in nodes:
            for r in n.get("relations", []):
                if r["type"] == "refutes":
                    found = True
                    print(f"REFUTES {n['id']} -> {r['target']}: {n['text'][:90]}")
        for n in nodes:
            if n["epistemic"] == "refuted":
                found = True
                print(f"REFUTED {n['id']}: {n['text'][:100]}")
        if not found:
            print("no contradictions recorded")
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
