#!/usr/bin/env python3
"""Fail when newly introduced established KG nodes have no graph edges.

The 511 IDs in kg/legacy-isolated.json are a frozen exception list from the
master snapshot recorded in that file. New work cannot enlarge it implicitly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "kg"


def check(nodes, graph, allowlist):
    problems = []
    ids = {node.get("id") for node in nodes}
    if len(ids) != len(nodes):
        problems.append("duplicate node IDs")
    degrees = {node_id: 0 for node_id in ids}
    for edge in graph.get("edges", []):
        src, dst = edge.get("from"), edge.get("to")
        if src not in ids or dst not in ids:
            problems.append(f"dangling graph edge {src!r} -> {dst!r}")
            continue
        degrees[src] += 1
        degrees[dst] += 1

    legacy = set(allowlist.get("ids", []))
    new_established = [
        node.get("id")
        for node in nodes
        if node.get("epistemic") == "established"
        and node.get("id") not in legacy
        and degrees.get(node.get("id"), 0) == 0
    ]
    for node_id in sorted(new_established):
        problems.append(f"new established node has no edges: {node_id}")

    return {
        "node_count": len(nodes),
        "edge_count": len(graph.get("edges", [])),
        "isolated_count": sum(value == 0 for value in degrees.values()),
        "legacy_isolated_allowlist_count": len(legacy),
        "new_established_isolated": sorted(new_established),
        "problems": problems,
    }


def main():
    nodes = [
        json.loads(line)
        for line in (KG / "nodes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    graph = json.loads((KG / "graph.json").read_text(encoding="utf-8"))
    allowlist = json.loads((KG / "legacy-isolated.json").read_text(encoding="utf-8"))
    report = check(nodes, graph, allowlist)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["problems"]:
        return 1
    print(
        f"OK: {report['node_count']} nodes, {report['edge_count']} edges, "
        f"{report['isolated_count']} isolated (legacy allowlist {report['legacy_isolated_allowlist_count']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
