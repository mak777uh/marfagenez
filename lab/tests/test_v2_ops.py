"""lab/tests/test_v2_ops.py — вторая серия Фазы 2 (план v0.3 §22, §23).

Проверяется не только exit-код, но и согласованное состояние БД после
каждого сценария (§23): proposals/CAS, schema v2, cancellation через
fencing, детерминированные проекции, GC blobs, CLI через сервис.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.service.v2_ops import (  # noqa: E402
    BadRequest, Conflict, ControlPlane2, Gone, NotFound)

LEASE_SPEC = {"ttl_seconds": 120, "heartbeat_seconds": 30,
              "max_attempts": 3, "max_lease_seconds": 200}

def bundle_sha(task_id: str, artifacts) -> str:
    """Канонический bundle-хэш (конвенция аудита 28.11.2026)."""
    from lab.service.control import _canon, _sha
    return _sha(_canon({"task": task_id, "batch": task_id,
                         "artifacts": artifacts}))


def make_task(tid: str, dept: str = "knowledge", priority: int = 5, **kw):
    return {
        "id": tid, "department": dept, "title": f"задача {tid}",
        "write_scope": ["results/"], "spec": {"mode": "verify_value",
                                             "required_evidence": ["quote"]},
        "validators": [{"profile": "knowledge-map-v1", "version": "1.0.0"}],
        "dependencies": [], "lease": dict(LEASE_SPEC), "priority": priority,
        "base_commit": "6a9fa461", "network_profile": "none",
        "budget": {"cpu_seconds": 600, "ram_bytes": 1, "disk_bytes": 1,
                   "network_allowlist": []},
        "tags": [], **kw,
    }


def dir_hash(root: Path) -> str:
    """Стабильный хэш дерева файлов: путь + sha256 содержимого."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def wall(self):
        return self.t

    def mono(self):
        return self.t

    def advance(self, seconds: float):
        self.t += seconds


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="lab-v2-"))
        self.clock = Clock()
        cp = ControlPlane2(self.dir / "control.sqlite3",
                          artifacts=self.dir / "artifacts",
                          wall=self.clock.wall, mono=self.clock.mono)
        cp.init()
        self.cp = cp

    def tearDown(self):
        self.cp.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def db(self):
        return self.cp.connect()

    def assertInvariants(self):
        self.assertTrue(self.cp.verify_audit_chain(), "hash chain аудита нарушена")
        doubles = self.db().execute(
            "SELECT task_id, COUNT(*) n FROM leases WHERE state='active' "
            "GROUP BY task_id HAVING COUNT(*)>1").fetchall()
        self.assertFalse(doubles, f"двойные активные lease: {[dict(r) for r in doubles]}")


