#!/usr/bin/env python3
"""EXP-2026-4106 analyzer: exact CSV contract, KM, paired seed-cluster bootstrap.

Stdlib only. Primary and deferred cohorts are analyzed separately. Deferred data
never enter primary estimates or the primary bootstrap. An unidentified T90 is
never replaced by the horizon: it makes the affected analysis void.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, replace
import datetime as dt
import fnmatch
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import random
import re
import struct
from typing import Any, Iterable, Optional

TASK_ID = "EXP-2026-4106"
ANALYZER_VERSION = "we-analyze-1.0.0"
SCHEMA = "analysis-wear-erase/v1"
RUN_SCHEMA = "run-wear-erase/v1"
HEADER = [
    "cell", "cohort", "seed", "pair", "t_erase", "event_status", "applied",
    "wearA_before", "wearA_after", "wearB_before", "wearB_after",
    "qA_event", "dA_event", "eA_event", "qB_event", "dB_event", "eB_event",
    "state_hash", "lifeA", "censA", "lifeB", "censB",
]
CELLS = ("base", "erase600", "erase221", "sham600", "erand", "silent")
INFERENCE_CELLS = ("base", "erase600", "erase221")
ERASE_CELLS = ("erase600", "erase221", "erand")
EVENT_STATUSES = {"applied", "sham", "not_scheduled", "not_due_death", "horizon"}
PRIMARY_SEEDS = 12
DEFERRED_SEEDS = 8
PRIMARY_SEED_BASE = 5501
DEFERRED_SEED_BASE = 5513
PAIRS = 400
HORIZON = 5000
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20261128
DEFERRED_BOOTSTRAP_SEED = BOOTSTRAP_SEED + 1
T90_SURVIVAL = 0.10
QUANTILE_LEVELS = (0.75, 0.50, 0.25, 0.10, 0.05)
LANDMARK_TIMES = (221, 400, 600, 800, 1000, HORIZON)
LANDMARK_BINS = ((600, 700), (700, 800), (800, 900), (900, 1000))
OUTCOMES = {"passed", "failed", "void", "insensitive_by_construction"}
FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211
MASK64 = (1 << 64) - 1
INT_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
STATE_HASH_RE = re.compile(r"^[0-9a-f]{16}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
FINDING_PATH = f"docs/FINDING-{TASK_ID}.md"
ARTIFACT_ROOT = f"results/experiments/{TASK_ID}"


@dataclass(frozen=True)
class Grid:
    primary_count: int = PRIMARY_SEEDS
    deferred_count: int = DEFERRED_SEEDS
    primary_seed_base: int = PRIMARY_SEED_BASE
    deferred_seed_base: int = DEFERRED_SEED_BASE
    pairs: int = PAIRS
    horizon: int = HORIZON

    def seeds(self, cohort: str) -> tuple[int, ...]:
        if cohort == "primary":
            return tuple(range(self.primary_seed_base,
                               self.primary_seed_base + self.primary_count))
        if cohort == "deferred":
            return tuple(range(self.deferred_seed_base,
                               self.deferred_seed_base + self.deferred_count))
        raise ValueError(f"unknown cohort: {cohort}")

    def expected_rows(self, cohort: str) -> int:
        count = self.primary_count if cohort == "primary" else self.deferred_count
        return len(CELLS) * count * self.pairs

    def expected_argv(self, cohort: str) -> list[str]:
        if cohort == "primary":
            return ["exp_wear_erase", "--seeds", str(self.primary_count),
                    "--deferred", "0", "--seed-base", str(self.primary_seed_base),
                    "--pairs", str(self.pairs)]
        return ["exp_wear_erase", "--seeds", "0",
                "--deferred", str(self.deferred_count),
                "--seed-base", str(self.deferred_seed_base),
                "--pairs", str(self.pairs)]


PRODUCTION_GRID = Grid()


class ContractError(ValueError):
    """A provenance or artifact contract violation."""


@dataclass
class RawValidation:
    records: list[dict[str, Any]]
    row_count: int
    errors: list[str]
    controls: dict[str, bool]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                               allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_artifact_path(value: Any) -> str:
    """Return a canonical relative POSIX path accepted by control-plane intake."""
    if not isinstance(value, str) or not value:
        raise ContractError("artifact path must be a nonempty string")
    if "\0" in value or "\\" in value or ":" in value:
        raise ContractError(f"unsafe artifact path: {value!r}")
    path = PurePosixPath(value)
    if (path.is_absolute() or ".." in path.parts or "." in path.parts
            or value != path.as_posix() or any(char in value for char in "*?[")):
        raise ContractError(f"unsafe artifact path: {value!r}")
    return path.as_posix()


def logical_artifact_path(staged_path: str) -> str:
    """Map a staging path to the immutable path registered in task.write_scope."""
    staged = safe_artifact_path(staged_path)
    if staged == f"FINDING-{TASK_ID}.md":
        return FINDING_PATH
    if staged.startswith("run/"):
        staged = staged[4:]
    return f"{ARTIFACT_ROOT}/{staged}"


def path_in_write_scope(path: str, scopes: Any) -> bool:
    """Mirror the service's fail-closed write_scope matching for dry-runs."""
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
    document = read_json(path)
    if not isinstance(document, dict):
        raise ContractError("task payload must be a JSON object")
    for key in ("payload", "task"):
        if isinstance(document.get(key), dict):
            return document[key]
    return document


def validate_task_contract(task: dict[str, Any]) -> None:
    """Pin the production grid and bootstrap settings to the published task."""
    spec = task.get("spec")
    params = spec.get("parameters", {}) if isinstance(spec, dict) else {}
    if not isinstance(params, dict):
        raise ContractError("task spec.parameters must be an object")
    expected = {
        "primary_seed_count": PRIMARY_SEEDS,
        "deferred_seed_count": DEFERRED_SEEDS,
        "primary_seed_base": PRIMARY_SEED_BASE,
        "deferred_seed_base": DEFERRED_SEED_BASE,
        "pairs_per_cell_seed": PAIRS,
        "horizon": HORIZON,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "primary_bootstrap_seed": BOOTSTRAP_SEED,
        "deferred_bootstrap_seed": DEFERRED_BOOTSTRAP_SEED,
    }
    for key, value in expected.items():
        if params.get(key) != value:
            raise ContractError(f"task parameter {key} does not match the production contract")
    if spec.get("seeds") != list(PRODUCTION_GRID.seeds("primary") + PRODUCTION_GRID.seeds("deferred")):
        raise ContractError("task seeds do not match the production grid")


def validate_bootstrap_contract(summary: dict[str, Any]) -> None:
    bootstrap = summary.get("bootstrap")
    if not isinstance(bootstrap, dict):
        raise ContractError("summary has no bootstrap contract")
    expected = {"draws": BOOTSTRAP_DRAWS, "primary_seed": BOOTSTRAP_SEED,
                "deferred_seed": DEFERRED_BOOTSTRAP_SEED}
    for key, value in expected.items():
        if bootstrap.get(key) != value:
            raise ContractError(f"summary bootstrap {key} does not match the production contract")
    for cohort, seed in (("primary", BOOTSTRAP_SEED), ("deferred", DEFERRED_BOOTSTRAP_SEED)):
        result = summary.get(cohort)
        if isinstance(result, dict) and result.get("status") != "not_analyzed":
            cohort_bootstrap = result.get("bootstrap")
            if not isinstance(cohort_bootstrap, dict) or cohort_bootstrap.get("draws") != BOOTSTRAP_DRAWS \
                    or cohort_bootstrap.get("seed") != seed:
                raise ContractError(f"summary {cohort} bootstrap does not match the production contract")


