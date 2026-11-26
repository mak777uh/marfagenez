#!/usr/bin/env python3
"""lab/migration/coord_import.py — импорт coord-export/v1 в SQLite (Фаза 3.5).

Потребляет снимок мигратора (lab/migration/coord_migrate.py --out), НЕ читает
.coord/ напрямую; тела сообщений берёт из coord_root по raw_path только когда
их нет в экспорте. Идемпотентен: повторный запуск не создаёт дублей.

Правила (план v0.3 §22 Фаза 3, §23.5):
- legacy ID сохраняются как есть (P*/S* разрешены контрактом new);
- pending -> ready; active+transferable -> claimed с lease/attempt и
  lease_epoch-базой gen; active без transferable -> ready (lease expired,
  attempt void); completed -> integrated; graveyard -> deferred (main);
- max_gen -> tasks.lease_epoch: следующий claim выдаёт эпоху max_gen+1;
- legacy events переносятся в audit chain (порядок сохранён, hash chain
  покрывает их);
- сообщения без верифицируемого тела -> deferred, не теряются молча;
- standing S* -> standing_templates (recurring template; раунды создаёт
  main при активации);
- вся операция атомарна: одна транзакция BEGIN IMMEDIATE.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.service.v2_ops import ControlPlane2  # noqa: E402
from lab.service.control import _utc  # noqa: E402

DEFAULT_LEASE = {"ttl_seconds": 5400, "heartbeat_seconds": 300,
                 "max_attempts": 3, "max_lease_seconds": 10800}

STATE_MAP = {
    "pending": "ready",
    "active": "claimed",       # placeholder; уточняется transferable-флагом
    "completed": "integrated",
}


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def expected_status(task: dict) -> str:
    """Чистое отображение legacy-состояния в новое: для verify-сверки."""
    if task.get("state") == "graveyard":
        return "deferred"
    if task.get("state") == "active":
        claim = task.get("claim") or {}
        return "claimed" if claim.get("transferable") else "ready"
    return STATE_MAP.get(task.get("state"), "ready")


class CoordImporter:
    def __init__(self, cp: ControlPlane2, coord_root: Path | None = None):
        self.cp = cp
        self.coord_root = Path(coord_root) if coord_root else None

    # ------------------------------------------------------------ импорт
    def import_export(self, export: dict, actor: str = "coord-migrator") -> dict:
        if export.get("schema") != "coord-export/v1":
            raise ValueError(f"не coord-export/v1: {export.get('schema')}")
        now_iso = self._utc_like(export)
        c = self.cp.connect()
        c.execute("BEGIN IMMEDIATE")   # одна атомарная транзакция
        imported = {"tasks": 0, "claims": 0, "standing": 0, "agents": 0,
                    "events": 0, "messages": 0}
        skipped = 0
        deferred: list[dict] = []
        try:
            for t in export.get("tasks", []):
                if c.execute("SELECT 1 FROM tasks WHERE id=?",
                             (t["id"],)).fetchone():
                    skipped += 1
                    continue
                exp_status = expected_status(t)
                if exp_status == "deferred":
                    deferred.append({"id": t["id"], "type": "graveyard_task",
                                     "reason": "graveyard: решение за main"})
                    self._deferred_task(c, t, now_iso)
                    continue
                imported["tasks"] += 1
                imported["claims"] += self._task(c, t, exp_status, actor,
                                                now_iso, deferred)
            for s in export.get("standing_templates", []):
                if c.execute("SELECT 1 FROM standing_templates WHERE id=?",
                              (s["id"],)).fetchone():
                    skipped += 1
                    continue
                imported["standing"] += 1
                c.execute(
                    "INSERT INTO standing_templates (id,department,card_json,"
                    "history_json,latest_round,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (s["id"], s.get("department", "knowledge"),
                     _canon(s), _canon(s.get("history", [])),
                     s.get("latest_round"), now_iso, now_iso))
                self._audit(c, actor, "standing.import", "standing", s["id"], {})
            for a in export.get("agents", []):
                if c.execute("SELECT 1 FROM agents WHERE agent_id=?",
                             (a["agent_id"],)).fetchone():
                    skipped += 1
                    continue
                imported["agents"] += 1
                c.execute(
                    "INSERT OR IGNORE INTO agents (agent_id,scopes_json,status,"
                    "boot_id,created_at) VALUES (?,?, 'active',?,?)",
                    (a["agent_id"], _canon(["legacy"]), a.get("boot_id") or "",
                     now_iso))
                self._audit(c, actor, "agent.import", "agent", a["agent_id"],
                            {"role_md_sha256": a.get("role_md_sha256")})
            for idx, ev in enumerate(export.get("events", [])):
                if c.execute("SELECT 1 FROM audit_events WHERE action="
                             "'coord.legacy_event' AND entity_id=?",
                             (f"{idx:05d}",)).fetchone():
                    skipped += 1
                    continue
                imported["events"] += 1
                self._audit(c, actor, "coord.legacy_event", "coord_event",
                            f"{idx:05d}", {"event": ev, "ordinal": idx})
            for m in export.get("messages", []):
                if c.execute("SELECT 1 FROM messages WHERE id=?",
                             (m["id"],)).fetchone():
                    skipped += 1
                    continue
                body = self._message_body(m, deferred)
                if body is None:
                    continue
                imported["messages"] += 1
                created = float(self.cp.wall())
                c.execute(
                    "INSERT INTO messages (id,sender,recipient,kind,severity,"
                    "scope,thread_id,requires_read,requires_ack,blocks_claim,"
                    "blocks_submit,halt,body,ref,expires_at,expires_at_mono,"
                    "superseded_by,ack_deadline,created_at,created_at_iso) "
                    "VALUES (?,?,?,'info','normal','agent',NULL,0,0,0,0,0,?,?"
                    ",NULL,NULL,NULL,NULL,?,?)",
                    (m["id"], m.get("from", "coord"), m.get("to", ""),
                     body, m.get("raw_path"), created, now_iso))
                self._audit(c, actor, "message.import", "message", m["id"],
                            {"body_sha256": m.get("body_sha256"),
                             "legacy_read_at": m.get("read_at"),
                             "legacy_ack_at": m.get("ack_at")})
            counts = dict(c.execute(
                "SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
            c.execute("COMMIT")
        except Exception:
            self.cp._safe_rollback(c)
            raise
        return {"imported": imported, "skipped_existing": skipped,
                "deferred": deferred, "tasks_by_status": counts,
                "audit_chain_ok": self.cp.verify_audit_chain()}

    # --------------------------------------------------------- помощники
    def _utc_like(self, export: dict) -> str:
        ts = export.get("exported_at")
        return ts if isinstance(ts, str) and "T" in ts else "1970-01-01T00:00:00Z"

    def _audit(self, c, actor, action, entity, entity_id, details) -> None:
        self.cp._audit(c, actor, action, entity, entity_id, details)

    def _deferred_task(self, c, t: dict, now_iso: str) -> None:
        """graveyard не пропадает: решение за main, поэтому фиксируем полный
        контекст в audit chain (строки в tasks не создаём)."""
        self._audit(c, "coord-migrator", "task.deferred", "task", t["id"],
                    {"legacy_state": t.get("state"), "title": t.get("title")})

    def _task(self, c, t: dict, status: str, actor: str, now_iso: str,
              deferred: list) -> int:
        """Возвращает 1, если перенесён живой transferable claim, иначе 0."""
        tid = t["id"]
        max_gen = t.get("max_gen") or 0
        priority = t.get("priority")
        prio = 5 if priority is None else max(0, min(100, int(priority)))
        c.execute(
            "INSERT INTO tasks (id,department,status,priority,current_version,"
            "lease_epoch,created_at) VALUES (?,?,?,?,1,?,?)",
            (tid, t.get("department", "knowledge"), status, prio,
             int(max_gen), now_iso))
        payload = {"schema": "legacy-task/v1", "id": tid,
                   "department": t.get("department", "knowledge"),
                   "title": t.get("title", ""), "area": t.get("area", []),
                   "write_scope": t.get("write_scope", []),
                   "accept": t.get("accept", []),
                   "has_result": t.get("has_result", False),
                   "done": t.get("done_json"),
                   "completed_at": t.get("completed_at"),
                   "max_gen": t.get("max_gen"),
                   "clamp": "постановка legacy; конформанс task/v1 — за main"}
        sha = hashlib.sha256(_canon(payload).encode()).hexdigest()
        c.execute(
            "INSERT INTO task_versions (task_id,version,task_version_sha256,"
            "payload_json,supersedes_version,change_reason,published_by,"
            "published_at,lease_json) VALUES (?,1,?,?,'legacy-import',?,"
            "?,?,?)",
            (tid, sha, _canon(payload), actor, now_iso, now_iso,
             _canon(DEFAULT_LEASE)))
        self._audit(c, actor, "task.import", "task", tid,
                    {"legacy_state": t.get("state"), "status": status,
                     "max_gen": t.get("max_gen")})
        claim = t.get("claim") or {}
        if status == "claimed" and claim.get("transferable"):
            gen = int(claim.get("gen") or 0)
            ttl = max(int(claim.get("ttl_remaining_seconds") or 0), 60)
            now_mono = float(self.cp.mono())
            lease_id = f"LEASE-COORD-{tid}"
            attempt_id = f"{tid}-a1"
            max_iso = _utc(self.cp.wall() + ttl + DEFAULT_LEASE["max_lease_seconds"])
            c.execute(
                "INSERT INTO leases (lease_id,task_id,task_version,attempt_id,"
                "lease_epoch,agent_id,instance_id,boot_id,issued_at,"
                "issued_at_mono,expires_at,expires_at_mono,max_expires_at,"
                "max_expires_at_mono,state) VALUES (?,?,?,?,?,?,?,NULL,?,?,?,?,"
                "?,?,'active')",
                (lease_id, tid, 1, attempt_id, gen, claim.get("agent", ""),
                 claim.get("round_id"), now_iso, now_mono, now_iso,
                 now_mono + ttl, max_iso,
                 now_mono + DEFAULT_LEASE["max_lease_seconds"]))
            c.execute(
                "INSERT INTO attempts (attempt_id,task_id,task_version,attempt_no,"
                "lease_id,lease_epoch,agent_id,started_at,status) VALUES "
                "(?,?,1,1,?,?,?,?, 'claimed')",
                (attempt_id, tid, lease_id, gen, claim.get("agent", ""), now_iso))
            c.execute("UPDATE tasks SET claimed_by=?, lease_expires_at_mono=?,"
                      "max_expires_at_mono=? WHERE id=?",
                      (claim.get("agent", ""), now_mono + ttl,
                       now_mono + DEFAULT_LEASE["max_lease_seconds"], tid))
            return 1
        elif t.get("state") == "active" and not claim.get("transferable"):
            # невыполнимый claim: lease фактически истёк, попытка void
            self._audit(c, actor, "task.claim_vanished", "task", tid,
                        {"reason": "claim не transferable: задача возвращена в ready"})
        return 0

    def _message_body(self, m: dict, deferred: list) -> str | None:
        if m.get("body") is not None:
            body = m["body"]
            want = m.get("body_sha256")
            if want and hashlib.sha256(body.encode()).hexdigest() != want:
                deferred.append({"id": m["id"], "type": "message_hash_mismatch"})
                return None
            return body
        raw = m.get("raw_path")
        if raw and self.coord_root:
            p = self.coord_root / raw
            if p.is_file():
                data = p.read_bytes()
                if m.get("body_sha256") and hashlib.sha256(data).hexdigest() \
                        != m["body_sha256"]:
                    deferred.append({"id": m["id"],
                                     "type": "message_hash_mismatch"})
                    return None
                return data.decode("utf-8", "replace")
        deferred.append({"id": m["id"], "type": "message_body_unavailable",
                         "reason": "нет body и raw_path недоступен: "
                                   "решение за main"})
        return None

    # ------------------------------------------------------------ сверка
    def verify_against_export(self, export: dict) -> dict:
        """Фаза 3 шаг 6: количества, статусы, эпохи, сообщения, изоляция."""
        c = self.cp.connect()
        mismatches: list[str] = []
        tasks_expected = [t for t in export.get("tasks", [])
                          if expected_status(t) != "deferred"]
        ids_db = {r[0] for r in c.execute("SELECT id FROM tasks")}
        ids_exp = {t["id"] for t in tasks_expected}
        if ids_db != ids_exp:
            mismatches.append(f"tasks: только в экспорте={sorted(ids_exp - ids_db)}"
                              f" только в БД={sorted(ids_db - ids_exp)}")
        by_status: dict[str, int] = {}
        for t in tasks_expected:
            st = expected_status(t)
            by_status[st] = by_status.get(st, 0) + 1
        got_status = dict(c.execute(
            "SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
        for st, n in by_status.items():
            if got_status.get(st, 0) != n:
                mismatches.append(f"status {st}: ожидалось {n}, "
                                  f"в БД {got_status.get(st, 0)}")
        for t in tasks_expected:
            row = c.execute("SELECT lease_epoch FROM tasks WHERE id=?",
                            (t["id"],)).fetchone()
            if row and row[0] != int(t.get("max_gen") or 0):
                mismatches.append(
                    f"{t['id']}: lease_epoch {row[0]} != max_gen "
                    f"{t.get('max_gen') or 0}")
        msgs = export.get("messages", [])
        msg_ids_db = {r[0] for r in c.execute("SELECT id FROM messages")}
        exp_msg_ids = {m["id"] for m in msgs if m["id"] in msg_ids_db
                        or m.get("body") is not None}
        missing = {m["id"] for m in msgs if m["id"] not in msg_ids_db
                   and m.get("body") is not None}
        if missing:
            mismatches.append(f"messages: не импортированы {sorted(missing)}")
        standing_exp = {s["id"] for s in export.get("standing_templates", [])}
        standing_db = {r[0] for r in c.execute("SELECT id FROM standing_templates")}
        if standing_exp != standing_db:
            mismatches.append(f"standing: расхождение "
                              f"{sorted(standing_exp ^ standing_db)}")
        events = export.get("events", [])
        legacy = c.execute(
            "SELECT COUNT(*) FROM audit_events WHERE action='coord.legacy_event'"
        ).fetchone()[0]
        if legacy != len(events):
            mismatches.append(f"events: {legacy} в цепи против {len(events)}")
        chain_ok = self.cp.verify_audit_chain()
        if not chain_ok:
            mismatches.append("audit hash chain нарушена")
        return {"ok": not mismatches and chain_ok,
                "mismatches": mismatches,
                "tasks_expected": len(tasks_expected),
                "messages_expected": len(exp_msg_ids),
                "standing_expected": len(standing_exp),
                "events_expected": len(events)}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="импорт coord-export/v1 в SQLite")
    ap.add_argument("--export", required=True, help="JSON coord-export/v1")
    ap.add_argument("--db", required=True, help="путь к control.db")
    ap.add_argument("--coord", default=None,
                    help="корень .coord/snapshot для тел сообщений по raw_path")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()
    export = json.loads(Path(args.export).read_text(encoding="utf-8"))
    cp = ControlPlane2(Path(args.db))
    try:
        cp.init()
        imp = CoordImporter(cp, Path(args.coord) if args.coord else None)
        if args.verify_only:
            print(json.dumps(imp.verify_against_export(export),
                             ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(json.dumps(imp.import_export(export),
                             ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        cp.close()


if __name__ == "__main__":
    sys.exit(main())
