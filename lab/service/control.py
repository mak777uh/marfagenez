"""lab/service/control.py — локальный контрольный слой (Фаза 2, план v0.3 §9–14).

SQLite WAL на ext4: единственный писатель — сервис; CLI/агенты вызывают его.
Инварианты: один активный lease на задачу (частичный уникальный индекс),
монотонный lease_epoch на задачу, expiry вычисляется внутри claim (reaper не
условие возврата), идемпотентность (agent, endpoint, key) со снапшотом ответа,
heartbeat не блокируется сообщениями, поздний submit — карантин, не мутация
попытки. Аудит — append-only с hash chain.

Время: wall (UTC RFC3339) для аудита, monotonic для TTL (NTP-скачок не
просрочивает lease). Оба времени инъектируются для тестов.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROTOCOL = 1
FALSE = ("false", 0)
TRUE = ("true", 1)

class CtlError(Exception):
    code = 500

class Conflict(CtlError):        # 409: idem-key с другим payload / CAS-гонка
    code = 409

class Gone(CtlError):             # 410: fencing — истёкший/чужой lease
    code = 410

class NotFound(CtlError):
    code = 404

class Blocked(CtlError):          # 412: обязательное сообщение не acked
    code = 412

class BadRequest(CtlError):
    code = 400


def _utc(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
  agent_id TEXT PRIMARY KEY, instance_id TEXT, scopes_json TEXT,
  status TEXT NOT NULL DEFAULT 'active', token_id TEXT,
  revoked_at TEXT, boot_id TEXT, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  department TEXT NOT NULL CHECK (department IN ('experiments','formulas','knowledge')),
  status TEXT NOT NULL
    CHECK (status IN ('ready','blocked','claimed','submitted','validating','waiting_main',
                     'cancellation_requested','cancelled','manual_review',
                     'accepted','integrating','integration_failed','integrated','rejected')),
  priority INTEGER NOT NULL DEFAULT 0 CHECK (priority BETWEEN 0 AND 100),
  current_version INTEGER NOT NULL,
  lease_epoch INTEGER NOT NULL DEFAULT 0,
  lease_expires_at_mono REAL,
  max_expires_at_mono REAL,
  claimed_by TEXT,
  created_at TEXT NOT NULL);

-- Immutable постановки; изменение = новая строка с supersedes_version.
CREATE TABLE IF NOT EXISTS task_versions (
  task_id TEXT NOT NULL REFERENCES tasks(id),
  version INTEGER NOT NULL,
  task_version_sha256 TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  supersedes_version INTEGER,
  change_reason TEXT,
  published_by TEXT NOT NULL,
  published_at TEXT NOT NULL,
  lease_json TEXT NOT NULL,
  PRIMARY KEY (task_id, version));

CREATE TABLE IF NOT EXISTS dependencies (
  task_id TEXT NOT NULL REFERENCES tasks(id),
  required_task_id TEXT NOT NULL,
  required_task_version INTEGER NOT NULL,
  required_state TEXT NOT NULL CHECK (required_state IN ('accepted','integrated')),
  required_artifact_sha256 TEXT NOT NULL,
  PRIMARY KEY (task_id, required_task_id, required_task_version));

CREATE TABLE IF NOT EXISTS leases (
  lease_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id),
  task_version INTEGER NOT NULL,
  attempt_id TEXT NOT NULL,
  lease_epoch INTEGER NOT NULL,
  agent_id TEXT NOT NULL,
  instance_id TEXT,
  boot_id TEXT,
  issued_at TEXT NOT NULL,
  issued_at_mono REAL NOT NULL,
  expires_at TEXT NOT NULL,
  expires_at_mono REAL NOT NULL,
  max_expires_at TEXT NOT NULL,
  max_expires_at_mono REAL NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('active','expired','released'))
    DEFAULT 'active',
  expired_at TEXT, expired_at_mono REAL,
  released_at TEXT,
  FOREIGN KEY (task_id, task_version) REFERENCES task_versions(task_id, version));

-- ровно один активный lease на задачу
CREATE UNIQUE INDEX IF NOT EXISTS ux_leases_active_task
  ON leases(task_id) WHERE state='active';

CREATE TABLE IF NOT EXISTS attempts (
  attempt_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id),
  task_version INTEGER NOT NULL,
  attempt_no INTEGER NOT NULL,
  lease_id TEXT NOT NULL,
  lease_epoch INTEGER NOT NULL,
  agent_id TEXT NOT NULL,
  started_at TEXT NOT NULL, ended_at TEXT,
  status TEXT NOT NULL CHECK (status IN
    ('claimed','submitted','expired','void','needs_work','accepted','rejected','manual_review')),
  failure_reason TEXT,
  UNIQUE (task_id, attempt_no));

CREATE TABLE IF NOT EXISTS artifacts (
  sha256 TEXT PRIMARY KEY, bytes INTEGER NOT NULL,
  media_type TEXT NOT NULL, blob_id TEXT NOT NULL, upload_id TEXT,
  task_id TEXT, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS uploads (
  upload_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
  finished_at TEXT);

CREATE TABLE IF NOT EXISTS submissions (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id),
  task_version INTEGER NOT NULL,
  task_version_sha256 TEXT,
  attempt_id TEXT, lease_id TEXT, lease_epoch INTEGER,
  agent_id TEXT NOT NULL, instance_id TEXT,
  base_commit TEXT, bundle_sha256 TEXT,
  artifacts_json TEXT, environment_json TEXT, toolchain_json TEXT,
  scientific_outcome TEXT,
  parent_submission_id TEXT,
  complied_messages_json TEXT,
  submitted_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN
    ('received','validating','needs_work','accepted','rejected','late')),
  status_reason TEXT);

-- bundle-дедупликация внутри попытки
CREATE UNIQUE INDEX IF NOT EXISTS ux_submission_bundle
  ON submissions(attempt_id, bundle_sha256) WHERE status != 'late';

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  sender TEXT NOT NULL,
  recipient TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'info',
  severity TEXT NOT NULL DEFAULT 'normal',
  scope TEXT NOT NULL DEFAULT 'agent',
  thread_id TEXT,
  requires_read INTEGER NOT NULL DEFAULT 0,
  requires_ack INTEGER NOT NULL DEFAULT 0,
  blocks_claim INTEGER NOT NULL DEFAULT 0,
  blocks_submit INTEGER NOT NULL DEFAULT 0,
  halt INTEGER NOT NULL DEFAULT 0,
  body TEXT NOT NULL,
  ref TEXT,
  expires_at TEXT, expires_at_mono REAL,
  superseded_by TEXT,
  ack_deadline TEXT,
  created_at REAL NOT NULL,          -- epoch wall, чтобы сортировка была линейной
  created_at_iso TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS message_receipts (
  message_id TEXT NOT NULL REFERENCES messages(id),
  agent_id TEXT NOT NULL,
  read_at TEXT, ack_at TEXT,
  PRIMARY KEY (message_id, agent_id));

CREATE TABLE IF NOT EXISTS idempotency (
  agent_id TEXT NOT NULL, endpoint TEXT NOT NULL, key TEXT NOT NULL,
  request_sha256 TEXT NOT NULL,
  response_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (agent_id, endpoint, key));

CREATE TABLE IF NOT EXISTS audit_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL, action TEXT NOT NULL,
  entity TEXT NOT NULL, entity_id TEXT NOT NULL,
  prev_event_hash TEXT NOT NULL,
  event_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  details_json TEXT NOT NULL DEFAULT '{}');
"""


