#!/usr/bin/env python3
"""Regression tests for v3 result role/phase semantics."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "checks"))
import result as result_module
import contract as contract_module


class ResultDesignTests(unittest.TestCase):
    def test_new_result_defaults_to_verification_exploratory(self):
        item = result_module.new_result("TEST-DESIGN", 1, {}, "selftest")
        self.assertEqual(item["schema"], "marfagenez.experiment-result.v3")
        self.assertEqual(item["role"], "verification")
        self.assertEqual(item["phase"], "exploratory")

    def test_explicit_verification_confirmatory_is_accepted(self):
        item = result_module.new_result(
            "TEST-DESIGN", 1, {}, "selftest",
            role="verification", phase="confirmatory",
        )
        self.assertEqual((item["role"], item["phase"]), ("verification", "confirmatory"))

    def test_invalid_values_are_rejected_by_constructor(self):
        with self.assertRaises(ValueError):
            result_module.new_result("X", 1, {}, "test", role="science", phase="exploratory")
        with self.assertRaises(ValueError):
            result_module.new_result("X", 1, {}, "test", role="verification", phase="pilot")

    def test_validation_confirmatory_is_rejected_by_constructor(self):
        with self.assertRaises(ValueError):
            result_module.new_result(
                "X", 1, {}, "test", role="validation", phase="confirmatory"
            )

    def test_contract_red_lines_validation_confirmatory(self):
        fixture = {
            "schema": contract_module.SCHEMA_V3,
            "role": "validation",
            "phase": "confirmatory",
            "arithmetic": {"threshold": 1},
            "controls": {n: {"passed": True} for n in contract_module.CONTROL_TESTS},
            "verdict": {"kind": "passed", "reason": "fixture"},
            "hashes": {"A": "a", "B": "b", "C": "c"},
            "limitations": ["fixture"],
        }
        problems = contract_module.check_one(Path("bad.json"), fixture)
        self.assertTrue(any("validation cannot be confirmatory" in p for p in problems))

    def test_legacy_v2_is_not_rewritten_or_forced_to_have_role_phase(self):
        fixture = {
            "schema": contract_module.SCHEMA_V2,
            "arithmetic": {"threshold": 1},
            "controls": {n: {"passed": True} for n in contract_module.CONTROL_TESTS},
            "verdict": {"kind": "passed", "reason": "legacy"},
            "hashes": {"A": "a", "B": "b", "C": "c"},
            "limitations": ["legacy"],
        }
        problems = contract_module.check_one(Path("legacy.json"), fixture)
        self.assertFalse(any("§3:" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
