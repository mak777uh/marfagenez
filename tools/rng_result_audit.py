#!/usr/bin/env python3
"""Report historic result records whose RNG pairing cannot be reproduced.

This deliberately distinguishes an LCG-tagged trace from a Box-Muller trace:
Life's current simulation consumes uniform draws, while the separate legacy
Cycle/Child module contains normal() calls. Missing metadata is UNKNOWN.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def collect_trace_paths(value):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in {"trace_file", "trace_path"} and isinstance(child, str):
                found.append(child.replace("\\", "/"))
            found.extend(collect_trace_paths(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_trace_paths(child))
    return found


def main() -> int:
    rows = []
    for path in sorted(RESULTS.glob("*/run-*.json")):
        if path.parts[-2] == "_archive":
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        trace_versions = []
        for rel in collect_trace_paths(record):
            candidate = (ROOT / rel).resolve()
            if ROOT not in candidate.parents or not candidate.is_file():
                continue
            try:
                trace = json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                continue
            version = trace.get("rng_version")
            if version:
                trace_versions.append(version)
        direct = record.get("rng_version")
        version = direct or (trace_versions[0] if trace_versions and len(set(trace_versions)) == 1 else None)
        rows.append({
            "id": f"{record.get('experiment_id', path.parent.name)}/{record.get('run_id', path.stem)}",
            "model_commit": record.get("model_commit"),
            "rng_version": version or "unrecorded",
            "pairing": "unrecorded",
            "box_muller_attribution": "unknown-from-result-metadata",
        })
    summary = {
        "schema": "marfagenez.rng-result-audit.v1",
        "records": len(rows),
        "version_unrecorded": sum(row["rng_version"] == "unrecorded" for row in rows),
        "lcg_tagged": sum(row["rng_version"] == "lcg64-v1" for row in rows),
        "xoshiro_tagged": sum(row["rng_version"] == "xoshiro256++-v1" for row in rows),
        "rows": rows,
        "interpretation": (
            "Unrecorded RNG version is not evidence that the record used Box-Muller. "
            "No record is labelled Box-Muller without an explicit trace/model-path locator."
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
