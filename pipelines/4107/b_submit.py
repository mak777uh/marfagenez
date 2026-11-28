#!/usr/bin/env python3
"""Assemble, validate, and optionally submit an EXP-2026-4107 submission/v1 bundle.

Dry-run is the default and uses only the Python standard library. --execute is the
only path that contacts the control plane; task identity is never pinned here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from b_analyze import (
    BASE_COMMIT_RE, REGISTERED_SEED_BASE, REGISTERED_SEEDS, SHA256_RE, TASK_ID,
    logical_artifact_path, path_in_write_scope, safe_artifact_path, task_document,
    validate_outcome, validate_task_contract,
)

OUTCOMES = {"passed", "failed", "void", "insensitive_by_construction"}
ARTIFACT_FIELDS = {"path", "sha256", "media_type", "bytes"}
PLAN_ARTIFACT_FIELDS = ARTIFACT_FIELDS | {"staged_path"}
EVIDENCE_ARTIFACTS = {
    "design.md", "driver.rs", "b_run.sh", "b_run_leased.py", "b_analyze.py",
    "b_make_finding.py", "b_make_plan.py", "b_submit.py", "tests/test_analyzer.py",
    "task.json", f"FINDING-{TASK_ID}.md", "run/raw.csv", "run/steps.csv",
    "run/raw-manifest.json", "run/environment.json", "run/toolchain.json",
    "run/run1/raw.csv", "run/run1/steps.csv", "run/run2/raw.csv", "run/run2/steps.csv",
    "run/analysis/summary.json",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def load_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def unwrap_task_payload(document: Any) -> tuple[dict, dict]:
    if not isinstance(document, dict):
        raise ValueError("task payload must be a JSON object")
    if document.get("draft_only") is True or document.get("do_not_execute") is True:
        raise ValueError("draft task payload must be finalized and published before submission")
    wrapper = document
    task = document
    for key in ("payload", "task", "task_payload"):
        if isinstance(document.get(key), dict):
            task = document[key]
            break
    if task.get("schema") != "task/v1" or task.get("id") != TASK_ID:
        raise ValueError(f"task payload is not task/v1 for {TASK_ID}")
    task_hash = (task.get("task_version_sha256") or wrapper.get("current_sha256")
                 or wrapper.get("task_version_sha256") or wrapper.get("sha256"))
    if not isinstance(task_hash, str) or not SHA256_RE.fullmatch(task_hash):
        raise ValueError("task payload has no valid task-version SHA256")
    if task_hash == "0" * 64:
        raise ValueError("task payload still has the draft task-version SHA256 placeholder")
    raw_version = task.get("version")
    if not isinstance(raw_version, int) or isinstance(raw_version, bool) or raw_version < 1:
        raise ValueError("task payload version must be an integer >=1")
    version = raw_version
    base = task.get("base_commit")
    if not isinstance(base, str) or not BASE_COMMIT_RE.fullmatch(base):
        raise ValueError("task payload base_commit must be 7..40 lowercase hex characters")
    if not base.strip("0"):
        raise ValueError("task payload still has the draft base_commit placeholder")
    identity = {
        "task_id": TASK_ID,
        "task_version": version,
        "task_version_sha256": task_hash,
        "base_commit": base,
    }
    if wrapper is not task:
        if wrapper.get("task_id") not in (None, TASK_ID):
            raise ValueError("task wrapper id mismatch")
        if wrapper.get("current_version") is not None and int(wrapper["current_version"]) != version:
            raise ValueError("task wrapper version mismatch")
        outer_hash = wrapper.get("current_sha256") or wrapper.get("task_version_sha256") or wrapper.get("sha256")
        if outer_hash is not None and outer_hash != task_hash:
            raise ValueError("task wrapper hash mismatch")
    validate_task_contract(task)
    return task, identity


def validate_submission(submission: dict[str, Any]) -> None:
    """Dependency-free validation of every field this pipeline constructs."""
    string_fields = (
        "schema", "id", "task_id", "task_version_sha256", "attempt_id", "lease_id",
        "agent_id", "instance_id", "base_commit", "bundle_sha256", "summary",
        "scientific_outcome", "limitations", "submitted_at",
    )
    for field in string_fields:
        if not isinstance(submission.get(field), str) or not submission[field]:
            raise ValueError(f"submission {field} must be a non-empty string")
    if submission["schema"] != "submission/v1" or submission["task_id"] != TASK_ID:
        raise ValueError("submission schema/task mismatch")
    if not isinstance(submission.get("task_version"), int) or isinstance(submission["task_version"], bool):
        raise ValueError("submission task_version must be an integer")
    if not isinstance(submission.get("lease_epoch"), int) or isinstance(submission["lease_epoch"], bool):
        raise ValueError("submission lease_epoch must be an integer")
    if not SHA256_RE.fullmatch(submission["task_version_sha256"]) or not SHA256_RE.fullmatch(submission["bundle_sha256"]):
        raise ValueError("submission hash must be lowercase SHA256 hex")
    if not BASE_COMMIT_RE.fullmatch(submission["base_commit"]):
        raise ValueError("submission base_commit is invalid")
    if submission["scientific_outcome"] not in OUTCOMES:
        raise ValueError("submission outcome is not registered")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", submission["submitted_at"]):
        raise ValueError("submission submitted_at must be UTC ISO-8601")
    artifacts = submission.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("submission artifacts must be a non-empty list")
    seen: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != ARTIFACT_FIELDS:
            raise ValueError("submission artifact must contain exactly path/sha256/media_type/bytes")
        path = safe_artifact_path(item["path"])
        if path in seen:
            raise ValueError(f"duplicate submission artifact: {path}")
        seen.add(path)
        if not isinstance(item["sha256"], str) or not SHA256_RE.fullmatch(item["sha256"]):
            raise ValueError(f"invalid artifact hash: {path}")
        if not isinstance(item["bytes"], int) or isinstance(item["bytes"], bool) or item["bytes"] < 0:
            raise ValueError(f"invalid artifact bytes: {path}")
        if not isinstance(item["media_type"], str) or not re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+", item["media_type"]):
            raise ValueError(f"invalid artifact media_type: {path}")
    reproduce = submission.get("reproduce")
    if not isinstance(reproduce, list) or not reproduce or not all(isinstance(item, str) and item for item in reproduce):
        raise ValueError("submission reproduce must be a non-empty string list")
    if not isinstance(submission.get("environment"), dict) or not isinstance(submission.get("toolchain"), dict):
        raise ValueError("submission environment/toolchain must be objects")
    if not isinstance(submission.get("links"), dict) or submission["links"].get("task") != TASK_ID:
        raise ValueError("submission task link mismatch")
    complied = submission.get("complied_messages")
    if not isinstance(complied, list) or not all(isinstance(item, str) for item in complied):
        raise ValueError("complied_messages must be a string list")


def require_identity(source: dict, expected: dict, label: str, *, claim: bool = False) -> None:
    id_key = "task_id"
    version_key = "version" if claim else "task_version"
    if source.get(id_key) != expected["task_id"]:
        raise ValueError(f"{label} task id mismatch")
    raw_version = source.get(version_key)
    if not isinstance(raw_version, int) or isinstance(raw_version, bool):
        raise ValueError(f"{label} task version missing or invalid")
    if raw_version != expected["task_version"]:
        raise ValueError(f"{label} task version mismatch")
    if source.get("task_version_sha256") != expected["task_version_sha256"]:
        raise ValueError(f"{label} task-version hash mismatch")
    if source.get("base_commit") not in (None, expected["base_commit"]):
        raise ValueError(f"{label} base_commit mismatch")
    if not claim and source.get("base_commit") != expected["base_commit"]:
        raise ValueError(f"{label} base_commit missing or mismatched")


def validate_planned_artifacts(plan: dict[str, Any], artifact_root: Path,
                               task: dict[str, Any]) -> tuple[list[dict[str, Any]],
                                                           list[tuple[str, bytes, str]],
                                                           dict[str, dict[str, Any]]]:
    """Hash-pin the plan to staged bytes and emit service-shaped descriptors."""
    root = artifact_root.resolve()
    entries: list[dict[str, Any]] = []
    pending: list[tuple[str, bytes, str]] = []
    by_staged: dict[str, dict[str, Any]] = {}
    seen_logical: set[str] = set()
    artifact_items = plan.get("artifacts")
    if not isinstance(artifact_items, list) or not artifact_items:
        raise ValueError("plan artifacts must be a non-empty list")
    scopes = task.get("write_scope")
    for item in artifact_items:
        if not isinstance(item, dict) or set(item) != PLAN_ARTIFACT_FIELDS:
            raise ValueError("plan artifact must contain exactly path/staged_path/media_type/sha256/bytes")
        logical = safe_artifact_path(item["path"])
        staged = safe_artifact_path(item["staged_path"])
        if logical != logical_artifact_path(staged):
            raise ValueError(f"logical/staged artifact mapping mismatch: {staged} -> {logical}")
        if not path_in_write_scope(logical, scopes):
            raise ValueError(f"artifact path is outside task.write_scope: {logical}")
        if staged in by_staged or logical in seen_logical:
            raise ValueError(f"duplicate artifact path: {staged} / {logical}")
        raw_path = root / staged
        if raw_path.is_symlink():
            raise ValueError(f"artifact is a symlink: {staged}")
        path = raw_path.resolve()
        if root != path and root not in path.parents:
            raise ValueError(f"artifact escapes artifacts-dir: {staged}")
        if not path.is_file():
            raise ValueError(f"artifact is not a regular file: {staged}")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if item["sha256"] != digest:
            raise ValueError(f"planned artifact hash mismatch: {staged}")
        if not isinstance(item["bytes"], int) or isinstance(item["bytes"], bool) or item["bytes"] != len(data):
            raise ValueError(f"planned artifact byte count mismatch: {staged}")
        media_type = item["media_type"]
        if not isinstance(media_type, str) or not media_type:
            raise ValueError(f"artifact media_type missing: {staged}")
        entry = {"path": logical, "sha256": digest, "media_type": media_type, "bytes": len(data)}
        entries.append(entry)
        pending.append((logical, data, media_type))
        by_staged[staged] = entry
        seen_logical.add(logical)
    missing = sorted(EVIDENCE_ARTIFACTS - set(by_staged))
    if missing:
        raise ValueError(f"missing core evidence artifacts: {missing}")
    return entries, pending, by_staged


def validate_staged_evidence(artifact_root: Path, by_staged: dict[str, dict[str, Any]],
                             task_path: Path, identity: dict[str, Any], plan: dict[str, Any],
                             summary: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Bind submitted scientific claims to the exact staged task and run evidence."""
    root = artifact_root.resolve()

    def staged_json(relative: str) -> Any:
        return load_json(root / relative)

    if (root / "task.json").read_bytes() != task_path.read_bytes():
        raise ValueError("staged task.json differs from the supplied task payload")
    staged_task, staged_identity = unwrap_task_payload(staged_json("task.json"))
    if staged_task != task_document(task_path) or staged_identity != identity:
        raise ValueError("staged task.json identity differs from the supplied task payload")
    if staged_json("run/analysis/summary.json") != summary:
        raise ValueError("staged analysis/summary.json differs from the supplied summary")
    if staged_json("run/raw-manifest.json") != manifest:
        raise ValueError("staged run/raw-manifest.json differs from the supplied manifest")

    for field, relative in (("raw_sha256", "run/raw.csv"), ("steps_sha256", "run/steps.csv")):
        expected = summary.get(field)
        actual = by_staged[relative]["sha256"]
        if expected != actual:
            raise ValueError(f"summary/staged {field} mismatch: {relative}")
        record = manifest.get("raw_csv" if field == "raw_sha256" else "steps_csv", {})
        if record.get("sha256") != actual or record.get("bytes") != by_staged[relative]["bytes"]:
            raise ValueError(f"manifest/staged {field} record mismatch: {relative}")

    for run in ("run1", "run2"):
        for name in ("raw.csv", "steps.csv"):
            relative = f"run/{run}/{name}"
            if by_staged[relative]["sha256"] != by_staged[f"run/{name}"]["sha256"]:
                raise ValueError(f"repeat/staged bytes differ: {relative}")
            record = manifest.get("executions", {}).get(run, {}).get(name.replace(".csv", "_csv"), {})
            if record.get("sha256") != by_staged[relative]["sha256"] or record.get("bytes") != by_staged[relative]["bytes"]:
                raise ValueError(f"manifest/staged execution record mismatch: {relative}")

    environment = staged_json("run/environment.json")
    require_identity(environment, identity, "environment artifact")
    if environment != plan.get("environment"):
        raise ValueError("plan environment differs from environment artifact")
    if environment.get("seeds") != REGISTERED_SEEDS or environment.get("seed_base") != REGISTERED_SEED_BASE:
        raise ValueError("environment seed grid differs from the task")
    if staged_json("run/toolchain.json") != plan.get("toolchain"):
        raise ValueError("plan toolchain differs from toolchain artifact")
    driver_source = manifest.get("driver", {}).get("source_sha256")
    if driver_source != by_staged["driver.rs"]["sha256"] or environment.get("driver_source_sha256") != driver_source:
        raise ValueError("driver.rs artifact hash differs from manifest/environment source hash")
    if summary.get("seeds") != REGISTERED_SEEDS or summary.get("seed_base") != REGISTERED_SEED_BASE:
        raise ValueError("summary seed grid differs from the task")
    if manifest.get("seeds") != REGISTERED_SEEDS or manifest.get("seed_base") != REGISTERED_SEED_BASE:
        raise ValueError("manifest seed grid differs from the task")
    finding = (root / f"FINDING-{TASK_ID}.md").read_text(encoding="utf-8")
    if TASK_ID not in finding or f"`{summary['scientific_outcome']}`" not in finding \
            or "## Воспроизведение" not in finding:
        raise ValueError("finding does not reflect the task/outcome or lacks reproduction section")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--task-payload", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    repo_root = Path(os.environ["EXP_REPO_ROOT"]) if os.environ.get("EXP_REPO_ROOT") else None
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--idem-key", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.idem_key:
        raise SystemExit("idempotency key must be nonempty")
    if args.execute and args.repo_root is None:
        raise SystemExit("--execute requires --repo-root or EXP_REPO_ROOT")
    response_path = args.out_dir / "submission-response.json"
    submission_path = args.out_dir / "submission.json"
    bundle_path = args.out_dir / "bundle.json"
    for path in (response_path, submission_path, bundle_path):
        if path.exists() or path.is_symlink():
            raise SystemExit(f"refusing to overwrite an existing submission/bundle/response: {path}")

    claim_doc = load_json(args.claim)
    claim = claim_doc.get("claimed") if isinstance(claim_doc, dict) else None
    if not isinstance(claim, dict):
        raise SystemExit("claim JSON has no claimed object")
    if claim.get("messages", {}).get("unread", 0) != 0:
        raise SystemExit("claim reports unread messages")
    for key in ("attempt_id", "lease_id", "lease_epoch"):
        if key not in claim:
            raise SystemExit(f"claim is missing {key}")
    if not isinstance(claim["attempt_id"], str) or not claim["attempt_id"] or \
            not isinstance(claim["lease_id"], str) or not claim["lease_id"]:
        raise SystemExit("claim attempt_id/lease_id must be nonempty strings")
    epoch = claim["lease_epoch"]
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise SystemExit("claim lease_epoch must be a positive integer")
    task, identity = unwrap_task_payload(load_json(args.task_payload))
    plan = load_json(args.plan)
    summary = load_json(args.summary)
    manifest = load_json(args.manifest)
    if not all(isinstance(value, dict) for value in (plan, summary, manifest)):
        raise SystemExit("plan, summary and manifest must be JSON objects")
    try:
        require_identity(claim, identity, "claim", claim=True)
        require_identity(manifest, identity, "manifest")
        require_identity(summary, identity, "summary")
        require_identity(plan, identity, "plan")
        require_identity(plan.get("environment", {}), identity, "plan environment")
        outcome = validate_outcome(summary, manifest)
        entries, pending, by_staged = validate_planned_artifacts(plan, args.artifacts_dir, task)
        validate_staged_evidence(args.artifacts_dir, by_staged, args.task_payload,
                                 identity, plan, summary, manifest)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    if plan.get("scientific_outcome") != outcome:
        raise SystemExit("plan outcome does not match analyzer outcome")
    if TASK_ID not in plan.get("summary", "") or f"scientific_outcome={outcome}" not in plan.get("summary", ""):
        raise SystemExit("plan summary does not name the task and actual outcome")
    if plan.get("links", {}).get("task") != TASK_ID:
        raise SystemExit("plan link task mismatch")

    total_bytes = sum(item["bytes"] for item in entries)
    try:
        disk_budget = int(task["budget"]["disk_bytes"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit("task payload has no valid disk budget") from exc
    if total_bytes > disk_budget:
        raise SystemExit(f"artifact bytes exceed task budget: {total_bytes} > {disk_budget}")
    bundle = {"task": TASK_ID, "batch": TASK_ID, "artifacts": entries}
    bundle_sha = hashlib.sha256(canonical(bundle)).hexdigest()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    submission = {
        "schema": "submission/v1",
        "id": plan["submission_id"],
        "task_id": TASK_ID,
        "task_version": identity["task_version"],
        "task_version_sha256": identity["task_version_sha256"],
        "attempt_id": claim["attempt_id"],
        "lease_id": claim["lease_id"],
        "lease_epoch": int(claim["lease_epoch"]),
        "agent_id": claim.get("agent_id", "exper"),
        "instance_id": plan["instance_id"],
        "base_commit": identity["base_commit"],
        "bundle_sha256": bundle_sha,
        "artifacts": entries,
        "summary": plan["summary"],
        "scientific_outcome": outcome,
        "limitations": plan["limitations"],
        "environment": plan["environment"],
        "toolchain": plan["toolchain"],
        "reproduce": plan["reproduce"],
        "links": plan.get("links", {}),
        "complied_messages": plan["complied_messages"],
        "submitted_at": now,
    }
    try:
        validate_submission(submission)
    except ValueError as exc:
        raise SystemExit(f"invalid submission: {exc}") from exc

    args.out_dir.mkdir(parents=True, exist_ok=True)
    submission_path.write_text(json.dumps(submission, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                               encoding="utf-8", newline="\n")
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8", newline="\n")
    print(json.dumps({
        "mode": "execute" if args.execute else "dry-run",
        "submission": str(submission_path), "bundle": str(bundle_path),
        "bundle_sha256": bundle_sha, "artifacts": len(entries),
        "artifact_bytes": total_bytes, "disk_budget_bytes": disk_budget,
        "scientific_outcome": outcome,
    }, ensure_ascii=False))
    if not args.execute:
        return 0

    sys.path.insert(0, str(args.repo_root.resolve()))
    from lab.service.v2_ops import ControlPlane2  # noqa: E402

    control_plane = ControlPlane2(args.repo_root.resolve() / "lab" / "state" / "control.db")
    upload_id = control_plane.create_upload(submission["agent_id"])
    for logical, data, media_type in pending:
        blob = control_plane.put_blob(upload_id, submission["agent_id"], data, media_type)
        expected = next(item for item in entries if item["path"] == logical)
        if blob != {"sha256": expected["sha256"], "bytes": expected["bytes"]}:
            raise SystemExit(f"blob response mismatch for {logical}: {blob}")
        print(json.dumps({"blob": logical, **blob}, ensure_ascii=False))
    response = control_plane.submit(submission, args.idem_key)
    print(json.dumps({"submit": response}, ensure_ascii=False))
    if response.get("status") not in {"received", "duplicate"}:
        raise SystemExit(f"submission was not received: {response}")
    response_path.write_text(json.dumps(response, ensure_ascii=False, indent=2,
                                        sort_keys=True, allow_nan=False) + "\n",
                             encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