class TestSchemaMigration(Base):
    def test_user_version_and_idempotent_init(self):
        self.assertEqual(self.cp.user_version(), 3)
        tables = {r[0] for r in self.db().execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("proposals", tables)
        self.assertIn("standing_templates", tables)
        # Repeated init must not rewind schema version or replay migrations.
        before = self.db().execute(
            "SELECT COUNT(*) FROM audit_events WHERE action='schema.migrate'"
        ).fetchone()[0]
        self.assertEqual(before, 2)
        self.cp.init()
        self.assertEqual(self.cp.user_version(), 3)
        after = self.db().execute(
            "SELECT COUNT(*) FROM audit_events WHERE action='schema.migrate'"
        ).fetchone()[0]
        self.assertEqual(after, before, "повторный init повторно записал миграции")
        self.assertInvariants()


class TestProposalsCAS(Base):
    def test_create_idempotent_and_conflict(self):
        prop = {"id": "PROP-0001", "author": "planner",
                "payload": {"kind": "comment", "comment": "units!"},
                }
        out = self.cp.create_proposal(prop)
        self.assertEqual(out, {"proposal_id": "PROP-0001", "revision": 1,
                               "status": "submitted"})
        # тот же id + тот же payload = duplicate, не новый
        dup = self.cp.create_proposal(prop)
        self.assertTrue(dup["duplicate"])
        # тот же id + другой payload = 409
        with self.assertRaises(Conflict):
            self.cp.create_proposal(dict(prop, payload={"kind": "comment",
                                                        "comment": "иные"}))
        with self.assertRaises(BadRequest):
            self.cp.create_proposal({"id": "X-1", "author": "a",
                                     "payload": {"kind": "comment"}})
        self.assertInvariants()

    def test_cas_update_review_revisions(self):
        self.cp.create_proposal({"id": "PROP-0002", "author": "planner",
                                 "payload": {"kind": "new_task",
                                             "draft": {"id": "KG-2027-0001"}}})
        # CAS: ревизия 1 -> 2
        out = self.cp.update_proposal("PROP-0002", "planner", 1,
                                      {"kind": "new_task",
                                       "draft": {"id": "KG-2027-0001",
                                                 "title": "уже с заголовком"}})
        self.assertEqual(out["revision"], 2)
        # устаревшая ревизия -> 409
        with self.assertRaises(Conflict):
            self.cp.update_proposal("PROP-0002", "planner", 1,
                                     {"kind": "new_task", "draft": {}})
        # чужой автор -> 409
        with self.assertRaises(Conflict):
            self.cp.update_proposal("PROP-0002", "intruder", 2,
                                     {"kind": "new_task", "draft": {}})
        # review: changes_requested по ревизии 2
        out = self.cp.review_proposal("PROP-0002", "main", "changes_requested",
                                      2, review_note="добавь lease")
        self.assertEqual(out, {"proposal_id": "PROP-0002",
                               "status": "changes_requested",
                               "revision": 3})
        with self.assertRaises(Conflict):
            self.cp.review_proposal("PROP-0002", "main", "published", 2)
        # после changes_requested автор ещё может обновить (rev 3 -> 4)
        upd = self.cp.update_proposal("PROP-0002", "planner", 3,
                                      {"kind": "new_task",
                                       "draft": {"id": "KG-2027-0001",
                                                 "lease": LEASE_SPEC}})
        self.assertEqual(upd["revision"], 4)
        # терминальное решение main
        pub = self.cp.review_proposal("PROP-0002", "main", "published", 4)
        self.assertEqual(pub["status"], "published")
        # терминальный статус: дальнейшие мутации запрещены
        with self.assertRaises(Conflict):
            self.cp.update_proposal("PROP-0002", "planner", 5,
                                     {"kind": "new_task", "draft": {}})
        got = self.cp.get_proposal("PROP-0002")
        self.assertEqual(got["schema"], "proposal/v1")
        self.assertEqual(got["revision"], 5)
        self.assertEqual(got["status"], "published")
        # ревизии монотонны и никогда не убывают
        revs = [r[0] for r in self.db().execute(
            "SELECT revision FROM proposals WHERE id='PROP-0002'")]
        self.assertEqual(revs, [5])
        self.assertInvariants()


class TestCancellation(Base):
    def _claim(self, tid, agent="fast-01"):
        return self.cp.claim(agent, "i", "knowledge", idem_key=f"c-{tid}-{agent}")

    def test_cancel_ready_immediately(self):
        self.cp.publish_task(make_task("KG-2026-0020"))
        out = self.cp.cancel_task("KG-2026-0020", "main", reason="неактуальна")
        self.assertEqual(out["status"], "cancelled")
        # cancelled никогда не выдаётся
        r = self._claim("KG-2026-0020", "fast-02")
        self.assertIsNone(r["claimed"])
        self.assertInvariants()

    def test_cancel_claimed_graceful_and_fencing(self):
        self.cp.publish_task(make_task("KG-2026-0021"))
        lease = self._claim("KG-2026-0021")["claimed"]
        out = self.cp.cancel_task("KG-2026-0021", "main")
        self.assertEqual(out["status"], "cancellation_requested")
        # submit в контуре отмены запрещён до подтверждения
        sub = {"id": "SUB-2021", "task_id": "KG-2026-0021",
               "task_version": 1, "task_version_sha256": lease["task_version_sha256"],
               "attempt_id": lease["attempt_id"], "lease_id": lease["lease_id"],
               "lease_epoch": lease["lease_epoch"], "agent_id": "fast-01",
               "artifacts": [], "bundle_sha256": "1" * 64}
        with self.assertRaises(BadRequest):
            self.cp.submit(sub, idem_key="s-x")
        # чужой агент/epoch не может подтвердить (fencing)
        with self.assertRaises(Gone):
            self.cp.acknowledge_cancel(lease["lease_id"], lease["lease_epoch"],
                                       "intruder")
        with self.assertRaises(Gone):
            self.cp.acknowledge_cancel(lease["lease_id"], lease["lease_epoch"] + 99,
                                       "fast-01")
        # правильное подтверждение: lease released, attempt void, задача cancelled
        ack = self.cp.acknowledge_cancel(lease["lease_id"], lease["lease_epoch"],
                                         "fast-01")
        self.assertEqual(ack["status"], "cancelled")
        c = self.db()
        self.assertEqual(c.execute(
            "SELECT status FROM tasks WHERE id='KG-2026-0021'"
        ).fetchone()[0], "cancelled")
        self.assertEqual(c.execute(
            "SELECT state FROM leases WHERE lease_id=?",
            (lease["lease_id"],)).fetchone()[0], "released")
        self.assertEqual(c.execute(
            "SELECT status FROM attempts WHERE attempt_id=?",
            (lease["attempt_id"],)).fetchone()[0], "void")
        # zombie heartbeat/submit после подтверждения -> Gone/late
        with self.assertRaises(Gone):
            self.cp.heartbeat(lease["lease_id"], lease["lease_epoch"], "fast-01")
        late = self.cp.submit(sub, idem_key="s-x")
        self.assertEqual(late["status"], "late_submission")
        self.assertInvariants()

    def test_cancel_terminal_states_conflict(self):
        self.cp.publish_task(make_task("KG-2026-0022"))
        lease = self._claim("KG-2026-0022")["claimed"]
        up = self.cp.create_upload("fast-01")
        blob = self.cp.put_blob(up, "fast-01", b"data",
                                "application/x-ndjson")
        arts = [{"sha256": blob["sha256"], "bytes": blob["bytes"],
                 "media_type": "application/x-ndjson"}]
        sub = {"id": "SUB-2022", "task_id": "KG-2026-0022",
               "task_version": 1, "task_version_sha256": lease["task_version_sha256"],
               "attempt_id": lease["attempt_id"], "lease_id": lease["lease_id"],
               "lease_epoch": lease["lease_epoch"], "agent_id": "fast-01",
               "artifacts": arts,
               "bundle_sha256": bundle_sha("KG-2026-0022", arts),
               "base_commit": "6a9fa461"}
        self.cp.submit(sub, idem_key="s-22")
        with self.assertRaises(Conflict):
            self.cp.cancel_task("KG-2026-0022", "main")
        with self.assertRaises(NotFound):
            self.cp.cancel_task("KG-9999-9999", "main")
        self.assertInvariants()


class TestProjections(Base):
    def test_deterministic_and_rebuildable(self):
        self.cp.publish_task(make_task("KG-2026-0030"))
        self.cp.publish_task(make_task("KG-2026-0030", version=2,
                                       supersedes_version=1,
                                       change_reason="уточнение"))
        self.cp.publish_task(make_task("KG-2026-0031", priority=1))
        self.cp.claim("fast-01", "i", "knowledge", idem_key="c30")
        self.cp.send_message({"id": "MSG-0030", "sender": "main",
                              "recipient": "department:knowledge",
                              "requires_read": True, "body": "проверять единицы"})
        proj = self.dir / "proj"
        out1 = self.cp.write_projections(proj)
        self.assertEqual(out1["tasks"], 2)
        self.assertEqual(out1["task_versions"], 3)
        h1 = dir_hash(proj)
        # повторная выгрузка байт-в-байт идентична
        self.cp.write_projections(proj)
        self.assertEqual(dir_hash(proj), h1)
        # потеря проекции не страшна: восстановление из БД
        shutil.rmtree(proj)
        self.cp.write_projections(proj)
        self.assertEqual(dir_hash(proj), h1)
        # содержимое соответствует БД
        lines = (proj / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
        statuses = {json.loads(l)["id"]: json.loads(l)["status"]
                    for l in lines}
        self.assertEqual(statuses["KG-2026-0030"], "claimed")
        self.assertEqual(statuses["KG-2026-0031"], "ready")
        self.assertTrue((proj / "task_versions" / "KG-2026-0030" /
                        "v2.json").exists())
        head = (proj / "audit_head.txt").read_text(encoding="utf-8").strip()
        self.assertNotEqual(head, "GENESIS")
        self.assertInvariants()


class TestGCBlobs(Base):
    def test_sweep_orphans_with_grace(self):
        self.cp.publish_task(make_task("KG-2026-0040"))
        up = self.cp.create_upload("fast-01")
        live = self.cp.put_blob(up, "fast-01", b"referenced bytes")
        self.cp.claim("fast-01", "i", "knowledge", idem_key="c40")
        # живой blob свежий — не трогаем даже без grace
        out = self.cp.gc_blobs(grace_seconds=0)
        self.assertEqual(out["deleted_blobs"], 0)
        self.assertTrue(self.cp.store.path(live["sha256"]).exists())
        # сирота: файл в store без записи в artifacts, старый mtime
        store = self.cp.store
        store.ensure()
        orphan = orphan_digest = "ab" * 32
        p = store.blobs / "ab" / orphan
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"orphan")
        old = time.time() - 7200
        import os
        os.utime(p, (old, old))
        # свежий сирота должен пережить grace
        fresh = store.blobs / "cd" / ("cd" * 32)
        fresh.parent.mkdir(parents=True, exist_ok=True)
        fresh.write_bytes(b"fresh orphan")
        # мусорный .part старше grace
        part = store.tmp / "dead.part"
        part.write_bytes(b"tmp")
        os.utime(part, (old, old))
        out = self.cp.gc_blobs(grace_seconds=3600.0)
        self.assertEqual(out["deleted_blobs"], 1)
        self.assertEqual(out["deleted_tmp"], 1)
        self.assertFalse(p.exists())
        self.assertFalse(part.exists())
        self.assertTrue(fresh.exists(), "свежий сирота не должен удаляться до grace")
        self.assertTrue(self.cp.store.path(live["sha256"]).exists())
        self.assertInvariants()


class TestCLI(Base):
    def test_cli_through_service(self):
        from lab.cli.main import main
        db = str(self.dir / "control.sqlite3")
        task_file = self.dir / "task.json"
        task_file.write_text(json.dumps(make_task("KG-2026-0050"),
                                        ensure_ascii=False), encoding="utf-8")
        sub_file = self.dir / "sub.json"
        self.assertEqual(main(["--db", db, "init"]), 0)
        self.assertEqual(main(["--db", db, "publish", str(task_file)]), 0)
        rc = main(["--db", db, "claim", "--agent", "cli-01", "--department",
                   "knowledge", "--idem-key", "cli-c1"])
        self.assertEqual(rc, 0)
        auth = main(["--db", db, "cancel", "--task", "KG-9999-9999"])
        self.assertEqual(auth, 1, "отмена несуществующей задачи = ошибка контракта")
        c = self.db()
        self.assertEqual(c.execute(
            "SELECT status FROM tasks WHERE id='KG-2026-0050'"
        ).fetchone()[0], "claimed")
        # proposal через CLI
        prop_file = self.dir / "prop.json"
        prop_file.write_text(json.dumps(
            {"id": "PROP-0050", "author": "cli",
             "payload": {"kind": "comment", "comment": "x"}},
            ensure_ascii=False), encoding="utf-8")
        self.assertEqual(main(["--db", db, "proposal-create", str(prop_file)]), 0)
        rc = main(["--db", db, "proposal-review", "--id", "PROP-0050",
                   "--decision", "published", "--revision", "1"])
        self.assertEqual(rc, 0)
        # проекции через CLI
        rc = main(["--db", db, "projections", "--out", str(self.dir / "proj")])
        self.assertEqual(rc, 0)
        self.assertTrue((self.dir / "proj" / "tasks.jsonl").exists())
        # Reaper has a public CLI path; this task has not expired yet.
        rc = main(["--db", db, "reap"])
        self.assertEqual(rc, 0)
        self.assertInvariants()


if __name__ == "__main__":
    unittest.main(verbosity=2)
