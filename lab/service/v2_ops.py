"""lab/service/v2_ops.py — вторая серия операций Фазы 2 (план v0.3 §22).

Расширяет lab.service.control.ControlPlane без правки уже зафиксированного
ядра (mixin + подкласс):

- proposals по контракту proposal/v1: revision = optimistic concurrency,
  любая мутация только при совпадении revision (иначе 409), ревизии
  монотонны, published/rejected — терминальные ревизии main;
- cancellation: ready -> cancelled сразу, claimed/waiting_main ->
  cancellation_requested (исполнитель подтверждает fencing-safe
  acknowledge_cancel), submitted и далее — решение за main (409);
- миграции схемы через PRAGMA user_version (v2 = таблица proposals);
- файловые проекции: детерминированный снимок БД, восстановление из БД
  повторным вызовом, атомарная подмена каталога;
- GC blobs: mark-and-sweep с grace-периодом, ссылочность по artifacts.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from lab.service.control import (  # noqa: F401 (re-export для cli/tests)
    BadRequest, Conflict, ControlPlane, CtlError, Gone, NotFound,
    _canon, _path_in_write_scope, _path_is_protected, _sha, _validate_relative_path)

PROPOSAL_ID_RE = re.compile(r"^PROP-[A-Za-z0-9._-]+$")
DECISIONS = ("published", "rejected", "changes_requested")

SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS proposals (
  id TEXT PRIMARY KEY,
  author TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'submitted'
    CHECK (status IN ('submitted','changes_requested','rejected','published')),
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  review_note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL);

PRAGMA user_version=2;
"""

SCHEMA_V3 = """
-- standing-задачи legacy S* — recurring template (план v0.3 §22, Фаза 3.5):
-- раунды main создаёт при активации; шаблон неизменяем, история append-only.
CREATE TABLE IF NOT EXISTS standing_templates (
  id TEXT PRIMARY KEY,
  department TEXT NOT NULL
    CHECK (department IN ('experiments','formulas','knowledge')),
  card_json TEXT NOT NULL,
  history_json TEXT NOT NULL,
  latest_round TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL);

PRAGMA user_version=3;
"""


