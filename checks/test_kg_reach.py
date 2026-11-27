from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "kg_reach.py"
SPEC = importlib.util.spec_from_file_location("kg_reach", SCRIPT)
reach = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(reach)


class ReachabilityTests(unittest.TestCase):
    def node(self, node_id, kind, evidence=None, artifact_type=None):
        data = {"artifact_type": artifact_type} if artifact_type else {}
        return {
            "id": node_id,
            "kind": kind,
            "text": node_id,
            "epistemic": "established",
            "evidence": evidence or [],
            "data": data,
        }

    def test_full_conclusion_measurement_data_code_chain(self):
        nodes = [
            self.node("C-1", "claim", [{"kind": "experiment", "ref": "X-1"}]),
            self.node("X-1", "experiment"),
            self.node("D-1", "evidence", artifact_type="result_record"),
            self.node("CODE-1", "evidence", artifact_type="code_locator"),
        ]
        nodes[-1]["data"]["version_pinned"] = True
        edges = [
            {"from": "C-1", "to": "X-1", "type": "tested_in"},
            {"from": "X-1", "to": "D-1", "type": "has_data"},
            {"from": "D-1", "to": "CODE-1", "type": "generated_by"},
        ]
        report = reach.reachability(nodes, edges)
        self.assertEqual(report["rows"][0]["status"], "reachable")
        self.assertEqual(report["rows"][0]["path"], ["C-1", "X-1", "D-1", "CODE-1"])

    def test_unversioned_command_path_is_not_full_reachability(self):
        nodes = [
            self.node("C-1", "claim", [{"kind": "experiment", "ref": "X-1"}]),
            self.node("X-1", "experiment"),
            self.node("D-1", "evidence", artifact_type="result_record"),
            self.node("CODE-1", "evidence", artifact_type="code_locator"),
        ]
        nodes[-1]["data"]["version_pinned"] = False
        edges = [
            {"from": "C-1", "to": "X-1", "type": "tested_in"},
            {"from": "X-1", "to": "D-1", "type": "has_data"},
            {"from": "D-1", "to": "CODE-1", "type": "generated_by"},
        ]
        report = reach.reachability(nodes, edges)
        self.assertEqual(report["rows"][0]["status"], "unversioned-code")

    def test_legacy_isolated_node_is_distinguished(self):
        nodes = [self.node("C-legacy", "claim")]
        report = reach.reachability(nodes, [], legacy_ids=["C-legacy"])
        self.assertEqual(report["rows"][0]["status"], "isolated")

    def test_new_isolated_node_is_distinguished(self):
        nodes = [self.node("C-new", "claim")]
        report = reach.reachability(nodes, [])
        self.assertEqual(report["rows"][0]["status"], "new-isolated")

    def test_source_without_directed_path_is_no_link(self):
        nodes = [self.node("C-source", "claim", [{"kind": "paper", "ref": "paper.pdf"}])]
        report = reach.reachability(nodes, [])
        self.assertEqual(report["rows"][0]["status"], "no-link")

    def test_node_without_source_but_with_incident_edge_is_no_source(self):
        nodes = [
            self.node("C-no-source", "claim"),
            self.node("L-1", "claim"),
        ]
        edges = [{"from": "C-no-source", "to": "L-1", "type": "derived_from"}]
        report = reach.reachability(nodes, edges)
        self.assertEqual(report["rows"][0]["status"], "no-source")


if __name__ == "__main__":
    unittest.main()
