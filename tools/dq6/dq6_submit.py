#!/usr/bin/env python3
"""Assemble, validate, and optionally submit the D-Q6 submission/v1 bundle.

Dry-run is the default. --execute uploads artifacts and calls the service submit
API; it is never implied by preparing the JSON files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any

ROOT = Path("/root/marfagenez")
TASK_ID = "EXP-2026-4103"
AGENT_ID = "main-exec"  # lease EXP-2026-4103-a2 held by main-exec per owner decision 2026-11-27
OUTCOME_MAP = {
    "passed": "passed",
    "failed": "failed",
    "void": "void",
    "not_applicable": "not_applicable",
    "horizon_limited": "failed",
    "yoked_reproduces_pole": "failed",
    "endpoint_failure": "failed",
    "specificity_not_confirmed": "failed",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_artifact_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError(f"unsafe artifact path: {value!r}")
    return path.as_posix()


def validate_submission(submission: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator, RefResolver

    schema_path = ROOT / "lab/schemas/v1/submission.schema.json"
    schema = load_json(schema_path)
    schema["$id"] = schema_path.resolve().as_uri()
    resolver = RefResolver.from_schema(schema)
    Draft202012Validator(schema, resolver=resolver).validate(submission)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--task-payload", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--idem-key", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    response_path = args.out_dir / "submission-response.json"
    if response_path.exists() or response_path.is_symlink():
        raise SystemExit(f"refusing to resubmit; response already exists: {response_path}")

    claim_doc = load_json(args.claim)
    claim = claim_doc.get("claimed")
    if not isinstance(claim, dict):
        raise SystemExit("claim JSON has no claimed object")
    if claim.get("messages", {}).get("unread", 0) != 0:
        raise SystemExit("claim reports unread messages")
    task = load_json(args.task_payload)
    if isinstance(task.get("payload"), dict):
        task = task["payload"]
    plan = load_json(args.plan)
    summary = load_json(args.summary)

    if task.get("schema") != "task/v1" or task.get("id") != TASK_ID:
        raise SystemExit(f"task payload is not task/v1 for {TASK_ID}")
    if claim.get("task_id") != TASK_ID:
        raise SystemExit("claim is for a different task")
    version = int(claim["version"])
    if version < 3 or int(task["version"]) != version:
        raise SystemExit("D-Q6 claim/task must be matching version >=3")
    if task.get("task_version_sha256") not in (None, claim["task_version_sha256"]):
        raise SystemExit("claim/task version hash mismatch")
    if summary.get("task") != TASK_ID:
        raise SystemExit("summary task mismatch")
    classification = summary.get("reported_scientific_classification")
    analysis_outcome = summary.get("scientific_outcome")
    if classification not in OUTCOME_MAP or analysis_outcome not in OUTCOME_MAP:
        raise SystemExit("unknown analyzer outcome/classification")
    expected_outcome = OUTCOME_MAP[analysis_outcome]
    if plan.get("scientific_outcome") != expected_outcome:
        raise SystemExit(
            f"plan outcome {plan.get('scientific_outcome')!r} does not match "
            f"analyzer mapping {analysis_outcome!r} -> {expected_outcome!r}"
        )
    if classification not in plan.get("summary", ""):
        raise SystemExit("plan summary does not preserve analyzer classification")
    if plan.get("links", {}).get("task") != TASK_ID:
        raise SystemExit("plan link task mismatch")
    if not plan.get("idem_key") and not args.idem_key:
        raise SystemExit("idempotency key is required")

    artifact_root = args.artifacts_dir.resolve()
    entries: list[dict[str, Any]] = []
    pending: list[tuple[str, Path, bytes, str]] = []
    seen: set[str] = set()
    for item in plan["artifacts"]:
        rel = safe_artifact_path(item["path"])
        if rel in seen:
            raise SystemExit(f"duplicate artifact path: {rel}")
        seen.add(rel)
        raw_path = artifact_root / rel
        if raw_path.is_symlink():
            raise SystemExit(f"artifact is a symlink: {rel}")
        path = raw_path.resolve()
        if artifact_root != path and artifact_root not in path.parents:
            raise SystemExit(f"artifact escapes artifacts-dir: {rel}")
        if not path.is_file():
            raise SystemExit(f"artifact is not a regular file: {rel}")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        media_type = item["media_type"]
        entries.append({
            "path": rel, "sha256": digest,
            "media_type": media_type, "bytes": len(data),
        })
        pending.append((rel, path, data, media_type))

    if not entries:
        raise SystemExit("artifact list is empty")
    total_bytes = sum(item["bytes"] for item in entries)
    disk_budget = int(task["budget"]["disk_bytes"])
    if total_bytes > disk_budget:
        raise SystemExit(f"artifact bytes exceed task budget: {total_bytes} > {disk_budget}")
    bundle = {"task": TASK_ID, "batch": TASK_ID, "artifacts": entries}
    bundle_sha = hashlib.sha256(canonical(bundle)).hexdigest()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    submission = {
        "schema": "submission/v1",
        "id": plan["submission_id"],
        "task_id": TASK_ID,
        "task_version": version,
        "task_version_sha256": claim["task_version_sha256"],
        "attempt_id": claim["attempt_id"],
        "lease_id": claim["lease_id"],
        "lease_epoch": int(claim["lease_epoch"]),
        "agent_id": AGENT_ID,
        "instance_id": plan["instance_id"],
        "base_commit": task["base_commit"],
        "bundle_sha256": bundle_sha,
        "artifacts": entries,
        "summary": plan["summary"],
        "scientific_outcome": plan["scientific_outcome"],
        "limitations": plan["limitations"],
        "environment": plan["environment"],
        "toolchain": plan["toolchain"],
        "reproduce": plan["reproduce"],
        "links": plan.get("links", {}),
        "complied_messages": plan["complied_messages"],
        "submitted_at": now,
    }
    validate_submission(submission)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    submission_path = args.out_dir / "submission.json"
    bundle_path = args.out_dir / "bundle.json"
    submission_path.write_text(
        json.dumps(submission, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "mode": "execute" if args.execute else "dry-run",
        "submission": str(submission_path),
        "bundle": str(bundle_path),
        "bundle_sha256": bundle_sha,
        "artifacts": len(entries),
        "artifact_bytes": total_bytes,
        "disk_budget_bytes": disk_budget,
        "analysis_classification": classification,
        "scientific_outcome": submission["scientific_outcome"],
    }, ensure_ascii=False))

    if not args.execute:
        return 0

    sys.path.insert(0, str(ROOT))
    from lab.service.v2_ops import ControlPlane2  # noqa: E402

    cp = ControlPlane2(ROOT / "lab/state/control.db")
    upload_id = cp.create_upload(AGENT_ID)
    for rel, _path, data, media_type in pending:
        blob = cp.put_blob(upload_id, AGENT_ID, data, media_type)
        expected = next(item for item in entries if item["path"] == rel)
        if blob != {"sha256": expected["sha256"], "bytes": expected["bytes"]}:
            raise SystemExit(f"blob response mismatch for {rel}: {blob}")
        print(json.dumps({"blob": rel, **blob}, ensure_ascii=False))
    response = cp.submit(submission, args.idem_key)
    print(json.dumps({"submit": response}, ensure_ascii=False))
    if response.get("status") not in {"received", "duplicate"}:
        raise SystemExit(f"submission was not received: {response}")
    response_path.write_text(
        json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
