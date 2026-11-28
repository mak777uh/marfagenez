#!/usr/bin/env python3
"""Synthetic contract tests for the EXP-2026-4106 analyzer."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import we_analyze as wa


IDENTITY = {
    "task_id": wa.TASK_ID,
    "task_version": 6,
    "task_version_sha256": "a" * 64,
    "base_commit": "b" * 40,
    "task_payload_sha256": "c" * 64,
}
GRID = wa.Grid(primary_count=2, deferred_count=2, pairs=4, horizon=1000)


def event_hash(row: dict) -> str:
    return wa.compute_state_hash(
        row["qA_event"], row["dA_event"], row["eA_event"], row["wearA_after"],
        row["qB_event"], row["dB_event"], row["eB_event"], row["wearB_after"],
    )


def make_row(cell: str, cohort: str, seed: int, pair: int, grid: wa.Grid,
             p3_delta: int = 100, break_silent: bool = False,
             no_wear: bool = False, unidentified: bool = False) -> dict:
    base_a = [600, 700, 800, 900]
    base_b = [650, 750, 850, 950]
    erase221_a = [321, 421, 521, 621]
    t_erase = 0
    status = "not_scheduled"
    applied = 0
    wear_before = 0.2
    wear_after = 0.2
    if cell == "base":
        life_a, life_b = base_a[pair], base_b[pair]
        if unidentified:
            life_b, cens_b = grid.horizon, 1
        else:
            cens_b = 0
        cens_a = 0
    elif cell == "sham600":
        life_a, life_b, cens_a, cens_b = base_a[pair], base_b[pair], 0, 0
        t_erase, status, wear_before, wear_after = 600, "sham", 0.3, 0.3
    elif cell == "erase600":
        life_a = life_b = base_a[pair]
        cens_a = cens_b = 0
        t_erase, status, applied = 600, "applied", 1
        wear_before, wear_after = (0.0 if no_wear else 0.3), 0.0
    elif cell == "erase221":
        life_a = erase221_a[pair]
        life_b = life_a - p3_delta
        cens_a = cens_b = 0
        t_erase, status, applied = 221, "applied", 1
        wear_before, wear_after = (0.0 if no_wear else 0.24), 0.0
    elif cell == "erand":
        t_erase = [600, 700, 800, 900][pair]
        life_a = life_b = t_erase
        cens_a = cens_b = 0
        status, applied = "applied", 1
        wear_before, wear_after = (0.0 if no_wear else 0.3), 0.0
    elif cell == "silent":
        life_a = base_a[pair]
        life_b = life_a + (10 if break_silent else 0)
        cens_a = cens_b = 0
        wear_before = wear_after = 0.3
    else:
        raise AssertionError(cell)
    row = {
        "cell": cell, "cohort": cohort, "seed": seed, "pair": pair,
        "t_erase": t_erase, "event_status": status, "applied": applied,
        "wearA_before": wear_before, "wearA_after": wear_after,
        "wearB_before": 0.0, "wearB_after": 0.0,
        "qA_event": 0.5, "dA_event": 0.4, "eA_event": 0.8,
        "qB_event": 0.5, "dB_event": 0.4, "eB_event": 0.8,
        "state_hash": "", "lifeA": life_a, "censA": cens_a,
        "lifeB": life_b, "censB": cens_b,
    }
    row["state_hash"] = event_hash(row)
    return row


def write_raw(path: Path, cohort: str, grid: wa.Grid, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [make_row(cell, cohort, seed, pair, grid, **kwargs)
            for cell in wa.CELLS for seed in grid.seeds(cohort)
            for pair in range(grid.pairs)]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=wa.HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path, raw_path: Path, cohort: str, grid: wa.Grid) -> None:
    manifest = {
        "schema": wa.RUN_SCHEMA, "cohort": cohort, **IDENTITY,
        "driver_rcs": {cohort: 0},
        "argv": {cohort: grid.expected_argv(cohort)},
        "driver": {"sha256": "d" * 64, "source_sha256": "e" * 64},
        "cohorts": {cohort: {"raw_csv": {
            "rows": grid.expected_rows(cohort), "sha256": wa.sha256_file(raw_path),
        }}},
    }
    path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")


def write_fixture(root: Path, **kwargs) -> tuple[Path, Path, Path, Path]:
    primary_raw = root / "primary" / "raw.csv"
    deferred_raw = root / "deferred" / "raw.csv"
    primary_manifest = root / "primary" / "raw-manifest.json"
    deferred_manifest = root / "deferred" / "raw-manifest.json"
    write_raw(primary_raw, "primary", GRID, **kwargs)
    write_raw(deferred_raw, "deferred", GRID, **kwargs)
    write_manifest(primary_manifest, primary_raw, "primary", GRID)
    write_manifest(deferred_manifest, deferred_raw, "deferred", GRID)
    return primary_raw, primary_manifest, deferred_raw, deferred_manifest


class AnalyzerTests(unittest.TestCase):
    def test_fnv1a64_known_vector(self) -> None:
        value = wa.FNV_OFFSET
        for byte in b"hello":
            value ^= byte
            value = (value * wa.FNV_PRIME) & wa.MASK64
        self.assertEqual(value, 0xA430D84680AABD0B)

    def test_exact_contract_and_state_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.csv"
            write_raw(raw, "primary", GRID)
            validation = wa.validate_raw(raw, "primary", GRID)
            self.assertEqual(validation.row_count, GRID.expected_rows("primary"))
            self.assertEqual(validation.errors, [])
            self.assertTrue(all(validation.controls.values()))

            with raw.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["state_hash"] = "0" * 16
            with raw.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=wa.HEADER, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            tampered = wa.validate_raw(raw, "primary", GRID)
            self.assertFalse(tampered.controls["state_hash"])

    def test_not_due_death_is_valid_when_either_arm_dies_first(self) -> None:
        row = {
            "cell": "erase600", "event_status": "not_due_death", "applied": 0,
            "t_erase": 600, "lifeA": 1000, "censA": 1,
            "lifeB": 500, "censB": 0,
            "wearA_before": 0.3, "wearA_after": 0.3,
            "wearB_before": 0.0, "wearB_after": 0.0,
        }
        self.assertEqual(wa._ledger_errors(row, GRID), [])

    def test_km_ties_and_no_horizon_substitution(self) -> None:
        curve = wa.km_curve([(100, [0], [1]), (200, [1], [])])
        self.assertEqual(wa.km_quantile(curve, 0.10), 200.0)
        unresolved = wa.km_curve([(100, [0], []), (1000, [], [1])])
        self.assertIsNone(wa.km_quantile(unresolved, 0.10))

    def test_p6_separates_survival_from_conditional_collapse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.csv"
            write_raw(raw, "primary", GRID)
            groups = wa.build_groups(wa.validate_raw(raw, "primary", GRID).records)
            row = groups["primary"]["erand"][GRID.primary_seed_base][0]
            row.update(lifeB=500, censB=0, event_status="not_due_death", applied=0,
                       wearA_after=row["wearA_before"])
            landmarks = wa._landmark_rows(groups, "primary", GRID)
            survived = next(x for x in landmarks
                            if x["dimension"] == "survival_to_erase" and x["stratum"] == "1")
            died = next(x for x in landmarks
                        if x["dimension"] == "survival_to_erase" and x["stratum"] == "0")
            self.assertEqual((survived["scheduled_n"], survived["applied_n"],
                              survived["collapsed_among_applied_n"]), (7, 7, 7))
            self.assertEqual((died["scheduled_n"], died["applied_n"]), (1, 0))
            self.assertNotIn("unconditional_collapse_fraction", survived)

    def test_descriptive_unidentified_t90_does_not_void_inference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.csv"
            write_raw(raw, "primary", GRID)
            with raw.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                if row["cell"] == "silent":
                    row["lifeA"] = row["lifeB"] = str(GRID.horizon)
                    row["censA"] = row["censB"] = "1"
            with raw.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=wa.HEADER, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            validation = wa.validate_raw(raw, "primary", GRID)
            result = wa.analyze_cohort(validation, [], "primary", GRID, draws=40,
                                       bootstrap_seed=wa.BOOTSTRAP_SEED)
            self.assertTrue(result["controls"]["T90_identifiable"])
            self.assertIsNone(result["mean_delta_t90"]["silent"])
            self.assertEqual(result["bootstrap"]["status"], "identified")
            self.assertEqual(wa._decision(result)[0], "passed")

    def test_draft_task_payload_cannot_be_executed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.json"
            path.write_text(json.dumps({
                "draft_only": True,
                "payload": {"schema": "task/v1", "id": wa.TASK_ID, "version": 6,
                            "task_version_sha256": "a" * 64, "base_commit": "b" * 40},
            }), encoding="utf-8")
            with self.assertRaises(wa.ContractError):
                wa.load_task_identity(path)

    def test_primary_p3_is_the_only_scientific_gate(self) -> None:
        result = {
            "controls": {"gate": True},
            "sensitivity": {"erase_event_changes_wear": True},
            "predictions": {
                "P3_erase221_primary": {"holds": True},
                "P2_erase600_shift": {"holds": False},
                "P5_base_replication": {"holds": False},
            },
        }
        self.assertEqual(wa._decision(result)[0], "passed")
        result["predictions"]["P3_erase221_primary"]["holds"] = False
        self.assertEqual(wa._decision(result)[0], "failed")

    def test_end_to_end_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture(root)
            summary = wa.run_analysis(*paths, root / "analysis", grid=GRID, draws=40,
                                      task_identity=IDENTITY)
            self.assertEqual(summary["scientific_outcome"], "passed", summary["reason"])
            self.assertTrue(summary["primary_decision"]["frozen_before_deferred"])
            self.assertEqual(summary["secondary_family"],
                             ["P2_erase600_shift", "P5_base_replication"])

    def test_negative_primary_is_failed_not_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture(root, p3_delta=-100)
            summary = wa.run_analysis(*paths, root / "analysis", grid=GRID, draws=40,
                                      task_identity=IDENTITY)
            self.assertEqual(summary["scientific_outcome"], "failed")
            self.assertFalse(summary["primary"]["predictions"]["P3_erase221_primary"]["holds"])

    def test_instrument_failure_is_void(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture(root, break_silent=True)
            summary = wa.run_analysis(*paths, root / "analysis", grid=GRID, draws=40,
                                      task_identity=IDENTITY)
            self.assertEqual(summary["scientific_outcome"], "void")
            self.assertFalse(summary["controls"]["silent_paired_life_identity"])

    def test_no_wear_change_is_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture(root, no_wear=True)
            summary = wa.run_analysis(*paths, root / "analysis", grid=GRID, draws=40,
                                      task_identity=IDENTITY)
            self.assertEqual(summary["scientific_outcome"], "insensitive_by_construction")
            self.assertEqual(summary["primary"]["bootstrap"]["status"], "not_run_insensitive")

    def test_unidentified_t90_is_void(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture(root, unidentified=True)
            summary = wa.run_analysis(*paths, root / "analysis", grid=GRID, draws=40,
                                      task_identity=IDENTITY)
            self.assertEqual(summary["scientific_outcome"], "void")
            self.assertFalse(summary["controls"]["T90_identifiable"])

    def test_missing_deferred_confirmation_is_void(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary_raw, primary_manifest, _deferred_raw, _deferred_manifest = write_fixture(root)
            summary = wa.run_analysis(primary_raw, primary_manifest, None, None,
                                      root / "analysis", grid=GRID, draws=40,
                                      task_identity=IDENTITY)
            self.assertEqual(summary["scientific_outcome"], "void")
            self.assertEqual(summary["decision_scope"], "primary_only")


    def test_short_base_commit_is_schema_compatible(self) -> None:
        self.assertIsNotNone(wa.COMMIT_RE.fullmatch("188dd76"))
        self.assertIsNone(wa.COMMIT_RE.fullmatch("188d"))

    def test_production_bootstrap_contract_is_fixed(self) -> None:
        summary = {"bootstrap": {"draws": wa.BOOTSTRAP_DRAWS,
                                  "primary_seed": wa.BOOTSTRAP_SEED,
                                  "deferred_seed": wa.DEFERRED_BOOTSTRAP_SEED},
                   "primary": {"bootstrap": {"draws": wa.BOOTSTRAP_DRAWS,
                                              "seed": wa.BOOTSTRAP_SEED}},
                   "deferred": {"status": "not_analyzed"}}
        wa.validate_bootstrap_contract(summary)
        summary["bootstrap"]["draws"] = 1
        with self.assertRaises(wa.ContractError):
            wa.validate_bootstrap_contract(summary)

    def test_root_manifest_cross_checks_both_cohorts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary_raw, primary_manifest, deferred_raw, deferred_manifest = write_fixture(root)
            manifests = {
                "primary": json.loads(primary_manifest.read_text(encoding="utf-8")),
                "deferred": json.loads(deferred_manifest.read_text(encoding="utf-8")),
            }
            environment = {"driver_sha256": "d" * 64, "driver_source_sha256": "e" * 64}
            aggregate = {
                "schema": wa.RUN_SCHEMA, **IDENTITY,
                "driver": {"sha256": "d" * 64, "source_sha256": "e" * 64},
                "driver_rcs": {"primary": 0, "deferred": 0},
                "argv": {cohort: GRID.expected_argv(cohort)
                         for cohort in ("primary", "deferred")},
                "grid": {"primary_seeds": GRID.primary_count,
                         "deferred_seeds": GRID.deferred_count,
                         "primary_seed_base": GRID.primary_seed_base,
                         "deferred_seed_base": GRID.deferred_seed_base,
                         "pairs": GRID.pairs, "horizon": GRID.horizon},
                "cohorts": json.loads(json.dumps({
                    cohort: manifests[cohort]["cohorts"][cohort]
                    for cohort in ("primary", "deferred")
                })),
            }
            self.assertEqual(wa.validate_root_manifest(
                aggregate, environment, manifests, IDENTITY, grid=GRID), [])
            aggregate["driver_rcs"]["deferred"] = 3
            aggregate["cohorts"]["primary"]["raw_csv"]["sha256"] = "0" * 64
            errors = wa.validate_root_manifest(
                aggregate, environment, manifests, IDENTITY, grid=GRID)
            self.assertTrue(any("return codes" in error for error in errors))
            self.assertTrue(any("cohort metadata mismatch" in error for error in errors))

    def test_task_contract_uses_spec_seed_grid(self) -> None:
        params = {
            "primary_seed_count": wa.PRIMARY_SEEDS,
            "deferred_seed_count": wa.DEFERRED_SEEDS,
            "primary_seed_base": wa.PRIMARY_SEED_BASE,
            "deferred_seed_base": wa.DEFERRED_SEED_BASE,
            "pairs_per_cell_seed": wa.PAIRS,
            "horizon": wa.HORIZON,
            "bootstrap_draws": wa.BOOTSTRAP_DRAWS,
            "primary_bootstrap_seed": wa.BOOTSTRAP_SEED,
            "deferred_bootstrap_seed": wa.DEFERRED_BOOTSTRAP_SEED,
        }
        seeds = list(wa.PRODUCTION_GRID.seeds("primary") + wa.PRODUCTION_GRID.seeds("deferred"))
        wa.validate_task_contract({"spec": {"parameters": params, "seeds": seeds}})
        with self.assertRaisesRegex(wa.ContractError, "task seeds"):
            wa.validate_task_contract({"spec": {"parameters": params, "seeds": seeds[:-1]}})

    def test_logical_artifact_paths_match_write_scope_contract(self) -> None:
        scopes = [f"results/experiments/{wa.TASK_ID}/**", wa.FINDING_PATH]
        cases = {
            "run/primary/raw.csv": f"results/experiments/{wa.TASK_ID}/primary/raw.csv",
            "run/deferred/raw.csv": f"results/experiments/{wa.TASK_ID}/deferred/raw.csv",
            "analysis/summary.json": f"results/experiments/{wa.TASK_ID}/analysis/summary.json",
            f"FINDING-{wa.TASK_ID}.md": wa.FINDING_PATH,
        }
        for staged, logical in cases.items():
            self.assertEqual(wa.logical_artifact_path(staged), logical)
            self.assertTrue(wa.path_in_write_scope(logical, scopes))
        self.assertFalse(wa.path_in_write_scope("run/primary/raw.csv", scopes))
        with self.assertRaises(wa.ContractError):
            wa.path_in_write_scope("../escape", scopes)

    def test_cli_has_no_unregistered_draw_override(self) -> None:
        parser = wa.build_parser()
        self.assertNotIn("--draws", {option for action in parser._actions for option in action.option_strings})


if __name__ == "__main__":
    unittest.main()
