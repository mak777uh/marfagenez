from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("mde_power.py")
SPEC = importlib.util.spec_from_file_location("mde_power", SCRIPT)
mde = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mde)


class MdePowerTests(unittest.TestCase):
    def test_synthetic_known_mde_for_eight_replicates(self):
        self.assertAlmostEqual(mde.proportion_mde(8, 0, 8), 0.7004, places=3)

    def test_more_replicates_reduce_mde_by_inverse_sqrt_n(self):
        m8 = mde.proportion_mde(8, 0, 8)
        m32 = mde.proportion_mde(32, 0, 32)
        self.assertAlmostEqual(m8 / m32, 2.0, places=8)

    def test_all_success_or_failure_still_has_positive_corrected_mde(self):
        self.assertGreater(mde.proportion_mde(20, 20, 20), 0.0)
        self.assertGreater(mde.proportion_mde(0, 0, 20), 0.0)

    def test_invalid_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            mde.proportion_mde(21, 0, 20)

    def test_repo_report_has_at_least_thirty_environments(self):
        report = mde.analyse()
        self.assertGreaterEqual(
            report["counts"]["protocol_capacity_paired_environments"], 30
        )
        self.assertEqual(
            report["counts"]["protocol_confirmed_nominal"]
            + report["counts"]["protocol_questionable_nominal"],
            report["counts"]["protocol_capacity_paired_environments"],
        )


if __name__ == "__main__":
    unittest.main()
