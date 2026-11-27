#!/usr/bin/env python3
"""Regression tests for result role/phase metadata."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "checks"))
import result as result_module
import contract as contract_module


class ResultDesignTests(unittest.TestCase):
    def fixture(self, schema: str, role=None, phase=None):
        data = {
            "schema": schema,
            "arithmetic": {"threshold": 1.0},
            "controls": {name: {"passed": True} for name in contract_module.CONTROL_TESTS},
            "verdict": {"kind": "passed", "reason": "synthetic fixture"},
            "hashes": {"A": "a", "B": "b", "C": "c"},
            "limitations": ["synthetic fixture"],
        }
        if role is not None:
            data["role"] = role
        if phase is not None:
            data["phase"] = phase
        return data

    def test_new_result_defaults_to_verification_exploratory(self):
        item = result_module.new_result("TEST-DESIGN", 1, {}, "selftest")
        self.assertEqual(item["schema"], "marfagenez.experiment-result.v3")
        self.assertEqual((item["role"], item["phase"]), ("verification", "exploratory"))

    def test_verification_confirmatory_is_allowed(self):
        item = result_module.new_result(
            "TEST-DESIGN", 1, {}, "selftest",
            role="verification", phase="confirmatory",
        )
        self.assertEqual((item["role"], item["phase"]), ("verification", "confirmatory"))

    def test_validation_confirmatory_is_rejected_by_constructor(self):
        with self.assertRaises(ValueError):
            result_module.new_result(
                "TEST-DESIGN", 1, {}, "selftest",
                role="validation", phase="confirmatory",
            )

    def test_invalid_enums_are_rejected(self):
        with self.assertRaises(ValueError):
            result_module.new_result("X", 1, {}, "test", role="unknown", phase="exploratory")
        with self.assertRaises(ValueError):
            result_module.new_result("X", 1, {}, "test", role="verification", phase="pilot")

    def test_contract_accepts_valid_v3(self):
        problems = contract_module.check_one(
            Path("valid.json"),
            self.fixture("marfagenez.experiment-result.v3", "verification", "confirmatory"),
        )
        self.assertFalse(any("§3:" in p for p in problems))

    def test_contract_rejects_missing_v3_role_or_phase(self):
        for data in (
            self.fixture("marfagenez.experiment-result.v3", None, "exploratory"),
            self.fixture("marfagenez.experiment-result.v3", "verification", None),
        ):
            problems = contract_module.check_one(Path("missing.json"), data)
            self.assertTrue(any("§3:" in p for p in problems))

    def test_contract_rejects_validation_confirmatory(self):
        data = self.fixture("marfagenez.experiment-result.v3", "validation", "confirmatory")
        problems = contract_module.check_one(Path("invalid.json"), data)
        self.assertTrue(any("validation cannot be confirmatory" in p for p in problems))

    def test_legacy_v2_is_not_forced_to_have_role_phase(self):
        data = self.fixture("marfagenez.experiment-result.v2")
        problems = contract_module.check_one(Path("legacy.json"), data)
        self.assertFalse(any("§3:" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
