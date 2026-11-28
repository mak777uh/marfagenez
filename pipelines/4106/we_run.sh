#!/usr/bin/env bash
# EXP-2026-4106 runner. Dry-run is the default; --execute is explicit.
# Usage: bash we_run.sh /path/to/exp_wear_erase /new/output-dir \
#          --task-payload /path/to/task.json [--driver-source driver.rs] --execute
set -euo pipefail
export LC_ALL=C
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if command -v cygpath >/dev/null 2>&1; then
  SCRIPT_DIR=$(cygpath -w -- "$SCRIPT_DIR")
fi
PYTHON_BIN=${PYTHON:-python}
exec "$PYTHON_BIN" - "$SCRIPT_DIR" "$@" <<'PY'
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

script_dir = Path(sys.argv[1])
sys.path.insert(0, str(script_dir))
from we_analyze import (PRODUCTION_GRID, RUN_SCHEMA, TASK_ID, load_task_identity,
                        sha256_file, task_document, utc_now, validate_raw,
                        validate_task_contract, write_json)


def native_path(value: str) -> Path:
    if os.name == "nt" and value.startswith("/"):
        try:
            value = subprocess.check_output(["cygpath", "-w", value], text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            if len(value) >= 3 and value[1] == ":":
                value = value[1] + ":" + value[2:]
            elif len(value) >= 2 and value[2] == "/":
                value = value[1].upper() + ":" + value[2:]
    return Path(value)


def version(argv: list[str]) -> str:
    try:
        result = subprocess.run(argv, check=True, capture_output=True, text=True, timeout=30)
        return (result.stdout or result.stderr).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unavailable"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("binary")
    result.add_argument("out")
    result.add_argument("--task-payload", required=True)
    result.add_argument("--driver-source")
    result.add_argument("--execute", action="store_true")
    result.add_argument("--leased-prepared", action="store_true", help=argparse.SUPPRESS)
    return result


def main() -> int:
    args = parser().parse_args(sys.argv[2:])
    binary = native_path(args.binary).resolve()
    out = native_path(args.out).resolve()
    task_path = native_path(args.task_payload).resolve()
    source_path = native_path(args.driver_source).resolve() if args.driver_source else None
    if not binary.is_file():
        raise SystemExit(f"driver binary is not a regular file: {binary}")
    if not task_path.is_file():
        raise SystemExit(f"task payload is not a regular file: {task_path}")
    if source_path is not None and not source_path.is_file():
        raise SystemExit(f"driver source is not a regular file: {source_path}")
    identity = load_task_identity(task_path)
    validate_task_contract(task_document(task_path))
    grid = PRODUCTION_GRID
    argv = {cohort: grid.expected_argv(cohort) for cohort in ("primary", "deferred")}
    command = {cohort: [str(binary), *argv[cohort][1:]] for cohort in argv}
    plan = {
        "mode": "execute" if args.execute else "dry-run",
        "task_id": TASK_ID, **identity,
        "binary": str(binary), "out": str(out), "argv": argv,
        "driver_sha256": sha256_file(binary),
        "driver_source": str(source_path) if source_path else None,
        "driver_source_sha256": sha256_file(source_path) if source_path else None,
        "expected_rows": {cohort: grid.expected_rows(cohort) for cohort in argv},
        "steps_csv": {"status": "not_emitted_by_contract", "sha256": None, "rows": None},
    }
    if not args.execute:
        # No directory, claim, heartbeat, or driver process is created in dry-run.
        print(json.dumps({"mode": "dry-run", "would_execute": command, **plan},
                         ensure_ascii=False, sort_keys=True))
        return 0

    if out.exists():
        protected = ("environment.json", "environment.txt", "toolchain.json", "run-plan.json",
                     "raw-manifest.json", "primary", "deferred")
        has_run_artifacts = any((out / name).exists() for name in protected)
        if not args.leased_prepared or not out.is_dir() or has_run_artifacts:
            raise SystemExit(f"refusing to overwrite existing output: {out}")
    else:
        out.mkdir(parents=True, exist_ok=False)
    started = utc_now()
    toolchain = {
        "python": sys.version.replace("\n", " "),
        "python_executable": sys.executable,
        "rust": version(["rustc", "--version"]),
        "cargo": version(["cargo", "--version"]),
        "bash": version(["bash", "--version"]),
    }
    environment = {
        "task_id": TASK_ID, **identity,
        "os": platform.platform(), "platform": platform.platform(),
        "machine": platform.machine(), "processor": platform.processor() or "unknown",
        "driver_path": str(binary), "driver_sha256": plan["driver_sha256"],
        "driver_source_path": plan["driver_source"],
        "driver_source_sha256": plan["driver_source_sha256"],
        "task_payload_path": str(task_path),
        "primary_seeds": grid.primary_count, "deferred_seeds": grid.deferred_count,
        "primary_seed_base": grid.primary_seed_base,
        "deferred_seed_base": grid.deferred_seed_base,
        "pairs": grid.pairs, "horizon": grid.horizon, "cells": 6,
        "paired_rng": True, "no_unseeded_random": True,
        "started_utc": started,
    }
    write_json(out / "environment.json", environment)
    write_json(out / "toolchain.json", toolchain)
    (out / "environment.txt").write_text(
        "".join(f"{key}={value}\n" for key, value in sorted(environment.items()))
        + "".join(f"toolchain.{key}={value}\n" for key, value in sorted(toolchain.items())),
        encoding="utf-8", newline="\n")
    write_json(out / "run-plan.json", {"schema": RUN_SCHEMA, "started_utc": started, **plan})

    cohorts: dict[str, object] = {}
    overall_rc = 0
    for cohort in ("primary", "deferred"):
        cohort_dir = out / cohort
        cohort_dir.mkdir(exist_ok=False)
        raw_path = cohort_dir / "raw.csv"
        stderr_path = cohort_dir / "driver.stderr.log"
        with raw_path.open("xb") as raw_handle, stderr_path.open("xb") as stderr_handle:
            try:
                completed = subprocess.run(command[cohort], stdin=subprocess.DEVNULL,
                                           stdout=raw_handle, stderr=stderr_handle,
                                           check=False)
                returncode = completed.returncode
            except OSError as exc:
                stderr_handle.write((repr(exc) + "\n").encode("utf-8", errors="replace"))
                returncode = 127
        validation = validate_raw(raw_path, cohort, grid)
        raw_info = {"path": f"{cohort}/raw.csv", "rows": validation.row_count,
                    "sha256": sha256_file(raw_path),
                    "stderr_sha256": sha256_file(stderr_path)}
        steps_info = {"status": "not_emitted_by_contract", "sha256": None, "rows": None,
                      "reason": "the 4106 CSV carries event snapshots and state_hash, not step rows"}
        cohorts[cohort] = {
            "raw_csv": raw_info, "steps_csv": steps_info,
            "driver_rc": returncode, "validation_controls": validation.controls,
            "validation_error_count": len(validation.errors),
            "validation_errors": validation.errors[:100],
        }
        manifest = {
            "schema": RUN_SCHEMA, "cohort": cohort, "task_id": TASK_ID, **identity,
            "driver": {"path": str(binary), "sha256": plan["driver_sha256"],
                       "source_path": plan["driver_source"],
                       "source_sha256": plan["driver_source_sha256"]},
            "argv": {cohort: argv[cohort]}, "driver_rcs": {cohort: returncode},
            "grid": {"primary_seeds": grid.primary_count, "deferred_seeds": grid.deferred_count,
                     "primary_seed_base": grid.primary_seed_base,
                     "deferred_seed_base": grid.deferred_seed_base,
                     "pairs": grid.pairs, "horizon": grid.horizon},
            "cohorts": {cohort: cohorts[cohort]},
        }
        write_json(cohort_dir / "raw-manifest.json", manifest)
        if returncode != 0:
            overall_rc = returncode
        elif not all(validation.controls.values()):
            overall_rc = 3

    ended = utc_now()
    environment["ended_utc"] = ended
    write_json(out / "environment.json", environment)
    manifest = {
        "schema": RUN_SCHEMA, "task_id": TASK_ID, **identity,
        "driver": {"path": str(binary), "sha256": plan["driver_sha256"],
                   "source_path": plan["driver_source"],
                   "source_sha256": plan["driver_source_sha256"]},
        "argv": argv, "driver_rcs": {cohort: cohorts[cohort]["driver_rc"] for cohort in cohorts},
        "grid": {"primary_seeds": grid.primary_count, "deferred_seeds": grid.deferred_count,
                 "primary_seed_base": grid.primary_seed_base,
                 "deferred_seed_base": grid.deferred_seed_base,
                 "pairs": grid.pairs, "horizon": grid.horizon},
        "cohorts": cohorts, "started_utc": started, "ended_utc": ended,
        "pipeline_sha256": {"we_run.sh": sha256_file(script_dir / "we_run.sh"),
                            "we_analyze.py": sha256_file(script_dir / "we_analyze.py")},
        "steps_csv": plan["steps_csv"],
    }
    write_json(out / "raw-manifest.json", manifest)
    print(json.dumps({"mode": "execute", "runner_status": overall_rc,
                      "rows": {cohort: cohorts[cohort]["raw_csv"]["rows"] for cohort in cohorts},
                      "expected_rows": plan["expected_rows"],
                      "raw_sha256": {cohort: cohorts[cohort]["raw_csv"]["sha256"]
                                     for cohort in cohorts},
                      "manifest": str(out / "raw-manifest.json")}, ensure_ascii=False))
    return overall_rc


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
PY
