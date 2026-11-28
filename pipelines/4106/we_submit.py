#!/usr/bin/env python3
"""Validate and optionally submit the EXP-2026-4106 submission/v1 bundle.

Dry-run is the default and uses only the standard library. --execute imports the
repository's service implementation and is never run by pipeline fixture tests.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from we_analyze import (COMMIT_RE, HASH_RE, OUTCOMES, PRODUCTION_GRID, SCHEMA,
                        TASK_ID, ContractError, load_task_identity, logical_artifact_path,
                        path_in_write_scope, read_json, require_identity, safe_artifact_path,
                        sha256_file, task_document, validate_bootstrap_contract,
                        validate_manifest, validate_root_manifest, validate_task_contract,
                        verify_summary_artifacts)

AGENT_ID = "exper"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _task_document(path: Path) -> dict[str, Any]:
    return task_document(path)


def _validate_claim(claim_doc: Any, identity: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(claim_doc, dict) or not isinstance(claim_doc.get("claimed"), dict):
        raise ContractError("claim JSON has no claimed object")
    claim = claim_doc["claimed"]
    version = claim.get("version")
    if claim.get("task_id") != TASK_ID or not isinstance(version, int) or isinstance(version, bool) \
            or version != identity["task_version"]:
        raise ContractError("claim task/version mismatch")
    if claim.get("task_version_sha256") != identity["task_version_sha256"]:
        raise ContractError("claim/task version hash mismatch")
    if claim.get("base_commit") not in (None, identity["base_commit"]):
        raise ContractError("claim/task base mismatch")
    if claim.get("messages", {}).get("unread", 0) != 0:
        raise ContractError("claim reports unread messages")
    for key in ("attempt_id", "lease_id", "lease_epoch"):
        if key not in claim:
            raise ContractError(f"claim is missing {key}")
    if not isinstance(claim["attempt_id"], str) or not claim["attempt_id"] or \
            not isinstance(claim["lease_id"], str) or not claim["lease_id"]:
        raise ContractError("claim attempt_id/lease_id must be nonempty strings")
    epoch = claim["lease_epoch"]
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise ContractError("claim lease_epoch must be a positive integer")
    return claim


def validate_submission_shape(submission: dict[str, Any], bundle: dict[str, Any]) -> None:
    """Stdlib validation of the submission/v1 fields used by this pipeline.

    The service remains authoritative for its full JSON Schema. This local check
    deliberately validates every field emitted here, including hashes and types.
    """
    if submission.get("schema") != "submission/v1":
        raise ContractError("submission schema must be submission/v1")
    if submission.get("task_id") != TASK_ID or bundle.get("task") != TASK_ID:
        raise ContractError("submission/bundle task mismatch")
    if submission.get("batch") not in (None, TASK_ID):
        raise ContractError("submission batch mismatch")
    required_strings = ("id", "task_version_sha256", "attempt_id", "lease_id", "agent_id",
                        "instance_id", "base_commit", "bundle_sha256", "summary",
                        "scientific_outcome", "limitations", "submitted_at")
    for key in required_strings:
        if not isinstance(submission.get(key), str) or not submission[key]:
            raise ContractError(f"submission {key} must be a nonempty string")
    if not isinstance(submission.get("task_version"), int) or isinstance(submission.get("task_version"), bool):
        raise ContractError("submission task_version must be an integer")
    if not isinstance(submission.get("lease_epoch"), int) or isinstance(submission.get("lease_epoch"), bool):
        raise ContractError("submission lease_epoch must be an integer")
    if submission["scientific_outcome"] not in OUTCOMES:
        raise ContractError("submission outcome is outside the analyzer taxonomy")
    if not HASH_RE.fullmatch(submission["task_version_sha256"]):
        raise ContractError("submission task hash is invalid")
    if not HASH_RE.fullmatch(submission["bundle_sha256"]):
        raise ContractError("submission bundle hash is invalid")
    if not COMMIT_RE.fullmatch(submission["base_commit"]):
        raise ContractError("submission base_commit is invalid")
    if not isinstance(submission.get("reproduce"), list) or not submission["reproduce"] or \
            not all(isinstance(item, str) and item for item in submission["reproduce"]):
        raise ContractError("submission reproduce must be a nonempty string list")
    if not isinstance(submission.get("environment"), dict) or not isinstance(submission.get("toolchain"), dict):
        raise ContractError("submission environment/toolchain must be objects")
    if not isinstance(submission.get("links"), dict) or submission["links"].get("task") != TASK_ID:
        raise ContractError("submission task link mismatch")
    if not isinstance(submission.get("complied_messages"), list) or \
            not all(isinstance(item, str) for item in submission["complied_messages"]):
        raise ContractError("complied_messages must be a string list")
    artifacts = submission.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts or artifacts != bundle.get("artifacts"):
        raise ContractError("submission/bundle artifact lists differ or are empty")
    seen: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            raise ContractError("artifact entry must be an object")
        relative = safe_artifact_path(item.get("path"))
        if relative in seen:
            raise ContractError(f"duplicate artifact: {relative}")
        seen.add(relative)
        if not isinstance(item.get("sha256"), str) or not HASH_RE.fullmatch(item["sha256"]):
            raise ContractError(f"invalid artifact hash: {relative}")
        if not isinstance(item.get("bytes"), int) or isinstance(item.get("bytes"), bool) \
                or item["bytes"] < 0:
            raise ContractError(f"invalid artifact bytes: {relative}")
        if not isinstance(item.get("media_type"), str) or not item["media_type"]:
            raise ContractError(f"invalid artifact media_type: {relative}")
    expected_bundle_hash = hashlib.sha256(canonical(bundle)).hexdigest()
    if submission["bundle_sha256"] != expected_bundle_hash:
        raise ContractError("bundle SHA256 mismatch")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--task-payload", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--idem-key", required=True)
    parser.add_argument("--agent", default=AGENT_ID)
    parser.add_argument("--root", type=Path, help="repository root; required only for --execute")
    parser.add_argument("--execute", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.execute and args.root is None:
        raise SystemExit("--execute requires --root for the repository service")
    response_path = args.out_dir / "submission-response.json"
    submission_path = args.out_dir / "submission.json"
    bundle_path = args.out_dir / "bundle.json"
    if any(path.exists() or path.is_symlink() for path in (response_path, submission_path, bundle_path)):
        raise SystemExit("refusing to overwrite an existing submission/bundle/response")
    identity = load_task_identity(args.task_payload)
    task = _task_document(args.task_payload)
    validate_task_contract(task)
    claim = _validate_claim(read_json(args.claim), identity)
    plan = read_json(args.plan)
    summary = read_json(args.summary)
    if not isinstance(plan, dict) or not isinstance(summary, dict):
        raise SystemExit("plan and summary must be JSON objects")
    require_identity(plan, identity, "plan")
    require_identity(summary, identity, "summary")
    if summary.get("schema") != SCHEMA:
        raise SystemExit("unexpected analysis schema")
    validate_bootstrap_contract(summary)
    outcome = summary.get("scientific_outcome")
    if outcome not in OUTCOMES or summary.get("outcome") != outcome:
        raise SystemExit("unknown or inconsistent analyzer outcome")
    if plan.get("scientific_outcome") != outcome:
        raise SystemExit("plan outcome does not match analyzer outcome")
    if TASK_ID not in plan.get("summary", "") or f"outcome={outcome}" not in plan.get("summary", ""):
        raise SystemExit("plan summary must name the task and actual outcome")
    if plan.get("links", {}).get("task") != TASK_ID:
        raise SystemExit("plan task link mismatch")
    if not isinstance(plan.get("limitations"), str) or not plan["limitations"].strip():
        raise SystemExit("plan limitations are required")
    if not isinstance(plan.get("reproduce"), list) or not plan["reproduce"]:
        raise SystemExit("plan reproduce commands are required")
    if not plan.get("idem_key") and not args.idem_key:
        raise SystemExit("idempotency key is required")
    analysis_errors = verify_summary_artifacts(summary, args.summary.resolve().parent)
    if analysis_errors:
        raise SystemExit("analysis artifact validation failed: " + "; ".join(analysis_errors))

    artifact_root = args.artifacts_dir.resolve()
    entries: list[dict[str, Any]] = []
    pending: list[tuple[str, bytes, str]] = []
    seen: set[str] = set()
    seen_logical: set[str] = set()
    planned = plan.get("artifacts")
    if not isinstance(planned, list) or not planned:
        raise SystemExit("plan artifact list is empty")
    by_path: dict[str, dict[str, Any]] = {}
    scopes = task.get("write_scope")
    for item in planned:
        if not isinstance(item, dict):
            raise SystemExit("plan artifact must be an object")
        logical = safe_artifact_path(item.get("path"))
        relative = safe_artifact_path(item.get("staged_path"))
        if logical != logical_artifact_path(relative):
            raise SystemExit(f"logical/staged artifact mapping mismatch: {relative} -> {logical}")
        if not path_in_write_scope(logical, scopes):
            raise SystemExit(f"artifact path is outside task.write_scope: {logical}")
        if relative in seen or logical in seen_logical:
            raise SystemExit(f"duplicate artifact path: {relative} / {logical}")
        seen.add(relative)
        seen_logical.add(logical)
        raw_path = artifact_root / relative
        if raw_path.is_symlink():
            raise SystemExit(f"artifact is a symlink: {relative}")
        path = raw_path.resolve()
        if artifact_root != path and artifact_root not in path.parents:
            raise SystemExit(f"artifact escapes artifacts-dir: {relative}")
        if not path.is_file():
            raise SystemExit(f"artifact is not a regular file: {relative}")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if item.get("sha256") != digest:
            raise SystemExit(f"planned artifact hash mismatch: {relative}")
        if item.get("bytes") != len(data) or isinstance(item.get("bytes"), bool):
            raise SystemExit(f"planned artifact byte count mismatch: {relative}")
        media_type = item.get("media_type")
        if not isinstance(media_type, str) or not media_type:
            raise SystemExit(f"invalid media type: {relative}")
        entry = {"path": logical, "sha256": digest, "media_type": media_type,
                 "bytes": len(data)}
        entries.append(entry)
        pending.append((logical, data, media_type))
        by_path[relative] = entry

    required = {"design.md", "task.json", "we_run.sh", "we_run_leased.py", "we_analyze.py",
                "we_submit.py", "we_make_finding.py", "we_make_plan.py",
                "tests/test_analyzer.py", "FINDING-EXP-2026-4106.md",
                "run/primary/raw.csv", "run/deferred/raw.csv",
                "run/primary/raw-manifest.json", "run/deferred/raw-manifest.json",
                "run/raw-manifest.json", "run/environment.json", "run/toolchain.json",
                "run/claim.json", "run/lease-run.json", "analysis/summary.json"}
    missing = sorted(required - seen)
    if missing:
        raise SystemExit(f"missing required submission artifacts: {missing}")
    task_artifact_identity = load_task_identity(artifact_root / "task.json")
    if task_artifact_identity != identity:
        raise SystemExit("task.json artifact identity differs from supplied task payload")
    if by_path["task.json"]["sha256"] != identity["task_payload_sha256"]:
        raise SystemExit("task.json artifact hash differs from supplied task payload")
    summary_data = (artifact_root / "analysis/summary.json").read_bytes()
    if hashlib.sha256(summary_data).hexdigest() != by_path["analysis/summary.json"]["sha256"] or \
            read_json(artifact_root / "analysis/summary.json") != summary:
        raise SystemExit("analysis/summary.json artifact differs from supplied summary")
    for name, expected in summary.get("artifacts", {}).items():
        relative = "analysis/" + name
        if relative not in by_path or by_path[relative]["sha256"] != expected:
            raise SystemExit(f"submission artifact does not match summary hash: {relative}")
    cohort_manifests: dict[str, dict] = {}
    staged_errors: list[str] = []
    for cohort in ("primary", "deferred"):
        relative = f"run/{cohort}/raw.csv"
        expected = summary.get("raw_sha256", {}).get(cohort)
        if relative not in by_path or by_path[relative]["sha256"] != expected:
            raise SystemExit(f"raw CSV artifact hash mismatch: {cohort}")
        manifest = read_json(artifact_root / f"run/{cohort}/raw-manifest.json")
        cohort_manifests[cohort] = manifest
        staged_errors.extend(validate_manifest(
            manifest, artifact_root / relative, cohort, PRODUCTION_GRID, identity))
        require_identity(manifest, identity, f"{cohort} manifest artifact")
        if manifest.get("cohorts", {}).get(cohort, {}).get("raw_csv", {}).get("sha256") != expected:
            raise SystemExit(f"manifest/raw hash mismatch: {cohort}")
        driver = manifest.get("driver", {})
        if driver.get("sha256") != plan.get("environment", {}).get("driver_sha256") or \
                driver.get("source_sha256") != plan.get("environment", {}).get("driver_source_sha256"):
            staged_errors.append(f"{cohort} manifest/environment driver hash mismatch")
    environment = read_json(artifact_root / "run/environment.json")
    require_identity(environment, identity, "environment artifact")
    if environment != plan.get("environment"):
        raise SystemExit("plan environment differs from environment artifact")
    source_hash = environment.get("driver_source_sha256")
    if not isinstance(source_hash, str) or not HASH_RE.fullmatch(source_hash) or \
            by_path.get("driver.rs", {}).get("sha256") != source_hash:
        raise SystemExit("driver.rs artifact is missing or differs from environment source hash")
    root_manifest = read_json(artifact_root / "run/raw-manifest.json")
    staged_errors.extend(validate_root_manifest(
        root_manifest, environment, cohort_manifests, identity))
    pipeline_hashes = root_manifest.get("pipeline_sha256", {})
    for name in ("we_run.sh", "we_analyze.py"):
        if pipeline_hashes.get(name) != by_path[name]["sha256"]:
            staged_errors.append(f"root manifest/pipeline artifact hash mismatch: {name}")
    if staged_errors:
        raise SystemExit("staged run provenance validation failed: " + "; ".join(staged_errors))
    if read_json(artifact_root / "run/toolchain.json") != plan.get("toolchain"):
        raise SystemExit("plan toolchain differs from toolchain artifact")
    finding = (artifact_root / "FINDING-EXP-2026-4106.md").read_text(encoding="utf-8")
    if TASK_ID not in finding or f"`{outcome}`" not in finding or \
            "## Ограничения" not in finding or "## Воспроизведение" not in finding:
        raise SystemExit("finding does not reflect the outcome or mandatory sections")

    total_bytes = sum(item["bytes"] for item in entries)
    disk_budget = int(task["budget"]["disk_bytes"])
    if total_bytes > disk_budget:
        raise SystemExit(f"artifact bytes exceed task budget: {total_bytes} > {disk_budget}")
    bundle = {"task": TASK_ID, "batch": TASK_ID, "artifacts": entries}
    bundle_sha = hashlib.sha256(canonical(bundle)).hexdigest()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    submission = {
        "schema": "submission/v1", "id": plan["submission_id"], "task_id": TASK_ID,
        "task_version": identity["task_version"],
        "task_version_sha256": identity["task_version_sha256"],
        "attempt_id": claim["attempt_id"], "lease_id": claim["lease_id"],
        "lease_epoch": int(claim["lease_epoch"]), "agent_id": args.agent,
        "instance_id": plan["instance_id"], "base_commit": identity["base_commit"],
        "bundle_sha256": bundle_sha, "artifacts": entries,
        "summary": plan["summary"], "scientific_outcome": outcome,
        "limitations": plan["limitations"], "environment": plan["environment"],
        "toolchain": plan["toolchain"], "reproduce": plan["reproduce"],
        "links": plan.get("links", {}), "complied_messages": plan.get("complied_messages", []),
        "submitted_at": now,
    }
    validate_submission_shape(submission, bundle)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    submission_path.write_text(json.dumps(submission, ensure_ascii=False, indent=2,
                                          allow_nan=False) + "\n",
                               encoding="utf-8", newline="\n")
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2,
                                      allow_nan=False) + "\n",
                           encoding="utf-8", newline="\n")
    print(json.dumps({"mode": "execute" if args.execute else "dry-run",
                      "submission": str(submission_path), "bundle": str(bundle_path),
                      "bundle_sha256": bundle_sha, "artifacts": len(entries),
                      "artifact_bytes": total_bytes, "disk_budget_bytes": disk_budget,
                      "scientific_outcome": outcome}, ensure_ascii=False))
    if not args.execute:
        return 0
    root = args.root.resolve()
    sys.path.insert(0, str(root))
    from lab.service.v2_ops import ControlPlane2  # noqa: E402

    control = ControlPlane2(root / "lab/state/control.db")
    upload_id = control.create_upload(args.agent)
    for relative, data, media_type in pending:
        expected = by_path[relative]
        blob = control.put_blob(upload_id, args.agent, data, media_type)
        if blob != {"sha256": expected["sha256"], "bytes": expected["bytes"]}:
            raise SystemExit(f"blob response mismatch for {relative}")
        print(json.dumps({"blob": relative, **blob}, ensure_ascii=False))
    response = control.submit(submission, args.idem_key)
    print(json.dumps({"submit": response}, ensure_ascii=False))
    if response.get("status") not in {"received", "duplicate"}:
        raise SystemExit(f"submission was not received: {response}")
    response_path.write_text(json.dumps(response, ensure_ascii=False, indent=2,
                                        sort_keys=True, allow_nan=False) + "\n",
                             encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, ContractError) as exc:
        raise SystemExit(str(exc)) from exc
