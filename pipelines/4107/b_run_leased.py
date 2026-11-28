#!/usr/bin/env python3
"""Run the two-execution EXP-2026-4107 pipeline while heartbeating its claimed lease."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import threading

from b_analyze import validate_task_contract

TASK_ID = "EXP-2026-4107"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def task_identity(document: dict) -> dict:
    if not isinstance(document, dict):
        raise ValueError("task payload must be a JSON object")
    if document.get("draft_only") is True or document.get("do_not_execute") is True:
        raise ValueError("draft task payload must be finalized and published before execution")
    wrapper = document
    task = document
    for key in ("payload", "task", "task_payload"):
        if isinstance(document.get(key), dict):
            task = document[key]
            break
    if task.get("schema") != "task/v1" or task.get("id") != TASK_ID:
        raise ValueError(f"task payload is not task/v1 for {TASK_ID}")
    raw_version = task.get("version")
    if not isinstance(raw_version, int) or isinstance(raw_version, bool) or raw_version < 1:
        raise ValueError("task payload version must be an integer >=1")
    task_hash = (task.get("task_version_sha256") or wrapper.get("current_sha256")
                 or wrapper.get("task_version_sha256") or wrapper.get("sha256"))
    identity = {
        "task_id": task["id"],
        "task_version": raw_version,
        "task_version_sha256": task_hash,
        "base_commit": task.get("base_commit"),
    }
    if wrapper is not task:
        if wrapper.get("task_id") not in (None, TASK_ID):
            raise ValueError("task wrapper id mismatch")
        if wrapper.get("current_version") is not None and int(wrapper["current_version"]) != identity["task_version"]:
            raise ValueError("task wrapper version mismatch")
        outer_hash = wrapper.get("current_sha256") or wrapper.get("task_version_sha256") or wrapper.get("sha256")
        if outer_hash is not None and outer_hash != task_hash:
            raise ValueError("task wrapper hash mismatch")
    if (not isinstance(task_hash, str) or len(task_hash) != 64
            or any(char not in "0123456789abcdef" for char in task_hash)):
        raise ValueError("task payload has no lowercase task-version SHA256")
    if task_hash == "0" * 64:
        raise ValueError("task payload still has the draft task-version SHA256 placeholder")
    if not isinstance(identity["base_commit"], str) or not (
            7 <= len(identity["base_commit"]) <= 40
            and all(char in "0123456789abcdef" for char in identity["base_commit"])):
        raise ValueError("task payload base_commit must be 7..40 lowercase hex characters")
    if not identity["base_commit"].strip("0"):
        raise ValueError("task payload still has the draft base_commit placeholder")
    validate_task_contract(task)
    return identity


def terminate(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--task-payload", required=True, type=Path)
    parser.add_argument("--driver", required=True, type=Path)
    parser.add_argument("--driver-source", type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--agent", default="exper")
    parser.add_argument("--heartbeat-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.heartbeat_seconds < 1:
        raise SystemExit("heartbeat interval must be >=1 second")

    claim_doc = load(args.claim)
    claim = claim_doc.get("claimed")
    if not isinstance(claim, dict):
        raise SystemExit("claim JSON has no claimed object")
    if claim.get("messages", {}).get("unread", 0) != 0:
        raise SystemExit("claim reports unread messages")
    try:
        identity = task_identity(load(args.task_payload))
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"invalid task payload: {exc}") from exc
    if claim.get("task_id") != identity["task_id"]:
        raise SystemExit("claim/task id mismatch")
    raw_version = claim.get("version")
    if not isinstance(raw_version, int) or isinstance(raw_version, bool):
        raise SystemExit("claim version is invalid")
    if raw_version != identity["task_version"]:
        raise SystemExit("claim/task version mismatch")
    if claim.get("task_version_sha256") != identity["task_version_sha256"]:
        raise SystemExit("claim/task task-version hash mismatch")
    if claim.get("base_commit") not in (None, identity["base_commit"]):
        raise SystemExit("claim/task base_commit mismatch")
    for key in ("attempt_id", "lease_id", "lease_epoch"):
        if key not in claim:
            raise SystemExit(f"claim is missing {key}")
    if not isinstance(claim["attempt_id"], str) or not claim["attempt_id"] or \
            not isinstance(claim["lease_id"], str) or not claim["lease_id"]:
        raise SystemExit("claim attempt_id/lease_id must be nonempty strings")
    epoch = claim["lease_epoch"]
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise SystemExit("claim lease_epoch must be a positive integer")
    lease = claim["lease_id"]

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ("raw.csv", "steps.csv", "raw-manifest.json", "run1", "run2"):
        if (out / name).exists():
            raise SystemExit(f"refusing to overwrite {out / name}")
    (out / "claim.json").write_text(
        json.dumps(claim_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copyfile(args.task_payload, out / "task.json")

    heartbeat_log = out / "heartbeat.log"
    run_stdout = out / "run.stdout.log"
    run_stderr = out / "run.stderr.log"
    stop = threading.Event()
    failure: dict[str, object] = {"message": None}
    heartbeat_count = 0
    lock = threading.Lock()
    process_ref: dict[str, subprocess.Popen | None] = {"process": None}

    def heartbeat() -> None:
        nonlocal heartbeat_count
        command = [
            sys.executable, str(args.cli), "--db", str(args.db),
            "heartbeat", "--lease", lease, "--epoch", str(epoch),
            "--agent", args.agent,
        ]
        while not stop.is_set():
            started = utc_now()
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                record = {
                    "started_utc": started,
                    "finished_utc": utc_now(),
                    "returncode": result.returncode,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                }
                with heartbeat_log.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                with lock:
                    heartbeat_count += 1
                if result.returncode != 0:
                    failure["message"] = f"heartbeat failed with status {result.returncode}"
                    stop.set()
                    terminate(process_ref["process"])
                    return
            except Exception as exc:
                failure["message"] = f"heartbeat exception: {exc!r}"
                stop.set()
                terminate(process_ref["process"])
                return
            stop.wait(args.heartbeat_seconds)

    thread = threading.Thread(target=heartbeat, name="b-unit-lease-heartbeat", daemon=True)
    thread.start()
    started = utc_now()
    command = [
        "bash", str(args.runner.resolve()), str(args.driver.resolve()), str(out),
        str(args.task_payload.resolve()),
    ]
    if args.driver_source is not None:
        command.append(str(args.driver_source.resolve()))
    with run_stdout.open("w", encoding="utf-8") as stdout_handle, \
            run_stderr.open("w", encoding="utf-8") as stderr_handle:
        popen_kwargs = {"stdout": stdout_handle, "stderr": stderr_handle}
        if hasattr(os, "killpg"):
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(command, **popen_kwargs)
        process_ref["process"] = process
        try:
            status = process.wait()
        except BaseException:
            terminate(process)
            process.wait()
            stop.set()
            thread.join(timeout=35)
            raise
    stop.set()
    thread.join(timeout=35)
    ended = utc_now()

    final_heartbeat = None
    if failure["message"] is None:
        command = [
            sys.executable, str(args.cli), "--db", str(args.db),
            "heartbeat", "--lease", lease, "--epoch", str(epoch),
            "--agent", args.agent,
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            final_heartbeat = {
                "finished_utc": utc_now(),
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
            with heartbeat_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"final": True, **final_heartbeat}, ensure_ascii=False, sort_keys=True) + "\n")
            if result.returncode != 0:
                failure["message"] = f"final heartbeat failed with status {result.returncode}"
        except Exception as exc:
            failure["message"] = f"final heartbeat exception: {exc!r}"

    record = {
        "task": identity["task_id"],
        "task_id": identity["task_id"],
        "version": identity["task_version"],
        "task_version": identity["task_version"],
        "task_version_sha256": identity["task_version_sha256"],
        "base_commit": identity["base_commit"],
        "lease_id": lease,
        "lease_epoch": epoch,
        "attempt_id": claim.get("attempt_id"),
        "started_utc": started,
        "ended_utc": ended,
        "heartbeat_interval_seconds": args.heartbeat_seconds,
        "heartbeat_count": heartbeat_count,
        "final_heartbeat": final_heartbeat,
        "heartbeat_failure": failure["message"],
        "runner_status": status,
        "scientific_evidence": "only analysis/summary.json determines the scientific outcome",
    }
    (out / "lease-run.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    if failure["message"] is not None:
        return 4
    return int(status)


if __name__ == "__main__":
    raise SystemExit(main())
