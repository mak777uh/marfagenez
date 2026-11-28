#!/usr/bin/env python3
"""Validate and analyze the two-execution deterministic EXP-2026-4107 contract.

Scientific predictions are evaluated only after every instrument control passes.
A broken control, death/censoring anomaly, non-repeatable run, or non-finite metric
makes the result void; driver exit 3 is insensitive_by_construction.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
from typing import Any

ANALYZER_VERSION = "b-unit-analyze-2.0.0"
TASK_ID = "EXP-2026-4107"
REGISTERED_SEEDS = 1
REGISTERED_SEED_BASE = 5401
WINDOW_T = 40
T_KO1 = 5
T_KO2 = 10
T_RESCUE = 15
R0 = 0.10
R0_PER_MODULE = 0.05
K_D = 0.30
COST_REPAIR_E = 0.2
COST_REPAIR_S = 0.2
MAINT_E_PER_MODULE = 0.01
INITIAL_E = 0.10
INITIAL_S = 0.10
LEDGER_TOL = 1e-12
EXACT_TOL = 1e-12
STEP_MARGIN = 1e-6

ARMS = (
    "A-control", "B1-sham", "B2-ko1", "B3-ko2", "rescue",
    "A-B2-cost", "A-B3-cost", "A-rescue-cost", "D-half", "D-third",
    "ghost", "placebo-k1",
)
PREDICTION_KEYS = (
    "P1_a_control_equals_b1_trajectory",
    "P2_a_b2_cost_equals_b2_trajectory",
    "P2b_b2_equals_b1_recovery",
    "P2c_a_b3_cost_equals_ghost_trajectory",
    "P3_b3_freezes_at_ko2",
    "P4_rescue_resumes_and_orders",
    "P5_d_ladder_abs_monotone",
)
CONTROL_KEYS = (
    "task_manifest_valid", "driver_exit_codes_valid", "input_validation_valid",
    "csv_headers_exact", "arm_seed_row_order_exact", "row_counts_exact",
    "finite_metrics_valid", "death_censoring_explicit", "registered_arms_alive",
    "artifact_hashes_valid", "repeat_byte_identical", "hash_format_fnv64",
    "state_trajectory_hashes_exact", "schedule_exact", "capacity_schedule_exact",
    "cost_yoking_exact", "rescue_stock_exact", "repair_formula_exact",
    "ledger_closed", "summary_recomputation_exact", "resource_control_schedules_exact",
    "ghost_control_valid", "placebo_control_valid",
)
SENSITIVITY_CONTROL_KEYS = (
    "task_manifest_valid", "driver_exit_codes_valid", "artifact_hashes_valid",
    "repeat_byte_identical", "sensitivity_exit_3",
)
FINDING_PATH = f"docs/FINDING-{TASK_ID}.md"
ARTIFACT_ROOT = f"results/experiments/{TASK_ID}"
RAW_HEADER = (
    "arm", "k_eff", "d0", "seed", "aurd", "aurd_abs", "f_final", "f_at_ko2",
    "v_after_ko2", "v_after_rescue", "binary95_10", "t_reach95", "max_imbalance",
    "v_first", "n_final", "aurd_observed", "aurd_abs_observed", "f_at_death",
    "maint_short_total", "maint_debt", "rescue_in_total", "external_rescue_stock",
    "failed_module_stock", "observed_steps", "alive", "death_step", "death_cause", "horizon_censored",
    "state_hash", "trajectory_hash",
)
STEPS_HEADER = (
    "arm", "seed", "step", "n_t", "event", "u_e", "u_s", "e_in", "s_in", "e_unc",
    "s_unc", "maint_e", "maint_short", "v", "d", "e", "s", "cap_now", "f",
    "imbalance", "maint_debt", "debt_imbalance", "module_in", "module_out",
    "module_imbalance", "failed_module_in", "failed_module_stock",
    "failed_module_imbalance", "external_rescue_stock", "rescue_stock_imbalance",
    "d_before", "e_before", "s_before", "alive", "death_cause",
)
RAW_FLOAT_FIELDS = {
    "k_eff", "d0", "aurd", "aurd_abs", "f_final", "f_at_ko2", "v_after_ko2",
    "v_after_rescue", "max_imbalance", "v_first", "aurd_observed",
    "aurd_abs_observed", "f_at_death", "maint_short_total", "maint_debt",
}
RAW_INT_FIELDS = {
    "seed", "binary95_10", "t_reach95", "n_final", "rescue_in_total",
    "external_rescue_stock", "failed_module_stock", "observed_steps", "alive", "death_step", "horizon_censored",
}
STEP_FLOAT_FIELDS = {
    "u_e", "u_s", "e_in", "s_in", "e_unc", "s_unc", "maint_e", "maint_short",
    "v", "d", "e", "s", "cap_now", "f", "imbalance", "maint_debt",
    "debt_imbalance", "module_imbalance", "failed_module_imbalance",
    "rescue_stock_imbalance", "d_before", "e_before", "s_before",
}
STEP_INT_FIELDS = {
    "seed", "step", "n_t", "module_in", "module_out", "failed_module_in",
    "failed_module_stock", "external_rescue_stock", "alive",
}
FIXED_CAP_ARMS = {"A-control", "A-B2-cost", "A-B3-cost", "A-rescue-cost", "ghost"}
KO1_ARMS = {"B2-ko1", "B3-ko2", "rescue", "A-B2-cost", "A-B3-cost", "A-rescue-cost", "ghost", "placebo-k1"}
KO2_ARMS = {"B3-ko2", "rescue", "A-B3-cost", "A-rescue-cost", "ghost", "placebo-k1"}
RESCUE_ARMS = {"rescue", "A-rescue-cost"}
D0_BY_ARM = {arm: 0.5 for arm in ARMS}
D0_BY_ARM.update({"D-half": 0.25, "D-third": 1.0 / 6.0})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BASE_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
FNV64_RE = re.compile(r"^[0-9a-f]{16}$")
INT_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
FNV64_OFFSET = 0xCBF29CE484222325
FNV64_PRIME = 0x100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF
SCHEDULE_FINGERPRINT = "schedule: t*=5;t**=10;t***=15;m=3;k=2;r0=R0/2"
SENSITIVITY_PREFIX = b"INSENSITIVE_BY_CONSTRUCTION "


class AnalysisInputError(ValueError):
    pass


def strict_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def read_rows_exact(path: Path, header: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise AnalysisInputError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, strict=True)
        try:
            actual = next(reader)
        except StopIteration as exc:
            raise AnalysisInputError(f"empty CSV: {path}") from exc
        if tuple(actual) != header:
            raise AnalysisInputError(f"header mismatch in {path}: expected {list(header)}, got {actual}")
        rows: list[dict[str, str]] = []
        for line_number, values in enumerate(reader, start=2):
            if len(values) != len(header):
                raise AnalysisInputError(f"{path}:{line_number}: expected {len(header)} fields, got {len(values)}")
            rows.append(dict(zip(header, values)))
        return rows


def parse_float(value: str, context: str, *, allow_nan: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AnalysisInputError(f"{context}: invalid float {value!r}") from exc
    if math.isinf(number) or (math.isnan(number) and not allow_nan):
        raise AnalysisInputError(f"{context}: non-finite float {value!r}")
    return number


def parse_int(value: str, context: str) -> int:
    if not isinstance(value, str) or not INT_RE.fullmatch(value):
        raise AnalysisInputError(f"{context}: invalid integer {value!r}")
    return int(value)


def close(a: float, b: float, tol: float = EXACT_TOL) -> bool:
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tol


def fnv1a64(data: bytes, state: int = FNV64_OFFSET) -> int:
    """FNV-1a 64 exactly as implemented by the reviewed Rust driver."""
    for byte in data:
        state ^= byte
        state = (state * FNV64_PRIME) & U64_MASK
    return state


def fnv_update_u64(state: int, value: int) -> int:
    return fnv1a64(struct.pack("<Q", value & U64_MASK), state)


def fnv_update_f64(state: int, value: float) -> int:
    return fnv_update_u64(state, struct.unpack("<Q", struct.pack("<d", value))[0])


def driver_state_hash(n_t: int, d: float, e: float, s: float, maint_debt: float,
                      external_rescue_stock: int, failed_module_stock: int) -> int:
    state = fnv_update_u64(FNV64_OFFSET, n_t)
    for value in (d, e, s, maint_debt):
        state = fnv_update_f64(state, value)
    state = fnv_update_u64(state, external_rescue_stock)
    return fnv_update_u64(state, failed_module_stock)


def driver_trajectory_hash(rows: list[dict[str, Any]]) -> int:
    state = FNV64_OFFSET
    for row in rows:
        state = fnv_update_u64(state, row["n_t"])
        for field in ("cap_now", "d", "e", "s", "v", "f", "maint_e", "maint_short"):
            state = fnv_update_f64(state, row[field])
    return state


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_artifact_path(value: Any) -> str:
    """Return a canonical relative POSIX path accepted by control-plane intake."""
    if not isinstance(value, str) or not value:
        raise ValueError("artifact path must be a nonempty string")
    if "\0" in value or "\\" in value or ":" in value:
        raise ValueError(f"unsafe artifact path: {value!r}")
    rel = PurePosixPath(value)
    if (rel.is_absolute() or ".." in rel.parts or "." in rel.parts
            or value != rel.as_posix() or any(char in value for char in "*?[")):
        raise ValueError(f"unsafe artifact path: {value!r}")
    return rel.as_posix()


def logical_artifact_path(staged_path: str) -> str:
    staged = safe_artifact_path(staged_path)
    if staged == f"FINDING-{TASK_ID}.md":
        return FINDING_PATH
    if staged.startswith("run/"):
        staged = staged[4:]
    return f"{ARTIFACT_ROOT}/{staged}"


def path_in_write_scope(path: str, scopes: Any) -> bool:
    if not isinstance(scopes, list) or not scopes:
        return False
    path = safe_artifact_path(path)
    for scope in scopes:
        if not isinstance(scope, str) or not scope or "\0" in scope or "\\" in scope or ":" in scope:
            return False
        if scope.startswith("/") or any(part in ("", ".", "..") for part in scope.rstrip("/").split("/")):
            return False
        if scope.endswith("/") and path.startswith(scope):
            return True
        if fnmatch.fnmatchcase(path, scope):
            return True
    return False


def task_document(path: Path) -> dict[str, Any]:
    document = strict_json(path)
    if not isinstance(document, dict):
        raise ValueError("task payload must be a JSON object")
    for key in ("payload", "task", "task_payload"):
        if isinstance(document.get(key), dict):
            return document[key]
    return document


def validate_task_contract(task: dict[str, Any]) -> None:
    spec = task.get("spec")
    params = spec.get("parameters", {}) if isinstance(spec, dict) else {}
    if not isinstance(params, dict):
        raise ValueError("task spec.parameters must be an object")
    if params.get("seeds") != REGISTERED_SEEDS or params.get("seed_base") != REGISTERED_SEED_BASE:
        raise ValueError("task seed grid must be seeds=1 and seed_base=5401")
    if spec.get("seeds") != [REGISTERED_SEED_BASE]:
        raise ValueError("task spec.seeds must be exactly [5401]")
    if params.get("schedule_fingerprint") != SCHEDULE_FINGERPRINT:
        raise ValueError("task schedule fingerprint does not match the B-unit contract")


def validate_outcome(summary: dict[str, Any], manifest: dict[str, Any]) -> str:
    outcome = summary.get("scientific_outcome")
    if outcome not in {"passed", "failed", "void", "insensitive_by_construction"}:
        raise ValueError(f"unknown analyzer outcome: {outcome!r}")
    if summary.get("schema") != "analysis-b-unit/v2":
        raise ValueError("unexpected analysis schema")
    controls = summary.get("controls")
    predictions = summary.get("predictions")
    if not isinstance(controls, dict) or not isinstance(predictions, dict):
        raise ValueError("summary controls/predictions must be objects")
    controls_ok = bool(controls) and all(value is True for value in controls.values())
    if summary.get("all_controls_valid") is not controls_ok:
        raise ValueError("summary all_controls_valid is inconsistent")
    if outcome in {"passed", "failed"}:
        if set(controls) != set(CONTROL_KEYS):
            raise ValueError("summary does not contain the exact registered control set")
        if set(predictions) != set(PREDICTION_KEYS):
            raise ValueError("summary does not contain the exact registered prediction set")
    elif outcome == "insensitive_by_construction" and set(controls) != set(SENSITIVITY_CONTROL_KEYS):
        raise ValueError("sensitivity summary does not contain the exact registered control set")
    if outcome == "passed":
        if not controls_ok or not all(predictions.values()):
            raise ValueError("passed outcome requires all controls and predictions")
    elif outcome == "failed":
        if not controls_ok or all(predictions.values()):
            raise ValueError("failed outcome requires valid controls and a failed prediction")
    elif outcome == "void":
        if controls_ok:
            raise ValueError("void outcome requires a failed control")
    elif outcome == "insensitive_by_construction":
        if (manifest.get("driver_rc") != 3 or manifest.get("run2_driver_rc") != 3
                or not controls_ok):
            raise ValueError("insensitive outcome requires both driver exits 3 and valid provenance controls")
    return outcome


def actual_csv_rows(path: Path) -> int:
    if not path.is_file() or path.stat().st_size == 0:
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return max(0, sum(1 for _ in csv.reader(handle)) - 1)


def safe_manifest_path(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise AnalysisInputError(f"unsafe manifest path: {value!r}")
    rel = PurePosixPath(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise AnalysisInputError(f"unsafe manifest path: {value!r}")
    path = (root / Path(*rel.parts)).resolve()
    if root.resolve() != path and root.resolve() not in path.parents:
        raise AnalysisInputError(f"manifest path escapes output directory: {value!r}")
    return path


def validate_task_identity(manifest: dict[str, Any]) -> tuple[int, int, int, list[str]]:
    errors: list[str] = []
    if manifest.get("schema") != "raw-manifest/v2":
        errors.append("manifest schema must be raw-manifest/v2")
    if manifest.get("task_id") != TASK_ID:
        errors.append("manifest task_id mismatch")
    version = manifest.get("task_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append("task_version must be an integer >=1")
        version = -1
    task_hash = manifest.get("task_version_sha256")
    if not isinstance(task_hash, str) or not SHA256_RE.fullmatch(task_hash):
        errors.append("invalid task-version SHA256")
    elif task_hash == "0" * 64:
        errors.append("task-version SHA256 is still the draft placeholder")
    base = manifest.get("base_commit")
    if not isinstance(base, str) or not BASE_COMMIT_RE.fullmatch(base):
        errors.append("base_commit must be 7..40 lowercase hex characters")
    elif not base.strip("0"):
        errors.append("base_commit is still the draft placeholder")
    seeds = manifest.get("seeds")
    if not isinstance(seeds, int) or isinstance(seeds, bool) or seeds < 1:
        errors.append("seeds must be an integer >=1")
        seeds = 1
    if seeds != REGISTERED_SEEDS:
        errors.append(f"seeds must equal the registered task value {REGISTERED_SEEDS}")
    seed_base = manifest.get("seed_base")
    if not isinstance(seed_base, int) or isinstance(seed_base, bool) or seed_base < 0:
        errors.append("seed_base must be a non-negative integer")
        seed_base = 0
    if seed_base != REGISTERED_SEED_BASE:
        errors.append(f"seed_base must equal the registered task value {REGISTERED_SEED_BASE}")
    environment = manifest.get("environment")
    if not isinstance(environment, dict):
        errors.append("manifest environment must be an object")
    else:
        expected = {
            "task_id": TASK_ID,
            "task_version": version,
            "task_version_sha256": task_hash,
            "base_commit": base,
            "seeds": seeds,
            "seed_base": seed_base,
        }
        for key, value in expected.items():
            if environment.get(key) != value:
                errors.append(f"environment/manifest {key} mismatch")
    return version, seeds, seed_base, errors


def _sensitivity_outputs(raw_path: Path, steps_path: Path, manifest_path: Path,
                         out: Path, manifest: dict[str, Any]) -> dict:
    """Exit 3 is a verdict only after its minimal evidence chain is verified."""
    controls = {
        "task_manifest_valid": True,
        "driver_exit_codes_valid": True,
        "artifact_hashes_valid": True,
        "repeat_byte_identical": True,
        "sensitivity_exit_3": True,
    }
    details: dict[str, list[str]] = {key: [] for key in controls}

    def mark(control: str, message: str) -> None:
        controls[control] = False
        details[control].append(message)

    version, seeds, _seed_base, errors = validate_task_identity(manifest)
    if errors:
        mark("task_manifest_valid", "; ".join(errors))
    if manifest.get("driver_rc") != 3 or manifest.get("run2_driver_rc") != 3:
        mark("driver_exit_codes_valid", "sensitivity requires both driver return codes to equal 3")
    if manifest.get("runner_rc") != 3:
        mark("driver_exit_codes_valid", "sensitivity runner_rc must equal 3")
    if manifest.get("expected_arms") != len(ARMS):
        mark("task_manifest_valid", "expected_arms must be 12")
    if manifest.get("expected_raw_rows") != len(ARMS) * seeds:
        mark("task_manifest_valid", "declared expected_raw_rows is wrong")
    if manifest.get("expected_steps_rows") != len(ARMS) * seeds * WINDOW_T:
        mark("task_manifest_valid", "declared expected_steps_rows is wrong")
    driver = manifest.get("driver", {})
    if not isinstance(driver, dict):
        mark("artifact_hashes_valid", "driver provenance must be an object")
    else:
        for key in ("sha256", "source_sha256"):
            value = driver.get(key)
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                mark("artifact_hashes_valid", f"missing or invalid driver {key}")

    manifest_root = manifest_path.resolve().parent
    try:
        executions = manifest.get("executions", {})
        run1_raw = safe_manifest_path(manifest_root, executions["run1"]["raw_csv"]["path"])
        run1_steps = safe_manifest_path(manifest_root, executions["run1"]["steps_csv"]["path"])
        run2_raw = safe_manifest_path(manifest_root, executions["run2"]["raw_csv"]["path"])
        run2_steps = safe_manifest_path(manifest_root, executions["run2"]["steps_csv"]["path"])
        pairs = [
            (raw_path, manifest.get("raw_csv", {}), "raw.csv"),
            (steps_path, manifest.get("steps_csv", {}), "steps.csv"),
            (run1_raw, executions["run1"]["raw_csv"], "run1/raw.csv"),
            (run1_steps, executions["run1"]["steps_csv"], "run1/steps.csv"),
            (run2_raw, executions["run2"]["raw_csv"], "run2/raw.csv"),
            (run2_steps, executions["run2"]["steps_csv"], "run2/steps.csv"),
        ]
        for path, record, label in pairs:
            if not path.is_file():
                raise AnalysisInputError(f"missing recorded artifact {label}")
            if record.get("sha256") != sha256_file(path):
                mark("artifact_hashes_valid", f"SHA256 mismatch: {label}")
            if record.get("bytes") != path.stat().st_size:
                mark("artifact_hashes_valid", f"byte-count mismatch: {label}")
            if record.get("rows") != actual_csv_rows(path):
                mark("artifact_hashes_valid", f"row-count mismatch: {label}")
        raw_identical = raw_path.read_bytes() == run1_raw.read_bytes() == run2_raw.read_bytes()
        steps_identical = steps_path.read_bytes() == run1_steps.read_bytes() == run2_steps.read_bytes()
        if not (raw_identical and steps_identical):
            mark("repeat_byte_identical", "sensitivity raw/steps executions are not byte-identical")
        if manifest.get("repeat", {}).get("byte_identical") is not True:
            mark("repeat_byte_identical", "manifest repeat.byte_identical is not true")
        sensitivity_bytes = raw_path.read_bytes()
        if (not sensitivity_bytes.startswith(SENSITIVITY_PREFIX)
                or not sensitivity_bytes.endswith(b"\n")
                or sensitivity_bytes.count(b"\n") != 1):
            mark("sensitivity_exit_3", "raw.csv is not one registered INSENSITIVE_BY_CONSTRUCTION line")
        if steps_path.read_bytes() != b"":
            mark("sensitivity_exit_3", "steps.csv must be empty for exit 3")
    except (AnalysisInputError, OSError, AttributeError, KeyError, TypeError, ValueError) as exc:
        mark("artifact_hashes_valid", str(exc))
        mark("repeat_byte_identical", str(exc))

    if all(controls.values()):
        return empty_outputs(
            out, manifest, "insensitive_by_construction",
            "insensitive_by_construction: both runs returned 3 and the marker/provenance chain is valid",
            controls, {}, details,
        )
    failed = [key for key, value in controls.items() if not value]
    return empty_outputs(
        out, manifest, "void",
        "void: exit-3 evidence failed validation: " + ", ".join(failed),
        controls, {}, details,
    )


def expected_event(arm: str, step: int) -> tuple[str, int, int, int, int]:
    """Return event, active module in/out, failed-module in, external-stock debit."""
    if arm == "B1-sham" and step == T_KO1:
        return "sham", 0, 0, 0, 0
    if arm in KO1_ARMS and step == T_KO1:
        return "ko1", 0, 1, 1, 0
    if arm in KO2_ARMS and step == T_KO2:
        return "ko2", 0, 1, 1, 0
    if arm in RESCUE_ARMS and step == T_RESCUE:
        return "rescue", 1, 0, 0, 1
    return "none", 0, 0, 0, 0


def expected_cap(arm: str, n_t: int) -> float:
    if arm in FIXED_CAP_ARMS:
        return R0
    if arm == "placebo-k1":
        return min(R0, R0_PER_MODULE * n_t) if n_t >= 1 else 0.0
    return min(R0, R0_PER_MODULE * n_t) if n_t >= 2 else 0.0


def cost_modules(arm: str, n_t: int) -> int:
    return 3 if arm == "A-control" else n_t


def json_safe(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def empty_outputs(out: Path, manifest: dict, outcome: str, reason: str,
                  controls: dict[str, bool], predictions: dict[str, bool],
                  details: dict[str, list[str]] | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "per_arm.csv").open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerow(RAW_HEADER)
    with (out / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["prediction", "kind", "holds"])
        for key, value in predictions.items():
            writer.writerow([key, "scientific", int(value)])
    with (out / "controls.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["control", "holds"])
        for key, value in controls.items():
            writer.writerow([key, int(value)])
    summary = {
        "schema": "analysis-b-unit/v2",
        "analyzer_version": ANALYZER_VERSION,
        "task_id": manifest.get("task_id"),
        "task_version": manifest.get("task_version"),
        "task_version_sha256": manifest.get("task_version_sha256"),
        "base_commit": manifest.get("base_commit"),
        "scientific_outcome": outcome,
        "reason": reason,
        "all_controls_valid": all(controls.values()) if controls else None,
        "controls": controls,
        "control_details": details or {},
        "predictions": predictions,
        "seeds": manifest.get("seeds"),
        "seed_base": manifest.get("seed_base"),
        "driver_rc": manifest.get("driver_rc"),
        "run2_driver_rc": manifest.get("run2_driver_rc"),
        "raw_sha256": manifest.get("raw_csv", {}).get("sha256"),
        "steps_sha256": manifest.get("steps_csv", {}).get("sha256"),
        "repeat": manifest.get("repeat"),
        "primary": {},
        "secondary": {},
        "non_finite_metrics": [],
    }
    (out / "summary.json").write_text(
        json.dumps(json_safe(summary), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8")
    return summary


def _analyze(raw_path: Path, steps_path: Path, manifest_path: Path, out: Path) -> dict:
    manifest = strict_json(manifest_path)
    if not isinstance(manifest, dict):
        raise AnalysisInputError("manifest must be a JSON object")
    rc1 = manifest.get("driver_rc")
    rc2 = manifest.get("run2_driver_rc", rc1)
    if not isinstance(rc1, int) or isinstance(rc1, bool) or not isinstance(rc2, int) or isinstance(rc2, bool):
        return empty_outputs(out, manifest, "void", "void: driver return codes are missing or invalid",
                             {"driver_exit_codes_valid": False}, {})
    if rc1 == 3 and rc2 == 3:
        return _sensitivity_outputs(raw_path, steps_path, manifest_path, out, manifest)
    if rc1 != 0 or rc2 != 0:
        return empty_outputs(
            out, manifest, "void",
            f"void: driver return codes {rc1}/{rc2} are not successful and are not sensitivity exit 3",
            {"driver_exit_codes_valid": False}, {},
        )

    controls: dict[str, bool] = {
        "task_manifest_valid": True,
        "driver_exit_codes_valid": True,
        "input_validation_valid": True,
        "csv_headers_exact": True,
        "arm_seed_row_order_exact": True,
        "row_counts_exact": True,
        "finite_metrics_valid": True,
        "death_censoring_explicit": True,
        "registered_arms_alive": True,
        "artifact_hashes_valid": True,
        "repeat_byte_identical": True,
        "hash_format_fnv64": True,
        "state_trajectory_hashes_exact": True,
        "schedule_exact": True,
        "capacity_schedule_exact": True,
        "cost_yoking_exact": True,
        "rescue_stock_exact": True,
        "repair_formula_exact": True,
        "ledger_closed": True,
        "summary_recomputation_exact": True,
        "resource_control_schedules_exact": True,
        "ghost_control_valid": True,
        "placebo_control_valid": True,
    }
    details: dict[str, list[str]] = {key: [] for key in controls}

    def mark(control: str, message: str) -> None:
        controls[control] = False
        details[control].append(message)

    try:
        raw_rows = read_rows_exact(raw_path, RAW_HEADER)
        step_rows = read_rows_exact(steps_path, STEPS_HEADER)
    except AnalysisInputError as exc:
        controls["input_validation_valid"] = False
        controls["csv_headers_exact"] = False
        details["input_validation_valid"].append(str(exc))
        return empty_outputs(out, manifest, "void", f"void: CSV validation failed: {exc}", controls, {}, details)

    # Task identity is dynamic; no task version or hash is pinned in this analyzer.
    version, seeds, seed_base, identity_errors = validate_task_identity(manifest)
    for message in identity_errors:
        mark("task_manifest_valid", message)

    # Validate artifact hashes, both executions, row counts, and actual byte identity.
    manifest_root = manifest_path.resolve().parent
    try:
        run1_raw = safe_manifest_path(manifest_root, manifest.get("executions", {}).get("run1", {}).get("raw_csv", {}).get("path"))
        run1_steps = safe_manifest_path(manifest_root, manifest.get("executions", {}).get("run1", {}).get("steps_csv", {}).get("path"))
        run2_raw = safe_manifest_path(manifest_root, manifest.get("executions", {}).get("run2", {}).get("raw_csv", {}).get("path"))
        run2_steps = safe_manifest_path(manifest_root, manifest.get("executions", {}).get("run2", {}).get("steps_csv", {}).get("path"))
        pairs = [
            (raw_path, manifest.get("raw_csv", {}), "raw.csv"),
            (steps_path, manifest.get("steps_csv", {}), "steps.csv"),
            (run1_raw, manifest.get("executions", {}).get("run1", {}).get("raw_csv", {}), "run1/raw.csv"),
            (run1_steps, manifest.get("executions", {}).get("run1", {}).get("steps_csv", {}), "run1/steps.csv"),
            (run2_raw, manifest.get("executions", {}).get("run2", {}).get("raw_csv", {}), "run2/raw.csv"),
            (run2_steps, manifest.get("executions", {}).get("run2", {}).get("steps_csv", {}), "run2/steps.csv"),
        ]
        for path, record, label in pairs:
            if not path.is_file():
                raise AnalysisInputError(f"missing recorded artifact {label}")
            if record.get("sha256") != sha256_file(path):
                mark("artifact_hashes_valid", f"SHA256 mismatch: {label}")
            if record.get("rows") != actual_csv_rows(path):
                mark("artifact_hashes_valid", f"row-count mismatch: {label}")
            if record.get("bytes") != path.stat().st_size:
                mark("artifact_hashes_valid", f"byte-count mismatch: {label}")
        raw_identical = raw_path.read_bytes() == run1_raw.read_bytes() == run2_raw.read_bytes()
        steps_identical = steps_path.read_bytes() == run1_steps.read_bytes() == run2_steps.read_bytes()
        if not (raw_identical and steps_identical):
            mark("repeat_byte_identical", "run1/run2 raw.csv or steps.csv differs byte-for-byte")
        repeat = manifest.get("repeat", {})
        if repeat.get("byte_identical") is not True:
            mark("repeat_byte_identical", "manifest repeat.byte_identical is not true")
        if manifest.get("expected_arms") != len(ARMS):
            mark("row_counts_exact", "manifest expected_arms is not 12")
        if manifest.get("expected_raw_rows") != len(ARMS) * seeds:
            mark("row_counts_exact", "manifest expected_raw_rows is wrong")
        if manifest.get("expected_steps_rows") != len(ARMS) * seeds * WINDOW_T:
            mark("row_counts_exact", "manifest expected_steps_rows is wrong")
        if len(raw_rows) != len(ARMS) * seeds:
            mark("row_counts_exact", f"raw row count {len(raw_rows)} != {len(ARMS) * seeds}")
        if len(step_rows) != len(ARMS) * seeds * WINDOW_T:
            mark("row_counts_exact", f"steps row count {len(step_rows)} != {len(ARMS) * seeds * WINDOW_T}")
        driver = manifest.get("driver", {})
        if not isinstance(driver, dict):
            mark("artifact_hashes_valid", "driver provenance must be an object")
        else:
            for key in ("sha256", "source_sha256"):
                value = driver.get(key)
                if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                    mark("artifact_hashes_valid", f"missing or invalid driver {key}")
        executions = manifest.get("executions", {})
        if not isinstance(executions, dict):
            mark("artifact_hashes_valid", "executions must be an object")
        else:
            for name, expected_rc in (("run1", rc1), ("run2", rc2)):
                execution = executions.get(name, {})
                if not isinstance(execution, dict) or execution.get("returncode") != expected_rc:
                    mark("driver_exit_codes_valid", f"{name} returncode disagrees with manifest")
                if execution.get("driver_schedule_line") != SCHEDULE_FINGERPRINT:
                    mark("schedule_exact", f"{name} driver schedule fingerprint is missing or wrong")
    except (AnalysisInputError, AttributeError, TypeError, ValueError) as exc:
        mark("artifact_hashes_valid", str(exc))
        mark("repeat_byte_identical", str(exc))

    expected_raw_keys = [(arm, seed_base + index) for arm in ARMS for index in range(seeds)]
    actual_raw_keys = [(row.get("arm"), parse_int(row.get("seed", ""), f"raw seed {row.get('arm')}")) for row in raw_rows]
    if actual_raw_keys != expected_raw_keys:
        mark("arm_seed_row_order_exact", "raw rows are not exactly arm-major with registered seeds")

    raw_typed: dict[tuple[str, int], dict[str, Any]] = {}
    raw_by_arm: dict[str, dict[int, dict[str, Any]]] = {arm: {} for arm in ARMS}
    non_finite_metrics: list[str] = []
    for row in raw_rows:
        arm = row["arm"]
        seed = parse_int(row["seed"], f"raw {arm} seed")
        typed: dict[str, Any] = {"arm": arm}
        for field in RAW_HEADER:
            if field == "arm":
                continue
            if field in RAW_FLOAT_FIELDS:
                typed[field] = parse_float(row[field], f"raw {arm}/{seed}/{field}", allow_nan=True)
            elif field in RAW_INT_FIELDS:
                typed[field] = parse_int(row[field], f"raw {arm}/{seed}/{field}")
            else:
                typed[field] = row[field]
        raw_typed[(arm, seed)] = typed
        raw_by_arm.setdefault(arm, {})[seed] = typed
        if arm not in ARMS:
            mark("arm_seed_row_order_exact", f"unexpected arm {arm}")
            continue
        if typed["d0"] != D0_BY_ARM[arm] or not math.isfinite(typed["d0"]):
            mark("schedule_exact", f"{arm}/{seed}: d0 is not registered")
        if arm in {"B1-sham", "B2-ko1", "B3-ko2", "rescue", "D-half", "D-third"} and typed["k_eff"] != 2:
            mark("schedule_exact", f"{arm}/{seed}: k_eff must be 2")
        if arm == "placebo-k1" and typed["k_eff"] != 1:
            mark("schedule_exact", f"{arm}/{seed}: placebo k_eff must be 1")
        if arm in FIXED_CAP_ARMS and typed["k_eff"] not in (-1.0, 0.0):
            mark("schedule_exact", f"{arm}/{seed}: fixed-capacity k_eff sentinel must be -1 or 0")
        for field in ("state_hash", "trajectory_hash"):
            if not isinstance(typed[field], str) or not FNV64_RE.fullmatch(typed[field]):
                mark("hash_format_fnv64", f"{arm}/{seed}: invalid {field}")
        for field in RAW_FLOAT_FIELDS:
            value = typed[field]
            if not math.isfinite(value):
                non_finite_metrics.append(f"{arm}/{seed}/{field}")
        alive = typed["alive"]
        if alive not in (0, 1) or typed["horizon_censored"] not in (0, 1) or typed["binary95_10"] not in (0, 1):
            mark("death_censoring_explicit", f"{arm}/{seed}: boolean fields must be 0/1")
        if alive:
            required_finite = (
                "aurd", "aurd_abs", "f_final", "f_at_ko2", "v_after_ko2", "v_after_rescue",
                "max_imbalance", "v_first", "aurd_observed", "aurd_abs_observed",
                "maint_short_total", "maint_debt",
            )
            for field in required_finite:
                if not math.isfinite(typed[field]):
                    mark("finite_metrics_valid", f"{arm}/{seed}: live metric {field} is non-finite")
            if not math.isnan(typed["f_at_death"]):
                mark("death_censoring_explicit", f"{arm}/{seed}: live f_at_death must be NaN")
            if typed["death_step"] != -1 or typed["death_cause"] != "none" or typed["horizon_censored"] != 1:
                mark("death_censoring_explicit", f"{arm}/{seed}: live death/censoring fields are inconsistent")
            if typed["observed_steps"] != WINDOW_T:
                mark("death_censoring_explicit", f"{arm}/{seed}: live observed_steps must be 40")
        else:
            mark("registered_arms_alive", f"{arm}/{seed}: registered arm died; outcome is not scientifically interpretable")
            for field in ("aurd", "aurd_abs", "f_final"):
                if not math.isnan(typed[field]):
                    mark("finite_metrics_valid", f"{arm}/{seed}: dead horizon metric {field} must be NaN")
            if typed["death_step"] < 0 or typed["death_cause"] not in ("energy", "damage") or typed["horizon_censored"] != 0:
                mark("death_censoring_explicit", f"{arm}/{seed}: dead death/censoring fields are inconsistent")
            if not math.isfinite(typed["f_at_death"]):
                mark("finite_metrics_valid", f"{arm}/{seed}: dead f_at_death must be finite")

    # Parse every step as finite numeric data before any independent recomputation.
    typed_steps: list[dict[str, Any]] = []
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    actual_step_keys: list[tuple[str, int, int]] = []
    for row in step_rows:
        typed: dict[str, Any] = {"arm": row["arm"], "event": row["event"], "death_cause": row["death_cause"]}
        for field in STEPS_HEADER:
            if field in ("arm", "event", "death_cause"):
                continue
            if field in STEP_FLOAT_FIELDS:
                typed[field] = parse_float(row[field], f"step {row['arm']}/{row['seed']}/{row['step']}/{field}")
            elif field in STEP_INT_FIELDS:
                typed[field] = parse_int(row[field], f"step {row['arm']}/{row['seed']}/{row['step']}/{field}")
        key = (typed["arm"], typed["seed"])
        groups.setdefault(key, []).append(typed)
        typed_steps.append(typed)
        actual_step_keys.append((typed["arm"], typed["seed"], typed["step"]))
    expected_step_keys = [
        (arm, seed_base + index, step)
        for arm in ARMS for index in range(seeds) for step in range(WINDOW_T)
    ]
    if actual_step_keys != expected_step_keys:
        mark("arm_seed_row_order_exact", "steps are not exactly arm/seed/time-major for live registered arms")

    # Death is a joint raw/steps contract, not a raw-only flag. A live raw row
    # cannot hide a dead final step, and a dead arm must stop on its death step.
    for arm in ARMS:
        for seed_index in range(seeds):
            seed = seed_base + seed_index
            raw = raw_typed.get((arm, seed))
            rows = groups.get((arm, seed), [])
            if raw is None or not rows:
                continue
            final = rows[-1]
            context = f"{arm}/{seed}"
            if final["alive"] not in (0, 1):
                mark("death_censoring_explicit", f"{context}: final steps alive flag must be 0/1")
                continue
            if raw["alive"] != final["alive"]:
                mark("death_censoring_explicit",
                     f"{context}: raw alive={raw['alive']} disagrees with final steps alive={final['alive']}")
            if raw["alive"] == 1:
                if any(row["alive"] != 1 for row in rows):
                    mark("death_censoring_explicit", f"{context}: live raw arm has a non-live step")
                if final["alive"] != 1:
                    mark("registered_arms_alive", f"{context}: final step is dead")
            else:
                if final["alive"] != 0:
                    mark("death_censoring_explicit", f"{context}: dead raw arm has a live final step")
                if any(row["alive"] != 1 for row in rows[:-1]):
                    mark("death_censoring_explicit", f"{context}: dynamics continue after death")
                if final["e"] > 0.0 and final["d"] < 1.0:
                    mark("death_censoring_explicit", f"{context}: final death flag is not supported by e/d state")
            if raw["alive"] == 1 and raw["observed_steps"] != WINDOW_T:
                mark("death_censoring_explicit", f"{context}: live observed_steps must be 40")
            if raw["alive"] == 0 and not (1 <= raw["observed_steps"] <= WINDOW_T):
                mark("death_censoring_explicit", f"{context}: dead observed_steps must be in 1..40")

    summaries: dict[tuple[str, int], dict[str, Any]] = {}
    signatures: dict[tuple[str, int], list[tuple[Any, ...]]] = {}
    for arm in ARMS:
        for seed_index in range(seeds):
            seed = seed_base + seed_index
            key = (arm, seed)
            raw = raw_typed.get(key)
            if raw is None:
                mark("arm_seed_row_order_exact", f"missing raw row {arm}/{seed}")
                continue
            rows = groups.get(key, [])
            observed = raw["observed_steps"]
            if len(rows) != observed:
                mark("row_counts_exact", f"{arm}/{seed}: step rows {len(rows)} != observed_steps {observed}")
            if [row["step"] for row in rows] != list(range(observed)):
                mark("arm_seed_row_order_exact", f"{arm}/{seed}: step sequence is not 0..observed_steps-1")

            prev_d = raw["d0"]
            prev_e = INITIAL_E
            prev_s = INITIAL_S
            prev_n = 3
            prev_debt = 0.0
            prev_failed = 0
            prev_external = 1 if arm in RESCUE_ARMS else 0
            aurd_sum = 0.0
            aurd_abs_sum = 0.0
            v_after_ko2 = 0.0
            v_after_rescue = 0.0
            maint_short_total = 0.0
            rescue_in_total = 0
            max_imbalance = 0.0
            v_first: float | None = None
            f_at_ko2: float | None = None
            t_reach95 = 0
            binary95 = 0
            signature: list[tuple[Any, ...]] = []
            trajectory_hash = FNV64_OFFSET

            for row in rows:
                step = row["step"]
                context = f"{arm}/{seed}/t{step}"
                event, module_in, module_out, failed_in, external_debit = expected_event(arm, step)
                if row["event"] not in ({event} if event != "none" else {"", "none"}):
                    mark("schedule_exact", f"{context}: event {row['event']!r} != {event!r}")
                expected_n = prev_n + module_in - module_out
                if row["n_t"] != expected_n:
                    mark("schedule_exact", f"{context}: n_t {row['n_t']} != {expected_n}")
                if row["module_in"] != module_in or row["module_out"] != module_out:
                    mark("schedule_exact", f"{context}: active module flows do not match event")
                if row["failed_module_in"] != failed_in or row["failed_module_in"] != module_out:
                    mark("schedule_exact", f"{context}: failed-module inflow does not match knockout")
                expected_external = prev_external - external_debit
                if row["external_rescue_stock"] != expected_external:
                    mark("rescue_stock_exact", f"{context}: external rescue stock {row['external_rescue_stock']} != {expected_external}")
                if arm in RESCUE_ARMS and step == T_RESCUE and (module_in != 1 or external_debit != 1):
                    mark("rescue_stock_exact", f"{context}: rescue must consume exactly one external module")
                cap = expected_cap(arm, row["n_t"])
                if not close(row["cap_now"], cap, 1e-15):
                    mark("capacity_schedule_exact", f"{context}: cap_now {row['cap_now']} != {cap}")
                if arm == "placebo-k1" and row["cap_now"] <= 0.0:
                    mark("placebo_control_valid", f"{context}: placebo capacity reached zero")
                if arm == "placebo-k1" and step >= T_KO2 and not close(row["cap_now"], R0_PER_MODULE, 1e-15):
                    mark("placebo_control_valid", f"{context}: placebo capacity after n=1 must be 0.05")

                e_add = row["e_in"] - row["e_unc"]
                s_add = row["s_in"] - row["s_unc"]
                if row["e_in"] < 0 or row["s_in"] < 0 or row["e_unc"] < 0 or row["s_unc"] < 0 or e_add < -LEDGER_TOL or s_add < -LEDGER_TOL:
                    mark("ledger_closed", f"{context}: invalid inflow/unclaimed signs")
                if prev_e + e_add > 1.0 + LEDGER_TOL or prev_s + s_add > 1.0 + LEDGER_TOL:
                    mark("ledger_closed", f"{context}: stock cap exceeded")
                expected_e_add = min(row["e_in"], max(0.0, 1.0 - prev_e))
                expected_s_add = min(row["s_in"], max(0.0, 1.0 - prev_s))
                if not close(e_add, expected_e_add) or not close(s_add, expected_s_add):
                    mark("ledger_closed", f"{context}: accepted inflow is not min(request, remaining stock capacity)")
                maint_need = cost_modules(arm, row["n_t"]) * MAINT_E_PER_MODULE
                if not close(row["maint_e"] + row["maint_short"], maint_need):
                    mark("cost_yoking_exact", f"{context}: maintenance need is not registered active-n cost")
                if row["maint_e"] < -LEDGER_TOL or row["maint_short"] < -LEDGER_TOL:
                    mark("cost_yoking_exact", f"{context}: negative maintenance payment/shortfall")
                expected_maint_paid = min(max(prev_e + e_add, 0.0), maint_need)
                if not close(row["maint_e"], expected_maint_paid):
                    mark("cost_yoking_exact", f"{context}: maintenance payment is not min(available, need)")
                if not close(row["e_before"], prev_e + e_add - row["maint_e"]):
                    mark("ledger_closed", f"{context}: e_before does not close inflow/maintenance transition")
                if not close(row["s_before"], prev_s + s_add):
                    mark("ledger_closed", f"{context}: s_before does not close inflow transition")
                if not close(row["d_before"], prev_d):
                    mark("repair_formula_exact", f"{context}: d_before does not equal prior damage")

                expected_v = min(
                    K_D * row["d_before"], row["cap_now"],
                    row["e_before"] / COST_REPAIR_E, row["s_before"] / COST_REPAIR_S,
                    row["d_before"],
                )
                expected_v = max(0.0, expected_v)
                if not close(row["v"], expected_v):
                    mark("repair_formula_exact", f"{context}: v {row['v']} != independently computed {expected_v}")
                expected_d = row["d_before"] - row["v"]
                expected_e = row["e_before"] - row["v"] * COST_REPAIR_E
                expected_s = row["s_before"] - row["v"] * COST_REPAIR_S
                expected_f = (raw["d0"] - expected_d) / raw["d0"]
                if not close(row["d"], expected_d) or not close(row["e"], expected_e) or not close(row["s"], expected_s):
                    mark("ledger_closed", f"{context}: post-repair state does not close")
                if not close(row["f"], expected_f):
                    mark("summary_recomputation_exact", f"{context}: f does not equal (d0-d)/d0")

                debt_residual = row["maint_debt"] - (prev_debt + row["maint_short"])
                module_residual = prev_n + row["module_in"] - row["module_out"] - row["n_t"]
                failed_residual = prev_failed + row["failed_module_in"] - row["failed_module_stock"]
                rescue_residual = prev_external - row["module_in"] - row["external_rescue_stock"]
                energy_residual = row["e_before"] - row["v"] * COST_REPAIR_E - row["e"]
                substrate_residual = row["s_before"] - row["v"] * COST_REPAIR_S - row["s"]
                residuals = (debt_residual, module_residual, failed_residual, rescue_residual,
                             energy_residual, substrate_residual)
                if not close(row["debt_imbalance"], debt_residual):
                    mark("ledger_closed", f"{context}: debt_imbalance is not independently recomputed")
                if not close(row["module_imbalance"], module_residual):
                    mark("ledger_closed", f"{context}: module_imbalance is not independently recomputed")
                if not close(row["failed_module_imbalance"], failed_residual):
                    mark("ledger_closed", f"{context}: failed_module_imbalance is not independently recomputed")
                if not close(row["rescue_stock_imbalance"], rescue_residual):
                    mark("ledger_closed", f"{context}: rescue_stock_imbalance is not independently recomputed")
                recomputed_imbalance = max(abs(value) for value in residuals)
                if recomputed_imbalance >= LEDGER_TOL or not close(row["imbalance"], recomputed_imbalance):
                    mark("ledger_closed", f"{context}: ledger imbalance {row['imbalance']} != {recomputed_imbalance}")

                expected_death = row["e"] <= 0.0 or row["d"] >= 1.0
                if row["alive"] != (0 if expected_death else 1):
                    mark("death_censoring_explicit", f"{context}: alive flag does not match e/d death rule")
                expected_cause = "none"
                if expected_death:
                    expected_cause = "energy" if row["e"] <= 0.0 else "damage"
                if row["death_cause"] != expected_cause:
                    mark("death_censoring_explicit", f"{context}: death_cause {row['death_cause']!r} != {expected_cause!r}")
                if not expected_death and row["alive"] == 0:
                    mark("death_censoring_explicit", f"{context}: unexpected death")
                if step < observed - 1 and row["alive"] != 1:
                    mark("death_censoring_explicit", f"{context}: dynamics continue after death")

                if step == 0:
                    v_first = row["v"]
                if step == T_KO2 - 1:
                    f_at_ko2 = row["f"]
                if step == T_KO2:
                    binary95 = int(row["alive"] == 1 and row["f"] >= 0.95)
                if t_reach95 == 0 and row["alive"] == 1 and row["f"] >= 0.95:
                    t_reach95 = step
                aurd_sum += row["d"] / raw["d0"]
                aurd_abs_sum += row["d"]
                if step >= T_KO2:
                    v_after_ko2 += row["v"]
                if step >= T_RESCUE:
                    v_after_rescue += row["v"]
                maint_short_total += row["maint_short"]
                rescue_in_total += row["module_in"]
                max_imbalance = max(max_imbalance, row["imbalance"])
                signature.append((
                    row["n_t"], maint_need, row["module_in"], row["module_out"],
                    row["failed_module_in"], row["failed_module_stock"], row["external_rescue_stock"],
                ))
                trajectory_hash = fnv_update_u64(trajectory_hash, row["n_t"])
                for field in ("cap_now", "d", "e", "s", "v", "f", "maint_e", "maint_short"):
                    trajectory_hash = fnv_update_f64(trajectory_hash, row[field])
                prev_d, prev_e, prev_s = row["d"], row["e"], row["s"]
                prev_n, prev_debt = row["n_t"], row["maint_debt"]
                prev_failed, prev_external = row["failed_module_stock"], row["external_rescue_stock"]

            signatures[key] = signature
            expected_state_hash = driver_state_hash(
                prev_n, prev_d, prev_e, prev_s, prev_debt, prev_external, prev_failed)
            if raw["trajectory_hash"] != f"{trajectory_hash:016x}":
                mark("state_trajectory_hashes_exact",
                     f"{arm}/{seed}: trajectory_hash does not match raw-bit recomputation")
            if raw["state_hash"] != f"{expected_state_hash:016x}":
                mark("state_trajectory_hashes_exact",
                     f"{arm}/{seed}: state_hash does not match final raw-bit state")
            if rows:
                final_alive = rows[-1]["alive"]
                expected_death_step = -1 if final_alive == 1 else observed - 1
                if raw["death_step"] != expected_death_step:
                    mark("death_censoring_explicit",
                         f"{arm}/{seed}: death_step {raw['death_step']} != {expected_death_step}")
            else:
                mark("row_counts_exact", f"{arm}/{seed}: no steps rows for death-step validation")
            aggregate = {
                "aurd": aurd_sum / WINDOW_T if raw["alive"] else math.nan,
                "aurd_abs": aurd_abs_sum / WINDOW_T if raw["alive"] else math.nan,
                "aurd_observed": aurd_sum / observed if observed else math.nan,
                "aurd_abs_observed": aurd_abs_sum / observed if observed else math.nan,
                "f_final": rows[-1]["f"] if raw["alive"] and rows else math.nan,
                "f_at_death": rows[-1]["f"] if (not raw["alive"] and rows) else math.nan,
                "f_at_ko2": f_at_ko2 if f_at_ko2 is not None else math.nan,
                "v_after_ko2": v_after_ko2,
                "v_after_rescue": v_after_rescue,
                "binary95_10": binary95,
                "t_reach95": t_reach95,
                "max_imbalance": max_imbalance,
                "v_first": v_first if v_first is not None else math.nan,
                "n_final": prev_n,
                "maint_short_total": maint_short_total,
                "maint_debt": prev_debt,
                "rescue_in_total": rescue_in_total,
                "external_rescue_stock": prev_external,
                "failed_module_stock": prev_failed,
                "observed_steps": observed,
            }
            summaries[key] = aggregate
            for field, expected in aggregate.items():
                actual = raw[field]
                if isinstance(expected, float) and math.isnan(expected):
                    if not (isinstance(actual, float) and math.isnan(actual)):
                        mark("summary_recomputation_exact", f"{arm}/{seed}: {field} should be NaN")
                elif isinstance(expected, int):
                    if actual != expected:
                        mark("summary_recomputation_exact", f"{arm}/{seed}: {field} {actual} != {expected}")
                elif not close(actual, expected):
                    mark("summary_recomputation_exact", f"{arm}/{seed}: {field} {actual} != {expected}")

    # Cost-yoked A arms must reproduce the corresponding B resource schedule.
    for a_arm, b_arm in (("A-B2-cost", "B2-ko1"), ("A-B3-cost", "B3-ko2"), ("A-rescue-cost", "rescue")):
        for seed_index in range(seeds):
            seed = seed_base + seed_index
            if signatures.get((a_arm, seed)) != signatures.get((b_arm, seed)):
                mark("resource_control_schedules_exact", f"{a_arm}/{seed}: resource schedule differs from {b_arm}")
    for seed_index in range(seeds):
        seed = seed_base + seed_index
        if signatures.get(("ghost", seed)) != signatures.get(("B3-ko2", seed)):
            mark("resource_control_schedules_exact", f"ghost/{seed}: not B3 schedule/cost")

    def finite_raw(arm: str, seed: int, field: str) -> float | None:
        value = raw_typed.get((arm, seed), {}).get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            return float(value)
        return None

    predictions: dict[str, bool] = {}
    predictions["P1_a_control_equals_b1_trajectory"] = all(
        raw_typed.get(("A-control", seed_base + i), {}).get("trajectory_hash")
        == raw_typed.get(("B1-sham", seed_base + i), {}).get("trajectory_hash")
        for i in range(seeds)
    )
    predictions["P2_a_b2_cost_equals_b2_trajectory"] = all(
        raw_typed.get(("A-B2-cost", seed_base + i), {}).get("trajectory_hash")
        == raw_typed.get(("B2-ko1", seed_base + i), {}).get("trajectory_hash")
        for i in range(seeds)
    )
    predictions["P2c_a_b3_cost_equals_ghost_trajectory"] = all(
        raw_typed.get(("A-B3-cost", seed_base + i), {}).get("trajectory_hash")
        == raw_typed.get(("ghost", seed_base + i), {}).get("trajectory_hash")
        for i in range(seeds)
    )
    p2b = True
    for i in range(seeds):
        seed = seed_base + i
        b2_rows = groups.get(("B2-ko1", seed), [])
        b1_rows = groups.get(("B1-sham", seed), [])
        target_equal = len(b2_rows) == len(b1_rows) and all(
            close(a["v"], b["v"]) and close(a["d"], b["d"]) and close(a["f"], b["f"])
            for a, b in zip(b2_rows, b1_rows)
        )
        b2_aurd, b1_aurd = finite_raw("B2-ko1", seed, "aurd"), finite_raw("B1-sham", seed, "aurd")
        b2_f, b1_f = finite_raw("B2-ko1", seed, "f_final"), finite_raw("B1-sham", seed, "f_final")
        if not (target_equal and b2_aurd is not None and b1_aurd is not None and close(b2_aurd, b1_aurd)
                and b2_f is not None and b1_f is not None and close(b2_f, b1_f)):
            p2b = False
    predictions["P2b_b2_equals_b1_recovery"] = p2b
    p3 = True
    for i in range(seeds):
        seed = seed_base + i
        f_final = finite_raw("B3-ko2", seed, "f_final")
        f_ko2 = finite_raw("B3-ko2", seed, "f_at_ko2")
        v_after = finite_raw("B3-ko2", seed, "v_after_ko2")
        frozen_steps = all(row["v"] == 0.0 for row in groups.get(("B3-ko2", seed), []) if row["step"] >= T_KO2)
        if not (f_final is not None and f_ko2 is not None and v_after == 0.0
                and close(f_final, f_ko2, 1e-15) and frozen_steps):
            p3 = False
    predictions["P3_b3_freezes_at_ko2"] = p3

    p4 = True
    for i in range(seeds):
        seed = seed_base + i
        b2 = finite_raw("B2-ko1", seed, "aurd")
        rescue = finite_raw("rescue", seed, "aurd")
        b3 = finite_raw("B3-ko2", seed, "aurd")
        v_after = finite_raw("rescue", seed, "v_after_rescue")
        resumed = any(row["v"] > 0.0 for row in groups.get(("rescue", seed), []) if row["step"] >= T_RESCUE)
        if not (b2 is not None and rescue is not None and b3 is not None and v_after is not None
                and v_after > 0.0 and resumed and b2 < rescue - STEP_MARGIN and rescue < b3 - STEP_MARGIN):
            p4 = False
    predictions["P4_rescue_resumes_and_orders"] = p4

    p5 = True
    for i in range(seeds):
        seed = seed_base + i
        full = finite_raw("A-control", seed, "aurd_abs")
        half = finite_raw("D-half", seed, "aurd_abs")
        third = finite_raw("D-third", seed, "aurd_abs")
        if not (full is not None and half is not None and third is not None and full > half > third):
            p5 = False
    predictions["P5_d_ladder_abs_monotone"] = p5

    for i in range(seeds):
        seed = seed_base + i
        ghost = raw_typed.get(("ghost", seed), {})
        b1 = raw_typed.get(("B1-sham", seed), {})
        ghost_aurd = finite_raw("ghost", seed, "aurd")
        b1_aurd = finite_raw("B1-sham", seed, "aurd")
        ghost_f = finite_raw("ghost", seed, "f_final")
        b1_f = finite_raw("B1-sham", seed, "f_final")
        ghost_rows = groups.get(("ghost", seed), [])
        b1_rows = groups.get(("B1-sham", seed), [])
        target_equal = len(ghost_rows) == len(b1_rows) and all(
            close(a["v"], b["v"]) and close(a["d"], b["d"]) and close(a["f"], b["f"])
            for a, b in zip(ghost_rows, b1_rows)
        )
        if not (target_equal
                and ghost_aurd is not None and b1_aurd is not None and close(ghost_aurd, b1_aurd)
                and ghost_f is not None and b1_f is not None and close(ghost_f, b1_f)
                and ghost.get("n_final") == 1):
            mark("ghost_control_valid", f"ghost/{seed}: fixed-capacity B3-schedule control does not reproduce B1")
        placebo_v = finite_raw("placebo-k1", seed, "v_after_ko2")
        placebo_f = finite_raw("placebo-k1", seed, "f_final")
        b3_f = finite_raw("B3-ko2", seed, "f_final")
        placebo_rows = groups.get(("placebo-k1", seed), [])
        if not (placebo_v is not None and placebo_v > 0.0
                and any(row["v"] > 0.0 for row in placebo_rows if row["step"] >= T_KO2)
                and placebo_f is not None and b3_f is not None and placebo_f > b3_f + EXACT_TOL):
            mark("placebo_control_valid", f"placebo-k1/{seed}: k_eff=1 control froze or failed to separate from B3")

    all_controls_valid = all(controls.values())
    if not all_controls_valid:
        outcome = "void"
        failed_controls = [key for key, value in controls.items() if not value]
        reason = "void: instrument/control failure: " + ", ".join(failed_controls)
    elif not all(predictions.values()):
        outcome = "failed"
        failed_predictions = [key for key, value in predictions.items() if not value]
        reason = "failed: controls valid; scientific prediction failure: " + ", ".join(failed_predictions)
    else:
        outcome = "passed"
        reason = "passed: all registered scientific predictions and controls hold; repeat is byte-identical"

    def metric_map(field: str) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for arm in ARMS:
            values = [finite_raw(arm, seed_base + i, field) for i in range(seeds)]
            result[arm] = sum(values) / len(values) if values and all(value is not None for value in values) else None
        return result

    primary = {
        "window_T": WINDOW_T,
        "schedule": "t*=5;t**=10;t***=15;m=3;k=2;R0=0.1;r0=0.05;D0=0.5",
        "aurd": metric_map("aurd"),
        "aurd_abs": metric_map("aurd_abs"),
        "f_final": metric_map("f_final"),
        "f_at_ko2_b3": metric_map("f_at_ko2")["B3-ko2"],
        "v_after_ko2": {arm: metric_map("v_after_ko2")[arm] for arm in ("B3-ko2", "placebo-k1", "ghost")},
        "rescue_margin_over_b2": None,
        "b3_margin_over_rescue": None,
    }
    margins = []
    for i in range(seeds):
        seed = seed_base + i
        b2, rescue, b3 = (finite_raw("B2-ko1", seed, "aurd"), finite_raw("rescue", seed, "aurd"), finite_raw("B3-ko2", seed, "aurd"))
        if b2 is not None and rescue is not None and b3 is not None:
            margins.append((rescue - b2, b3 - rescue))
    if margins:
        primary["rescue_margin_over_b2"] = sum(item[0] for item in margins) / len(margins)
        primary["b3_margin_over_rescue"] = sum(item[1] for item in margins) / len(margins)
    secondary = {
        "binary95": metric_map("binary95_10"),
        "t_reach95": metric_map("t_reach95"),
        "n_final": metric_map("n_final"),
        "maint_debt": metric_map("maint_debt"),
        "external_rescue_stock": metric_map("external_rescue_stock"),
        "holm": "disabled_deterministic_unit_test",
    }

    out.mkdir(parents=True, exist_ok=True)
    with (out / "per_arm.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_HEADER)
        writer.writeheader()
        writer.writerows(raw_rows)
    with (out / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["prediction", "kind", "holds"])
        for key, value in predictions.items():
            writer.writerow([key, "scientific", int(value)])
    with (out / "controls.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["control", "holds"])
        for key, value in controls.items():
            writer.writerow([key, int(value)])
    summary = {
        "schema": "analysis-b-unit/v2",
        "analyzer_version": ANALYZER_VERSION,
        "task_id": manifest.get("task_id"),
        "task_version": manifest.get("task_version"),
        "task_version_sha256": manifest.get("task_version_sha256"),
        "base_commit": manifest.get("base_commit"),
        "scientific_outcome": outcome,
        "reason": reason,
        "all_controls_valid": all_controls_valid,
        "controls": controls,
        "control_details": details,
        "predictions": predictions,
        "seeds": seeds,
        "seed_base": seed_base,
        "driver_rc": rc1,
        "run2_driver_rc": rc2,
        "schedule": manifest.get("executions", {}).get("run1", {}).get("driver_schedule_line"),
        "raw_sha256": manifest.get("raw_csv", {}).get("sha256"),
        "steps_sha256": manifest.get("steps_csv", {}).get("sha256"),
        "repeat": manifest.get("repeat"),
        "primary": primary,
        "secondary": secondary,
        "non_finite_metrics": non_finite_metrics,
    }
    (out / "summary.json").write_text(
        json.dumps(json_safe(summary), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8")
    return summary


def analyze(raw_path: Path, steps_path: Path, manifest_path: Path, out: Path) -> dict:
    """Return a void summary rather than crashing on malformed evidence."""
    try:
        return _analyze(raw_path, steps_path, manifest_path, out)
    except (AnalysisInputError, OSError, json.JSONDecodeError, ValueError,
            TypeError, KeyError, AttributeError, IndexError) as exc:
        manifest: dict = {}
        try:
            loaded = strict_json(manifest_path)
            if isinstance(loaded, dict):
                manifest = loaded
        except Exception:
            pass
        return empty_outputs(
            out, manifest, "void", f"void: analyzer input error: {exc}",
            {"input_validation_valid": False}, {},
            {"input_validation_valid": [str(exc)]},
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--steps", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        summary = analyze(args.raw, args.steps, args.manifest, args.out)
    except (AnalysisInputError, OSError, json.JSONDecodeError, ValueError) as exc:
        manifest = {}
        try:
            manifest = strict_json(args.manifest)
        except Exception:
            pass
        summary = empty_outputs(
            args.out, manifest if isinstance(manifest, dict) else {}, "void",
            f"void: analyzer input error: {exc}", {"input_validation_valid": False}, {},
            {"input_validation_valid": [str(exc)]},
        )
    print(json.dumps({
        "scientific_outcome": summary["scientific_outcome"],
        "reason": summary["reason"],
        "all_controls_valid": summary.get("all_controls_valid"),
        "predictions": summary.get("predictions", {}),
        "controls": summary.get("controls", {}),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
