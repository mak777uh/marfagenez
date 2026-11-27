"""Focused regression tests for result model_commit pinning.

Run through checks/contract.py (part of run.sh exp), or directly with
`python3 checks/result_commit_test.py`.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import result


def run() -> list[str]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="result-commit-pin-") as tmp:
        target = Path(tmp) / "results"
        with patch.object(result, "RESULTS_DIR", target):
            # save() must overwrite caller metadata with the actual current HEAD.
            with patch.object(result, "_git_state", return_value=("a" * 40, False)):
                clean = result.new_result("PIN-CLEAN", 1, {}, "selftest")
                clean["model_commit"] = "caller-supplied-wrong-sha"
                path = result.save(clean)
                stored = json.loads(path.read_text(encoding="utf-8"))
                if stored.get("model_commit") != "a" * 40:
                    problems.append("clean save did not pin git rev-parse HEAD")

            # A dirty source snapshot is labelled and cannot produce verdict=passed.
            with patch.object(result, "_git_state", return_value=("b" * 40, True)):
                dirty_pass = result.new_result("PIN-DIRTY-PASS", 2, {}, "selftest")
                dirty_pass["verdict"] = {"kind": "passed", "reason": "must be refused"}
                try:
                    result.save(dirty_pass)
                except ValueError:
                    pass
                else:
                    problems.append("dirty working tree was allowed to save verdict=passed")

                dirty_failed = result.new_result("PIN-DIRTY-FAILED", 3, {}, "selftest")
                dirty_failed["verdict"] = {"kind": "failed", "reason": "not a passing claim"}
                path = result.save(dirty_failed)
                stored = json.loads(path.read_text(encoding="utf-8"))
                if stored.get("model_commit") != ("b" * 40 + "+dirty"):
                    problems.append("dirty save did not write <HEAD>+dirty")

                # A dirty record must not fingerprint-identify with a clean record.
                clean_record = dict(stored, model_commit="b" * 40)
                if result._fingerprint(clean_record) == result._fingerprint(stored):
                    problems.append("dirty record fingerprint collapsed into a clean record")

    return problems


if __name__ == "__main__":
    errors = run()
    if errors:
        for error in errors:
            print("FAIL:", error)
        raise SystemExit(1)
    print("OK: model_commit pinning and dirty-pass refusal")