class ArtifactStore:
    """Content-addressed blobs: tmp-загрузка -> fsync -> атомарный os.replace."""

    def __init__(self, root: Path):
        self.root = root
        self.tmp = root / "tmp"
        self.blobs = root / "blobs"

    def ensure(self):
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.blobs.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, upload_id: str | None = None) -> str:
        self.ensure()
        digest = _sha(data)
        dest = self.blobs / digest[:2] / digest
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            t = self.tmp / f"{uuid.uuid4().hex}.part"
            with open(t, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(t, dest)
        return digest

    def path(self, digest: str) -> Path:
        return self.blobs / digest[:2] / digest


class ControlPlane:
    def __init__(self, db_path: Path, artifacts: Path | None = None,
                 wall: Callable[[], float] = time.time,
                 mono: Callable[[], float] = time.monotonic):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = ArtifactStore(artifacts or (self.db_path.parent / "artifacts"))
        self.wall, self.mono = wall, mono
        self._conn: sqlite3.Connection | None = None

    # ---------------------------------------------------------------- базовые
    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            c = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA busy_timeout=30000")
            c.execute("PRAGMA synchronous=FULL")
            self._conn = c
        return self._conn

    def init(self) -> None:
        c = self.connect()
        c.executescript(SCHEMA)
        # Version 1 is assigned only to an unversioned database. Re-running
        # init on a v2/v3 database must not rewind its migration head.
        if c.execute("PRAGMA user_version").fetchone()[0] == 0:
            c.execute("PRAGMA user_version=1")

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def backup(self, dest_path: Path) -> None:
        import contextlib
        dst = sqlite3.connect(dest_path)
        with dst:
            self.connect().backup(dst)
        dst.close()

    def _now(self) -> tuple[str, float]:
        return _utc(self.wall()), self.mono()

    def _safe_rollback(self, c: sqlite3.Connection) -> None:
        """ROLLBACK, который не взрывает обработчик ошибки после COMMIT."""
        try:
            c.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass

    def _audit(self, c: sqlite3.Connection, actor: str, action: str,
               entity: str, entity_id: str, details: dict) -> None:
        prev_row = c.execute(
            "SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
        prev = prev_row[0] if prev_row else "GENESIS"
        now_iso, _ = self._now()
        h = _sha(f"{prev}|{actor}|{action}|{entity}|{entity_id}|{now_iso}|{_canon(details)}")
        c.execute(
            "INSERT INTO audit_events (actor,action,entity,entity_id,prev_event_hash,"
            "event_hash,created_at,details_json) VALUES (?,?,?,?,?,?,?,?)",
            (actor, action, entity, entity_id, prev, h, now_iso, _canon(details)))

    def verify_audit_chain(self) -> bool:
        c = self.connect()
        prev = "GENESIS"
        for row in c.execute(
                "SELECT * FROM audit_events ORDER BY seq"):
            h = _sha(f"{prev}|{row['actor']}|{row['action']}|{row['entity']}|"
                     f"{row['entity_id']}|{row['created_at']}|{row['details_json']}")
            if h != row["event_hash"]:
                return False
            prev = row["event_hash"]
        return True

    # -------------------------------------------------- идемпотентность
    def _idem(self, c, agent_id: str, endpoint: str, key: str) -> dict | None:
        row = c.execute(
            "SELECT request_sha256, response_json FROM idempotency "
            "WHERE agent_id=? AND endpoint=? AND key=?",
            (agent_id, endpoint, key)).fetchone()
        return dict(row) if row else None

    def _idem_save(self, c, agent_id: str, endpoint: str, key: str,
                   payload: Any, response: dict) -> None:
        now_iso, _ = self._now()
        c.execute(
            "INSERT INTO idempotency (agent_id,endpoint,key,request_sha256,response_json,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (agent_id, endpoint, key, _sha(_canon(payload)), _canon(response), now_iso))

    # ------------------------------------------------------- публикация задач
    def register_agent(self, agent_id: str, scopes: list[str] | None = None,
                       boot_id: str = "") -> None:
        now_iso, _ = self._now()
        with self.connect() as c:
            self._audit(c, agent_id, "agent.register", "agent", agent_id, {})
        self.connect().execute(
            "INSERT OR IGNORE INTO agents (agent_id,scopes_json,boot_id,created_at) VALUES (?,?,?,?)",
            (agent_id, _canon(scopes or []), boot_id, now_iso))

    TASK_ID_RE = re.compile(r"^(EXP|MATH|KG)-\d{4}-\d{4}$|^[PS]\d+")

    def publish_task(self, payload: dict) -> dict:
        for field in ("id", "department", "title", "lease", "spec"):
            if field not in payload:
                raise BadRequest(f"task missing field: {field}")
        # Аудит 28.11.2026: write_scope не валидировался (4106 v4 указывала
        # на пути 4103). Обязателен непустой список относительных путей без ..
        ws = payload.get("write_scope") or []
        ws_ok = (isinstance(ws, list) and len(ws) > 0
                 and all(isinstance(x, str) and x and not x.startswith("/")
                         and ".." not in x.split("/") for x in ws))
        if not ws_ok:
            raise BadRequest(
                "write_scope: обязателен непустой список относительных путей без ..")
        if not self.TASK_ID_RE.match(payload["id"]):
            raise BadRequest(f"task id не по контракту: {payload['id']}")
        tid, dept = payload["id"], payload["department"]
        version = int(payload.get("version", 1))
        payload = dict(payload, schema="task/v1", version=version)
        payload.setdefault("created_at", _utc(self.wall()))
        payload.setdefault("published_at", payload["created_at"])
        payload.setdefault("created_by", "main")
        payload.setdefault("published_by", "main")
        sha = _sha(_canon(payload))
        now_iso, _ = self._now()
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            exists = c.execute("SELECT 1 FROM tasks WHERE id=?", (tid,)).fetchone()
            if exists and payload.get("supersedes_version") is None:
                raise Conflict(f"задача {tid} уже опубликована; укажи supersedes_version")
            if not exists:
                c.execute(
                    "INSERT INTO tasks (id,department,status,priority,current_version,"
                    "created_at) VALUES (?,?,?,?,?,?)",
                    (tid, dept, "ready", int(payload.get("priority", 0)), version, now_iso))
            else:
                row = c.execute("SELECT current_version,priority FROM tasks WHERE id=?",
                                (tid,)).fetchone()
                if version != row["current_version"] + 1:
                    raise Conflict(
                        f"ожидается версия {row['current_version'] + 1}, пришла {version}")
                c.execute("UPDATE tasks SET current_version=? WHERE id=?", (version, tid))
            c.execute(
                "INSERT INTO task_versions (task_id,version,task_version_sha256,payload_json,"
                "supersedes_version,change_reason,published_by,published_at,lease_json)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (tid, version, sha, _canon(payload),
                 payload.get("supersedes_version"), payload.get("change_reason"),
                 payload["published_by"], payload["published_at"], _canon(payload["lease"])))
            for dep in payload.get("dependencies", []):
                c.execute(
                    "INSERT OR REPLACE INTO dependencies (task_id,required_task_id,"
                    "required_task_version,required_state,required_artifact_sha256)"
                    " VALUES (?,?,?,?,?)",
                    (tid, dep["task_id"], dep["required_task_version"],
                     dep["required_state"], dep["required_artifact_sha256"]))
            self._audit(c, payload["published_by"], "task.publish", "task", tid,
                        {"version": version, "sha256": sha})
            c.execute("COMMIT")
        except Exception:
            self._safe_rollback(c)
            raise
        return {"task_id": tid, "version": version, "task_version_sha256": sha}

    # --------------------------------------------- блокирующие сообщения
    def _blocking_messages(self, c, agent_id: str, department: str | None,
                           now_mono: float) -> list[dict]:
        """Не acked, не expired, не superseded сообщения с blocks_claim=1."""
        rows = c.execute(
            "SELECT m.id, m.recipient, m.ack_deadline FROM messages m "
            "WHERE m.blocks_claim=1 AND m.requires_ack=1 AND m.superseded_by IS NULL "
            "AND (m.expires_at_mono IS NULL OR m.expires_at_mono > ?) "
            "AND m.recipient IN (?, ?, ?) "
            "AND NOT EXISTS (SELECT 1 FROM message_receipts r WHERE r.message_id=m.id "
            "AND r.agent_id=? AND r.ack_at IS NOT NULL)",
            (now_mono, agent_id, f"department:{department}", "all", agent_id)).fetchall()
        return [dict(r) for r in rows]

    def _blocking_submit_messages(self, c, agent_id: str, department: str | None,
                                  now_mono: float) -> list[dict]:
        """Не acked, не expired, не superseded сообщения с blocks_submit=1 или halt=1.
        Аудит 28.11.2026: submit не проверял blocks_submit/halt (в claim-
        контуре был только blocks_claim); блокирующее сообщение -- отказ submit."""
        rows = c.execute(
            "SELECT m.id, m.recipient, m.ack_deadline FROM messages m "
            "WHERE (m.blocks_submit=1 OR m.halt=1) AND m.requires_ack=1 "
            "AND m.superseded_by IS NULL "
            "AND (m.expires_at_mono IS NULL OR m.expires_at_mono > ?) "
            "AND m.recipient IN (?, ?, ?) "
            "AND NOT EXISTS (SELECT 1 FROM message_receipts r WHERE r.message_id=m.id "
            "AND r.agent_id=? AND r.ack_at IS NOT NULL)",
            (now_mono, agent_id, f"department:{department}", "all", agent_id)).fetchall()
        return [dict(r) for r in rows]

    def _message_counters(self, c, agent_id: str, department: str | None) -> dict:
        now_mono = self.mono()
        unread = c.execute(
            "SELECT COUNT(*) FROM messages m WHERE m.requires_read=1 "
            "AND m.recipient IN (?,?,?) AND (m.expires_at_mono IS NULL OR m.expires_at_mono>?) "
            "AND NOT EXISTS (SELECT 1 FROM message_receipts r WHERE r.message_id=m.id "
            "AND r.agent_id=? AND r.read_at IS NOT NULL)",
            (agent_id, f"department:{department}", "all", now_mono, agent_id)).fetchone()[0]
        acks = c.execute(
            "SELECT COUNT(*) FROM messages m WHERE m.requires_ack=1 "
            "AND m.recipient IN (?,?,?) AND (m.expires_at_mono IS NULL OR m.expires_at_mono>?) "
            "AND NOT EXISTS (SELECT 1 FROM message_receipts r WHERE r.message_id=m.id "
            "AND r.agent_id=? AND r.ack_at IS NOT NULL)",
            (agent_id, f"department:{department}", "all", now_mono, agent_id)).fetchone()[0]
        return {"unread": unread, "awaiting_ack": acks}

    def send_message(self, payload: dict) -> dict:
        for field in ("id", "sender", "recipient", "body"):
            if field not in payload:
                raise BadRequest(f"message missing field: {field}")
        now_iso, now_mono = self._now()
        msg = dict(payload, schema="message/v1")
        msg.setdefault("kind", "info")
        msg.setdefault("severity", "normal")
        msg.setdefault("scope", "agent")
        msg.setdefault("requires_read", True)
        for b in ("requires_ack", "blocks_claim", "blocks_submit", "halt"):
            msg.setdefault(b, False)
        expires_iso = msg.get("expires_at")
        expires_mono = None
        if expires_iso is not None:
            try:
                if not isinstance(expires_iso, str):
                    raise ValueError("expires_at must be a string")
                expires_dt = datetime.fromisoformat(expires_iso.replace("Z", "+00:00"))
                if expires_dt.tzinfo is None or expires_dt.utcoffset() is None:
                    raise ValueError("expires_at must include a timezone")
                expires_mono = now_mono + (expires_dt.timestamp() - self.wall())
            except (TypeError, ValueError, OverflowError) as exc:
                raise BadRequest(
                    "message.expires_at должен быть RFC3339 с часовым поясом") from exc
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            c.execute(
                "INSERT INTO messages (id,sender,recipient,kind,severity,scope,thread_id,"
                "requires_read,requires_ack,blocks_claim,blocks_submit,halt,body,ref,"
                "expires_at,expires_at_mono,superseded_by,ack_deadline,created_at,created_at_iso)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (msg["id"], msg["sender"], msg["recipient"], msg["kind"], msg["severity"],
                 msg["scope"], msg.get("thread_id"),
                 int(bool(msg["requires_read"])), int(bool(msg["requires_ack"])),
                 int(bool(msg["blocks_claim"])), int(bool(msg["blocks_submit"])),
                 int(bool(msg["halt"])), msg["body"], msg.get("ref"),
                 expires_iso, expires_mono, None, msg.get("ack_deadline"), self.wall(), now_iso))
            self._audit(c, msg["sender"], "message.send", "message", msg["id"],
                        {"to": msg["recipient"], "blocks_claim": int(bool(msg["blocks_claim"]))})
            c.execute("COMMIT")
        except Exception:
            self._safe_rollback(c)
            raise
        return {"message_id": msg["id"]}

    def mark_read(self, message_id: str, agent_id: str) -> dict:
        now_iso, _ = self._now()
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute("SELECT id FROM messages WHERE id=?", (message_id,)).fetchone()
            if not row:
                raise NotFound(f"нет сообщения {message_id}")
            c.execute(
                "INSERT INTO message_receipts (message_id,agent_id,read_at) VALUES (?,?,?) "
                "ON CONFLICT(message_id,agent_id) DO UPDATE SET read_at=excluded.read_at",
                (message_id, agent_id, now_iso))
            self._audit(c, agent_id, "message.read", "message", message_id, {})
            c.execute("COMMIT")
        except Exception:
            self._safe_rollback(c)
            raise
        return {"message_id": message_id, "read_at": now_iso}

    def ack(self, message_id: str, agent_id: str) -> dict:
        now_iso, _ = self._now()
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute("SELECT id FROM messages WHERE id=?", (message_id,)).fetchone()
            if not row:
                raise NotFound(f"нет сообщения {message_id}")
            c.execute(
                "INSERT INTO message_receipts (message_id,agent_id,read_at,ack_at) "
                "VALUES (?,?,?,?) ON CONFLICT(message_id,agent_id) DO UPDATE SET "
                "ack_at=excluded.ack_at, read_at=COALESCE(message_receipts.read_at, excluded.read_at)",
                (message_id, agent_id, now_iso, now_iso))
            self._audit(c, agent_id, "message.ack", "message", message_id, {})
            c.execute("COMMIT")
        except Exception:
            self._safe_rollback(c)
            raise
        return {"message_id": message_id, "ack_at": now_iso}

    def supersede(self, old_id: str, new_id: str) -> dict:
        c = self.connect()
        c.execute("BEGIN IMMEDIATE")
        try:
            c.execute("UPDATE messages SET superseded_by=? WHERE id=? AND superseded_by IS NULL",
                      (new_id, old_id))
            if c.execute("SELECT changes()").fetchone()[0] != 1:
                raise NotFound(f"{old_id} не найдена или уже заменена")
            self._audit(c, "main", "message.supersede", "message", old_id, {"new": new_id})
            c.execute("COMMIT")
        except Exception:
            self._safe_rollback(c)
            raise
        return {"superseded": old_id, "by": new_id}

    # ------------------------------------------------------------- claim
    def _dependency_satisfied(self, c, dep: sqlite3.Row, now_mono: float) -> bool:
        row = c.execute(
            "SELECT status FROM tasks WHERE id=?", (dep["required_task_id"],)).fetchone()
        if not row or row["status"] != dep["required_state"]:
            return False
        art = c.execute(
            "SELECT 1 FROM artifacts WHERE sha256=? AND task_id=?",
            (dep["required_artifact_sha256"], dep["required_task_id"])).fetchone()
        return bool(art)

    def claim(self, agent_id: str, instance_id: str, department: str,
              idem_key: str, request: dict | None = None,
              agent_limit: int = 5) -> dict:
        request = request or {"department": department, "wait": 0}
        c = self.connect()
        now_iso, now_mono = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            # Lookup под той же write-lock, что и claim: параллельный повтор
            # с тем же ключом возвращает сохранённый результат, а не второй lease.
            saved = self._idem(c, agent_id, "claim", idem_key)
            if saved:
                if saved["request_sha256"] != _sha(_canon(request)):
                    raise Conflict("Idempotency-Key уже использован с другим payload")
                response = json.loads(saved["response_json"])
                c.execute("COMMIT")
                return response
            # блокирующие сообщения: claim запрещён, heartbeat — нет (§13)
            blocking = self._blocking_messages(c, agent_id, department, now_mono)
            if blocking:
                raise Blocked("есть обязательные не acked сообщения: "
                              + ", ".join(m["id"] for m in blocking))
            active_cnt = c.execute(
                "SELECT COUNT(*) FROM leases WHERE agent_id=? AND state='active'",
                (agent_id,)).fetchone()[0]
            if active_cnt >= agent_limit:
                raise Blocked(f"лимит одновременно взятых задач: {agent_limit}")
            # 2. expire старых lease выбранных кандидатов внутри транзакции
            c.execute(
                "UPDATE leases SET state='expired', expired_at=?, expired_at_mono=? "
                "WHERE state='active' AND expires_at_mono<?",
                (now_iso, now_mono, now_mono))
            c.execute(
                "UPDATE tasks SET status='ready' WHERE status='claimed' "
                "AND lease_expires_at_mono IS NOT NULL AND lease_expires_at_mono<?",
                (now_mono,))
            c.execute(
                "UPDATE attempts SET status='expired', ended_at=?, failure_reason='lease expired' "
                "WHERE status='claimed' AND lease_id IN "
                "(SELECT lease_id FROM leases WHERE state='expired')", (now_iso,))
            # 3. кандидат: ready с выполненными зависимостями
            row = c.execute(
                "SELECT t.id, t.current_version FROM tasks t WHERE t.department=? AND t.status='ready' "
                "AND NOT EXISTS (SELECT 1 FROM dependencies d WHERE d.task_id=t.id AND NOT EXISTS ("
                "  SELECT 1 FROM tasks rt WHERE rt.id=d.required_task_id "
                "  AND rt.status=d.required_state)) "
                "AND NOT EXISTS (SELECT 1 FROM dependencies d WHERE d.task_id=t.id AND NOT EXISTS("
                "  SELECT 1 FROM submission_artifacts sa "
                "  JOIN submissions s ON s.id=sa.submission_id "
                "  WHERE sa.sha256=d.required_artifact_sha256 "
                "  AND s.task_id=d.required_task_id "
                "  AND s.task_version=d.required_task_version AND s.status='received')) "
                "ORDER BY t.priority DESC, t.created_at ASC LIMIT 1",
                (department,)).fetchone()
            if not row:
                response = {"claimed": None, "reason": "нет готовых задач"}
                # Пустая очередь тоже является результатом запроса: тот же ключ
                # не должен захватывать задачу, опубликованную после первого ответа.
                self._idem_save(c, agent_id, "claim", idem_key, request, response)
                c.execute("COMMIT")
                return response
            tid, version = row["id"], row["current_version"]
            tv = c.execute(
                "SELECT task_version_sha256,lease_json,payload_json FROM task_versions "
                "WHERE task_id=? AND version=?", (tid, version)).fetchone()
            lease_spec = json.loads(tv["lease_json"])
            ttl = int(lease_spec.get("ttl_seconds", 5400))
            max_lease = int(lease_spec.get("max_lease_seconds", ttl * 2))
            # Аудит 28.11.2026: max_attempts нигде не читался (4105 получила a2
            # при max_attempts=1). Потраченные попытки -- все завершённые
            # attempts задачи; исчерпаны -- задача в manual_review, не выдаётся.
            max_attempts = int(lease_spec.get("max_attempts", 1))
            spent = c.execute(
                "SELECT COUNT(*) FROM attempts WHERE task_id=? AND status!='claimed'",
                (tid,)).fetchone()[0]
            if spent >= max_attempts:
                c.execute(
                    "UPDATE tasks SET status='manual_review' WHERE id=? AND status='ready'",
                    (tid,))
                self._audit(c, agent_id, "task.manual_review", "task", tid,
                            {"reason": "max_attempts исчерпаны",
                             "max_attempts": max_attempts, "spent": spent})
                response = {"claimed": None,
                            "reason": (f"задача {tid}: исчерпаны max_attempts "
                                       f"({spent}/{max_attempts}), manual_review")}
                self._idem_save(c, agent_id, "claim", idem_key, request, response)
                c.execute("COMMIT")
                return response
            # 4. условный UPDATE — изменена ровно одна строка
            epoch_row = c.execute("SELECT lease_epoch FROM tasks WHERE id=?", (tid,)).fetchone()
            new_epoch = epoch_row["lease_epoch"] + 1
            cur = c.execute(
                "UPDATE tasks SET status='claimed', claimed_by=?, lease_epoch=?, "
                "lease_expires_at_mono=?, max_expires_at_mono=? "
                "WHERE id=? AND status='ready'",
                (agent_id, new_epoch, now_mono + ttl, now_mono + ttl + max_lease, tid))
            if cur.rowcount != 1:
                raise Conflict("задача ушла из ready во время claim (повторить)")
            attempt_no = c.execute(
                "SELECT COALESCE(MAX(attempt_no),0)+1 FROM attempts WHERE task_id=?",
                (tid,)).fetchone()[0]
            lease_id = f"LEASE-{uuid.uuid4().hex[:12]}"
            attempt_id = f"{tid}-a{attempt_no}"
            c.execute(
                "INSERT INTO leases (lease_id,task_id,task_version,attempt_id,lease_epoch,"
                "agent_id,instance_id,issued_at,issued_at_mono,expires_at,expires_at_mono,"
                "max_expires_at,max_expires_at_mono,state) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'active')",
                (lease_id, tid, version, attempt_id, new_epoch, agent_id, instance_id,
                 now_iso, now_mono, now_iso, now_mono + ttl,
                 _utc(self.wall() + ttl + max_lease), now_mono + ttl + max_lease))
            c.execute(
                "INSERT INTO attempts (attempt_id,task_id,task_version,attempt_no,lease_id,"
                "lease_epoch,agent_id,started_at,status) VALUES (?,?,?,?,?,?,?,?, 'claimed')",
                (attempt_id, tid, version, attempt_no, lease_id, new_epoch, agent_id, now_iso))
            self._audit(c, agent_id, "lease.claim", "lease", lease_id,
                        {"task": tid, "epoch": new_epoch, "attempt": attempt_id})
            response = {
                "claimed": {
                    "task_id": tid, "version": version,
                    "task_version_sha256": tv["task_version_sha256"],
                    "lease_id": lease_id, "lease_epoch": new_epoch,
                    "attempt_id": attempt_id,
                    "expires_at": _utc(self.wall() + ttl),
                    # Аудит 28.11.2026: write_scope обязан приезжать в
                    # claim-response -- runner обязан знать границы записи.
                    "write_scope": json.loads(tv["payload_json"]).get("write_scope", []),
                },
                "messages": self._message_counters(c, agent_id, department),
            }
            self._idem_save(c, agent_id, "claim", idem_key, request, response)
            c.execute("COMMIT")
            return response
        except Exception:
            self._safe_rollback(c)
            raise

    # ------------------------------------------------- heartbeat / release
    def _check_lease(self, c, lease_id: str, lease_epoch: int, agent_id: str,
                     instance_id: str | None) -> sqlite3.Row:
        row = c.execute(
            "SELECT l.*, t.status AS task_status FROM leases l JOIN tasks t ON t.id=l.task_id "
            "WHERE l.lease_id=?", (lease_id,)).fetchone()
        if not row:
            raise NotFound(f"нет lease {lease_id}")
        if row["agent_id"] != agent_id or (instance_id and row["instance_id"]
                                           and row["instance_id"] != instance_id):
            raise Gone("lease принадлежит другому исполнителю")
        if row["lease_epoch"] != lease_epoch:
            raise Gone("fencing: устаревший lease_epoch")
        return row

    def heartbeat(self, lease_id: str, lease_epoch: int, agent_id: str,
                  department: str | None = None, instance_id: str | None = None,
                  boot_id: str | None = None) -> dict:
        c = self.connect()
        now_iso, now_mono = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = self._check_lease(c, lease_id, lease_epoch, agent_id, instance_id)
            # heartbeat живого lease не блокируется сообщениями (§13.2)
            counters = self._message_counters(c, agent_id, department)
            if row["state"] != "active":
                raise Gone(f"lease {row['state']}; heartbeat не возрождает истёкший lease")
            if row["expires_at_mono"] < now_mono:
                c.execute("UPDATE leases SET state='expired', expired_at=?, expired_at_mono=? "
                          "WHERE lease_id=?", (now_iso, now_mono, lease_id))
                self._audit(c, agent_id, "lease.expire", "lease", lease_id, {"by": "heartbeat"})
                c.execute("COMMIT")
                raise Gone("lease истёк к моменту heartbeat")
            lease_spec_row = c.execute(
                "SELECT lease_json FROM task_versions WHERE task_id=? AND version=?",
                (row["task_id"], row["task_version"])).fetchone()
            if lease_spec_row is None:
                raise BadRequest("не найдена lease-конфигурация версии задачи")
            try:
                ttl_seconds = int(json.loads(lease_spec_row["lease_json"]).get(
                    "ttl_seconds", 5400))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise BadRequest("lease.ttl_seconds должен быть положительным целым") from exc
            if ttl_seconds <= 0:
                raise BadRequest("lease.ttl_seconds должен быть положительным целым")
            new_expire = min(now_mono + ttl_seconds, row["max_expires_at_mono"])
            if new_expire <= now_mono:
                raise Gone("max_lease_seconds исчерпан: вечный zombie-heartbeat запрещён")
            c.execute("UPDATE leases SET expires_at_mono=?, expires_at=? WHERE lease_id=?",
                      (new_expire, _utc(self.wall() + (new_expire - now_mono)), lease_id))
            c.execute("UPDATE tasks SET lease_expires_at_mono=? WHERE id=?",
                      (new_expire, row["task_id"]))
            if boot_id:
                c.execute("UPDATE leases SET boot_id=? WHERE lease_id=?", (boot_id, lease_id))
            self._audit(c, agent_id, "lease.heartbeat", "lease", lease_id, {})
            c.execute("COMMIT")
            return {"ok": True, "expires_at": _utc(self.wall() + (new_expire - now_mono)),
                    "messages": counters}
        except Exception:
            self._safe_rollback(c)
            raise

    def release(self, lease_id: str, lease_epoch: int, agent_id: str,
                reason: str = "") -> dict:
        c = self.connect()
        now_iso, now_mono = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = self._check_lease(c, lease_id, lease_epoch, agent_id, None)
            if row["state"] != "active":
                raise Gone(f"lease уже {row['state']}")
            c.execute("UPDATE leases SET state='released', released_at=? WHERE lease_id=?",
                      (now_iso, lease_id))
            c.execute("UPDATE tasks SET status='ready', claimed_by=NULL, "
                      "lease_expires_at_mono=NULL WHERE id=? AND status IN ('claimed','waiting_main')",
                      (row["task_id"],))
            c.execute("UPDATE attempts SET status='void', ended_at=?, failure_reason=? "
                      "WHERE attempt_id=? AND status='claimed'",
                      (now_iso, reason or "released", row["attempt_id"]))
            self._audit(c, agent_id, "lease.release", "lease", lease_id, {"reason": reason})
            c.execute("COMMIT")
            return {"released": lease_id}
        except Exception:
            self._safe_rollback(c)
            raise

    # ------------------------------------------------------------ submit
    def create_upload(self, agent_id: str) -> str:
        now_iso, _ = self._now()
        upload_id = f"UPL-{uuid.uuid4().hex[:12]}"
        self.connect().execute(
            "INSERT INTO uploads (upload_id,agent_id,state,created_at) VALUES (?,?, 'open', ?)",
            (upload_id, agent_id, now_iso))
        return upload_id

    def put_blob(self, upload_id: str, agent_id: str, data: bytes,
                 media_type: str = "application/octet-stream") -> dict:
        row = self.connect().execute(
            "SELECT state, agent_id FROM uploads WHERE upload_id=?", (upload_id,)).fetchone()
        if not row:
            raise NotFound(f"нет upload {upload_id}")
        if row["agent_id"] != agent_id:
            raise Gone("upload принадлежит другому агенту")
        digest = self.store.put(data)
        now_iso, _ = self._now()
        self.connect().execute(
            "INSERT OR IGNORE INTO artifacts (sha256,bytes,media_type,blob_id,upload_id,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (digest, len(data), media_type, digest, upload_id, now_iso))
        return {"sha256": digest, "bytes": len(data)}

    def submit(self, payload: dict, idem_key: str, mark_artifacts_for_task: bool = True) -> dict:
        # Минимальная цепочка provenance обязательна на intake:
        # lease -> attempt -> immutable task version -> SHA-256.
        for field in ("id", "task_id", "task_version", "task_version_sha256",
                      "attempt_id", "lease_id", "lease_epoch", "agent_id",
                      "artifacts", "bundle_sha256"):
            if field not in payload:
                raise BadRequest(f"submission missing field: {field}")
        if (not isinstance(payload["task_version"], int)
                or isinstance(payload["task_version"], bool)
                or payload["task_version"] < 1):
            raise BadRequest("submission.task_version должен быть целым числом >= 1")
        if not isinstance(payload["task_version_sha256"], str):
            raise BadRequest("submission.task_version_sha256 должен быть SHA-256 строкой")
        request = payload
        c = self.connect()
        now_iso, now_mono = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            # Lookup под write-lock закрывает гонку двух одинаковых submit.
            saved = self._idem(c, payload["agent_id"], "submit", idem_key)
            if saved:
                if saved["request_sha256"] != _sha(_canon(request)):
                    raise Conflict("Idempotency-Key уже использован с другим payload")
                response = json.loads(saved["response_json"])
                c.execute("COMMIT")
                return response

            row = self._check_lease(c, payload["lease_id"], payload["lease_epoch"],
                                    payload["agent_id"], payload.get("instance_id"))
            task_id = payload["task_id"]
            dep_version = payload["task_version"]
            if task_id != row["task_id"]:
                raise BadRequest("submission.task_id не соответствует lease")
            if dep_version != row["task_version"]:
                raise BadRequest("submission.task_version не соответствует версии lease")
            if payload["attempt_id"] != row["attempt_id"]:
                raise BadRequest("submission.attempt_id не соответствует lease")
            version_row = c.execute(
                "SELECT task_version_sha256,payload_json FROM task_versions "
                "WHERE task_id=? AND version=?",
                (task_id, dep_version)).fetchone()
            if version_row is None:
                raise BadRequest("не найдена immutable task version для lease")
            expected_task_sha = version_row["task_version_sha256"]
            if payload["task_version_sha256"] != expected_task_sha:
                raise BadRequest("submission.task_version_sha256 не соответствует task version")
            cur = c.execute(
                "SELECT current_version, department FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
            if cur is None:
                raise NotFound(f"нет задачи {task_id}")
            # Department-scoped halt/blocks_submit messages apply to the
            # department of the leased task, not the literal None scope.
            blocking = self._blocking_submit_messages(
                c, payload["agent_id"], cur["department"], now_mono)
            if blocking:
                raise Blocked("submit заблокирован не-acked сообщениями: "
                              + ", ".join(m["id"] for m in blocking))

            # Не полагаемся на heartbeat/reaper/следующий claim: отправка после
            # monotonic deadline должна попасть в карантин даже если lease.state
            # ещё "active". Проверка и fencing происходят в этой же транзакции.
            expired_by_deadline = (
                row["state"] == "active" and row["expires_at_mono"] < now_mono
            )
            if expired_by_deadline:
                c.execute(
                    "UPDATE leases SET state='expired', expired_at=?, expired_at_mono=? "
                    "WHERE lease_id=? AND state='active'",
                    (now_iso, now_mono, payload["lease_id"]))
                c.execute(
                    "UPDATE attempts SET status='expired', ended_at=?, "
                    "failure_reason='lease expired before submit' "
                    "WHERE attempt_id=? AND status='claimed'",
                    (now_iso, row["attempt_id"]))
                self._audit(c, payload["agent_id"], "lease.expire", "lease",
                            payload["lease_id"], {"by": "submit", "deadline": row["expires_at_mono"]})
                # Та же переочередь, что и при следующем claim/reaper: задача
                # больше не должна оставаться claimed без активного lease.
                c.execute(
                    "UPDATE tasks SET status='ready', claimed_by=NULL, "
                    "lease_expires_at_mono=NULL, max_expires_at_mono=NULL "
                    "WHERE id=? AND status='claimed' AND lease_epoch=?",
                    (task_id, row["lease_epoch"]))
            # дедупликация bundle в рамках попытки — до веток late/stale:
            # одинаковый bundle не создаёт дубль, даже если lease уже закрыт (§14.4)
            dup = c.execute(
                "SELECT id FROM submissions WHERE attempt_id=? AND bundle_sha256=? AND status!='late'",
                (row["attempt_id"], payload["bundle_sha256"])).fetchone()
            if dup:
                response = {"status": "duplicate", "submission_id": dup["id"]}
                self._idem_save(c, payload["agent_id"], "submit", idem_key, request, response)
                c.execute("COMMIT")
                return response
            stale = cur["current_version"] != dep_version
            if row["state"] != "active" or expired_by_deadline or stale:
                reason = (
                    "lease срок истёк до submit" if expired_by_deadline
                    else "lease больше не активен" if row["state"] != "active"
                    else f"постановка обновлена до v{cur['current_version']}"
                )
                c.execute(
                    "INSERT INTO submissions (id,task_id,task_version,task_version_sha256,"
                    "attempt_id,lease_id,lease_epoch,agent_id,instance_id,base_commit,"
                    "bundle_sha256,artifacts_json,environment_json,toolchain_json,"
                    "scientific_outcome,parent_submission_id,complied_messages_json,"
                    "submitted_at,status,status_reason) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'late', ?)",
                    (payload["id"], task_id, dep_version, expected_task_sha,
                     row["attempt_id"], payload["lease_id"], payload["lease_epoch"],
                     payload["agent_id"], payload.get("instance_id"), payload.get("base_commit"),
                     payload["bundle_sha256"], _canon(payload["artifacts"]),
                     _canon(payload.get("environment", {})), _canon(payload.get("toolchain", {})),
                     payload.get("scientific_outcome"), payload.get("parent_submission_id"),
                     _canon(payload.get("complied_messages", [])), now_iso, reason))
                self._audit(c, payload["agent_id"], "submission.late", "submission",
                            payload["id"], {"reason": reason, "task_version_sha256": expected_task_sha})
                response = {"status": "late_submission", "reason": reason,
                            "submission_id": payload["id"]}
                self._idem_save(c, payload["agent_id"], "submit", idem_key, request, response)
                c.execute("COMMIT")
                return response
            # Аудит 28.11.2026: base_commit не сверялся со спецификацией,
            # bundle_sha256 не пересчитывался. Оба -- fail-closed.
            expected_base = json.loads(version_row["payload_json"]).get("base_commit")
            if expected_base and payload.get("base_commit") != expected_base:
                raise BadRequest(
                    "submission.base_commit не соответствует spec.base_commit: "
                    f"ожидался {expected_base}, получен {payload.get('base_commit')!r}")
            expected_bundle = _sha(_canon(
                {"task": task_id, "batch": task_id, "artifacts": payload["artifacts"]}))
            if payload["bundle_sha256"] != expected_bundle:
                raise BadRequest("submission.bundle_sha256 не совпадает с пересчитанным "
                                 "bundle-хэшем артефактов")
            # сверка blobs — только для живого lease (поздний уже в карантине)
            missing = []
            for art in payload["artifacts"]:
                hit = c.execute("SELECT 1 FROM artifacts WHERE sha256=?",
                                (art["sha256"],)).fetchone()
                if not hit:
                    missing.append(art["sha256"])
            if missing:
                raise BadRequest(f"blobs отсутствуют в store: {missing}")
            c.execute(
                "INSERT INTO submissions (id,task_id,task_version,task_version_sha256,"
                "attempt_id,lease_id,lease_epoch,agent_id,instance_id,base_commit,"
                "bundle_sha256,artifacts_json,environment_json,toolchain_json,"
                "scientific_outcome,parent_submission_id,complied_messages_json,"
                "submitted_at,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'received')",
                (payload["id"], task_id, dep_version, expected_task_sha, row["attempt_id"],
                 payload["lease_id"], payload["lease_epoch"], payload["agent_id"],
                 payload.get("instance_id"), payload.get("base_commit"),
                 payload["bundle_sha256"], _canon(payload["artifacts"]),
                 _canon(payload.get("environment", {})), _canon(payload.get("toolchain", {})),
                 payload.get("scientific_outcome"), payload.get("parent_submission_id"),
                 _canon(payload.get("complied_messages", [])), now_iso))
            if mark_artifacts_for_task:
                for artifact_index, art in enumerate(payload["artifacts"]):
                    c.execute(
                        "INSERT INTO submission_artifacts "
                        "(submission_id,artifact_index,sha256) VALUES (?,?,?)",
                        (payload["id"], artifact_index, art["sha256"]),
                    )
            c.execute("UPDATE tasks SET status='submitted' WHERE id=? AND status='claimed'",
                      (task_id,))
            c.execute("UPDATE attempts SET status='submitted' WHERE attempt_id=?",
                      (row["attempt_id"],))
            c.execute("UPDATE leases SET state='released', released_at=? WHERE lease_id=?",
                      (now_iso, payload["lease_id"]))
            self._audit(c, payload["agent_id"], "submission.receive", "submission",
                        payload["id"], {"task": task_id, "epoch": payload["lease_epoch"],
                                        "task_version_sha256": expected_task_sha})
            response = {"status": "received", "submission_id": payload["id"]}
            self._idem_save(c, payload["agent_id"], "submit", idem_key, request, response)
            c.execute("COMMIT")
            return response
        except Exception:
            self._safe_rollback(c)
            raise

    # ---------------------------------------------------------- waiting_main
    def waiting_main(self, lease_id: str, lease_epoch: int, agent_id: str,
                     timeout_seconds: int) -> dict:
        c = self.connect()
        now_iso, now_mono = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = self._check_lease(c, lease_id, lease_epoch, agent_id, None)
            if row["state"] != "active":
                raise Gone(f"lease {row['state']}")
            new_expire = min(row["expires_at_mono"] + timeout_seconds,
                             row["max_expires_at_mono"] + timeout_seconds)
            c.execute("UPDATE leases SET expires_at_mono=?, expires_at=? WHERE lease_id=?",
                      (new_expire, _utc(self.wall() + (new_expire - now_mono)), lease_id))
            c.execute("UPDATE tasks SET status='waiting_main', lease_expires_at_mono=? "
                      "WHERE id=?", (new_expire, row["task_id"]))
            self._audit(c, agent_id, "attempt.waiting_main", "lease", lease_id,
                        {"timeout": timeout_seconds})
            c.execute("COMMIT")
            return {"status": "waiting_main", "expires_at": _utc(self.wall() + (new_expire - now_mono))}
        except Exception:
            self._safe_rollback(c)
            raise

    # ------------------------------------------------------------------ reaper
    def reap(self) -> dict:
        c = self.connect()
        now_iso, now_mono = self._now()
        c.execute("BEGIN IMMEDIATE")
        try:
            expired = c.execute(
                "UPDATE leases SET state='expired', expired_at=?, expired_at_mono=? "
                "WHERE state='active' AND expires_at_mono<? RETURNING lease_id",
                (now_iso, now_mono, now_mono)).fetchall()
            c.execute("UPDATE tasks SET status='ready', claimed_by=NULL, "
                      "lease_expires_at_mono=NULL WHERE status IN ('claimed','waiting_main') "
                      "AND lease_expires_at_mono<?", (now_mono,))
            c.execute("UPDATE attempts SET status='expired', ended_at=?, "
                      "failure_reason='reaper' WHERE status='claimed' AND lease_id IN "
                      "(SELECT lease_id FROM leases WHERE state='expired')", (now_iso,))
            self._audit(c, "reaper", "lease.reap", "queue", "all", {"count": len(expired)})
            c.execute("COMMIT")
            return {"expired": len(expired)}
        except Exception:
            self._safe_rollback(c)
            raise

    def status(self) -> dict:
        c = self.connect()
        out = {"tasks": {}, "leases_active": 0, "audit_chain_ok": self.verify_audit_chain()}
        for row in c.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status"):
            out["tasks"][row["status"]] = row["n"]
        out["leases_active"] = c.execute(
            "SELECT COUNT(*) FROM leases WHERE state='active'").fetchone()[0]
        return out
