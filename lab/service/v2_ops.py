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

import ctypes
import errno
import fcntl
import hashlib
import json
import math
import os
import re
import stat
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
                columns = {
                    row["name"] for row in c.execute("PRAGMA table_info(artifacts)")
                }
                if "last_seen_at" not in columns:
                    c.execute("ALTER TABLE artifacts ADD COLUMN last_seen_at TEXT")
                    c.execute("UPDATE artifacts SET last_seen_at=created_at "
                              "WHERE last_seen_at IS NULL")
                c.execute(
                    "CREATE TABLE IF NOT EXISTS upload_artifacts ("
                    "upload_id TEXT NOT NULL REFERENCES uploads(upload_id), "
                    "sha256 TEXT NOT NULL REFERENCES artifacts(sha256), "
                    "created_at TEXT NOT NULL, "
                    "PRIMARY KEY (upload_id,sha256))"
                )
                c.execute(
                    "CREATE INDEX IF NOT EXISTS ix_upload_artifacts_sha "
                    "ON upload_artifacts(sha256)"
                )
                orphan_upload_refs = c.execute(
                    "SELECT COUNT(*) FROM artifacts a LEFT JOIN uploads u "
                    "ON u.upload_id=a.upload_id "
                    "WHERE a.upload_id IS NOT NULL AND u.upload_id IS NULL"
                ).fetchone()[0]
                c.execute(
                    "INSERT OR IGNORE INTO upload_artifacts(upload_id,sha256,created_at) "
                    "SELECT a.upload_id,a.sha256,a.created_at FROM artifacts a "
                    "JOIN uploads u ON u.upload_id=a.upload_id "
                    "WHERE a.upload_id IS NOT NULL"
                )
                linked = c.execute(
                    "SELECT COUNT(*) FROM upload_artifacts"
                ).fetchone()[0]
                c.execute("PRAGMA user_version=5")
                self._audit(c, "schema", "schema.migrate", "db", str(self.db_path),
                            {"from": 4, "to": 5, "upload_artifact_links": linked,
                             "unresolved_upload_references": orphan_upload_refs})
                c.execute("COMMIT")
            except Exception:
                self._safe_rollback(c)
                raise

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
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _write_projection_file(path: Path, data: bytes) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o644)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _remove_projection_entry(path: Path) -> None:
        try:
            info = path.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISDIR(info.st_mode):
            shutil.rmtree(path)
        else:
            # Symlinks and special files are unlinked, never traversed.
            path.unlink()

    @staticmethod
    def _rename_exchange(source: Path, destination: Path) -> bool:
        """Atomically exchange two same-filesystem directory names when Linux supports it."""
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            return False
        renameat2.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100, os.fsencode(source), -100, os.fsencode(destination), 2
        )  # AT_FDCWD, RENAME_EXCHANGE
        if result == 0:
            return True
        error = ctypes.get_errno()
        unsupported = {
            errno.ENOSYS, errno.EINVAL,
            getattr(errno, "EOPNOTSUPP", errno.EINVAL),
            getattr(errno, "ENOTSUP", errno.EINVAL),
        }
        if error in unsupported:
            return False
        raise OSError(error, os.strerror(error), f"{source} <-> {destination}")

    def _recover_projection_publication(self, target: Path) -> None:
        """Recover the old snapshot if a process died after target -> .old rename."""
        parent = target.parent
        name = target.name
        try:
            target_info = target.lstat()
        except FileNotFoundError:
            target_info = None
        if target_info is not None:
            if stat.S_ISLNK(target_info.st_mode) or not stat.S_ISDIR(target_info.st_mode):
                raise BadRequest(f"projection target must be a real directory: {target}")

        old_prefix = f".{name}.old-"
        tmp_prefix = f".{name}.tmp-"
        entries = list(parent.iterdir())
        old_dirs = [p for p in entries if p.name.startswith(old_prefix)]
        temp_dirs = [p for p in entries if p.name.startswith(tmp_prefix)]

        if target_info is None and old_dirs:
            # There can be several after repeated interrupted recovery attempts.
            # Restore the newest valid backup; leave no dangling projection path.
            for old in old_dirs:
                info = old.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise BadRequest(f"unsafe projection recovery entry: {old}")
            restore = max(old_dirs, key=lambda p: p.lstat().st_mtime_ns)
            os.replace(restore, target)
            self._fsync_directory(parent)
            old_dirs.remove(restore)

        for stale in old_dirs + temp_dirs:
            self._remove_projection_entry(stale)
        if old_dirs or temp_dirs:
            self._fsync_directory(parent)

    def write_projections(self, target: Path) -> dict:
        """Create a consistent DB snapshot and publish it with crash recovery.

        Writers are serialized by an advisory lock. Linux uses renameat2
        RENAME_EXCHANGE for an atomic directory swap; unsupported filesystems
        fall back to a recoverable old-directory rename protocol.
        """
        target = Path(target)
        if not target.name or target.name in (".", ".."):
            raise BadRequest("projection target must name a directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        lock_path = target.parent / f".{target.name}.lock"
        lock_flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        try:
            lock_fd = os.open(lock_path, lock_flags, 0o600)
        except OSError as exc:
            raise BadRequest(f"cannot safely open projection lock: {exc}") from exc
        tmp = target.parent / f".{target.name}.tmp-{uuid.uuid4().hex}"
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            self._recover_projection_publication(target)

            # Materialise every query under one SQLite read transaction. No
            # SELECT below this point observes a newer control-plane commit.
            c = self.connect()
            c.execute("BEGIN")
            try:
                tasks = c.execute(
                    "SELECT id,department,status,current_version,lease_epoch,created_at "
                    "FROM tasks ORDER BY id").fetchall()
                versions = c.execute(
                    "SELECT task_id,version,payload_json FROM task_versions "
                    "ORDER BY task_id, version").fetchall()
                submissions = c.execute(
                    "SELECT id,task_id,attempt_id,agent_id,status,bundle_sha256,submitted_at "
                    "FROM submissions ORDER BY id").fetchall()
                messages = c.execute(
                    "SELECT id,recipient,kind,severity,requires_ack,blocks_claim,"
                    "blocks_submit,halt,superseded_by,created_at_iso "
                    "FROM messages ORDER BY created_at, id").fetchall()
                head = c.execute(
                    "SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1"
                ).fetchone()
                audit_head = head["event_hash"] if head else "GENESIS"
                c.execute("COMMIT")
            except Exception:
                self._safe_rollback(c)
                raise

            (tmp / "task_versions").mkdir(parents=True)
            task_lines = "".join(
                _canon({k: task[k] for k in task.keys()}) + "\n" for task in tasks
            )
            self._write_projection_file(tmp / "tasks.jsonl", task_lines.encode("utf-8"))

            version_dirs: set[Path] = set()
            for version in versions:
                task_id = version["task_id"]
                if (not isinstance(task_id, str) or not task_id
                        or "/" in task_id or "\\" in task_id
                        or task_id in (".", "..")):
                    raise BadRequest(f"unsafe task id in projection: {task_id!r}")
                directory = tmp / "task_versions" / task_id
                if directory not in version_dirs:
                    directory.mkdir()
                    version_dirs.add(directory)
                self._write_projection_file(
                    directory / f"v{version['version']}.json",
                    version["payload_json"].encode("utf-8"),
                )

            submission_lines = "".join(
                _canon({k: item[k] for k in item.keys()}) + "\n"
                for item in submissions
            )
            self._write_projection_file(
                tmp / "submissions.jsonl", submission_lines.encode("utf-8"))

            message_lines = "".join(
                _canon({k: item[k] for k in item.keys()}) + "\n"
                for item in messages
            )
            self._write_projection_file(
                tmp / "messages.jsonl", message_lines.encode("utf-8"))
            self._write_projection_file(
                tmp / "audit_head.txt", (audit_head + "\n").encode("utf-8"))

            file_hashes = {}
            for item in sorted(tmp.rglob("*")):
                if item.is_file():
                    relative = item.relative_to(tmp).as_posix()
                    file_hashes[relative] = hashlib.sha256(item.read_bytes()).hexdigest()
            manifest = {
                "schema": "lab-projection/v1",
                "counts": {
                    "tasks": len(tasks),
                    "task_versions": len(versions),
                    "submissions": len(submissions),
                    "messages": len(messages),
                },
                "audit_head": audit_head,
                "files": file_hashes,
            }
            manifest_bytes = (_canon(manifest) + "\n").encode("utf-8")
            self._write_projection_file(tmp / "manifest.json", manifest_bytes)

            # fsync nested directories bottom-up before publishing the name.
            directories = [p for p in tmp.rglob("*") if p.is_dir()]
            for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
                self._fsync_directory(directory)
            self._fsync_directory(tmp)

            if target.exists() and self._rename_exchange(tmp, target):
                # tmp now names the previous complete generation.
                self._fsync_directory(target.parent)
                self._remove_projection_entry(tmp)
                self._fsync_directory(target.parent)
            else:
                old = None
                if target.exists():
                    old = target.parent / f".{target.name}.old-{uuid.uuid4().hex}"
                    os.replace(target, old)
                    self._fsync_directory(target.parent)
                try:
                    os.replace(tmp, target)
                    self._fsync_directory(target.parent)
                except Exception:
                    # Restore synchronously if publication failed in this process.
                    if old is not None and old.exists() and not target.exists():
                        os.replace(old, target)
                        self._fsync_directory(target.parent)
                    raise
                if old is not None:
                    self._remove_projection_entry(old)
                    self._fsync_directory(target.parent)

            return {
                "path": str(target),
                "tasks": len(tasks),
                "task_versions": len(versions),
                "submissions": len(submissions),
                "messages": len(messages),
                "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "audit_head": audit_head,
            }
        finally:
            self._remove_projection_entry(tmp)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)

    # -------------------------------------------------------- GC blobs
    def gc_blobs(self, grace_seconds: float = 3600.0) -> dict:
        """Transactional mark-and-sweep; never removes a blob linked to a submission."""
        if (not isinstance(grace_seconds, (int, float)) or isinstance(grace_seconds, bool)
                or grace_seconds < 0 or not math.isfinite(grace_seconds)):
            raise BadRequest("grace_seconds должен быть конечным неотрицательным числом")
        c = self.connect()
        self.store.ensure()
        file_deadline = time.time() - grace_seconds
        db_deadline = _utc(self.wall() - grace_seconds)
        deleted_tmp = 0
        deleted_blobs = 0
        c.execute("BEGIN IMMEDIATE")
        try:
            for path in self.store.tmp.glob("*.part"):
                try:
                    info = path.lstat()
                    if info.st_mtime < file_deadline and (
                        stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                    ):
                        path.unlink()
                        deleted_tmp += 1
                except FileNotFoundError:
                    pass

            has_submission_links = c.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='submission_artifacts'"
            ).fetchone()
            has_upload_links = c.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='upload_artifacts'"
            ).fetchone()
            has_last_seen = "last_seen_at" in {
                row["name"] for row in c.execute("PRAGMA table_info(artifacts)")
            }
            if has_submission_links and has_upload_links and has_last_seen:
                candidates = c.execute(
                    "SELECT a.sha256 FROM artifacts a "
                    "WHERE COALESCE(a.last_seen_at,a.created_at) < ? "
                    "AND NOT EXISTS (SELECT 1 FROM submission_artifacts sa "
                    "WHERE sa.sha256=a.sha256) "
                    "AND NOT EXISTS (SELECT 1 FROM upload_artifacts ua "
                    "JOIN uploads u ON u.upload_id=ua.upload_id "
                    "WHERE ua.sha256=a.sha256 AND u.state='open' AND u.created_at>=?)",
                    (db_deadline, db_deadline),
                ).fetchall()
                for candidate in candidates:
                    digest = candidate["sha256"]
                    if isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest):
                        path = self.store.path(digest)
                        try:
                            info = path.lstat()
                            if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                                path.unlink()
                        except FileNotFoundError:
                            pass
                    c.execute("DELETE FROM upload_artifacts WHERE sha256=?", (digest,))
                    c.execute("DELETE FROM artifacts WHERE sha256=?", (digest,))
                    deleted_blobs += 1

            # Remove old physical orphans not represented in metadata. lstat
            # means a symlink is unlinked as a link and never followed.
            known = {row["sha256"] for row in c.execute(
                "SELECT sha256 FROM artifacts"
            ).fetchall()}
            for path in self.store.blobs.glob("*/*"):
                if path.name in known:
                    continue
                try:
                    info = path.lstat()
                    if info.st_mtime < file_deadline and (
                        stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                    ):
                        path.unlink()
                        deleted_blobs += 1
                except FileNotFoundError:
                    pass

            if deleted_blobs or deleted_tmp:
                self._audit(c, "gc", "blob.sweep", "store", str(self.store.root),
                            {"blobs": deleted_blobs, "tmp": deleted_tmp,
                             "cutoff": db_deadline})
            c.execute("COMMIT")
        except Exception:
            self._safe_rollback(c)
            raise
        return {"deleted_blobs": deleted_blobs, "deleted_tmp": deleted_tmp}


class ControlPlane2(V2OpsMixin, ControlPlane):
    """Ядро Фазы 2 + вторая серия операций; единый писатель для CLI и агентов."""
