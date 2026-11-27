#!/usr/bin/env python3
"""Run the D-Q6 runner while heartbeating its claimed lease.

The scientific runner creates the results directory itself. Lease metadata is
first kept in a sibling sidecar and copied byte-for-byte into the results
bundle after the runner exits. This wrapper does not choose data or gates.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bash_path(path: Path) -> str:
    """Return a path understood by Git Bash without changing WSL POSIX paths."""
    if os.name == "nt":
        try:
            converted = subprocess.check_output(["cygpath", "-u", str(path)], text=True).strip()
            if converted:
                return converted
        except (OSError, subprocess.CalledProcessError):
            pass
    return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--driver", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--toolchain", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--bash", default="bash", help="Bash executable used to invoke the runner")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--task", default="EXP-2026-4103")
    parser.add_argument("--version", required=True, type=int)
    parser.add_argument("--task-hash", required=True)
    parser.add_argument("--agent", default="exper")
    parser.add_argument("--heartbeat-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.heartbeat_seconds < 1:
        raise SystemExit("heartbeat interval must be >=1 second")
    if args.version < 3:
        raise SystemExit("D-Q6 confirmatory requires published version >=3")
    if len(args.task_hash) != 64 or any(c not in "0123456789abcdef" for c in args.task_hash):
        raise SystemExit("task hash must be 64 lowercase hexadecimal characters")

    claim_path = args.claim.resolve()
    claim_doc = load(claim_path)
    claim = claim_doc.get("claimed")
    if not isinstance(claim, dict):
        raise SystemExit("claim JSON has no claimed object")
    if claim.get("task_id") != args.task or int(claim.get("version", -1)) != args.version:
        raise SystemExit("claim task/version mismatch")
    if claim.get("task_version_sha256") != args.task_hash:
        raise SystemExit("claim task-version hash mismatch")
    if claim.get("messages", {}).get("unread", 0) != 0:
        raise SystemExit("claim reports unread messages")
    lease = str(claim["lease_id"])
    epoch = int(claim["lease_epoch"])

    runner = args.runner.resolve()
    driver = args.driver.resolve()
    source = args.source.resolve()
    toolchain = args.toolchain.resolve()
    cli = args.cli.resolve()
    db = args.db.resolve()
    out = args.out.resolve()
    if not runner.is_file() or not driver.is_file() or not source.is_file() or not toolchain.is_file() \
            or not cli.is_file() or not db.is_file():
        raise SystemExit("runner, driver, source, toolchain, CLI and database must be existing files")
    toolchain_doc = load(toolchain)
    if not isinstance(toolchain_doc, dict) or not toolchain_doc:
        raise SystemExit("toolchain JSON must be a nonempty object")
    if not out.parent.is_dir():
        raise SystemExit(f"output parent is absent: {out.parent}")
    if out.exists() or out.is_symlink():
        raise SystemExit(f"refusing to overwrite existing output: {out}")
    sidecar = out.parent / f".{out.name}-lease"
    if sidecar.exists() or sidecar.is_symlink():
        raise SystemExit(f"refusing to overwrite existing lease sidecar: {sidecar}")
    sidecar.mkdir(mode=0o700)
    shutil.copyfile(claim_path, sidecar / "claim.json")
    heartbeat_log = sidecar / "heartbeat.log"
    run_stdout = sidecar / "run.stdout.log"
    run_stderr = sidecar / "run.stderr.log"
    heartbeat_log.touch(mode=0o600)
    run_stdout.touch(mode=0o600)
    run_stderr.touch(mode=0o600)

    stop = threading.Event()
    failure: dict[str, object] = {"message": None}
    heartbeat_count = 0
    process_ref: dict[str, subprocess.Popen] = {}

    def terminate_runner() -> None:
        process = process_ref.get("process")
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def heartbeat() -> None:
        nonlocal heartbeat_count
        command = [
            sys.executable, str(cli), "--db", str(db),
            "heartbeat", "--lease", lease, "--epoch", str(epoch),
            "--agent", args.agent,
        ]
        while not stop.is_set():
            started = utc_now()
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=30,
                )
                record = {
                    "started_utc": started,
                    "finished_utc": utc_now(),
                    "returncode": result.returncode,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                }
                with heartbeat_log.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                heartbeat_count += 1
                if result.returncode != 0:
                    failure["message"] = f"heartbeat failed with status {result.returncode}"
                    stop.set()
                    terminate_runner()
                    return
            except Exception as exc:
                failure["message"] = f"heartbeat exception: {exc!r}"
                stop.set()
                terminate_runner()
                return
            stop.wait(args.heartbeat_seconds)

    thread = threading.Thread(target=heartbeat, name="dq6-lease-heartbeat", daemon=True)
    thread.start()
    started = utc_now()
    with run_stdout.open("w", encoding="utf-8") as stdout_handle, \
            run_stderr.open("w", encoding="utf-8") as stderr_handle:
        runner_env = os.environ.copy()
        runner_env["D_Q6_DRIVER_SOURCE"] = bash_path(source)
        runner_env["D_Q6_TOOLCHAIN"] = bash_path(toolchain)
        process = subprocess.Popen(
            [args.bash, bash_path(runner), bash_path(out), bash_path(driver)],
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
            env=runner_env,
        )
        process_ref["process"] = process
        try:
            status = process.wait()
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.wait()
            stop.set()
            thread.join(timeout=35)
            raise
    stop.set()
    thread.join(timeout=35)
    ended = utc_now()

    final_heartbeat: dict[str, object] | None = None
    if failure["message"] is None:
        command = [
            sys.executable, str(cli), "--db", str(db),
            "heartbeat", "--lease", lease, "--epoch", str(epoch),
            "--agent", args.agent,
        ]
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
            failure["message"] = "final heartbeat failed"

    copied: dict[str, object] = {}
    if out.is_dir() and not out.is_symlink():
        for name in ("claim.json", "heartbeat.log", "run.stdout.log", "run.stderr.log"):
            sidecar_source = sidecar / name
            destination = out / name
            if destination.exists() or destination.is_symlink():
                failure["message"] = failure["message"] or f"refusing to overwrite {destination}"
                continue
            shutil.copyfile(sidecar_source, destination)
            assert sha256(sidecar_source) == sha256(destination)
            copied[name] = {"sha256": sha256(destination), "bytes": destination.stat().st_size}

    record = {
        "task": args.task,
        "version": args.version,
        "task_version_sha256": args.task_hash,
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
        "runner": str(runner),
        "driver": str(driver),
        "driver_source": {"path": str(source), "sha256": sha256(source), "bytes": source.stat().st_size},
        "toolchain": {"path": str(toolchain), "sha256": sha256(toolchain), "bytes": toolchain.stat().st_size},
        "out": str(out),
        "lease_sidecar": str(sidecar),
        "copied_lease_artifacts": copied,
        "scientific_evidence": False,
        "outcome_source": "analysis/summary.json only",
    }
    lease_record = sidecar / "lease-run.json"
    lease_record.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if out.is_dir() and not out.is_symlink():
        destination = out / "lease-run.json"
        if destination.exists() or destination.is_symlink():
            failure["message"] = failure["message"] or f"refusing to overwrite {destination}"
        else:
            shutil.copyfile(lease_record, destination)
            assert sha256(lease_record) == sha256(destination)
    if failure["message"] is None and status == 0 and out.is_dir():
        shutil.rmtree(sidecar)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    if failure["message"] is not None:
        return 4
    return int(status)


if __name__ == "__main__":
    raise SystemExit(main())
