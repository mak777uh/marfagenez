from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("kg_edges.py")
SPEC = importlib.util.spec_from_file_location("kg_edges", SCRIPT)
kg_edges = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(kg_edges)


class KgEdgeGateTests(unittest.TestCase):
    def node(self, node_id, epistemic="established"):
        return {"id": node_id, "epistemic": epistemic}

    def test_frozen_legacy_orphan_is_allowed(self):
        report = kg_edges.check(
            [self.node("C-old")],
            {"edges": []},
            {"ids": ["C-old"], "baseline_isolated_count": 1},
        )
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["isolated_count"], 1)

    def test_new_established_orphan_is_a_failure(self):
        report = kg_edges.check(
            [self.node("C-new")],
            {"edges": []},
            {"ids": [], "baseline_isolated_count": 0},
        )
        self.assertTrue(any("new established node has no edges" in p for p in report["problems"]))

    def test_dangling_edge_is_a_failure(self):
        report = kg_edges.check(
            [self.node("C-live")],
            {"edges": [{"from": "C-live", "to": "MISSING"}]},
            {"ids": [], "baseline_isolated_count": 0},
        )
        self.assertTrue(any("dangling graph edge" in p for p in report["problems"]))

    def test_allowlist_cannot_be_extended_without_metadata_change(self):
        report = kg_edges.check(
            [self.node("C-old"), self.node("C-new")],
            {"edges": []},
            {"ids": ["C-old", "C-new"], "baseline_isolated_count": 1},
        )
        self.assertTrue(any("allowlist size differs" in p for p in report["problems"]))


if __name__ == "__main__":
    unittest.main()