def _plain_int(value: Any, label: str, minimum: Optional[int] = None,
               maximum: Optional[int] = None) -> int:
    if isinstance(value, bool):
        raise ContractError(f"{label} must be an integer")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and INT_RE.fullmatch(value):
        number = int(value)
    else:
        raise ContractError(f"{label} must be a decimal integer")
    if minimum is not None and number < minimum:
        raise ContractError(f"{label} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ContractError(f"{label} must be <= {maximum}")
    return number


def load_task_identity(path: Path) -> dict[str, Any]:
    """Accept raw task/v1, {payload: task}, or {task: task} wrapper formats.

    The service-issued task_version_sha256 is validated for shape and agreement,
    not recomputed from an invented canonicalization.
    """
    document = read_json(path)
    if not isinstance(document, dict):
        raise ContractError("task payload must be a JSON object")
    if document.get("draft_only") is True or document.get("do_not_execute") is True:
        raise ContractError("draft task payload must be finalized and published before execution")
    if isinstance(document.get("payload"), dict):
        task = document["payload"]
        outer_hash = document.get("task_version_sha256", document.get("current_sha256"))
        outer_version = document.get("task_version", document.get("current_version"))
    elif isinstance(document.get("task"), dict):
        task = document["task"]
        outer_hash = document.get("task_version_sha256")
        outer_version = document.get("task_version")
    else:
        task = document
        outer_hash = None
        outer_version = None
    if task.get("schema") != "task/v1" or task.get("id") != TASK_ID:
        raise ContractError(f"task payload is not task/v1 for {TASK_ID}")
    version = _plain_int(task.get("version"), "task version", 1)
    if outer_version is not None and _plain_int(outer_version, "wrapper task version", 1) != version:
        raise ContractError("wrapper/task version mismatch")
    inner_hash = task.get("task_version_sha256")
    if inner_hash is not None and (not isinstance(inner_hash, str)
                                   or not HASH_RE.fullmatch(inner_hash)):
        raise ContractError("invalid inner task_version_sha256")
    if outer_hash is not None and (not isinstance(outer_hash, str)
                                   or not HASH_RE.fullmatch(outer_hash)):
        raise ContractError("invalid wrapper task_version_sha256")
    if inner_hash is not None and outer_hash is not None and inner_hash != outer_hash:
        raise ContractError("wrapper/task version hash mismatch")
    task_hash = inner_hash or outer_hash
    if task_hash is None:
        raise ContractError("task payload has no task_version_sha256")
    if task_hash == "0" * 64:
        raise ContractError("task payload still has the draft task_version_sha256 placeholder")
    base = task.get("base_commit")
    if not isinstance(base, str) or not COMMIT_RE.fullmatch(base):
        raise ContractError("task payload has no valid 7..40-hex base_commit")
    if not base.strip("0"):
        raise ContractError("task payload still has the draft base_commit placeholder")
    return {
        "task_id": TASK_ID,
        "task_version": version,
        "task_version_sha256": task_hash,
        "base_commit": base,
        "task_payload_sha256": sha256_file(path),
    }


def identity_from_manifest(manifest: Any) -> Optional[dict[str, Any]]:
    if not isinstance(manifest, dict):
        return None
    try:
        version = _plain_int(manifest.get("task_version"), "manifest task version", 1)
        task_hash = manifest.get("task_version_sha256")
        base = manifest.get("base_commit")
        if manifest.get("task_id") != TASK_ID:
            return None
        if not isinstance(task_hash, str) or not HASH_RE.fullmatch(task_hash):
            return None
        if not isinstance(base, str) or not COMMIT_RE.fullmatch(base):
            return None
        return {
            "task_id": TASK_ID,
            "task_version": version,
            "task_version_sha256": task_hash,
            "base_commit": base,
            "task_payload_sha256": manifest.get("task_payload_sha256"),
        }
    except ContractError:
        return None


def require_identity(document: Any, identity: dict[str, Any], label: str) -> None:
    if not isinstance(document, dict):
        raise ContractError(f"{label} is not an object")
    checks = (
        ("task_id", identity["task_id"]),
        ("task_version", identity["task_version"]),
        ("task_version_sha256", identity["task_version_sha256"]),
        ("base_commit", identity["base_commit"]),
    )
    for key, expected in checks:
        if document.get(key) != expected:
            raise ContractError(f"{label} {key} mismatch")
    payload_hash = document.get("task_payload_sha256")
    if payload_hash is not None and payload_hash != identity["task_payload_sha256"]:
        raise ContractError(f"{label} task_payload_sha256 mismatch")


def compute_state_hash(q_a: float, d_a: float, e_a: float, wear_a_after: float,
                       q_b: float, d_b: float, e_b: float,
                       wear_b_after: float) -> str:
    """FNV-1a-64 over little-endian IEEE-754 raw bits of eight post-event values."""
    raw = struct.pack("<8d", q_a, d_a, e_a, wear_a_after,
                      q_b, d_b, e_b, wear_b_after)
    value = FNV_OFFSET
    for byte in raw:
        value ^= byte
        value = (value * FNV_PRIME) & MASK64
    return f"{value:016x}"


def _csv_float(value: str, label: str, line: int,
               errors: list[str], nonnegative: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"line {line}: {label} is not a float")
        return None
    if not math.isfinite(number):
        errors.append(f"line {line}: {label} is not finite")
        return None
    if nonnegative and number < 0:
        errors.append(f"line {line}: {label} is negative")
        return None
    return number


def _csv_int(value: str, label: str, line: int, errors: list[str],
             minimum: int = 0, maximum: Optional[int] = None) -> Optional[int]:
    if not isinstance(value, str) or not INT_RE.fullmatch(value):
        errors.append(f"line {line}: {label} is not a decimal integer")
        return None
    number = int(value)
    if number < minimum or (maximum is not None and number > maximum):
        errors.append(f"line {line}: {label} is out of range")
        return None
    return number


def _ledger_errors(row: dict[str, Any], grid: Grid) -> list[str]:
    errors: list[str] = []
    cell = row["cell"]
    status = row["event_status"]
    applied = row["applied"]
    t_erase = row["t_erase"]
    life_a = row["lifeA"]
    life_b = row["lifeB"]
    cens_a = row["censA"]
    expected_t = {"base": 0, "silent": 0, "erase600": 600,
                  "erase221": 221, "sham600": 600}.get(cell)
    if expected_t is not None and t_erase != expected_t:
        errors.append(f"{cell}: t_erase must be {expected_t}")
    if cens_a == 1 and life_a != grid.horizon:
        errors.append("censA=1 requires right-censoring at the horizon")
    if row["censB"] == 1 and row["lifeB"] != grid.horizon:
        errors.append("censB=1 requires right-censoring at the horizon")
    if cell == "erand" and not 600 <= t_erase < 1000:
        errors.append("erand: t_erase must be in [600,1000)")
    if status not in EVENT_STATUSES:
        errors.append(f"unknown event_status {status!r}")
        return errors
    if cell in {"base", "silent"}:
        if status != "not_scheduled" or applied != 0:
            errors.append(f"{cell}: expected not_scheduled and applied=0")
    elif status == "applied":
        if cell not in ERASE_CELLS or applied != 1:
            errors.append("applied status requires an erase cell and applied=1")
        if life_a < t_erase or life_b < t_erase:
            errors.append("applied event occurs after death of either arm")
        if row["wearA_after"] != 0.0:
            errors.append("applied=1 requires wearA_after=0")
    elif status == "sham":
        if cell != "sham600" or applied != 0:
            errors.append("sham status requires sham600 and applied=0")
        if life_a < t_erase or life_b < t_erase:
            errors.append("sham event occurs after death of either arm")
    elif status == "not_due_death":
        if applied != 0 or not (life_a < t_erase or life_b < t_erase):
            errors.append("not_due_death requires applied=0 and death of either arm before t_erase")
    elif status == "horizon":
        # Reserved for a scheduled event beyond the horizon. All registered
        # erasure times are <1000 and the horizon is 5000, so this is invalid in
        # the fixed 4106 grid rather than an alternate outcome to silently use.
        errors.append("horizon event status is incompatible with t_erase<horizon")
    if status in {"not_scheduled", "not_due_death", "horizon"}:
        if row["wearA_before"] != row["wearA_after"]:
            errors.append("wearA changed without an applied/sham event")
        if row["wearB_before"] != row["wearB_after"]:
            errors.append("wearB changed without an applied/sham event")
    if status == "sham":
        if row["wearA_before"] != row["wearA_after"]:
            errors.append("sham changed wearA")
        if row["wearB_before"] != row["wearB_after"]:
            errors.append("sham changed wearB")
    return errors


def validate_raw(path: Path, cohort: str, grid: Grid = PRODUCTION_GRID) -> RawValidation:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    controls = {"schema_and_grid": True, "state_hash": True,
                "full_ledger": True, "event_qde_equal": True}
    seen: set[tuple[str, int, int]] = set()
    expected_keys = {(cell, seed, pair) for cell in CELLS
                     for seed in grid.seeds(cohort) for pair in range(grid.pairs)}
    row_count = 0
    try:
        handle = path.open(newline="", encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot open raw CSV: {exc}")
        controls["schema_and_grid"] = False
        return RawValidation(records, row_count, errors, controls)
    with handle:
        reader = csv.reader(handle)
        try:
            actual_header = next(reader)
        except StopIteration:
            errors.append("raw CSV is empty")
            controls["schema_and_grid"] = False
            return RawValidation(records, row_count, errors, controls)
        if actual_header != HEADER:
            errors.append(f"exact header mismatch: expected {HEADER}, got {actual_header}")
            controls["schema_and_grid"] = False
            return RawValidation(records, row_count, errors, controls)
        for values in reader:
            row_count += 1
            line = reader.line_num
            if len(values) != len(HEADER):
                errors.append(f"line {line}: expected {len(HEADER)} fields, got {len(values)}")
                controls["schema_and_grid"] = False
                continue
            raw = dict(zip(HEADER, values))
            row_errors: list[str] = []
            cell = raw["cell"]
            if cell not in CELLS:
                row_errors.append(f"unknown cell {cell!r}")
            if raw["cohort"] != cohort:
                row_errors.append(f"cohort must be {cohort!r}")
            status = raw["event_status"]
            if status not in EVENT_STATUSES:
                row_errors.append(f"unknown event_status {status!r}")
            seed = _csv_int(raw["seed"], "seed", line, row_errors)
            pair = _csv_int(raw["pair"], "pair", line, row_errors)
            t_erase = _csv_int(raw["t_erase"], "t_erase", line, row_errors)
            applied = _csv_int(raw["applied"], "applied", line, row_errors, 0, 1)
            life_a = _csv_int(raw["lifeA"], "lifeA", line, row_errors, 1, grid.horizon)
            life_b = _csv_int(raw["lifeB"], "lifeB", line, row_errors, 1, grid.horizon)
            cens_a = _csv_int(raw["censA"], "censA", line, row_errors, 0, 1)
            cens_b = _csv_int(raw["censB"], "censB", line, row_errors, 0, 1)
            floats: dict[str, Optional[float]] = {}
            for name in ("wearA_before", "wearA_after", "wearB_before", "wearB_after"):
                floats[name] = _csv_float(raw[name], name, line, row_errors, nonnegative=True)
            for name in ("qA_event", "dA_event", "eA_event",
                         "qB_event", "dB_event", "eB_event"):
                floats[name] = _csv_float(raw[name], name, line, row_errors)
            schema_bad = bool(row_errors)
            if schema_bad:
                errors.extend(row_errors)
                controls["schema_and_grid"] = False
                continue
            row: dict[str, Any] = {
                "cell": cell, "cohort": cohort, "seed": seed, "pair": pair,
                "t_erase": t_erase, "event_status": status, "applied": applied,
                "lifeA": life_a, "censA": cens_a, "lifeB": life_b, "censB": cens_b,
                "state_hash": raw["state_hash"], **floats,
            }
            key = (cell, seed, pair)
            if key in seen or key not in expected_keys:
                row_errors.append(f"duplicate or unexpected key {key}")
                controls["schema_and_grid"] = False
            seen.add(key)
            if not STATE_HASH_RE.fullmatch(row["state_hash"]):
                row_errors.append("state_hash must be 16 lowercase hex characters")
                controls["state_hash"] = False
            else:
                expected_hash = compute_state_hash(
                    row["qA_event"], row["dA_event"], row["eA_event"], row["wearA_after"],
                    row["qB_event"], row["dB_event"], row["eB_event"], row["wearB_after"])
                if row["state_hash"] != expected_hash:
                    row_errors.append("state_hash does not match raw snapshot bits")
                    controls["state_hash"] = False
            if struct.pack("<3d", row["qA_event"], row["dA_event"], row["eA_event"]) != \
                    struct.pack("<3d", row["qB_event"], row["dB_event"], row["eB_event"]):
                row_errors.append("q/D/e snapshots differ between arms")
                controls["event_qde_equal"] = False
            ledger = _ledger_errors(row, grid)
            if ledger:
                row_errors.extend(ledger)
                controls["full_ledger"] = False
            if row_errors:
                errors.extend(f"line {line}: {message}" for message in row_errors)
            records.append(row)
    if row_count != grid.expected_rows(cohort):
        errors.append(f"row count {row_count}, expected {grid.expected_rows(cohort)}")
        controls["schema_and_grid"] = False
    missing = expected_keys - seen
    if missing:
        errors.append(f"missing {len(missing)} cell/seed/pair keys; first: {sorted(missing)[:3]}")
        controls["schema_and_grid"] = False
    return RawValidation(records, row_count, errors, controls)


def validate_manifest(manifest: Any, raw_path: Path, cohort: str,
                      grid: Grid = PRODUCTION_GRID,
                      task_identity: Optional[dict[str, Any]] = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    if manifest.get("schema") != RUN_SCHEMA:
        errors.append("unexpected run manifest schema")
    if manifest.get("cohort") != cohort:
        errors.append("manifest cohort mismatch")
    identity = identity_from_manifest(manifest)
    if identity is None:
        errors.append("manifest task id/version/hash/base is invalid or incomplete")
    elif task_identity is not None:
        try:
            require_identity(manifest, task_identity, "manifest")
        except ContractError as exc:
            errors.append(str(exc))
    rcs = manifest.get("driver_rcs")
    if not isinstance(rcs, dict) or rcs.get(cohort) != 0:
        errors.append("driver return code is missing or nonzero")
    argv = manifest.get("argv", {}).get(cohort) if isinstance(manifest.get("argv"), dict) else None
    if argv != grid.expected_argv(cohort):
        errors.append(f"argv mismatch: expected {grid.expected_argv(cohort)}")
    raw_info = manifest.get("cohorts", {}).get(cohort, {}).get("raw_csv") \
        if isinstance(manifest.get("cohorts"), dict) else None
    if not isinstance(raw_info, dict):
        errors.append("manifest has no raw_csv metadata")
    else:
        if raw_info.get("rows") != grid.expected_rows(cohort):
            errors.append("manifest raw row count mismatch")
        try:
            actual = sha256_file(raw_path)
        except OSError as exc:
            errors.append(f"cannot hash raw CSV: {exc}")
        else:
            if raw_info.get("sha256") != actual:
                errors.append("raw CSV SHA256 mismatch")
    driver = manifest.get("driver", {})
    driver_hash = driver.get("sha256") if isinstance(driver, dict) else None
    if not isinstance(driver_hash, str) or not HASH_RE.fullmatch(driver_hash):
        errors.append("manifest driver SHA256 is invalid")
    source_hash = driver.get("source_sha256") if isinstance(driver, dict) else None
    if not isinstance(source_hash, str) or not HASH_RE.fullmatch(source_hash):
        errors.append("manifest driver source SHA256 is missing or invalid")
    return errors


def validate_root_manifest(manifest: Any, environment: dict[str, Any],
                           cohort_manifests: dict[str, Any],
                           task_identity: dict[str, Any],
                           grid: Grid = PRODUCTION_GRID) -> list[str]:
    """Cross-check the aggregate runner manifest against both cohort ledgers."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["root manifest is not a JSON object"]
    if manifest.get("schema") != RUN_SCHEMA:
        errors.append("unexpected root manifest schema")
    try:
        require_identity(manifest, task_identity, "root manifest")
    except ContractError as exc:
        errors.append(str(exc))
    driver = manifest.get("driver")
    if not isinstance(driver, dict):
        errors.append("root manifest driver metadata is missing")
    else:
        driver_hash = driver.get("sha256")
        source_hash = driver.get("source_sha256")
        if not isinstance(driver_hash, str) or not HASH_RE.fullmatch(driver_hash):
            errors.append("root manifest driver SHA256 is missing or invalid")
        if driver_hash != environment.get("driver_sha256"):
            errors.append("root manifest/environment driver hash mismatch")
        if not isinstance(source_hash, str) or not HASH_RE.fullmatch(source_hash):
            errors.append("root manifest driver source SHA256 is missing or invalid")
        if source_hash != environment.get("driver_source_sha256"):
            errors.append("root manifest/environment driver source hash mismatch")
    rcs = manifest.get("driver_rcs")
    if rcs != {cohort: 0 for cohort in ("primary", "deferred")}:
        errors.append("root manifest driver return codes are not exactly zero")
    expected_argv = {cohort: grid.expected_argv(cohort)
                     for cohort in ("primary", "deferred")}
    if manifest.get("argv") != expected_argv:
        errors.append("root manifest argv mismatch")
    expected_grid = {"primary_seeds": grid.primary_count,
                     "deferred_seeds": grid.deferred_count,
                     "primary_seed_base": grid.primary_seed_base,
                     "deferred_seed_base": grid.deferred_seed_base,
                     "pairs": grid.pairs, "horizon": grid.horizon}
    if manifest.get("grid") != expected_grid:
        errors.append("root manifest grid mismatch")
    cohorts = manifest.get("cohorts")
    if not isinstance(cohorts, dict):
        errors.append("root manifest cohorts metadata is missing")
        cohorts = {}
    for cohort in ("primary", "deferred"):
        source = cohort_manifests.get(cohort)
        if not isinstance(source, dict) or not isinstance(source.get("cohorts"), dict):
            errors.append(f"{cohort} manifest is unavailable for root cross-check")
            continue
        if cohorts.get(cohort) != source["cohorts"].get(cohort):
            errors.append(f"root/{cohort} cohort metadata mismatch")
    return errors


def build_groups(records: Iterable[dict[str, Any]]) -> dict:
    groups: dict[str, dict[str, dict[int, dict[int, dict[str, Any]]]]] = {}
    for row in records:
        groups.setdefault(row["cohort"], {}).setdefault(row["cell"], {}) \
            .setdefault(row["seed"], {})[row["pair"]] = row
    return groups


def _rows_for(groups: dict, cohort: str, cell: str) -> dict[int, dict[int, dict[str, Any]]]:
    return groups.get(cohort, {}).get(cell, {})


def _projection(row: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    return (row["seed"], row["pair"], row["lifeA"], row["censA"],
            row["lifeB"], row["censB"])


def _paired_control(groups: dict, cohort: str, cell: str, grid: Grid,
                    compare_cells: bool = False, require_censor: bool = True) -> tuple[bool, int, int]:
    by_seed = _rows_for(groups, cohort, cell)
    base = _rows_for(groups, cohort, "base") if compare_cells else None
    checked = 0
    violations = 0
    for seed in grid.seeds(cohort):
        for pair in range(grid.pairs):
            row = by_seed.get(seed, {}).get(pair)
            if row is None:
                violations += 1
                continue
            checked += 1
            if compare_cells:
                other = base.get(seed, {}).get(pair)
                if other is None or _projection(row) != _projection(other):
                    violations += 1
            elif row["lifeA"] != row["lifeB"] or (
                    require_censor and row["censA"] != row["censB"]):
                violations += 1
    return checked > 0 and violations == 0, checked, violations


def _collapse_control(groups: dict, cohort: str, cell: str, grid: Grid,
                      conditional: bool = False) -> tuple[bool, int, int, int]:
    by_seed = _rows_for(groups, cohort, cell)
    eligible = 0
    applied = 0
    violations = 0
    for seed in grid.seeds(cohort):
        for pair in range(grid.pairs):
            row = by_seed.get(seed, {}).get(pair)
            if row is None:
                violations += 1
                continue
            if conditional:
                selected = (row["applied"] == 1 and row["lifeA"] >= row["t_erase"]
                            and row["lifeB"] >= row["t_erase"])
            else:
                selected = row["applied"] == 1
            if not selected:
                continue
            eligible += 1
            if row["applied"] == 1:
                applied += 1
            if (row["lifeA"], row["censA"]) != (row["lifeB"], row["censB"]):
                violations += 1
    return eligible > 0 and violations == 0, eligible, applied, violations


def km_groups(by_seed: dict[int, dict[int, dict[str, Any]]], arm: str,
              grid: Grid) -> dict[int, list[tuple[int, list[int], list[int]]]]:
    """Group deaths/censors by time; both remain in the risk set at that time."""
    result = {}
    life = "lifeA" if arm == "A" else "lifeB"
    cens = "censA" if arm == "A" else "censB"
    for seed, by_pair in by_seed.items():
        items = sorted((by_pair[pair][life], by_pair[pair][cens], pair)
                       for pair in range(grid.pairs) if pair in by_pair)
        grouped: list[tuple[int, list[int], list[int]]] = []
        index = 0
        while index < len(items):
            time = items[index][0]
            deaths: list[int] = []
            censored: list[int] = []
            while index < len(items) and items[index][0] == time:
                _time, flag, pair = items[index]
                (censored if flag == 1 else deaths).append(pair)
                index += 1
            grouped.append((time, deaths, censored))
        result[seed] = grouped
    return result


def km_curve(groups: list[tuple[int, list[int], list[int]]],
             counts: Optional[list[int]] = None) -> list[tuple[float, float, int, int, int]]:
    """Return (time, survival, at_risk, deaths, censored), deaths before censors."""
    if counts is None:
        total = sum(len(deaths) + len(censored) for _t, deaths, censored in groups)
    else:
        total = sum(counts)
    at_risk = total
    survival = 1.0
    curve: list[tuple[float, float, int, int, int]] = []
    for time, deaths, censored in groups:
        if counts is None:
            death_count = len(deaths)
            censor_count = len(censored)
        else:
            death_count = sum(counts[pair] for pair in deaths)
            censor_count = sum(counts[pair] for pair in censored)
        if at_risk <= 0:
            break
        if death_count:
            survival *= 1.0 - death_count / at_risk
        curve.append((float(time), survival, at_risk, death_count, censor_count))
        at_risk -= death_count + censor_count
    return curve


def km_quantile(curve: list[tuple[float, float, int, int, int]],
                level: float) -> Optional[float]:
    for time, survival, _risk, _deaths, _censored in curve:
        if survival <= level + 1e-12:
            return time
    return None


def km_survival_at(curve: list[tuple[float, float, int, int, int]],
                   time: int) -> float:
    value = 1.0
    for event_time, survival, _risk, _deaths, _censored in curve:
        if event_time > time:
            break
        value = survival
    return value


def t90_from_groups(groups: list[tuple[int, list[int], list[int]]],
                    counts: list[int]) -> Optional[float]:
    at_risk = sum(counts)
    survival = 1.0
    for _time, deaths, censored in groups:
        death_count = sum(counts[pair] for pair in deaths)
        if death_count:
            survival *= 1.0 - death_count / at_risk
            if survival <= T90_SURVIVAL + 1e-12:
                return float(_time)
        at_risk -= death_count + sum(counts[pair] for pair in censored)
        if at_risk <= 0:
            break
    return None


def mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def percentile(ordered: list[float], probability: float) -> float:
    if not ordered:
        raise ValueError("percentile of empty sample")
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def ci95(draws: list[Optional[float]]) -> Optional[list[float]]:
    if not draws or any(value is None for value in draws):
        return None
    ordered = sorted(float(value) for value in draws)
    return [percentile(ordered, 0.025), percentile(ordered, 0.975)]


def directional_p(draws: list[Optional[float]], direction: str) -> Optional[float]:
    """Plus-one bootstrap tail probability; direction is 'greater' or 'less'."""
    if not draws or any(value is None for value in draws):
        return None
    values = [float(value) for value in draws]
    if direction == "greater":
        extreme = sum(value <= 0.0 for value in values)
    elif direction == "less":
        extreme = sum(value >= 0.0 for value in values)
    else:
        raise ValueError("direction must be greater or less")
    return min(1.0, (extreme + 1.0) / (len(values) + 1.0))


def holm_adjust(p_values: dict[str, Optional[float]]) -> dict[str, Optional[float]]:
    """Holm step-down adjusted p-values; deterministic tie order by name."""
    if any(value is None for value in p_values.values()):
        return {name: None for name in p_values}
    ordered = sorted(p_values, key=lambda name: (float(p_values[name]), name))
    adjusted: dict[str, Optional[float]] = {}
    running = 0.0
    family_size = len(ordered)
    for index, name in enumerate(ordered):
        running = max(running, (family_size - index) * float(p_values[name]))
        adjusted[name] = min(1.0, running)
    return adjusted


def _bootstrap(cohort: str, cell_km: dict, grid: Grid, draws: int,
               seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    seeds = grid.seeds(cohort)
    cell_draws: dict[str, list[Optional[float]]] = {cell: [] for cell in CELLS}
    contrast_draws: dict[str, list[Optional[float]]] = {
        "P2_erase600_minus_base": [], "P3_erase221_minus_base": [],
        "P5_base": [],
    }
    invalid_by_cell = {cell: 0 for cell in CELLS}
    for _draw in range(draws):
        sampled_seeds = [rng.choice(seeds) for _index in seeds]
        per_cell: dict[str, list[Optional[float]]] = {cell: [] for cell in CELLS}
        invalid_draw = False
        for sampled_seed in sampled_seeds:
            counts = [0] * grid.pairs
            for _index in range(grid.pairs):
                counts[rng.randrange(grid.pairs)] += 1
            for cell in CELLS:
                km = cell_km[cell][sampled_seed]
                t_a = t90_from_groups(km["A"], counts)
                t_b = t90_from_groups(km["B"], counts)
                if t_a is None or t_b is None:
                    invalid_by_cell[cell] += 1
                    per_cell[cell].append(None)
                    if cell in INFERENCE_CELLS:
                        invalid_draw = True
                else:
                    per_cell[cell].append(t_a - t_b)
        draw_means: dict[str, Optional[float]] = {}
        for cell in CELLS:
            values = per_cell[cell]
            value = None if any(item is None for item in values) else mean(values)
            draw_means[cell] = value
            cell_draws[cell].append(value)
        if invalid_draw:
            for name in contrast_draws:
                contrast_draws[name].append(None)
        else:
            base = float(draw_means["base"])
            contrast_draws["P2_erase600_minus_base"].append(
                float(draw_means["erase600"]) - base)
            contrast_draws["P3_erase221_minus_base"].append(
                float(draw_means["erase221"]) - base)
            contrast_draws["P5_base"].append(base)
    invalid_draws = sum(value is None for value in contrast_draws["P3_erase221_minus_base"])
    return {
        "status": "identified" if invalid_draws == 0 else "unidentifiable",
        "draws": draws,
        "seed": seed,
        "invalid_draws": invalid_draws,
        "invalid_by_cell": invalid_by_cell,
        "cell_draws": cell_draws,
        "contrast_draws": contrast_draws,
    }


def _landmark_rows(groups: dict, cohort: str, grid: Grid) -> list[dict[str, Any]]:
    rows = _rows_for(groups, cohort, "erand")
    output: list[dict[str, Any]] = []
    strata: list[tuple[str, str]] = []
    for low, high in LANDMARK_BINS:
        strata.append(("t_erase_bin", f"[{low},{high})"))
    strata.extend((("survival_to_erase", "0"), ("survival_to_erase", "1")))
    for dimension, label in strata:
        selected = []
        for seed in grid.seeds(cohort):
            for pair in range(grid.pairs):
                row = rows.get(seed, {}).get(pair)
                if row is None:
                    continue
                if dimension == "t_erase_bin":
                    low, high = (int(label[1:label.index(",")]),
                                 int(label[label.index(",") + 1:label.index(")")]))
                    belongs = low <= row["t_erase"] < high
                else:
                    belongs = (row["lifeA"] >= row["t_erase"]
                               and row["lifeB"] >= row["t_erase"]) == (label == "1")
                if belongs:
                    selected.append(row)
        applied = [row for row in selected if row["applied"] == 1]
        collapsed = [row for row in applied
                     if (row["lifeA"], row["censA"]) == (row["lifeB"], row["censB"])]
        output.append({
            "cohort": cohort, "dimension": dimension, "stratum": label,
            "scheduled_n": len(selected), "applied_n": len(applied),
            "collapsed_among_applied_n": len(collapsed),
            "collapse_given_applied": (len(collapsed) / len(applied) if applied else None),
            "unconditional_applied_fraction": (len(applied) / len(selected) if selected else None),
        })
    return output


def _distribution(per_seed: list[dict[str, Any]], cohort: str,
                  cell: str) -> list[dict[str, Any]]:
    selected = [row for row in per_seed if row["cohort"] == cohort and row["cell"] == cell]
    output: list[dict[str, Any]] = []
    for level in QUANTILE_LEVELS:
        a_values = [row[f"q{int(level * 100):02d}_A"] for row in selected]
        b_values = [row[f"q{int(level * 100):02d}_B"] for row in selected]
        identified = bool(a_values) and all(value is not None for value in a_values + b_values)
        a = mean(float(value) for value in a_values) if identified else None
        b = mean(float(value) for value in b_values) if identified else None
        output.append({"cohort": cohort, "cell": cell, "metric": "quantile",
                       "level": level, "time": None, "value_A": a, "value_B": b,
                       "difference_A_minus_B": (a - b if identified else None),
                       "identified": identified})
    # Survival means are stored temporarily in private keys, then removed by the
    # CSV/JSON serializer. They are means of per-seed KM curves, not pooled pairs.
    for time in LANDMARK_TIMES:
        a_values = [row["_curves"][f"survival_A_{time}"] for row in selected]
        b_values = [row["_curves"][f"survival_B_{time}"] for row in selected]
        a = mean(a_values) if a_values else None
        b = mean(b_values) if b_values else None
        output.append({"cohort": cohort, "cell": cell, "metric": "survival",
                       "level": None, "time": time, "value_A": a, "value_B": b,
                       "difference_A_minus_B": (a - b if a is not None and b is not None else None),
                       "identified": a is not None and b is not None})
    return output


def _evaluate_predictions(point: dict[str, Optional[float]],
                          bootstrap: dict[str, Any]) -> tuple[dict, dict, dict]:
    contrasts = {
        "P2_erase600_shift": {
            "estimate": (point["erase600"] - point["base"]
                         if point["erase600"] is not None and point["base"] is not None else None),
            "direction": "greater", "draw_key": "P2_erase600_minus_base"},
        "P3_erase221_primary": {
            "estimate": (point["erase221"] - point["base"]
                         if point["erase221"] is not None and point["base"] is not None else None),
            "direction": "greater", "draw_key": "P3_erase221_minus_base"},
        "P5_base_replication": {
            "estimate": point["base"], "direction": "less", "draw_key": "P5_base"},
    }
    raw_p: dict[str, Optional[float]] = {}
    details: dict[str, Any] = {}
    for name, spec in contrasts.items():
        draws = bootstrap["contrast_draws"].get(spec["draw_key"], [])
        interval = ci95(draws)
        p_value = directional_p(draws, spec["direction"])
        raw_p[name] = p_value
        details[name] = {**spec, "ci95": interval, "p_directional": p_value,
                         "p_holm": None, "holds": None}
    adjusted = holm_adjust({"P2_erase600_shift": raw_p["P2_erase600_shift"],
                            "P5_base_replication": raw_p["P5_base_replication"]})
    for name in ("P2_erase600_shift", "P5_base_replication"):
        details[name]["p_holm"] = adjusted[name]
    if bootstrap["status"] == "identified" and all(
            point[cell] is not None for cell in INFERENCE_CELLS):
        for name, spec in details.items():
            estimate = spec["estimate"]
            direction_ok = estimate > 0 if spec["direction"] == "greater" else estimate < 0
            if name == "P3_erase221_primary":
                spec["holds"] = bool(direction_ok and spec["ci95"][0] > 0.0)
            else:
                spec["holds"] = bool(direction_ok and spec["p_holm"] < 0.05)
    return details, raw_p, adjusted


def _decision(cohort_result: dict[str, Any]) -> tuple[str, str]:
    if not all(cohort_result["controls"].values()):
        failed = [name for name, holds in cohort_result["controls"].items() if not holds]
        return "void", "instrument/provenance control failed: " + ", ".join(failed)
    if not cohort_result["sensitivity"]["erase_event_changes_wear"]:
        return ("insensitive_by_construction",
                "no applied erase event in this cohort had nonzero wearA_before; the carrier was never perturbed")
    predictions = cohort_result["predictions"]
    primary = predictions.get("P3_erase221_primary")
    if primary is None or primary["holds"] is not True:
        return "failed", "the sole primary scientific contrast P3 was not confirmed"
    return "passed", "all instrument controls hold and the sole primary contrast P3 is confirmed"


def analyze_cohort(validation: RawValidation, manifest_errors: list[str],
                   cohort: str, grid: Grid, draws: int, bootstrap_seed: int) -> dict[str, Any]:
    groups = build_groups(validation.records)
    p1 = _collapse_control(groups, cohort, "erase600", grid, conditional=True)
    p4 = _paired_control(groups, cohort, "sham600", grid, compare_cells=True)
    silent = _paired_control(groups, cohort, "silent", grid, require_censor=False)
    p6 = _collapse_control(groups, cohort, "erand", grid, conditional=False)
    controls = {
        "schema_and_grid": validation.controls["schema_and_grid"] and not manifest_errors,
        "state_hash": validation.controls["state_hash"],
        "full_ledger": validation.controls["full_ledger"],
        "event_qde_equal": validation.controls["event_qde_equal"],
        "P1_conditional_collapse_erase600": p1[0],
        "P4_sham_base_canonical_projection": p4[0],
        "silent_paired_life_identity": silent[0],
        "P6_exact_collapse_among_erand_applied": p6[0],
        "T90_identifiable": False,
    }
    details = {
        "P1": {"eligible_lifeA_ge_600": p1[1], "applied": p1[2], "violations": p1[3]},
        "P4": {"checked": p4[1], "violations": p4[2]},
        "silent": {"checked": silent[1], "violations": silent[2]},
        "P6": {"applied": p6[2], "violations": p6[3]},
        "validation_errors": validation.errors[:100],
        "validation_error_count": len(validation.errors),
        "manifest_errors": manifest_errors,
    }
    result: dict[str, Any] = {
        "cohort": cohort, "controls": controls, "control_details": details,
        "rows": validation.row_count, "expected_rows": grid.expected_rows(cohort),
        "mean_delta_t90": {cell: None for cell in CELLS},
        "ci95_bootstrap": {cell: None for cell in CELLS},
        "predictions": {}, "per_seed": [], "distribution": [],
        "landmarks": _landmark_rows(groups, cohort, grid),
        "sensitivity": {
            "applied_erase_rows": 0,
            "applied_erase_rows_with_nonzero_wear_before": 0,
            "erase_event_changes_wear": False,
        },
        "bootstrap": {"status": "not_run", "draws": draws, "seed": bootstrap_seed,
                      "invalid_draws": None, "invalid_by_cell": {}},
    }
    if not validation.controls["schema_and_grid"]:
        return result
    applied_erase = [row for row in validation.records
                     if row["cell"] in ERASE_CELLS and row["applied"] == 1]
    changed = [row for row in applied_erase if row["wearA_before"] != 0.0]
    result["sensitivity"] = {
        "applied_erase_rows": len(applied_erase),
        "applied_erase_rows_with_nonzero_wear_before": len(changed),
        "erase_event_changes_wear": bool(changed),
    }
    cell_km: dict[str, dict[int, dict[str, list]]] = {}
    per_seed: list[dict[str, Any]] = []
    all_identified = True
    for cell in CELLS:
        by_seed = _rows_for(groups, cohort, cell)
        km_a = km_groups(by_seed, "A", grid)
        km_b = km_groups(by_seed, "B", grid)
        cell_km[cell] = {}
        for seed in grid.seeds(cohort):
            curves = {"A": km_curve(km_a[seed]), "B": km_curve(km_b[seed])}
            cell_km[cell][seed] = {"A": km_a[seed], "B": km_b[seed]}
            row: dict[str, Any] = {
                "cohort": cohort, "cell": cell, "seed": seed, "pairs": grid.pairs,
                "deaths_A": sum(row["censA"] == 0 for row in by_seed[seed].values()),
                "censored_A": sum(row["censA"] == 1 for row in by_seed[seed].values()),
                "deaths_B": sum(row["censB"] == 0 for row in by_seed[seed].values()),
                "censored_B": sum(row["censB"] == 1 for row in by_seed[seed].values()),
                "t90_A": km_quantile(curves["A"], T90_SURVIVAL),
                "t90_B": km_quantile(curves["B"], T90_SURVIVAL),
                "_curves": {},
            }
            for level in QUANTILE_LEVELS:
                label = f"q{int(level * 100):02d}"
                row[f"{label}_A"] = km_quantile(curves["A"], level)
                row[f"{label}_B"] = km_quantile(curves["B"], level)
            for time in LANDMARK_TIMES:
                row["_curves"][f"survival_A_{time}"] = km_survival_at(curves["A"], time)
                row["_curves"][f"survival_B_{time}"] = km_survival_at(curves["B"], time)
            identified = row["t90_A"] is not None and row["t90_B"] is not None
            row["t90_identified"] = identified
            row["delta_t90"] = row["t90_A"] - row["t90_B"] if identified else None
            if cell in INFERENCE_CELLS:
                all_identified = all_identified and identified
            per_seed.append(row)
    controls["T90_identifiable"] = all_identified
    result["per_seed"] = per_seed
    for cell in CELLS:
        deltas = [row["delta_t90"] for row in per_seed if row["cell"] == cell]
        result["mean_delta_t90"][cell] = (mean(deltas)
                                           if deltas and all(value is not None for value in deltas)
                                           else None)
    result["distribution"] = [item for cell in CELLS
                              for item in _distribution(per_seed, cohort, cell)]
    # A failed non-T90 gate or a no-op intervention cannot support inferential
    # bootstrap. Point estimates remain descriptive; no partial CI is reported.
    if not all(controls.values()) or not result["sensitivity"]["erase_event_changes_wear"]:
        result["bootstrap"]["status"] = ("not_run_control_failure" if not all(controls.values())
                                         else "not_run_insensitive")
        return result
    bootstrap = _bootstrap(cohort, cell_km, grid, draws, bootstrap_seed)
    public_bootstrap = {key: value for key, value in bootstrap.items()
                        if key not in {"cell_draws", "contrast_draws"}}
    result["bootstrap"] = public_bootstrap
    if bootstrap["status"] != "identified":
        controls["T90_identifiable"] = False
        result["controls"] = controls
        result["bootstrap"] = public_bootstrap
        return result
    for cell in CELLS:
        result["ci95_bootstrap"][cell] = ci95(bootstrap["cell_draws"][cell])
    predictions, raw_p, adjusted = _evaluate_predictions(result["mean_delta_t90"], bootstrap)
    result["predictions"] = predictions
    result["secondary_holm"] = {"family": ["P2_erase600_shift", "P5_base_replication"],
                                "raw_p": raw_p, "adjusted_p": adjusted, "alpha": 0.05}
    return result


def _clean_per_seed(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: value for key, value in row.items() if not key.startswith("_")} for row in rows]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in fieldnames})


def _combined_controls(primary: dict, deferred: Optional[dict]) -> dict[str, bool]:
    combined: dict[str, bool] = {}
    for name in primary["controls"]:
        values = [primary["controls"][name]]
        if deferred is not None:
            values.append(deferred["controls"][name])
        combined[name] = all(values)
    return combined


def run_analysis(primary_raw: Path, primary_manifest_path: Path,
                 deferred_raw: Optional[Path], deferred_manifest_path: Optional[Path],
                 out: Path, grid: Grid = PRODUCTION_GRID, draws: int = BOOTSTRAP_DRAWS,
                 task_identity: Optional[dict[str, Any]] = None,
                 task_identity_error: Optional[str] = None) -> dict[str, Any]:
    if draws < 1:
        raise ContractError("bootstrap draws must be positive")
    if out.exists() and any(out.iterdir()):
        raise ContractError(f"refusing to overwrite nonempty output directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    try:
        primary_manifest = read_json(primary_manifest_path)
    except (OSError, ValueError) as exc:
        primary_manifest = {"manifest_error": str(exc)}
    primary_manifest_errors = validate_manifest(primary_manifest, primary_raw, "primary", grid,
                                                task_identity)
    primary_validation = validate_raw(primary_raw, "primary", grid)
    # Freeze the primary decision before deferred data are analyzed.
    primary = analyze_cohort(primary_validation, primary_manifest_errors, "primary", grid,
                             draws, BOOTSTRAP_SEED)
    primary_outcome, primary_reason = _decision(primary)

    deferred: Optional[dict[str, Any]] = None
    if deferred_raw is not None and deferred_manifest_path is not None:
        try:
            deferred_manifest = read_json(deferred_manifest_path)
        except (OSError, ValueError) as exc:
            deferred_manifest = {"manifest_error": str(exc)}
        deferred_manifest_errors = validate_manifest(deferred_manifest, deferred_raw, "deferred",
                                                     grid, task_identity)
        deferred_validation = validate_raw(deferred_raw, "deferred", grid)
        deferred = analyze_cohort(deferred_validation, deferred_manifest_errors, "deferred", grid,
                                  draws, DEFERRED_BOOTSTRAP_SEED)
        deferred_outcome, deferred_reason = _decision(deferred)
        deferred["descriptive_primary_rule"] = {
            "outcome": deferred_outcome, "reason": deferred_reason,
            "role": "descriptive_only_not_used_in_primary_or_final_confirmation_gate"}
        if all(deferred["controls"].values()) and deferred["sensitivity"]["erase_event_changes_wear"]:
            point = deferred["mean_delta_t90"]
            deferred["confirmation_directions"] = {
                "P2_erase600_shift": point["erase600"] > point["base"],
                "P3_erase221_primary": point["erase221"] > point["base"],
                "P5_base_replication": point["base"] < 0.0,
            }
        else:
            deferred["confirmation_directions"] = {}
    else:
        deferred_outcome = None
        deferred_reason = "deferred cohort not supplied"

    controls = _combined_controls(primary, deferred)
    controls["task_payload"] = task_identity_error is None
    if not all(controls.values()):
        outcome = "void"
        reason = ("task payload validation failed: " + task_identity_error
                  if task_identity_error is not None else
                  "at least one analyzed cohort failed an instrument/provenance gate")
    elif primary_outcome == "insensitive_by_construction":
        outcome = "insensitive_by_construction"
        reason = "the erase carrier was not perturbed in primary data"
    elif primary_outcome != "passed":
        outcome = primary_outcome
        reason = primary_reason
    elif deferred is None:
        outcome = "void"
        reason = "the registered deferred confirmation cohort was not supplied"
    elif not deferred["sensitivity"]["erase_event_changes_wear"]:
        outcome = "insensitive_by_construction"
        reason = "primary passed, but the confirmation cohort never perturbed the erase carrier"
    elif not deferred["confirmation_directions"].get("P3_erase221_primary", False):
        outcome = "failed"
        reason = "deferred cohort did not confirm the pre-registered primary P3 direction"
    else:
        outcome = "passed"
        reason = primary_reason + "; deferred directions confirmed without tuning"

    identity = task_identity or identity_from_manifest(primary_manifest) or {
        "task_id": TASK_ID, "task_version": None, "task_version_sha256": None,
        "base_commit": None, "task_payload_sha256": primary_manifest.get("task_payload_sha256")
        if isinstance(primary_manifest, dict) else None,
    }
    primary_per_seed = _clean_per_seed(primary["per_seed"])
    deferred_per_seed = _clean_per_seed(deferred["per_seed"]) if deferred else []
    distribution = primary["distribution"] + (deferred["distribution"] if deferred else [])
    landmarks = primary["landmarks"] + (deferred["landmarks"] if deferred else [])
    per_seed_fields = ["cohort", "cell", "seed", "pairs", "deaths_A", "censored_A",
                       "deaths_B", "censored_B", "t90_A", "t90_B", "delta_t90",
                       "t90_identified"]
    for level in QUANTILE_LEVELS:
        label = f"q{int(level * 100):02d}"
        per_seed_fields.extend((f"{label}_A", f"{label}_B"))
    distribution_fields = ["cohort", "cell", "metric", "level", "time", "value_A",
                           "value_B", "difference_A_minus_B", "identified"]
    landmark_fields = ["cohort", "dimension", "stratum", "scheduled_n", "applied_n",
                       "collapsed_among_applied_n", "collapse_given_applied",
                       "unconditional_applied_fraction"]
    _write_csv(out / "per_seed.csv", per_seed_fields, primary_per_seed + deferred_per_seed)
    _write_csv(out / "distribution.csv", distribution_fields, distribution)
    _write_csv(out / "landmarks.csv", landmark_fields, landmarks)
    control_rows = []
    for scope, cohort_result in (("primary", primary), ("deferred", deferred)):
        if cohort_result is None:
            continue
        for name, holds in cohort_result["controls"].items():
            detail = cohort_result["control_details"].get(
                name, {"validation_error_count": cohort_result["control_details"]["validation_error_count"]})
            control_rows.append({"scope": scope, "control": name, "holds": int(holds),
                                 "details": json.dumps(detail, ensure_ascii=False, sort_keys=True)})
    control_rows.append({
        "scope": "provenance", "control": "task_payload", "holds": int(controls["task_payload"]),
        "details": json.dumps({"error": task_identity_error}, ensure_ascii=False, sort_keys=True),
    })
    _write_csv(out / "controls.csv", ["scope", "control", "holds", "details"], control_rows)
    prediction_rows = []
    for scope, cohort_result in (("primary", primary), ("deferred", deferred)):
        if cohort_result is None:
            continue
        for name, detail in cohort_result["predictions"].items():
            prediction_rows.append({
                "scope": scope, "prediction": name,
                "holds": "" if detail["holds"] is None else int(detail["holds"]),
                "estimate": detail["estimate"], "ci95_low": (
                    detail["ci95"][0] if detail["ci95"] is not None else None),
                "ci95_high": (detail["ci95"][1] if detail["ci95"] is not None else None),
                "p_directional": detail["p_directional"], "p_holm": detail["p_holm"],
            })
    _write_csv(out / "predictions.csv", ["scope", "prediction", "holds", "estimate",
                                         "ci95_low", "ci95_high", "p_directional", "p_holm"],
               prediction_rows)

    public_primary = {key: value for key, value in primary.items() if key != "per_seed"}
    public_deferred = ({key: value for key, value in deferred.items() if key != "per_seed"}
                       if deferred else {"status": "not_analyzed", "reason": deferred_reason})
    raw_hashes = {"primary": None, "deferred": None}
    for cohort, path in (("primary", primary_raw), ("deferred", deferred_raw)):
        if path is not None:
            try:
                raw_hashes[cohort] = sha256_file(path)
            except OSError:
                pass
    summary: dict[str, Any] = {
        "schema": SCHEMA, "analyzer_version": ANALYZER_VERSION, "task_id": TASK_ID,
        "task_version": identity["task_version"],
        "task_version_sha256": identity["task_version_sha256"],
        "base_commit": identity["base_commit"],
        "task_payload_sha256": identity["task_payload_sha256"],
        "scientific_outcome": outcome, "outcome": outcome, "reason": reason,
        "primary_decision": {"outcome": primary_outcome, "reason": primary_reason,
                             "frozen_before_deferred": True},
        "decision_scope": "primary_plus_deferred_confirmation" if deferred else "primary_only",
        "controls": controls, "instrument_gate": all(controls.values()),
        "task_payload_error": task_identity_error,
        "primary": public_primary, "deferred": public_deferred,
        "grid": {"primary_seeds": grid.primary_count, "deferred_seeds": grid.deferred_count,
                 "primary_seed_base": grid.primary_seed_base,
                 "deferred_seed_base": grid.deferred_seed_base,
                 "pairs": grid.pairs, "horizon": grid.horizon, "cells": list(CELLS),
                 "expected_primary_rows": grid.expected_rows("primary"),
                 "expected_deferred_rows": grid.expected_rows("deferred")},
        "bootstrap": {"draws": draws, "primary_seed": BOOTSTRAP_SEED,
                      "deferred_seed": DEFERRED_BOOTSTRAP_SEED,
                      "method": "seed-cluster: resample seeds with replacement; within each "
                                "selected seed resample pairs with replacement; identical "
                                "(seed,pair) multiplicities for every cell and both arms",
                      "interval": "two-sided percentile 95%; primary P3 requires lower>0",
                      "unidentified_policy": "any unidentified point or bootstrap T90 is void; "
                                             "no horizon substitution and no partial CI"},
        "t90_convention": "first KM time survival <=0.10; deaths before censors at tied times",
        "secondary_family": ["P2_erase600_shift", "P5_base_replication"],
        "holm_alpha": 0.05,
        "P6": {"role": "descriptive_landmark_only",
               "independence_test": None,
               "note": "collapse_given_applied is stratified by t_erase bin and by "
                       "survival_of_both_arms_to_erase; unconditional_applied_fraction "
                       "is descriptive and is not required to be independent",
               "landmarks": landmarks},
        "survival_distribution": distribution,
        "raw_sha256": raw_hashes,
        "limitations": [
            "Standalone R/wear-erase model only; not a live-core or closure result.",
            "Inference is limited to the tested model, seeds, pairs, and pinned driver artifacts.",
            "T90 is a KM quantile, not the horizon and not a pointwise life difference.",
            "P6 is descriptive conditional-on-applied landmark reporting, not an independence test.",
            "P3 is the sole primary scientific contrast; P2/P5 are secondary with Holm adjustment.",
            "Deferred cohorts are confirmation only and never enter primary estimates or bootstrap.",
        ],
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
        "generated_utc": utc_now(),
        "artifacts": {},
    }
    for name in ("per_seed.csv", "distribution.csv", "landmarks.csv",
                 "controls.csv", "predictions.csv"):
        summary["artifacts"][name] = sha256_file(out / name)
    write_json(out / "summary.json", summary)
    return summary


def verify_summary_artifacts(summary: dict[str, Any], analysis_dir: Path) -> list[str]:
    errors: list[str] = []
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        return ["summary has no artifact hashes"]
    for relative, expected in artifacts.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"unsafe summary artifact path: {relative}")
            continue
        full = analysis_dir / path
        if full.is_symlink() or not full.is_file():
            errors.append(f"missing summary artifact: {relative}")
            continue
        if not isinstance(expected, str) or not HASH_RE.fullmatch(expected):
            errors.append(f"invalid summary artifact hash: {relative}")
        elif sha256_file(full) != expected:
            errors.append(f"summary artifact hash mismatch: {relative}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-raw", required=True, type=Path)
    parser.add_argument("--primary-manifest", required=True, type=Path)
    parser.add_argument("--deferred-raw", type=Path)
    parser.add_argument("--deferred-manifest", type=Path)
    parser.add_argument("--task-payload", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if (args.deferred_raw is None) != (args.deferred_manifest is None):
        raise SystemExit("--deferred-raw and --deferred-manifest must be supplied together")
    identity = None
    identity_error = None
    if args.task_payload is not None:
        try:
            identity = load_task_identity(args.task_payload)
            validate_task_contract(task_document(args.task_payload))
        except (OSError, ValueError, ContractError) as exc:
            identity_error = str(exc)
    try:
        summary = run_analysis(args.primary_raw, args.primary_manifest,
                               args.deferred_raw, args.deferred_manifest, args.out,
                               task_identity=identity,
                               task_identity_error=identity_error)
    except (OSError, ValueError, ContractError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({"scientific_outcome": summary["scientific_outcome"],
                      "reason": summary["reason"], "summary": str(args.out / "summary.json")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
