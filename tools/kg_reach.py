#!/usr/bin/env python3
"""Trace conclusion -> measurement -> data file -> code locator paths in the KG."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "kg"
REPORT = KG / "reachability-report.json"
DOC = ROOT / "docs" / "KG-REACHABILITY.md"
CONCLUSIONS = {"claim", "formula", "definition"}


def reachability(nodes, edges, legacy_ids=()):
    by_id = {node["id"]: node for node in nodes}
    outgoing = defaultdict(list)
    degree = Counter()
    for edge in edges:
        source, target = edge.get("from"), edge.get("to")
        if source in by_id and target in by_id:
            outgoing[source].append((edge.get("type", ""), target))
            degree[source] += 1
            degree[target] += 1
    legacy = set(legacy_ids)

    def has_source(node):
        for evidence in node.get("evidence") or []:
            if evidence.get("ref"):
                return True
        data = node.get("data") or {}
        return bool(data.get("source") or data.get("artifact"))

    rows = []
    for node in nodes:
        if node.get("kind") not in CONCLUSIONS:
            continue
        start = node["id"]
        initial_experiment = node.get("kind") == "experiment"
        queue = deque([(start, [start], False, initial_experiment)])
        seen_states = {(start, False, initial_experiment)}
        found = None
        unversioned_path = None
        while queue:
            current, path, has_measurement, has_experiment = queue.popleft()
            current_data = by_id[current].get("data") or {}
            artifact_type = current_data.get("artifact_type")
            has_measurement = has_measurement or artifact_type == "result_record"
            has_experiment = has_experiment or by_id[current].get("kind") == "experiment"
            if artifact_type == "code_locator" and has_measurement and has_experiment:
                if current_data.get("version_pinned") is True:
                    found = path
                    break
                unversioned_path = unversioned_path or path
            for edge_type, target in outgoing.get(current, []):
                state = (
                    target,
                    has_measurement,
                    has_experiment or by_id[target].get("kind") == "experiment",
                )
                if state not in seen_states:
                    seen_states.add(state)
                    queue.append((target, path + [target], state[1], state[2]))
        if found:
            status = "reachable"
        elif unversioned_path:
            status = "unversioned-code"
        elif has_source(node):
            # a conclusion that names a source is a repair job (materialise the
            # edge), not an orphan; report it as no-link even without edges.
            status = "no-link"
        elif degree.get(start, 0) == 0:
            status = "new-isolated" if start not in legacy else "isolated"
        else:
            status = "no-source"
        rows.append({
            "id": start,
            "text": node.get("text", ""),
            "epistemic": node.get("epistemic"),
            "status": status,
            "path": found or unversioned_path or [],
            "degree": degree.get(start, 0),
        })

    all_isolated = sorted(node_id for node_id in by_id if degree.get(node_id, 0) == 0)
    old_isolated = sorted(set(all_isolated) & legacy)
    new_isolated = sorted(set(all_isolated) - legacy)
    counts = Counter(row["status"] for row in rows)
    return {
        "schema": "marfagenez.kg-reachability.v1",
        "scope": "claim, formula and definition nodes; directed path to result data and code",
        "graph_node_count": len(nodes),
        "graph_edge_count": len(edges),
        "isolated_count": len(all_isolated),
        "legacy_isolated_still_isolated": len(old_isolated),
        "new_isolated_count": len(new_isolated),
        "baseline_isolated_count": len(legacy),
        "isolation_delta_vs_baseline": len(all_isolated) - len(legacy),
        "conclusion_count": len(rows),
        "counts": dict(sorted(counts.items())),
        "rows": rows,
    }


def markdown(report):
    lines = [
        "# KG reachability audit",
        "",
        f"Conclusion nodes checked: {report['conclusion_count']}.",
        "",
        "| Graph measure | Count |",
        "|---|---:|",
        f"| Nodes after rebuild | {report['graph_node_count']} |",
        f"| Edges after rebuild | {report['graph_edge_count']} |",
        f"| Isolated before (frozen baseline) | {report['baseline_isolated_count']} |",
        f"| Isolated after rebuild | {report['isolated_count']} |",
        f"| Baseline isolates still isolated | {report['legacy_isolated_still_isolated']} |",
        f"| New isolates | {report['new_isolated_count']} |",
        f"| Change vs baseline | {report['isolation_delta_vs_baseline']:+d} |",
        "",
        "| Conclusion-path status | Nodes |",
        "|---|---:|",
    ]
    for status, count in report["counts"].items():
        lines.append(f"| {status} | {count} |")
    lines += [
        "",
        "A node is reachable only if a directed path reaches an experiment, its result-data",
        "artifact, and then a code source/commit locator. Literature-only evidence does not",
        "count as an experimental code path. Isolated is a baseline orphan; new-isolated is",
        "a new conclusion node with no incident edge; no-source and no-link identify separate",
        "repair jobs. The audit never treats a mechanically linked artifact as scientific support.",
        "",
        "Reproduce after python3 kg/migrate.py and python3 kg/kg.py build:",
        "",
        "    python3 tools/kg_reach.py --write",
        "    python3 checks/kg_edges.py",
        "    python3 -m unittest checks.test_kg_reach",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    nodes = [
        json.loads(line)
        for line in (KG / "nodes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    graph = json.loads((KG / "graph.json").read_text(encoding="utf-8"))
    baseline = json.loads((KG / "legacy-isolated.json").read_text(encoding="utf-8"))
    report = reachability(nodes, graph.get("edges", []), baseline.get("ids", []))
    rendered = markdown(report)
    if args.write:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        DOC.write_text(rendered, encoding="utf-8")
        print(f"wrote {REPORT.relative_to(ROOT)} and {DOC.relative_to(ROOT)}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
