#!/usr/bin/env python3
"""Leased EXP-2026-4106 runner. Dry-run never claims, heartbeats, or executes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
from typing import Any

from we_analyze import (TASK_ID, ContractError, load_task_identity, read_json,
                        sha256_file, task_document, utc_now,
                        validate_task_contract, write_json)


def native_path(value: str) -> Path:
    if os.name == "nt" and value.startswith("/"):
        try:
            value = subprocess.check_output(["cygpath", "-w", value], text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            if len(value) >= 3 and value[2] == "/":
                value = value[1].upper() + ":" + value[2:]
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--task-payload", required=True)
    parser.add_argument("--runner", default=str(Path(__file__).resolve().with_name("we_run.sh")))
    parser.add_argument("--driver-source")
    parser.add_argument("--claim")
    parser.add_argument("--db")
    parser.add_argument("--cli")
    parser.add_argument("--agent", default="exper")
    parser.add_argument("--heartbeat-seconds", type=int, default=60)
    parser.add_argument("--execute", action="store_true")
    return parser


def _validate_claim(claim_doc: Any, identity: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(claim_doc, dict) or not isinstance(claim_doc.get("claimed"), dict):
        raise ContractError("claim JSON has no claimed object")
    claim = claim_doc["claimed"]
    if claim.get("task_id") != TASK_ID:
        raise ContractError("claim task mismatch")
    version = claim.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ContractError("claim version is invalid")
    if version != identity["task_version"]:
        raise ContractError("claim/task version mismatch")
    if claim.get("task_version_sha256") != identity["task_version_sha256"]:
        raise ContractError("claim/task version hash mismatch")
    if claim.get("base_commit") not in (None, identity["base_commit"]):
        raise ContractError("claim/task base_commit mismatch")
    if claim.get("messages", {}).get("unread", 0) != 0:
        raise ContractError("claim reports unread messages")
    for key in ("lease_id", "lease_epoch", "attempt_id"):
        if key not in claim:
            raise ContractError(f"claim is missing {key}")
    if not isinstance(claim["attempt_id"], str) or not claim["attempt_id"] or \
            not isinstance(claim["lease_id"], str) or not claim["lease_id"]:
        raise ContractError("claim attempt_id/lease_id must be nonempty strings")
    epoch = claim["lease_epoch"]
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise ContractError("claim lease_epoch must be a positive integer")
    return claim


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            process.terminate()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (AttributeError, ProcessLookupError):
            process.terminate()


def main() -> int:
    args = build_parser().parse_args()
    if args.heartbeat_seconds < 1:
        raise SystemExit("heartbeat interval must be >=1 second")
    driver = native_path(args.driver).resolve()
    out = native_path(args.out).resolve()
    task_path = native_path(args.task_payload).resolve()
    runner = native_path(args.runner).resolve()
    source = native_path(args.driver_source).resolve() if args.driver_source else None
    if not driver.is_file():
        raise SystemExit(f"driver is not a regular file: {driver}")
    if not runner.is_file():
        raise SystemExit(f"runner is not a regular file: {runner}")
    if not task_path.is_file():
        raise SystemExit(f"task payload is not a regular file: {task_path}")
    if source is not None and not source.is_file():
        raise SystemExit(f"driver source is not a regular file: {source}")
    identity = load_task_identity(task_path)
    validate_task_contract(task_document(task_path))
    command = ["bash", runner.as_posix(), driver.as_posix(), out.as_posix(),
               "--task-payload", task_path.as_posix()]
    if source is not None:
        command.extend(["--driver-source", source.as_posix()])
    command.append("--execute")
    if not args.execute:
        print(json.dumps({
            "mode": "dry-run", "task_id": TASK_ID, **identity,
            "would_execute": command + ["--leased-prepared"],
            "driver_sha256": sha256_file(driver),
            "driver_source_sha256": sha256_file(source) if source else None,
            "claim": "not read; no claim or heartbeat in dry-run",
        }, ensure_ascii=False, sort_keys=True))
        return 0
    missing = [name for name in ("claim", "db", "cli")
               if getattr(args, name) is None]
    if missing:
        raise SystemExit("--execute requires " + ", ".join("--" + name for name in missing))
    claim_path = native_path(args.claim).resolve()
    db_path = native_path(args.db).resolve()
    cli_path = native_path(args.cli).resolve()
    claim_doc = read_json(claim_path)
    claim = _validate_claim(claim_doc, identity)
    if not cli_path.is_file():
        raise SystemExit(f"claim CLI is not a regular file: {cli_path}")
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing output: {out}")
    out.mkdir(parents=True, exist_ok=False)
    # Only the explicit execute path writes claim material into the run folder.
    write_json(out / "claim.json", claim_doc)
    heartbeat_log = out / "heartbeat.log"
    run_stdout = out / "run.stdout.log"
    run_stderr = out / "run.stderr.log"
    stop = threading.Event()
    lock = threading.Lock()
    process_ref: dict[str, subprocess.Popen] = {}
    failure: dict[str, Any] = {"message": None}
    heartbeat_count = 0
    lease = str(claim["lease_id"])
    epoch = int(claim["lease_epoch"])

    def heartbeat() -> None:
        nonlocal heartbeat_count
        heartbeat_command = [sys.executable, str(cli_path), "--db", str(db_path),
                             "heartbeat", "--lease", lease, "--epoch", str(epoch),
                             "--agent", args.agent]
        while not stop.is_set():
            started = utc_now()
            try:
                result = subprocess.run(heartbeat_command, capture_output=True, text=True,
                                        timeout=30, check=False)
                record = {"started_utc": started, "finished_utc": utc_now(),
                          "returncode": result.returncode, "stdout": result.stdout.strip(),
                          "stderr": result.stderr.strip()}
                with heartbeat_log.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                with lock:
                    heartbeat_count += 1
                if result.returncode != 0:
                    failure["message"] = f"heartbeat failed with status {result.returncode}"
                    stop.set()
                    process = process_ref.get("process")
                    if process is not None:
                        _terminate(process)
                    return
            except Exception as exc:  # preserve the lease failure and stop the driver
                failure["message"] = f"heartbeat exception: {exc!r}"
                stop.set()
                process = process_ref.get("process")
                if process is not None:
                    _terminate(process)
                return
            stop.wait(args.heartbeat_seconds)

    thread = threading.Thread(target=heartbeat, name="we-lease-heartbeat", daemon=True)
    started = utc_now()
    thread.start()
    status = 4 if failure["message"] is not None else 1
    try:
        if failure["message"] is not None:
            for log in (run_stdout, run_stderr):
                with log.open("xb") as handle:
                    handle.write((failure["message"] + "\n").encode("utf-8"))
        else:
            with run_stdout.open("xb") as stdout_handle, run_stderr.open("xb") as stderr_handle:
                process = subprocess.Popen(command + ["--leased-prepared"], stdout=stdout_handle,
                                           stderr=stderr_handle, stdin=subprocess.DEVNULL,
                                           start_new_session=(os.name != "nt"))
                process_ref["process"] = process
                if failure["message"] is not None:
                    _terminate(process)
                try:
                    status = process.wait()
                except BaseException:
                    _terminate(process)
                    process.wait()
                    raise
    finally:
        stop.set()
        thread.join(timeout=35)
    ended = utc_now()
    final_heartbeat = None
    if failure["message"] is None:
        heartbeat_command = [sys.executable, str(cli_path), "--db", str(db_path),
                             "heartbeat", "--lease", lease, "--epoch", str(epoch),
                             "--agent", args.agent]
        try:
            result = subprocess.run(heartbeat_command, capture_output=True, text=True,
                                    timeout=30, check=False)
            final_heartbeat = {"finished_utc": utc_now(), "returncode": result.returncode,
                               "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
            with heartbeat_log.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps({"final": True, **final_heartbeat},
                                        ensure_ascii=False, sort_keys=True) + "\n")
            if result.returncode != 0:
                failure["message"] = f"final heartbeat failed with status {result.returncode}"
        except Exception as exc:
            failure["message"] = f"final heartbeat exception: {exc!r}"
    record = {
        "task_id": TASK_ID, **identity,
        "lease_id": lease, "lease_epoch": epoch, "attempt_id": claim.get("attempt_id"),
        "started_utc": started, "ended_utc": ended,
        "heartbeat_interval_seconds": args.heartbeat_seconds,
        "heartbeat_count": heartbeat_count, "final_heartbeat": final_heartbeat,
        "heartbeat_failure": failure["message"], "runner_status": status,
        "argv": command + ["--leased-prepared"],
        "driver_path": str(driver), "driver_sha256": sha256_file(driver),
        "driver_source_path": str(source) if source else None,
        "driver_source_sha256": sha256_file(source) if source else None,
        "runner_sha256": sha256_file(runner),
        "scientific_evidence": "only analysis/summary.json determines the scientific outcome",
    }
    write_json(out / "lease-run.json", record)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    if failure["message"] is not None:
        return 4
    return int(status)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, ContractError) as exc:
        raise SystemExit(str(exc)) from exc
