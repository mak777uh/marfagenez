#!/usr/bin/env python3
"""Build an outcome-conditional, hash-pinned EXP-2026-4106 submission plan."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from we_analyze import (CELLS, OUTCOMES, PRODUCTION_GRID, SCHEMA, TASK_ID,
                        ContractError, load_task_identity, logical_artifact_path,
                        path_in_write_scope, read_json, require_identity,
                        sha256_file, task_document, validate_bootstrap_contract,
                        validate_manifest, validate_root_manifest,
                        validate_task_contract, verify_summary_artifacts, write_json)

ARTIFACTS = [
    ("design.md", "text/markdown"),
    ("we_run.sh", "text/x-shellscript"),
    ("we_run_leased.py", "text/x-python"),
    ("we_analyze.py", "text/x-python"),
    ("we_submit.py", "text/x-python"),
    ("we_make_finding.py", "text/x-python"),
    ("we_make_plan.py", "text/x-python"),
    ("tests/test_analyzer.py", "text/x-python"),
    ("task.json", "application/json"),
    ("FINDING-EXP-2026-4106.md", "text/markdown"),
    ("run/environment.txt", "text/plain"),
    ("run/environment.json", "application/json"),
    ("run/toolchain.json", "application/json"),
    ("run/run-plan.json", "application/json"),
    ("run/raw-manifest.json", "application/json"),
    ("run/primary/raw.csv", "text/csv"),
    ("run/primary/raw-manifest.json", "application/json"),
    ("run/primary/driver.stderr.log", "text/plain"),
    ("run/deferred/raw.csv", "text/csv"),
    ("run/deferred/raw-manifest.json", "application/json"),
    ("run/deferred/driver.stderr.log", "text/plain"),
    ("run/claim.json", "application/json"),
    ("run/lease-run.json", "application/json"),
    ("run/heartbeat.log", "text/plain"),
    ("run/run.stdout.log", "text/plain"),
    ("run/run.stderr.log", "text/plain"),
    ("analysis/per_seed.csv", "text/csv"),
    ("analysis/distribution.csv", "text/csv"),
    ("analysis/landmarks.csv", "text/csv"),
    ("analysis/controls.csv", "text/csv"),
    ("analysis/predictions.csv", "text/csv"),
    ("analysis/summary.json", "application/json"),
]


def fmt(value, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.{digits}g}"
    except (TypeError, ValueError):
        return str(value)


def interval(value) -> str:
    return "n/a" if value is None else f"[{fmt(value[0])}, {fmt(value[1])}]"


def outcome_summary(summary: dict, outcome: str) -> str:
    reason = summary.get("reason", "")
    prefix = f"{TASK_ID} scientific_outcome={outcome}. {reason}. "
    primary = summary.get("primary", {})
    point = primary.get("mean_delta_t90", {})
    ci = primary.get("ci95_bootstrap", {})
    predictions = primary.get("predictions", {})
    if outcome == "passed":
        p3 = predictions.get("P3_erase221_primary", {})
        p2 = predictions.get("P2_erase600_shift", {})
        p5 = predictions.get("P5_base_replication", {})
        confirmation = summary.get("deferred", {}).get("confirmation_directions", {})
        return (prefix + f"Primary erase221-base DeltaT90={fmt(p3.get('estimate'))}, "
                f"CI95={interval(p3.get('ci95'))}; P2={fmt(p2.get('estimate'))} "
                f"(Holm p={fmt(p2.get('p_holm'))}), P5 base={fmt(p5.get('estimate'))} "
                f"(Holm p={fmt(p5.get('p_holm'))}). Deferred directions="
                + ("confirmed" if confirmation and all(confirmation.values()) else "not analyzed")
                + ". This is evidence only for the tested standalone wear-erase model and seeds.")
    if outcome == "failed":
        violated = [name for name, value in predictions.items() if value.get("holds") is not True]
        confirmation = summary.get("deferred", {}).get("confirmation_directions", {})
        if confirmation and not all(confirmation.values()):
            violated.append("deferred_confirmation")
        return (prefix + "No positive scientific claim is made. Violated decisions: "
                + (", ".join(violated) if violated else "see primary/deferred decision fields") + ".")
    if outcome == "void":
        failed = [name for name, holds in summary.get("controls", {}).items() if not holds]
        return (prefix + "No scientific interpretation is made. Failed gates: "
                + (", ".join(failed) if failed else "see validation details") + ".")
    support = primary.get("sensitivity", {})
    return (prefix + f"Applied erase rows with nonzero wear before={support.get('applied_erase_rows_with_nonzero_wear_before')}; "
            "the intervention was a no-op by construction, so the hypothesis was not tested.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--toolchain", required=True, type=Path)
    parser.add_argument("--task-payload", required=True, type=Path)
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--submission-id", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--complied-message", action="append", default=[])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit(f"refusing to overwrite {args.out}")
    root = args.artifacts_dir.resolve()
    identity = load_task_identity(args.task_payload)
    task = task_document(args.task_payload)
    validate_task_contract(task)
    summary = read_json(args.summary)
    environment = read_json(args.environment)
    toolchain = read_json(args.toolchain)
    require_identity(summary, identity, "analysis summary")
    require_identity(environment, identity, "environment")
    if summary.get("schema") != SCHEMA:
        raise SystemExit("unexpected analysis schema")
    validate_bootstrap_contract(summary)
    outcome = summary.get("scientific_outcome")
    if outcome not in OUTCOMES or summary.get("outcome") != outcome:
        raise SystemExit("unknown or inconsistent scientific outcome")
    expected_grid = {"primary_seeds": PRODUCTION_GRID.primary_count,
                     "deferred_seeds": PRODUCTION_GRID.deferred_count,
                     "primary_seed_base": PRODUCTION_GRID.primary_seed_base,
                     "deferred_seed_base": PRODUCTION_GRID.deferred_seed_base,
                     "pairs": PRODUCTION_GRID.pairs, "horizon": PRODUCTION_GRID.horizon,
                     "cells": list(CELLS),
                     "expected_primary_rows": PRODUCTION_GRID.expected_rows("primary"),
                     "expected_deferred_rows": PRODUCTION_GRID.expected_rows("deferred")}
    if summary.get("grid") != expected_grid:
        raise SystemExit("summary is not the fixed production 4106 grid")
    errors = verify_summary_artifacts(summary, args.summary.resolve().parent)
    root_manifest = read_json(root / "run/raw-manifest.json")
    cohort_manifests: dict[str, dict] = {}
    for cohort in ("primary", "deferred"):
        raw = root / "run" / cohort / "raw.csv"
        manifest_path = root / "run" / cohort / "raw-manifest.json"
        manifest = read_json(manifest_path)
        cohort_manifests[cohort] = manifest
        errors.extend(validate_manifest(manifest, raw, cohort, PRODUCTION_GRID, identity))
        driver = manifest.get("driver", {})
        if driver.get("sha256") != environment.get("driver_sha256") or \
                driver.get("source_sha256") != environment.get("driver_source_sha256"):
            errors.append(f"{cohort} manifest/environment driver hash mismatch")
        if summary.get("raw_sha256", {}).get(cohort) != sha256_file(raw):
            errors.append(f"summary/raw hash mismatch: {cohort}")
    errors.extend(validate_root_manifest(root_manifest, environment, cohort_manifests, identity))
    if sha256_file(root / "we_analyze.py") != summary.get("analyzer_sha256"):
        errors.append("analyzer source hash mismatch")
    if errors:
        raise SystemExit("artifact validation failed: " + "; ".join(errors))
    if args.claim is not None:
        claim_doc = read_json(args.claim)
        claim = claim_doc.get("claimed", {})
        version = claim.get("version")
        epoch = claim.get("lease_epoch")
        if claim.get("task_id") != TASK_ID or not isinstance(version, int) or isinstance(version, bool) \
                or version != identity["task_version"] or \
                claim.get("task_version_sha256") != identity["task_version_sha256"] or \
                claim.get("base_commit") not in (None, identity["base_commit"]):
            raise SystemExit("claim/task identity mismatch")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
            raise SystemExit("claim lease_epoch must be a positive integer")

    artifact_specs = list(ARTIFACTS)
    source_hash = environment.get("driver_source_sha256")
    if source_hash is not None:
        artifact_specs.append(("driver.rs", "text/rust"))
    missing = [relative for relative, _media in artifact_specs if not (root / relative).is_file()]
    if missing:
        raise SystemExit(f"missing required artifacts: {missing}")
    entries = []
    scopes = task.get("write_scope")
    for relative, media_type in artifact_specs:
        path = root / relative
        if path.is_symlink():
            raise SystemExit(f"artifact is a symlink: {relative}")
        if not path.is_file():
            raise SystemExit(f"artifact is not a regular file: {relative}")
        resolved = path.resolve()
        if root != resolved and root not in resolved.parents:
            raise SystemExit(f"artifact escapes artifacts-dir: {relative}")
        logical = logical_artifact_path(relative)
        if not path_in_write_scope(logical, scopes):
            raise SystemExit(f"artifact path is outside task.write_scope: {logical}")
        data = path.read_bytes()
        entries.append({"path": logical, "staged_path": relative,
                        "media_type": media_type,
                        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    by_path = {entry["staged_path"]: entry for entry in entries}
    if by_path["task.json"]["sha256"] != identity["task_payload_sha256"]:
        raise SystemExit("task.json artifact differs from supplied task payload")
    if source_hash is not None and by_path["driver.rs"]["sha256"] != source_hash:
        raise SystemExit("driver.rs artifact hash differs from environment source hash")
    pipeline_hashes = root_manifest.get("pipeline_sha256", {})
    for name in ("we_run.sh", "we_analyze.py"):
        if pipeline_hashes.get(name) != by_path[name]["sha256"]:
            raise SystemExit(f"root manifest/pipeline artifact hash mismatch: {name}")
    finding = (root / "FINDING-EXP-2026-4106.md").read_text(encoding="utf-8")
    if TASK_ID not in finding or f"`{outcome}`" not in finding or \
            "## Ограничения" not in finding or "## Воспроизведение" not in finding:
        raise SystemExit("finding is not outcome-conditional or lacks mandatory sections")
    for name, expected in summary.get("artifacts", {}).items():
        if by_path.get("analysis/" + name, {}).get("sha256") != expected:
            raise SystemExit(f"plan/summary artifact hash mismatch: {name}")

    limitations = [
        "Standalone wear-erase/R model only; this is not a live-core result and not closure.",
        "Inference is limited to the tested model, primary seeds 5501..5512, deferred seeds "
        "5513..5520, 400 pairs per cell/seed, and the pinned driver/analyzer artifacts.",
        "KM T90 is a survival quantile; an unidentified T90 is void and is never replaced by the horizon.",
        "P6 is descriptive collapse_given_applied by t_erase bin and survival_to_erase; "
        "independence of unconditional collapse is not claimed or tested.",
        "Deferred data are confirmation only after the primary analyzer/decision are frozen; "
        "they never enter primary estimates or bootstrap.",
        "No claim is made about other doses, model parameters, ecological realism, or evolution.",
        "received is terminal for the agent; main owns received-to-integrated.",
    ]
    reproduce = [
        "bash we_run.sh /path/to/exp_wear_erase /new/results-directory "
        "--task-payload task.json --driver-source driver.rs",
        "bash we_run.sh /path/to/exp_wear_erase /new/results-directory "
        "--task-payload task.json --driver-source driver.rs --execute",
        "python we_run_leased.py --driver /path/to/exp_wear_erase "
        "--out /new/results-directory --runner we_run.sh --task-payload task.json "
        "--driver-source driver.rs --claim claim.json --db /path/to/lab/state/control.db "
        "--cli /path/to/lab/cli/main.py --agent exper --execute",
        "python we_analyze.py --primary-raw /new/results-directory/primary/raw.csv "
        "--primary-manifest /new/results-directory/primary/raw-manifest.json "
        "--deferred-raw /new/results-directory/deferred/raw.csv "
        "--deferred-manifest /new/results-directory/deferred/raw-manifest.json "
        "--task-payload task.json --out /new/results-directory/analysis",
        "python we_make_finding.py --results-dir /new/results-directory "
        "--lease-run /new/results-directory/lease-run.json --task-payload task.json "
        "--out FINDING-EXP-2026-4106.md --submission-status not_submitted",
        "python we_make_plan.py --artifacts-dir /path/to/artifact-root "
        "--summary /path/to/artifact-root/analysis/summary.json "
        "--environment /path/to/artifact-root/run/environment.json "
        "--toolchain /path/to/artifact-root/run/toolchain.json "
        "--task-payload task.json --submission-id <submission-id> --instance-id <instance-id> "
        "--out plan.json",
        "python we_submit.py --claim claim.json --task-payload task.json --plan plan.json "
        "--summary /path/to/artifact-root/analysis/summary.json "
        "--artifacts-dir /path/to/artifact-root --out-dir /new/submission-bundle "
        "--idem-key <idem-key>  # dry-run; add --execute --root /path/to/repo only for real submission",
    ]
    plan = {
        "submission_id": args.submission_id, "instance_id": args.instance_id,
        "task_id": TASK_ID, "task_version": identity["task_version"],
        "task_version_sha256": identity["task_version_sha256"],
        "base_commit": identity["base_commit"],
        "task_payload_sha256": identity["task_payload_sha256"],
        "scientific_outcome": outcome, "summary": outcome_summary(summary, outcome),
        "limitations": "\n".join(f"- {item}" for item in limitations),
        "environment": environment, "toolchain": toolchain, "reproduce": reproduce,
        "links": {"task": TASK_ID, "finding": "docs/FINDING-EXP-2026-4106.md"},
        "complied_messages": args.complied_message,
        "artifacts": entries,
    }
    require_identity(plan, identity, "plan")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, plan)
    print(json.dumps({"out": str(args.out), "artifacts": len(entries),
                      "scientific_outcome": outcome}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, ContractError) as exc:
        raise SystemExit(str(exc)) from exc
