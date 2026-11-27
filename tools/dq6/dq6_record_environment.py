#!/usr/bin/env python3
"""Record observed D-Q6 run provenance, hardware and toolchain as JSON."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--driver", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--analyzer", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--leased-runner", required=True, type=Path)
    parser.add_argument("--toolchain", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    task_doc = load(args.task)
    task = task_doc.get("task", task_doc.get("payload", task_doc))
    if task.get("id") != "EXP-2026-4103" or int(task.get("version", -1)) < 3:
        raise SystemExit("environment recorder requires D-Q6 task version >=3")
    manifest = load(run_dir / "run-manifest.json")
    lease = load(run_dir / "lease-run.json")
    if manifest.get("task") != task["id"] or lease.get("task") != task["id"]:
        raise SystemExit("run manifest/lease task mismatch")
    if int(lease["version"]) != int(task["version"]):
        raise SystemExit("lease/task version mismatch")
    if lease.get("runner_status") != 0 or lease.get("heartbeat_failure") is not None:
        raise SystemExit("cannot record a successful environment for a failed runner")

    toolchain = load(args.toolchain)
    pages = os.sysconf("SC_PHYS_PAGES") if hasattr(os, "sysconf") else 0
    page_size = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 0
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    paths = {
        "driver": args.driver,
        "source": args.source,
        "analyzer": args.analyzer,
        "runner": args.runner,
        "leased_runner": args.leased_runner,
        "task_file": args.task,
        "run_manifest": run_dir / "run-manifest.json",
        "lease_run": run_dir / "lease-run.json",
    }
    hashes = {name: {"path": str(path.resolve()), "sha256": sha256(path), "bytes": path.stat().st_size}
              for name, path in paths.items()}
    spec = task["spec"]
    environment = {
        "task": task["id"],
        "version": int(task["version"]),
        "task_version_sha256": lease["task_version_sha256"],
        "base_commit": task["base_commit"],
        "attempt_id": lease["attempt_id"],
        "lease_id": lease["lease_id"],
        "lease_epoch": int(lease["lease_epoch"]),
        "started_utc": lease["started_utc"],
        "raw_completed_utc": lease["ended_utc"],
        "environment_recorded_utc": now,
        "architecture": platform.machine(),
        "os": platform.platform(),
        "kernel": platform.release(),
        "network_profile": task["network_profile"],
        "network_used": False,
        "no_unseeded_random": bool(spec["no_unseeded_random"]),
        "confirmatory_seeds": list(spec["seeds"]),
        "sample_steps": list(spec["parameters"]["sample_steps"]),
        "histogram_detail": "global-only",
        "hardware": {
            "selected_pool": "CPU WSL",
            "gpu_used": False,
            "network_used": False,
            "cpu_model": cpu_model(),
            "logical_cpus": os.cpu_count(),
            "physical_memory_bytes": int(pages * page_size),
            "observation_source": "/proc/cpuinfo and os.sysconf",
        },
        "hardware_observed_utc": now,
        "hardware_pool": "CPU WSL",
        "provenance": hashes,
    }
    out = args.out.resolve() if args.out else run_dir / "environment.json"
    if out.exists() or out.is_symlink():
        raise SystemExit(f"refusing to overwrite environment output: {out}")
    out.write_text(json.dumps(environment, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
                   encoding="utf-8", newline="\n")
    toolchain_out = run_dir / "toolchain.json"
    if toolchain_out.exists() or toolchain_out.is_symlink():
        raise SystemExit(f"refusing to overwrite toolchain output: {toolchain_out}")
    shutil.copyfile(args.toolchain, toolchain_out)
    assert sha256(args.toolchain) == sha256(toolchain_out)
    print(json.dumps({"environment": str(out), "toolchain": str(toolchain_out),
                      "hardware": environment["hardware"], "provenance": hashes},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
