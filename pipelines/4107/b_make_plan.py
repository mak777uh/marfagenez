#!/usr/bin/env python3
"""Build an honest EXP-2026-4107 submission plan from verified analysis artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from b_analyze import (TASK_ID, logical_artifact_path, path_in_write_scope,
                       sha256_file, validate_outcome)
from b_submit import require_identity, unwrap_task_payload, validate_staged_evidence
MESSAGES = [
    "MSG-CUTOVER-1",
    "MSG-MAIN-EXPER-861F-01",
    "MSG-MAIN-EXPER-861O-01",
    "MSG-MAIN-EXPER-DQ6-RUN-20261127-23",
    "MSG-MAIN-EXPER-BOARD-20261127-25",
]
ARTIFACTS = [
    ("design.md", "text/markdown"),
    ("driver.rs", "text/rust"),
    ("b_run.sh", "text/x-shellscript"),
    ("b_run_leased.py", "text/x-python"),
    ("b_analyze.py", "text/x-python"),
    ("b_make_finding.py", "text/x-python"),
    ("b_make_plan.py", "text/x-python"),
    ("b_submit.py", "text/x-python"),
    ("tests/test_analyzer.py", "text/x-python"),
    ("task.json", "application/json"),
    ("FINDING-EXP-2026-4107.md", "text/markdown"),
    ("run/raw.csv", "text/csv"),
    ("run/steps.csv", "text/csv"),
    ("run/raw-manifest.json", "application/json"),
    ("run/environment.txt", "text/plain"),
    ("run/environment.json", "application/json"),
    ("run/toolchain.json", "application/json"),
    ("run/claim.json", "application/json"),
    ("run/lease-run.json", "application/json"),
    ("run/heartbeat.log", "text/plain"),
    ("run/run.stdout.log", "text/plain"),
    ("run/run.stderr.log", "text/plain"),
    ("run/run1/raw.csv", "text/csv"),
    ("run/run1/steps.csv", "text/csv"),
    ("run/run1/driver.stderr.log", "text/plain"),
    ("run/run1/driver.rc", "text/plain"),
    ("run/run1/run-manifest.json", "application/json"),
    ("run/run2/raw.csv", "text/csv"),
    ("run/run2/steps.csv", "text/csv"),
    ("run/run2/driver.stderr.log", "text/plain"),
    ("run/run2/driver.rc", "text/plain"),
    ("run/run2/run-manifest.json", "application/json"),
    ("run/analysis/per_arm.csv", "text/csv"),
    ("run/analysis/predictions.csv", "text/csv"),
    ("run/analysis/controls.csv", "text/csv"),
    ("run/analysis/summary.json", "application/json"),
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_artifact_entries(root: Path, task: dict) -> tuple[list[dict], dict[str, dict]]:
    root = root.resolve()
    missing = [rel for rel, _ in ARTIFACTS if not (root / rel).is_file()]
    if missing:
        raise ValueError(f"missing required artifacts: {missing}")
    entries = []
    by_staged = {}
    scopes = task.get("write_scope")
    for relative, media_type in ARTIFACTS:
        path = root / relative
        if path.is_symlink():
            raise ValueError(f"artifact is a symlink: {relative}")
        resolved = path.resolve()
        if root != resolved and root not in resolved.parents:
            raise ValueError(f"artifact escapes artifacts-dir: {relative}")
        logical = logical_artifact_path(relative)
        if not path_in_write_scope(logical, scopes):
            raise ValueError(f"artifact path is outside task.write_scope: {logical}")
        data = path.read_bytes()
        entry = {"path": logical, "staged_path": relative, "media_type": media_type,
                 "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        entries.append(entry)
        by_staged[relative] = entry
    return entries, by_staged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--task-payload", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--toolchain", required=True, type=Path)
    parser.add_argument("--submission-id", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit(f"refusing to overwrite {args.out}")

    root = args.artifacts_dir.resolve()
    task, identity = unwrap_task_payload(load(args.task_payload))
    summary = load(args.summary)
    manifest = load(args.manifest)
    environment = load(args.environment)
    toolchain = load(args.toolchain)
    if summary.get("task_id") != TASK_ID or manifest.get("task_id") != TASK_ID:
        raise SystemExit("task_id mismatch")
    for source, label in ((summary, "summary"), (manifest, "manifest"),
                          (environment, "environment")):
        require_identity(source, identity, label)
    outcome = validate_outcome(summary, manifest)
    controls = summary.get("controls", {})
    predictions = summary.get("predictions", {})
    controls_ok = bool(controls) and all(controls.values())
    if outcome == "passed" and not (controls_ok and predictions and all(predictions.values())):
        raise SystemExit("passed plan requires all controls and predictions to hold")
    if outcome == "failed" and not (controls_ok and predictions and not all(predictions.values())):
        raise SystemExit("failed plan requires valid controls and a violated prediction")
    if outcome == "void" and controls_ok:
        raise SystemExit("void plan must identify a failed control")
    if outcome == "insensitive_by_construction" and not (
            manifest.get("driver_rc") == 3 and manifest.get("run2_driver_rc") == 3
            and controls_ok):
        raise SystemExit("insensitive plan requires both driver exits 3 and valid provenance controls")
    try:
        entries, by_staged = build_artifact_entries(root, task)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    primary = summary.get("primary", {})
    aurd = primary.get("aurd", {})
    aurd_abs = primary.get("aurd_abs", {})
    pred_text = "; ".join(f"{key}={'ok' if value else 'VIOLATED'}" for key, value in predictions.items())
    control_failures = [key for key, value in controls.items() if not value]
    outcome_text = {
        "passed": "all registered predictions and controls hold",
        "failed": "controls are valid, but registered scientific predictions are violated",
        "void": "no scientific interpretation; failed controls: " + ", ".join(control_failures),
        "insensitive_by_construction": "driver exit 3; the design is not sensitive enough to discriminate",
    }[outcome]
    metrics_text = (
        f"AURD: A-control={aurd.get('A-control')}, B1-sham={aurd.get('B1-sham')}, "
        f"B2-ko1={aurd.get('B2-ko1')}, B3-ko2={aurd.get('B3-ko2')}, rescue={aurd.get('rescue')}, "
        f"A-B2-cost={aurd.get('A-B2-cost')}, A-B3-cost={aurd.get('A-B3-cost')}, "
        f"A-rescue-cost={aurd.get('A-rescue-cost')}, ghost={aurd.get('ghost')}, placebo-k1={aurd.get('placebo-k1')}. "
        f"AURD_abs D-ladder={aurd_abs.get('A-control')}/{aurd_abs.get('D-half')}/{aurd_abs.get('D-third')}."
        if aurd else "Metrics are not interpreted for this outcome."
    )
    summary_text = (
        f"{TASK_ID} task v{summary.get('task_version')} scientific_outcome={outcome}: {outcome_text}. "
        f"{summary.get('reason', '')} {metrics_text} Predictions: {pred_text or 'not evaluated'}. "
        f"Seeds={summary.get('seeds')} seed_base={summary.get('seed_base')}; T=40; "
        f"schedule t*=5/t**=10/t***=15; two executions; repeat_byte_identical="
        f"{summary.get('repeat', {}).get('byte_identical')}."
    )
    limitations = [
        "Deterministic unit-test only: no probabilistic module failures or stochastic replacement flow.",
        "No population inference or multiplicity claim is made from this run.",
        "A non-passed outcome is reported honestly and is not converted into a scientific failure or success by submission logic.",
        "The task version, hash and base commit are validated dynamically against the claim, manifest and summary at submit time.",
        "Received is terminal for the agent; main owns received-to-integrated.",
    ]
    plan = {
        "submission_id": args.submission_id,
        "instance_id": args.instance_id,
        "task_id": TASK_ID,
        "task_version": summary["task_version"],
        "task_version_sha256": summary["task_version_sha256"],
        "task_payload_sha256": sha256_file(args.task_payload),
        "base_commit": summary["base_commit"],
        "scientific_outcome": outcome,
        "summary": summary_text,
        "limitations": "\n".join(f"- {item}" for item in limitations),
        "environment": environment,
        "toolchain": load(args.toolchain),
        "reproduce": [
            "Build the reviewed exp_b_unit driver from the task base_commit; do not substitute an unreviewed binary.",
            "bash b_run.sh /path/to/exp_b_unit /new/results-directory task.json /path/to/exp_b_unit.rs",
            "For a leased run: python b_run_leased.py --claim claim.json --task-payload task.json "
            "--driver /path/to/exp_b_unit --driver-source /path/to/exp_b_unit.rs --runner b_run.sh "
            "--out /new/results-directory --cli lab/cli/main.py --db lab/state/control.db --agent exper "
            "--heartbeat-seconds 60",
            "python b_analyze.py --raw /new/results-directory/raw.csv "
            "--steps /new/results-directory/steps.csv "
            "--manifest /new/results-directory/raw-manifest.json --out /new/results-directory/analysis",
            "python -m unittest discover -s tests -v",
            "Verify raw-manifest.json, both run directories, environment.json and analysis/summary.json.",
            "python b_make_finding.py --results-dir /new/results-directory "
            "--lease-run /new/results-directory/lease-run.json --out FINDING-EXP-2026-4107.md",
            "python b_make_plan.py --artifacts-dir /staging-directory --task-payload task.json "
            "--summary /new/results-directory/analysis/summary.json "
            "--manifest /new/results-directory/raw-manifest.json "
            "--environment /new/results-directory/environment.json "
            "--toolchain /new/results-directory/toolchain.json "
            "--submission-id <id> --instance-id <id> --out plan.json",
            "python b_submit.py --claim claim.json --task-payload task.json --plan plan.json "
            "--summary /new/results-directory/analysis/summary.json "
            "--manifest /new/results-directory/raw-manifest.json "
            "--artifacts-dir /staging-directory --out-dir /new/submission-directory --idem-key <key>",
        ],
        "links": {"task": TASK_ID, "finding": f"docs/FINDING-{TASK_ID}.md"},
        "complied_messages": MESSAGES,
        "artifacts": entries,
    }
    validate_staged_evidence(root, by_staged, args.task_payload, identity,
                             plan, summary, manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "artifacts": len(ARTIFACTS),
                      "scientific_outcome": outcome}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