class V2OpsMixin:
    """Фаза 2, вторая серия: proposals/CAS, cancellation, projections, GC."""

    # --------------------------------------------------------- миграции
    def init(self) -> None:
        super().init()
        self._migrate()

    def user_version(self) -> int:
        return self.connect().execute("PRAGMA user_version").fetchone()[0]

    def _migrate(self) -> None:
        c = self.connect()
        v = c.execute("PRAGMA user_version").fetchone()[0]
        if v < 2:
            c.executescript(SCHEMA_V2)
            self._audit_migration(c, v, 2)
        v = c.execute("PRAGMA user_version").fetchone()[0]
        if v < 3:
            c.executescript(SCHEMA_V3)
            self._audit_migration(c, v, 3)
        v = c.execute("PRAGMA user_version").fetchone()[0]
        if v < 4:
            c.execute("BEGIN IMMEDIATE")
            try:
                c.execute(
                    "CREATE TABLE IF NOT EXISTS submission_artifacts ("
                    "submission_id TEXT NOT NULL REFERENCES submissions(id), "
                    "artifact_index INTEGER NOT NULL CHECK (artifact_index >= 0), "
                    "sha256 TEXT NOT NULL REFERENCES artifacts(sha256), "
                    "PRIMARY KEY (submission_id, artifact_index))"
                )
                c.execute(
                    "CREATE INDEX IF NOT EXISTS ix_submission_artifacts_sha "
                    "ON submission_artifacts(sha256)"
                )
                linked = 0
                unresolved = 0
                legacy = c.execute(
                    "SELECT id, artifacts_json FROM submissions "
                    "WHERE artifacts_json IS NOT NULL ORDER BY id"
                ).fetchall()
                for submission in legacy:
                    try:
                        descriptors = json.loads(submission["artifacts_json"])
                    except (TypeError, ValueError, json.JSONDecodeError):
                        unresolved += 1
                        continue
                    if not isinstance(descriptors, list):
                        unresolved += 1
                        continue
                    for index, descriptor in enumerate(descriptors):
                        digest = descriptor.get("sha256") if isinstance(descriptor, dict) else None
                        if not isinstance(digest, str) or len(digest) != 64:
                            unresolved += 1
                            continue
                        artifact = c.execute(
                            "SELECT bytes, upload_id FROM artifacts WHERE sha256=?",
                            (digest,),
                        ).fetchone()
                        if not artifact:
                            unresolved += 1
                            continue
                        descriptor_bytes = descriptor.get("bytes")
                        if (not isinstance(descriptor_bytes, int)
                                or isinstance(descriptor_bytes, bool)
                                or descriptor_bytes != artifact["bytes"]):
                            unresolved += 1
                            continue
                        if not isinstance(artifact["upload_id"], str):
                            unresolved += 1
                            continue
                        upload_exists = c.execute(
                            "SELECT 1 FROM uploads WHERE upload_id=?",
                            (artifact["upload_id"],),
                        ).fetchone()
                        if not upload_exists:
                            unresolved += 1
                            continue
                        inserted = c.execute(
                            "INSERT OR IGNORE INTO submission_artifacts "
                            "(submission_id,artifact_index,sha256) VALUES (?,?,?)",
                            (submission["id"], index, digest)
                        )
                        linked += inserted.rowcount
                c.execute("PRAGMA user_version=4")
                self._audit(c, "schema", "schema.migrate", "db", str(self.db_path),
                            {"from": 3, "to": 4,
                             "submission_artifact_links": linked,
                             "unresolved_legacy_artifacts": unresolved})
                c.execute("COMMIT")
            except Exception:
                self._safe_rollback(c)
                raise
        v = c.execute("PRAGMA user_version").fetchone()[0]
        if v < 5:
            c.execute("BEGIN IMMEDIATE")
            try:
                c.execute(
                    "CREATE TABLE IF NOT EXISTS upload_artifacts ("
                    "upload_id TEXT NOT NULL REFERENCES uploads(upload_id), "
                    "sha256 TEXT NOT NULL REFERENCES artifacts(sha256), "
                    "media_type TEXT NOT NULL, created_at TEXT NOT NULL, "
                    "PRIMARY KEY (upload_id,sha256,media_type))"
                )
                c.execute(
                    "CREATE INDEX IF NOT EXISTS ix_upload_artifacts_sha "
                    "ON upload_artifacts(sha256,upload_id)"
                )
                linked = 0
                unresolved = 0
                legacy = c.execute(
                    "SELECT a.upload_id,a.sha256,a.media_type,a.created_at "
                    "FROM artifacts a WHERE a.upload_id IS NOT NULL ORDER BY a.sha256"
                ).fetchall()
                for artifact in legacy:
                    exists = c.execute(
                        "SELECT 1 FROM uploads WHERE upload_id=?",
                        (artifact["upload_id"],),
                    ).fetchone()
                    if not exists:
                        unresolved += 1
                        continue
                    inserted = c.execute(
                        "INSERT OR IGNORE INTO upload_artifacts "
                        "(upload_id,sha256,media_type,created_at) VALUES (?,?,?,?)",
                        (artifact["upload_id"], artifact["sha256"],
                         artifact["media_type"], artifact["created_at"]),
                    )
                    linked += inserted.rowcount
                c.execute("PRAGMA user_version=5")
                self._audit(
                    c, "schema", "schema.migrate", "db", str(self.db_path),
                    {"from": 4, "to": 5, "upload_artifact_links": linked,
                     "unresolved_legacy_uploads": unresolved},
                )
                c.execute("COMMIT")
            except Exception:
                self._safe_rollback(c)
                raise

        v = c.execute("PRAGMA user_version").fetchone()[0]
        if v < 6:
            c.execute("BEGIN IMMEDIATE")
            try:
                c.execute(
                    "CREATE TABLE IF NOT EXISTS validations ("
                    "id TEXT PRIMARY KEY, "
                    "submission_id TEXT NOT NULL REFERENCES submissions(id), "
                    "bundle_sha256 TEXT NOT NULL, "
                    "validator_profile TEXT NOT NULL, "
                    "validator_version TEXT NOT NULL, "
                    "recommendation TEXT NOT NULL "
                    "CHECK (recommendation IN ('accepted','needs_work','rejected')), "
                    "actor TEXT NOT NULL, payload_sha256 TEXT NOT NULL, "
                    "payload_json TEXT NOT NULL, created_at TEXT NOT NULL)"
                )
                c.execute(
                    "CREATE INDEX IF NOT EXISTS ix_validations_submission "
                    "ON validations(submission_id,created_at,id)"
                )
                c.execute(
                    "CREATE TABLE IF NOT EXISTS decisions ("
                    "id TEXT PRIMARY KEY, "
                    "submission_id TEXT NOT NULL UNIQUE REFERENCES submissions(id), "
                    "validation_id TEXT NOT NULL REFERENCES validations(id), "
                    "decision TEXT NOT NULL "
                    "CHECK (decision IN ('accepted','needs_work','rejected')), "
                    "reason TEXT NOT NULL, actor TEXT NOT NULL, "
                    "payload_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL, "
                    "created_at TEXT NOT NULL)"
                )
                c.execute(
                    "CREATE TABLE IF NOT EXISTS integrations ("
                    "id TEXT PRIMARY KEY, "
                    "submission_id TEXT NOT NULL REFERENCES submissions(id), "
                    "decision_id TEXT NOT NULL REFERENCES decisions(id), "
                    "attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1), "
                    "status TEXT NOT NULL "
                    "CHECK (status IN ('started','integrated','integration_failed')), "
                    "base_commit TEXT NOT NULL, head_before TEXT NOT NULL, head_after TEXT, "
                    "changed_files_json TEXT NOT NULL DEFAULT '[]', error TEXT, "
                    "actor TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT, "
                    "UNIQUE (submission_id,attempt_no))"
                )
                c.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_integrations_started_submission "
                    "ON integrations(submission_id) WHERE status='started'"
                )
                c.execute(
                    "CREATE INDEX IF NOT EXISTS ix_integrations_submission "
                    "ON integrations(submission_id,attempt_no)"
                )
                c.execute("PRAGMA user_version=6")
                self._audit(
                    c, "schema", "schema.migrate", "db", str(self.db_path),
                    {"from": 5, "to": 6,
                     "tables": ["validations", "decisions", "integrations"]},
                )
                c.execute("COMMIT")
            except Exception:
                self._safe_rollback(c)
                raise

    @staticmethod
    def _validate_relative_projection_path(value: Any) -> str:
        if (not isinstance(value, str) or not value or value.startswith("/")
                or "\\" in value or "\0" in value or ":" in value):
            raise BadRequest("invalid path in projection manifest")
        parts = value.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise BadRequest("invalid path segment in projection manifest")
        return value


    def _audit_migration(self, c, from_v: int, to_v: int) -> None:
        c.execute("BEGIN IMMEDIATE")
        try:
            self._audit(c, "schema", "schema.migrate", "db", str(self.db_path),
                        {"from": from_v, "to": to_v})
            c.execute("COMMIT")
        except Exception:
            self._safe_rollback(c)
            raise

    # -------------------------------------------------------- proposals
    def create_proposal(self, payload: dict) -> dict:
        """Создание proposal/v1. Идемпотентно: тот же id+payload -> duplicate."""
        for field in ("id", "author", "payload"):
            if field not in payload:
                raise BadRequest(f"proposal missing field: {field}")
        pid = payload["id"]
        if not PROPOSAL_ID_RE.match(pid):
            raise BadRequest(f"proposal id не по контракту: {pid}")
        body = payload["payload"]
        if not isinstance(body, dict) or not body.get("kind"):
            raise BadRequest("proposal.payload.kind обязателен")
        sha = _sha(_canon(body))
        now_iso, _ = self._now()
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute(
                "SELECT revision,status,payload_sha256 FROM proposals WHERE id=?",
                (pid,)).fetchone()
            if row:
                if row["payload_sha256"] != sha:
                    raise Conflict(f"{pid} уже существует с другим payload")
                c.execute("COMMIT")
                return {"proposal_id": pid, "revision": row["revision"],
                        "status": row["status"], "duplicate": True}
            c.execute(
                "INSERT INTO proposals "
                "(id,author,revision,status,payload_json,payload_sha256,review_note,"
                "created_at,updated_at) VALUES (?,?,1,'submitted',?,?,NULL,?,?)",
                (pid, payload["author"], _canon(body), sha, now_iso, now_iso))
            self._audit(c, payload["author"], "proposal.create", "proposal", pid,
                        {"kind": body["kind"], "sha256": sha})
            c.execute("COMMIT")
            return {"proposal_id": pid, "revision": 1, "status": "submitted"}
        except Exception:
            self._safe_rollback(c)
            raise

    def update_proposal(self, proposal_id: str, author: str,
                        expected_revision: int, payload: dict) -> dict:
        """CAS-обновление payload: revision ожидается, иначе 409."""
        if not isinstance(payload, dict) or not payload.get("kind"):
            raise BadRequest("proposal.payload.kind обязателен")
        sha = _sha(_canon(payload))
        now_iso, _ = self._now()
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            cur = c.execute(
                "UPDATE proposals SET payload_json=?, payload_sha256=?, "
                "revision=revision+1, updated_at=? WHERE id=? AND author=? "
                "AND revision=? AND status IN ('submitted','changes_requested')",
                (_canon(payload), sha, now_iso, proposal_id, author, expected_revision))
            if cur.rowcount != 1:
                raise Conflict(
                    f"устаревшая ревизия {expected_revision}, автор или статус "
                    f"{proposal_id}; перечитай и повтори")
            self._audit(c, author, "proposal.update", "proposal", proposal_id,
                        {"expected_revision": expected_revision,
                         "new_revision": expected_revision + 1})
            c.execute("COMMIT")
            return {"proposal_id": proposal_id,
                    "revision": expected_revision + 1}
        except Exception:
            self._safe_rollback(c)
            raise

    def review_proposal(self, proposal_id: str, actor: str, decision: str,
                        expected_revision: int, review_note: str = "") -> dict:
        """Решение main по proposal/v1. CAS по revision; published — терминальный."""
        if decision not in DECISIONS:
            raise BadRequest(f"decision должен быть одним из {DECISIONS}")
        now_iso, _ = self._now()
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            cur = c.execute(
                "UPDATE proposals SET status=?, review_note=?, revision=revision+1, "
                "updated_at=? WHERE id=? AND revision=? "
                "AND status IN ('submitted','changes_requested')",
                (decision, review_note or None, now_iso,
                 proposal_id, expected_revision))
            if cur.rowcount != 1:
                raise Conflict(
                    f"устаревшая ревизия {expected_revision} или уже решённое "
                    f"{proposal_id}")
            self._audit(c, actor, "proposal.review", "proposal", proposal_id,
                        {"decision": decision,
                         "new_revision": expected_revision + 1})
            c.execute("COMMIT")
            out = {"proposal_id": proposal_id, "status": decision,
                   "revision": expected_revision + 1}
            if decision == "published":
                out["note"] = ("main публикует draft самостоятельно через "
                               "publish_task; proposal сам задачи не публикует")
            return out
        except Exception:
            self._safe_rollback(c)
            raise

    def get_proposal(self, proposal_id: str) -> dict:
        row = self.connect().execute(
            "SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
        if not row:
            raise NotFound(f"нет proposal {proposal_id}")
        return {"schema": "proposal/v1", "id": row["id"], "author": row["author"],
                "revision": row["revision"], "status": row["status"],
                "payload": json.loads(row["payload_json"]),
                "review_note": row["review_note"],
                "created_at": row["created_at"], "updated_at": row["updated_at"]}

    # ----------------------------------------------------- cancellation
    def cancel_task(self, task_id: str, actor: str, reason: str = "") -> dict:
        """Отмена: ready -> сразу; claimed/waiting_main -> graceful (исполнитель
        подтверждает); submitted и дальше -> 409 (решение за main-review)."""
        c = self.connect()
        now_iso, _ = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                raise NotFound(f"нет задачи {task_id}")
            st = row["status"]
            if st == "ready":
                c.execute("UPDATE tasks SET status='cancelled' WHERE id=? AND status='ready'",
                          (task_id,))
                self._audit(c, actor, "task.cancel", "task", task_id,
                            {"reason": reason, "immediate": 1})
                c.execute("COMMIT")
                return {"task_id": task_id, "status": "cancelled"}
            if st in ("claimed", "waiting_main"):
                c.execute("UPDATE tasks SET status='cancellation_requested' "
                          "WHERE id=? AND status=?", (task_id, st))
                self._audit(c, actor, "task.cancel_request", "task", task_id,
                            {"reason": reason})
                c.execute("COMMIT")
                return {"task_id": task_id, "status": "cancellation_requested",
                        "note": "исполнитель подтверждает через acknowledge_cancel"}
            raise Conflict(
                f"задача {task_id} в статусе {st}: отмена на этом этапе — "
                f"решение main-review (validating/accepted/...)")
        except Exception:
            self._safe_rollback(c)
            raise

    def acknowledge_cancel(self, lease_id: str, lease_epoch: int, agent_id: str,
                           instance_id: str | None = None,
                           remark: str = "") -> dict:
        """Исполнитель подтверждает отмену; fencing: чужой epoch/агент -> 410."""
        c = self.connect()
        now_iso, _ = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = self._check_lease(c, lease_id, lease_epoch, agent_id, instance_id)
            if row["task_status"] != "cancellation_requested":
                raise Conflict(
                    f"задача не в cancellation_requested "
                    f"(сейчас {row['task_status']})")
            c.execute(
                "UPDATE tasks SET status='cancelled', claimed_by=NULL, "
                "lease_expires_at_mono=NULL WHERE id=? AND status='cancellation_requested'",
                (row["task_id"],))
            c.execute("UPDATE leases SET state='released', released_at=? WHERE lease_id=?",
                      (now_iso, lease_id))
            c.execute("UPDATE attempts SET status='void', ended_at=?, failure_reason=? "
                      "WHERE attempt_id=? AND status='claimed'",
                      (now_iso, remark or "cancelled by main", row["attempt_id"]))
            self._audit(c, agent_id, "task.cancel_ack", "lease", lease_id,
                        {"task": row["task_id"]})
            c.execute("COMMIT")
            return {"task_id": row["task_id"], "status": "cancelled"}
        except Exception:
            self._safe_rollback(c)
            raise

    def submit(self, payload: dict, idem_key: str) -> dict:
        """Cancellation fencing is checked atomically by the core submit transaction."""
        return super().submit(payload, idem_key)

    # -------------------------------------- Validation / Decision / Integration
    @staticmethod
    def _require_rfc3339(value: Any, field: str) -> datetime:
        if not isinstance(value, str) or not value:
            raise BadRequest(f"{field} должен быть RFC3339")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise BadRequest(f"{field} должен быть RFC3339") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise BadRequest(f"{field} должен содержать timezone")
        return parsed

    @staticmethod
    def _require_git_sha(value: Any, field: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{7,40}", value):
            raise BadRequest(f"{field} должен быть lowercase git SHA длиной 7..40")
        return value

    def record_validation(self, payload: dict, actor: str = "validation-service") -> dict:
        """Store a validator report; it records a recommendation, never a decision."""
        if actor != "validation-service":
            raise BadRequest("validation может записывать только validation-service")
        if not isinstance(payload, dict):
            raise BadRequest("validation payload должен быть объектом")

        required = {
            "schema", "id", "submission_id", "bundle_sha256",
            "validator_profile", "validator_version", "gate_script_sha256",
            "sandbox_image_digest", "toolchain", "checks", "recommendation",
            "reason", "started_at", "finished_at", "created_at",
        }
        optional = {
            "network_log_artifact", "escalate_to_main", "logs_artifact",
        }
        missing = required - set(payload)
        extra = set(payload) - required - optional
        if missing:
            raise BadRequest(f"validation missing fields: {sorted(missing)}")
        if extra:
            raise BadRequest(f"validation has unknown fields: {sorted(extra)}")
        if payload["schema"] != "validation/v1":
            raise BadRequest("validation.schema должен быть validation/v1")
        if not isinstance(payload["id"], str) or not re.fullmatch(
                r"VAL-[A-Za-z0-9._-]+", payload["id"]):
            raise BadRequest("validation.id должен иметь вид VAL-*")
        if not isinstance(payload["submission_id"], str) or not payload["submission_id"]:
            raise BadRequest("validation.submission_id обязателен")
        for field in ("bundle_sha256", "gate_script_sha256"):
            if not isinstance(payload[field], str) or not re.fullmatch(
                    r"[0-9a-f]{64}", payload[field]):
                raise BadRequest(f"validation.{field} должен быть lowercase SHA-256")
        for field in ("validator_profile", "sandbox_image_digest", "reason"):
            if not isinstance(payload[field], str) or not payload[field].strip():
                raise BadRequest(f"validation.{field} обязателен")
        if not isinstance(payload["validator_version"], str) or not re.fullmatch(
                r"\d+\.\d+\.\d+", payload["validator_version"]):
            raise BadRequest("validation.validator_version должен быть semver")
        if not isinstance(payload["toolchain"], dict):
            raise BadRequest("validation.toolchain должен быть объектом")
        if payload["recommendation"] not in ("accepted", "needs_work", "rejected"):
            raise BadRequest("неизвестная recommendation")
        escalate = payload.get("escalate_to_main", False)
        if not isinstance(escalate, bool):
            raise BadRequest("validation.escalate_to_main должен быть boolean")
        for optional_field in ("network_log_artifact", "logs_artifact"):
            if optional_field in payload and not isinstance(payload[optional_field], str):
                raise BadRequest(f"validation.{optional_field} должен быть строкой")

        checks = payload["checks"]
        if not isinstance(checks, list) or not checks:
            raise BadRequest("validation.checks должен быть непустым массивом")
        all_checks_green = True
        for index, check in enumerate(checks):
            if not isinstance(check, dict) or not {"name", "rc"} <= set(check):
                raise BadRequest(f"validation.checks[{index}] missing name/rc")
            if set(check) - {"name", "rc", "skipped_reason", "evidence"}:
                raise BadRequest(f"validation.checks[{index}] содержит неизвестные поля")
            if not isinstance(check["name"], str) or not check["name"].strip():
                raise BadRequest(f"validation.checks[{index}].name обязателен")
            if not isinstance(check["rc"], int) or isinstance(check["rc"], bool):
                raise BadRequest(f"validation.checks[{index}].rc должен быть integer")
            skipped = check.get("skipped_reason")
            if skipped is not None and (
                    not isinstance(skipped, str) or not skipped.strip()):
                raise BadRequest("skipped_reason должен содержать объяснение")
            if "evidence" in check and not isinstance(check["evidence"], str):
                raise BadRequest("check.evidence должен быть строкой")
            if check["rc"] != 0 or skipped:
                all_checks_green = False

        started = self._require_rfc3339(payload["started_at"], "started_at")
        finished = self._require_rfc3339(payload["finished_at"], "finished_at")
        created = self._require_rfc3339(payload["created_at"], "created_at")
        if finished < started or created < finished:
            raise BadRequest("validation timestamps нарушают порядок started <= finished <= created")
        if payload["recommendation"] == "accepted" and (
                not all_checks_green or escalate):
            raise BadRequest(
                "recommendation=accepted невозможна при failed/skipped checks или escalate_to_main")

        payload_json = _canon(payload)
        payload_sha = _sha(payload_json)
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            existing = c.execute(
                "SELECT payload_sha256 FROM validations WHERE id=?", (payload["id"],)
            ).fetchone()
            if existing:
                if existing["payload_sha256"] != payload_sha:
                    raise Conflict("validation id уже использован с другим payload")
                c.execute("COMMIT")
                return {"status": "duplicate", "validation_id": payload["id"]}

            row = c.execute(
                "SELECT s.id,s.task_id,s.task_version,s.task_version_sha256,"
                "s.bundle_sha256,s.status AS submission_status,"
                "t.status AS task_status,t.current_version,"
                "tv.task_version_sha256 AS pinned_task_sha,tv.payload_json "
                "FROM submissions s JOIN tasks t ON t.id=s.task_id "
                "JOIN task_versions tv ON tv.task_id=s.task_id AND tv.version=s.task_version "
                "WHERE s.id=?",
                (payload["submission_id"],),
            ).fetchone()
            if row is None:
                raise NotFound(f"нет submission {payload['submission_id']}")
            if row["submission_status"] not in ("received", "validating"):
                raise Conflict("submission не находится в состоянии received/validating")
            if row["task_status"] not in ("submitted", "validating"):
                raise Conflict(f"task status не допускает validation: {row['task_status']}")
            if row["bundle_sha256"] != payload["bundle_sha256"]:
                raise BadRequest("validation.bundle_sha256 не совпадает с submission")
            if (not row["task_version_sha256"]
                    or row["task_version_sha256"] != row["pinned_task_sha"]):
                raise BadRequest("submission не pin'ит SHA immutable task version")

            task_payload = json.loads(row["payload_json"])
            validators = task_payload.get("validators")
            profile_pinned = (
                isinstance(validators, list)
                and any(
                    isinstance(v, dict)
                    and v.get("profile") == payload["validator_profile"]
                    and v.get("version") == payload["validator_version"]
                    for v in validators
                )
            )
            if not profile_pinned:
                raise BadRequest("validator profile/version не закреплён в task version")
            if c.execute(
                    "SELECT 1 FROM decisions WHERE submission_id=?",
                    (payload["submission_id"],)).fetchone():
                raise Conflict("submission уже имеет Decision")

            c.execute(
                "INSERT INTO validations "
                "(id,submission_id,bundle_sha256,validator_profile,validator_version,"
                "recommendation,actor,payload_sha256,payload_json,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (payload["id"], payload["submission_id"], payload["bundle_sha256"],
                 payload["validator_profile"], payload["validator_version"],
                 payload["recommendation"], actor, payload_sha, payload_json,
                 payload["created_at"]),
            )
            c.execute(
                "UPDATE submissions SET status='validating' "
                "WHERE id=? AND status IN ('received','validating')",
                (payload["submission_id"],),
            )
            c.execute(
                "UPDATE tasks SET status='validating' "
                "WHERE id=? AND status IN ('submitted','validating')",
                (row["task_id"],),
            )
            self._audit(
                c, actor, "validation.record", "submission", payload["submission_id"],
                {"validation_id": payload["id"], "bundle_sha256": payload["bundle_sha256"],
                 "profile": payload["validator_profile"],
                 "version": payload["validator_version"],
                 "recommendation": payload["recommendation"],
                 "payload_sha256": payload_sha},
            )
            c.execute("COMMIT")
            return {"status": "recorded", "validation_id": payload["id"]}
        except Exception:
            self._safe_rollback(c)
            raise

    def decide_submission(self, submission_id: str, validation_id: str,
                          decision: str, reason: str, actor: str = "main") -> dict:
        """Append main's scientific decision after a pinned validation report."""
        if actor != "main":
            raise BadRequest("Decision может принимать только main")
        if decision not in ("accepted", "needs_work", "rejected"):
            raise BadRequest("decision должен быть accepted/needs_work/rejected")
        if not isinstance(reason, str) or not reason.strip():
            raise BadRequest("decision reason обязателен")
        c = self.connect()
        now_iso, _ = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute(
                "SELECT s.id,s.task_id,s.task_version,s.task_version_sha256,"
                "s.bundle_sha256,s.status AS submission_status,s.attempt_id,"
                "t.status AS task_status,t.current_version,"
                "v.id AS validation_id,v.bundle_sha256 AS validation_bundle_sha,"
                "v.payload_json AS validation_payload,v.actor AS validation_actor "
                "FROM submissions s JOIN tasks t ON t.id=s.task_id "
                "JOIN validations v ON v.submission_id=s.id AND v.id=? "
                "WHERE s.id=?",
                (validation_id, submission_id),
            ).fetchone()
            if row is None:
                raise NotFound("submission/validation pair does not exist")
            existing_decision = c.execute(
                "SELECT id,validation_id,decision,reason,actor FROM decisions "
                "WHERE submission_id=?", (submission_id,)
            ).fetchone()
            if existing_decision:
                if (existing_decision["validation_id"] == validation_id
                        and existing_decision["decision"] == decision
                        and existing_decision["reason"] == reason.strip()
                        and existing_decision["actor"] == actor):
                    c.execute("COMMIT")
                    return {"status": "duplicate",
                            "decision_id": existing_decision["id"]}
                raise Conflict("submission уже имеет неизменяемый Decision")
            if row["validation_actor"] != "validation-service":
                raise BadRequest("validation record has no validation-service principal")
            if row["submission_status"] != "validating" or row["task_status"] != "validating":
                raise Conflict("Decision допустим только после перехода в validating")
            if row["bundle_sha256"] != row["validation_bundle_sha"]:
                raise BadRequest("validation относится к другому bundle")
            if row["task_version_sha256"] is None:
                raise BadRequest("submission не pin'ит task version")

            validation = json.loads(row["validation_payload"])
            checks = validation.get("checks", [])
            all_checks_green = (
                isinstance(checks, list) and bool(checks)
                and all(isinstance(check, dict)
                        and check.get("rc") == 0
                        and not check.get("skipped_reason")
                        for check in checks)
            )
            if decision == "accepted":
                if row["current_version"] != row["task_version"]:
                    raise Conflict("stale task version не может быть accepted/integrated")
                if validation.get("escalate_to_main") is True:
                    raise Conflict("escalate_to_main блокирует accepted")
                if not all_checks_green:
                    raise Conflict("accepted требует все checks passed без skipped/N/A")

            decision_id = f"DEC-{uuid.uuid4().hex[:16]}"
            record = {
                "schema": "decision/v1", "id": decision_id,
                "submission_id": submission_id, "validation_id": validation_id,
                "actor": actor, "decision": decision, "reason": reason.strip(),
                "decided_at": now_iso,
            }
            payload_json = _canon(record)
            payload_sha = _sha(payload_json)
            c.execute(
                "INSERT INTO decisions "
                "(id,submission_id,validation_id,decision,reason,actor,"
                "payload_sha256,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (decision_id, submission_id, validation_id, decision, reason.strip(),
                 actor, payload_sha, payload_json, now_iso),
            )
            task_status = {
                "accepted": "accepted",
                "needs_work": "ready",
                "rejected": "rejected",
            }[decision]
            c.execute(
                "UPDATE submissions SET status=?,status_reason=? WHERE id=?",
                (decision, reason.strip(), submission_id),
            )
            c.execute(
                "UPDATE tasks SET status=?,claimed_by=NULL,lease_expires_at_mono=NULL "
                "WHERE id=? AND status='validating'",
                (task_status, row["task_id"]),
            )
            if row["attempt_id"]:
                c.execute(
                    "UPDATE attempts SET status=?,ended_at=?,failure_reason=? "
                    "WHERE attempt_id=? AND status='submitted'",
                    (decision, now_iso, reason.strip(), row["attempt_id"]),
                )
            self._audit(
                c, actor, "submission.decision", "submission", submission_id,
                {"decision_id": decision_id, "validation_id": validation_id,
                 "decision": decision, "reason": reason.strip(),
                 "payload_sha256": payload_sha},
            )
            c.execute("COMMIT")
            return {"status": decision, "decision_id": decision_id}
        except Exception:
            self._safe_rollback(c)
            raise

    def start_integration(self, submission_id: str, head_before: str,
                          actor: str = "main") -> dict:
        """Create a fenced integration attempt; this records intent, not a git push."""
        if actor != "main":
            raise BadRequest("Integration может запускать только main")
        head_before = self._require_git_sha(head_before, "head_before")
        c = self.connect()
        now_iso, _ = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute(
                "SELECT s.id,s.task_id,s.task_version,s.status AS submission_status,"
                "t.status AS task_status,t.current_version,"
                "tv.payload_json,d.id AS decision_id,d.decision "
                "FROM submissions s JOIN tasks t ON t.id=s.task_id "
                "JOIN task_versions tv ON tv.task_id=s.task_id AND tv.version=s.task_version "
                "JOIN decisions d ON d.submission_id=s.id "
                "WHERE s.id=?",
                (submission_id,),
            ).fetchone()
            if row is None:
                raise NotFound(f"нет accepted submission {submission_id}")
            if row["submission_status"] != "accepted" or row["decision"] != "accepted":
                raise Conflict("Integration требует accepted submission и Decision")
            if row["current_version"] != row["task_version"]:
                raise Conflict("stale task version нельзя интегрировать")
            task_payload = json.loads(row["payload_json"])
            base_commit = self._require_git_sha(task_payload.get("base_commit"), "base_commit")
            if not head_before.startswith(base_commit):
                raise Conflict("head_before не совпадает с pinned task base_commit")

            active = c.execute(
                "SELECT id,decision_id,base_commit,head_before,actor,attempt_no "
                "FROM integrations WHERE submission_id=? AND status='started'",
                (submission_id,),
            ).fetchone()
            if active:
                if (row["task_status"] == "integrating"
                        and active["decision_id"] == row["decision_id"]
                        and active["base_commit"] == base_commit
                        and active["head_before"] == head_before
                        and active["actor"] == actor):
                    c.execute("COMMIT")
                    return {"status": "duplicate", "integration_id": active["id"],
                            "attempt_no": active["attempt_no"]}
                raise Conflict("у submission уже есть другая активная integration")
            if row["task_status"] not in ("accepted", "integration_failed"):
                raise Conflict(f"task status не допускает integration: {row['task_status']}")

            attempt_no = c.execute(
                "SELECT COALESCE(MAX(attempt_no),0)+1 FROM integrations WHERE submission_id=?",
                (submission_id,),
            ).fetchone()[0]
            integration_id = f"INT-{uuid.uuid4().hex[:16]}"
            c.execute(
                "INSERT INTO integrations "
                "(id,submission_id,decision_id,attempt_no,status,base_commit,head_before,"
                "changed_files_json,actor,started_at) "
                "VALUES (?,?,?,?, 'started',?,?, '[]',?,?)",
                (integration_id, submission_id, row["decision_id"], attempt_no,
                 base_commit, head_before, actor, now_iso),
            )
            c.execute(
                "UPDATE tasks SET status='integrating' WHERE id=? "
                "AND status IN ('accepted','integration_failed')",
                (row["task_id"],),
            )
            self._audit(
                c, actor, "integration.start", "integration", integration_id,
                {"submission_id": submission_id, "decision_id": row["decision_id"],
                 "attempt_no": attempt_no, "base_commit": base_commit,
                 "head_before": head_before},
            )
            c.execute("COMMIT")
            return {"status": "started", "integration_id": integration_id,
                    "attempt_no": attempt_no}
        except Exception:
            self._safe_rollback(c)
            raise

    def finish_integration(self, integration_id: str, head_after: str,
                           changed_files: list[str], actor: str = "main") -> dict:
        """Record a successful main-owned integration after final trusted gates."""
        if actor != "main":
            raise BadRequest("finish Integration может только main")
        head_after = self._require_git_sha(head_after, "head_after")
        if not isinstance(changed_files, list) or any(
                not isinstance(path, str) for path in changed_files):
            raise BadRequest("changed_files должен быть массивом строк")
        if len(changed_files) != len(set(changed_files)):
            raise BadRequest("changed_files содержит дубликаты")

        c = self.connect()
        now_iso, _ = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute(
                "SELECT i.*,s.task_id,s.task_version,t.current_version,"
                "t.status AS task_status,tv.payload_json "
                "FROM integrations i JOIN submissions s ON s.id=i.submission_id "
                "JOIN tasks t ON t.id=s.task_id "
                "JOIN task_versions tv ON tv.task_id=s.task_id AND tv.version=s.task_version "
                "WHERE i.id=?",
                (integration_id,),
            ).fetchone()
            if row is None:
                raise NotFound(f"нет integration {integration_id}")
            changed_json = _canon(changed_files)
            if row["status"] == "integrated":
                if row["head_after"] == head_after and row["changed_files_json"] == changed_json:
                    c.execute("COMMIT")
                    return {"status": "duplicate", "integration_id": integration_id}
                raise Conflict("integration уже завершена с другим содержимым")
            if row["status"] != "started" or row["task_status"] != "integrating":
                raise Conflict("integration не находится в started/integrating")
            if row["current_version"] != row["task_version"]:
                raise Conflict("task version изменилась во время integration")

            task_payload = json.loads(row["payload_json"])
            scopes = task_payload.get("write_scope")
            seen = set()
            for index, path in enumerate(changed_files):
                try:
                    _validate_relative_path(path)
                except BadRequest as exc:
                    raise BadRequest(f"changed_files[{index}]: {exc}") from exc
                if path in seen:
                    raise BadRequest(f"повторный changed file: {path}")
                seen.add(path)
                if _path_is_protected(path):
                    raise BadRequest(f"integration затрагивает PROTECTED path: {path}")
                if not _path_in_write_scope(path, scopes):
                    raise BadRequest(f"integration path вне task.write_scope: {path}")

            c.execute(
                "UPDATE integrations SET status='integrated',head_after=?,"
                "changed_files_json=?,finished_at=? WHERE id=? AND status='started'",
                (head_after, changed_json, now_iso, integration_id),
            )
            c.execute(
                "UPDATE tasks SET status='integrated' WHERE id=? AND status='integrating'",
                (row["task_id"],),
            )
            self._audit(
                c, actor, "integration.finish", "integration", integration_id,
                {"submission_id": row["submission_id"], "head_before": row["head_before"],
                 "head_after": head_after, "changed_files": changed_files},
            )
            c.execute("COMMIT")
            return {"status": "integrated", "integration_id": integration_id}
        except Exception:
            self._safe_rollback(c)
            raise

    def fail_integration(self, integration_id: str, reason: str,
                         actor: str = "main") -> dict:
        """Record a failed integration; an explicit retry creates a new attempt."""
        if actor != "main":
            raise BadRequest("отметить integration_failed может только main")
        if not isinstance(reason, str) or not reason.strip():
            raise BadRequest("integration failure reason обязателен")
        c = self.connect()
        now_iso, _ = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute(
                "SELECT i.*,s.task_id,t.status AS task_status "
                "FROM integrations i JOIN submissions s ON s.id=i.submission_id "
                "JOIN tasks t ON t.id=s.task_id WHERE i.id=?",
                (integration_id,),
            ).fetchone()
            if row is None:
                raise NotFound(f"нет integration {integration_id}")
            if row["status"] == "integration_failed":
                if row["error"] == reason.strip():
                    c.execute("COMMIT")
                    return {"status": "duplicate", "integration_id": integration_id}
                raise Conflict("integration уже помечена failed с другой причиной")
            if row["status"] != "started" or row["task_status"] != "integrating":
                raise Conflict("можно завершить ошибкой только started integration")
            c.execute(
                "UPDATE integrations SET status='integration_failed',error=?,finished_at=? "
                "WHERE id=? AND status='started'",
                (reason.strip(), now_iso, integration_id),
            )
            c.execute(
                "UPDATE tasks SET status='integration_failed' "
                "WHERE id=? AND status='integrating'",
                (row["task_id"],),
            )
            self._audit(
                c, actor, "integration.fail", "integration", integration_id,
                {"submission_id": row["submission_id"], "reason": reason.strip()},
            )
            c.execute("COMMIT")
            return {"status": "integration_failed", "integration_id": integration_id}
        except Exception:
            self._safe_rollback(c)
            raise

    # ------------------------------------------------ файловые проекции
    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            # Some supported filesystems/platforms do not implement directory fsync.
            pass

    @staticmethod
    def _write_fsynced(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _verify_projection_snapshot(self, snapshot: Path, snapshot_id: str) -> None:
        """Verify every file against the immutable snapshot content address."""
        if snapshot.is_symlink() or not snapshot.is_dir():
            raise NotFound(f"projection snapshot is missing: {snapshot_id}")
        manifest_path = snapshot / "manifest.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise BadRequest("projection snapshot manifest is missing or unsafe")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BadRequest("projection snapshot manifest cannot be read") from exc
        if not isinstance(manifest, dict) or manifest.get("schema") != "projection/v1":
            raise BadRequest("unsupported projection manifest")
        expected_files = manifest.get("files")
        if not isinstance(expected_files, dict):
            raise BadRequest("projection manifest files must be an object")

        actual_files: dict[str, bytes] = {}
        for path in snapshot.rglob("*"):
            if path.is_symlink():
                raise BadRequest(f"symlink in immutable projection: {path.relative_to(snapshot)}")
            if path.is_file():
                rel = path.relative_to(snapshot).as_posix()
                actual_files[rel] = path.read_bytes()
            elif not path.is_dir():
                raise BadRequest(f"special file in immutable projection: {path.relative_to(snapshot)}")

        if set(actual_files) != set(expected_files) | {"manifest.json"}:
            raise BadRequest("projection snapshot files do not match manifest")
        for rel, expected_sha in expected_files.items():
            self._validate_relative_projection_path(rel)
            if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
                raise BadRequest("projection manifest contains an invalid file hash")
            if _sha(actual_files[rel]) != expected_sha:
                raise BadRequest(f"projection file hash mismatch: {rel}")

        hasher = hashlib.sha256()
        for rel in sorted(actual_files):
            hasher.update(rel.encode("utf-8"))
            hasher.update(b"\0")
            hasher.update(actual_files[rel])
        if hasher.hexdigest() != snapshot_id:
            raise BadRequest("projection snapshot content hash does not match CURRENT")

    def resolve_projections(self, target: Path) -> Path:
        """Resolve and verify the immutable snapshot named by CURRENT."""
        target = Path(target)
        if target.is_symlink() or not target.is_dir():
            raise BadRequest("projection root must be a real directory")
        current = target / "CURRENT"
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError as exc:
            raise NotFound(f"projection CURRENT is missing: {target}") from exc
        if current.is_symlink() or not os.path.isfile(current):
            raise BadRequest("projection CURRENT must be a regular file")
        snapshot_id = current.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[0-9a-f]{64}", snapshot_id):
            raise BadRequest("projection CURRENT contains an invalid snapshot id")
        snapshots = target / "snapshots"
        if snapshots.is_symlink() or not snapshots.is_dir():
            raise BadRequest("projection snapshots directory is missing or unsafe")
        snapshot = snapshots / snapshot_id
        self._verify_projection_snapshot(snapshot, snapshot_id)
        return snapshot

    def write_projections(self, target: Path) -> dict:
        """Build a consistent immutable snapshot and atomically publish CURRENT.

        Consumers must resolve the snapshot with resolve_projections(); the
        root directory is persistent and CURRENT is the single publication point.
        An interrupted build can leave an unreferenced snapshot, never a missing
        or partially replaced current projection.
        """
        target = Path(target)
        if target.is_symlink():
            raise BadRequest("projection root must not be a symlink")
        target.mkdir(parents=True, exist_ok=True)
        if not target.is_dir():
            raise BadRequest("projection root must be a directory")
        snapshots_dir = target / "snapshots"
        if snapshots_dir.is_symlink():
            raise BadRequest("projection snapshots directory must not be a symlink")
        snapshots_dir.mkdir(exist_ok=True)
        if not snapshots_dir.is_dir():
            raise BadRequest("projection snapshots path is not a directory")

        # Fetch every table under one SQLite read snapshot. Commit before the
        # slower filesystem write so writers are not held behind projection I/O.
        c = self.connect()
        c.execute("BEGIN")
        try:
            tasks = c.execute(
                "SELECT id,department,status,current_version,lease_epoch,created_at "
                "FROM tasks ORDER BY id"
            ).fetchall()
            versions = c.execute(
                "SELECT task_id,version,payload_json FROM task_versions "
                "ORDER BY task_id, version"
            ).fetchall()
            submissions = c.execute(
                "SELECT id,task_id,attempt_id,agent_id,status,bundle_sha256,submitted_at "
                "FROM submissions ORDER BY id"
            ).fetchall()
            messages = c.execute(
                "SELECT id,recipient,kind,severity,requires_ack,blocks_claim,"
                "blocks_submit,halt,superseded_by,created_at_iso "
                "FROM messages ORDER BY created_at, id"
            ).fetchall()
            validations = c.execute(
                "SELECT id,submission_id,bundle_sha256,validator_profile,validator_version,"
                "recommendation,actor,payload_sha256,created_at "
                "FROM validations ORDER BY created_at,id"
            ).fetchall()
            decisions = c.execute(
                "SELECT id,submission_id,validation_id,decision,reason,actor,created_at "
                "FROM decisions ORDER BY created_at,id"
            ).fetchall()
            integrations = c.execute(
                "SELECT id,submission_id,decision_id,attempt_no,status,base_commit,"
                "head_before,head_after,changed_files_json,error,actor,started_at,finished_at "
                "FROM integrations ORDER BY submission_id,attempt_no"
            ).fetchall()
            head = c.execute(
                "SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            audit_head = head["event_hash"] if head else "GENESIS"
            c.execute("COMMIT")
        except Exception:
            self._safe_rollback(c)
            raise

        files: dict[str, bytes] = {}
        files["tasks.jsonl"] = "".join(
            _canon({k: row[k] for k in row.keys()}) + "\n" for row in tasks
        ).encode("utf-8")
        files["submissions.jsonl"] = "".join(
            _canon({k: row[k] for k in row.keys()}) + "\n" for row in submissions
        ).encode("utf-8")
        files["messages.jsonl"] = "".join(
            _canon({k: row[k] for k in row.keys()}) + "\n" for row in messages
        ).encode("utf-8")
        files["validations.jsonl"] = "".join(
            _canon({k: row[k] for k in row.keys()}) + "\n" for row in validations
        ).encode("utf-8")
        files["decisions.jsonl"] = "".join(
            _canon({k: row[k] for k in row.keys()}) + "\n" for row in decisions
        ).encode("utf-8")
        files["integrations.jsonl"] = "".join(
            _canon({k: row[k] for k in row.keys()}) + "\n" for row in integrations
        ).encode("utf-8")
        files["audit_head.txt"] = audit_head.encode("ascii")

        for version in versions:
            rel = f"task_versions/{version['task_id']}/v{version['version']}.json"
            self._validate_relative_projection_path(rel)
            files[rel] = version["payload_json"].encode("utf-8")

        manifest = {
            "schema": "projection/v1",
            "files": {rel: _sha(data) for rel, data in sorted(files.items())},
        }
        files["manifest.json"] = _canon(manifest).encode("utf-8")
        snapshot_hasher = hashlib.sha256()
        for rel in sorted(files):
            snapshot_hasher.update(rel.encode("utf-8"))
            snapshot_hasher.update(b"\0")
            snapshot_hasher.update(files[rel])
        snapshot_id = snapshot_hasher.hexdigest()
        snapshot_dir = snapshots_dir / snapshot_id

        if snapshot_dir.is_symlink():
            raise BadRequest("snapshot id path must not be a symlink")
        if not snapshot_dir.exists():
            tmp = snapshots_dir / f".tmp-{uuid.uuid4().hex}"
            tmp.mkdir(mode=0o700)
            try:
                for rel, data in sorted(files.items()):
                    self._write_fsynced(tmp / rel, data)
                # Persist nested directory entries bottom-up before publishing
                # the immutable snapshot directory itself.
                dirs = [p for p in tmp.rglob("*") if p.is_dir()]
                for directory in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
                    self._fsync_directory(directory)
                self._fsync_directory(tmp)
                try:
                    os.rename(tmp, snapshot_dir)
                    self._fsync_directory(snapshots_dir)
                except OSError:
                    # Another writer may have published the same content hash.
                    if not snapshot_dir.is_dir() or snapshot_dir.is_symlink():
                        raise
            finally:
                if tmp.exists():
                    shutil.rmtree(tmp, ignore_errors=True)
        elif not snapshot_dir.is_dir():
            raise BadRequest("snapshot id path is not a directory")

        # Verify the completed immutable tree before publishing the pointer.
        self._verify_projection_snapshot(snapshot_dir, snapshot_id)

        # One small, fsynced pointer is the only mutable publication artifact.
        # If the replace fails, the previous CURRENT remains readable.
        current_tmp = target / f".CURRENT-{uuid.uuid4().hex}.tmp"
        current_path = target / "CURRENT"
        try:
            self._write_fsynced(current_tmp, (snapshot_id + "\n").encode("ascii"))
            os.replace(current_tmp, current_path)
            self._fsync_directory(target)
        finally:
            try:
                current_tmp.unlink(missing_ok=True)
            except OSError:
                pass

        snapshot_path = self.resolve_projections(target)
        return {
            "path": str(target),
            "snapshot_path": str(snapshot_path),
            "snapshot_id": snapshot_id,
            "tasks": len(tasks),
            "task_versions": len(versions),
            "submissions": len(submissions),
            "messages": len(messages),
            "validations": len(validations),
            "decisions": len(decisions),
            "integrations": len(integrations),
        }

    # -------------------------------------------------------- GC blobs
    def gc_blobs(self, grace_seconds: float = 3600.0) -> dict:
        """Mark-and-sweep: .part старше grace; blob без артефакт-ссылки старше
        grace. Ссылочность определяется по таблице artifacts (mark на upload)."""
        c = self.connect()
        self.store.ensure()
        deadline = time.time() - grace_seconds
        deleted_tmp = 0
        deleted_blobs = 0
        for p in self.store.tmp.glob("*.part"):
            try:
                if p.stat().st_mtime < deadline:
                    p.unlink()
                    deleted_tmp += 1
            except FileNotFoundError:
                pass
        for p in self.store.blobs.glob("*/*"):
            if not p.is_file():
                continue
            if c.execute("SELECT 1 FROM artifacts WHERE sha256=?",
                         (p.name,)).fetchone():
                continue
            try:
                if p.stat().st_mtime < deadline:
                    p.unlink()
                    deleted_blobs += 1
            except FileNotFoundError:
                pass
        if deleted_blobs or deleted_tmp:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._audit(c, "gc", "blob.sweep", "store", str(self.store.root),
                            {"blobs": deleted_blobs, "tmp": deleted_tmp})
                c.execute("COMMIT")
            except Exception:
                self._safe_rollback(c)
                raise
        return {"deleted_blobs": deleted_blobs, "deleted_tmp": deleted_tmp}


class ControlPlane2(V2OpsMixin, ControlPlane):
    """Ядро Фазы 2 + вторая серия операций; единый писатель для CLI и агентов."""
