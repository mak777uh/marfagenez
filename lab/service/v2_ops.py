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
from pathlib import Path
from typing import Any

from lab.service.control import (  # noqa: F401 (re-export для cli/tests)
    BadRequest, Conflict, ControlPlane, CtlError, Gone, NotFound, _canon, _sha)

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
                        exists = c.execute(
                            "SELECT 1 FROM artifacts WHERE sha256=?", (digest,)
                        ).fetchone()
                        if not exists:
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
        """Submit в контуре отмены запрещён до acknowledge; иначе — ядро (§14.4)."""
        row = self.connect().execute(
            "SELECT status FROM tasks WHERE id=?", (payload.get("task_id"),)).fetchone()
        if row and row["status"] == "cancellation_requested":
            raise BadRequest(
                "задача отменяется main: сначала acknowledge_cancel; "
                "submit после подтверждения уйдёт в карантин late")
        return super().submit(payload, idem_key)

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
