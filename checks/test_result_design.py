#!/usr/bin/env python3
"""Regression tests for result role/phase metadata."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
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


    def test_new_result_persists_question(self):
        item = result_module.new_result(
            "TEST-QUESTION", 1, {}, "selftest",
            question="Which boundary decides survival?",
        )
        self.assertEqual(item["question"], "Which boundary decides survival?")

    def test_legacy_new_result_without_question_keeps_legacy_fingerprint_shape(self):
        item = result_module.new_result("TEST-LEGACY-QUESTION", 1, {}, "selftest")
        self.assertNotIn("question", item)

    def test_experiment_persists_its_required_question(self):
        from checks.experiment import Experiment, ExperimentError
        item = Experiment(
            experiment_id="TEST-QUESTION",
            question="Does repair capacity set the survival boundary?",
            arithmetic={"threshold": 1.0},
            arms={"A": "control"},
            seed=7,
            command="selftest",
        )
        self.assertEqual(
            item.result["question"],
            "Does repair capacity set the survival boundary?",
        )
        with self.assertRaises(ExperimentError):
            Experiment(
                experiment_id="TEST-EMPTY-QUESTION", question=" ",
                arithmetic={"threshold": 1.0}, arms={"A": "control"},
                seed=7, command="selftest",
            )

    def test_run_ids_are_unique_even_within_one_second(self):
        first = result_module.new_result("TEST-RUN-ID", 1, {}, "selftest")
        second = result_module.new_result("TEST-RUN-ID", 1, {}, "selftest")
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_save_does_not_overwrite_a_colliding_run_id(self):
        with tempfile.TemporaryDirectory(prefix="result-identity-") as directory:
            with patch.object(result_module, "RESULTS_DIR", Path(directory)):
                with patch.object(result_module, "_git_state", return_value=("a" * 40, False)):
                    first = result_module.new_result(
                        "TEST-COLLISION", 1, {}, "selftest", question="first question"
                    )
                    first.update({
                        "run_id": "run-fixed-id",
                        "verdict": {"kind": "failed", "reason": "first"},
                        "limitations": ["synthetic"],
                    })
                    first_path = result_module.save(first)
                    first_bytes = first_path.read_bytes()

                    second = result_module.new_result(
                        "TEST-COLLISION", 1, {}, "selftest", question="second question"
                    )
                    second.update({
                        "run_id": "run-fixed-id",
                        "verdict": {"kind": "failed", "reason": "second"},
                        "limitations": ["synthetic"],
                    })
                    second_path = result_module.save(second)

                    self.assertNotEqual(first_path, second_path)
                    self.assertEqual(first_path.read_bytes(), first_bytes)
                    self.assertEqual(
                        json.loads(second_path.read_text(encoding="utf-8"))["question"],
                        "second question",
                    )
                    self.assertFalse(list(Path(directory).glob("*/*.tmp")))

    def test_question_participates_in_result_fingerprint(self):
        first = result_module.new_result(
            "TEST-FINGERPRINT", 1, {}, "selftest", question="question one"
        )
        second = result_module.new_result(
            "TEST-FINGERPRINT", 1, {}, "selftest", question="question two"
        )
        self.assertNotEqual(
            result_module._fingerprint(first),
            result_module._fingerprint(second),
        )

    def test_result_identifiers_reject_path_traversal(self):
        for identifier in ("../escape", "/absolute", "sub/path", ".."):
            with self.assertRaises(ValueError):
                result_module.new_result(identifier, 1, {}, "selftest")

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
