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
    def write_projections(self, target: Path) -> dict:
        """Детерминированный файловый снимок БД; восстановление = повторный
        вызов. Атомарная подмена каталога (tmp -> os.replace)."""
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        c = self.connect()
        tmp = target.parent / f".{target.name}.tmp-{uuid.uuid4().hex[:8]}"
        if tmp.exists():
            shutil.rmtree(tmp)
        (tmp / "task_versions").mkdir(parents=True)
        tasks = c.execute(
            "SELECT id,department,status,current_version,lease_epoch,created_at "
            "FROM tasks ORDER BY id").fetchall()
        with (tmp / "tasks.jsonl").open("w", encoding="utf-8") as f:
            for t in tasks:
                f.write(_canon({k: t[k] for k in t.keys()}) + "\n")
        versions = c.execute(
            "SELECT task_id,version,payload_json FROM task_versions "
            "ORDER BY task_id, version").fetchall()
        for v in versions:
            d = tmp / "task_versions" / v["task_id"]
            d.mkdir(exist_ok=True)
            (d / f"v{v['version']}.json").write_text(
                v["payload_json"], encoding="utf-8")
        submissions = c.execute(
            "SELECT id,task_id,attempt_id,agent_id,status,bundle_sha256,submitted_at "
            "FROM submissions ORDER BY id").fetchall()
        with (tmp / "submissions.jsonl").open("w", encoding="utf-8") as f:
            for s in submissions:
                f.write(_canon({k: s[k] for k in s.keys()}) + "\n")
        messages = c.execute(
            "SELECT id,recipient,kind,severity,requires_ack,blocks_claim,"
            "blocks_submit,halt,superseded_by,created_at_iso "
            "FROM messages ORDER BY created_at, id").fetchall()
        with (tmp / "messages.jsonl").open("w", encoding="utf-8") as f:
            for m in messages:
                f.write(_canon({k: m[k] for k in m.keys()}) + "\n")
        head = c.execute(
            "SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
        (tmp / "audit_head.txt").write_text(
            head["event_hash"] if head else "GENESIS", encoding="utf-8")
        if target.exists():
            old = target.parent / f".{target.name}.old-{uuid.uuid4().hex[:8]}"
            os.replace(target, old)
            os.replace(tmp, target)
            shutil.rmtree(old, ignore_errors=True)
        else:
            os.replace(tmp, target)
        return {"path": str(target), "tasks": len(tasks),
                "task_versions": len(versions),
                "submissions": len(submissions), "messages": len(messages)}

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
