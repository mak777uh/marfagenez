"""lab/tests/test_migration_tools.py — shadow-сверка и импортёр (§23.5).

Импортёр тестируется на синтетическом coord-export/v1: legacy ID,
перенос transferable claim, эпохи max_gen, идемпотентность повторного
импорта, deferred-сущности без молчаливой потери. Shadow-сверка
запускается против реального снапшота .coord/, если задан
COORD_TEST_SNAPSHOT (иначе skip: полный срез живой очереди дорогой).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.migration.coord_import import (  # noqa: E402
    CoordImporter, expected_status)
from lab.service.v2_ops import ControlPlane2  # noqa: E402

EXPORT = {
    "schema": "coord-export/v1",
    "exported_at": "2026-11-26T07:10:00Z",
    "repo_head": "dbd148a3487e8d358b705aa984dc1079894e258d",
    "coord_snapshot_sha256": "0" * 64,
    "counts": {"tasks": 6, "messages": 2},
    "tasks": [
        {"id": "P101", "state": "pending", "department": "knowledge",
         "title": "литература", "area": ["docs/"], "write_scope": ["docs/"],
         "accept": ["python3 run.py"], "priority": 7, "max_gen": 2,
         "raw_paths": ["pending/P101/task.md"]},
        {"id": "P102", "state": "active", "department": "experiments",
         "title": "прогон", "area": ["results/"], "write_scope": ["results/"],
         "priority": 9, "max_gen": 5,
         "claim": {"round_id": "P102-20261126T070000-aaa", "agent": "probe",
                   "gen": 5, "taken_at": "2026-11-26T07:00:00Z",
                   "ttl_remaining_seconds": 300, "transferable": True}},
        {"id": "P103", "state": "active", "department": "formulas",
         "title": "формула", "area": ["laws/"], "write_scope": ["laws/"],
         "max_gen": None,
         "claim": {"agent": "dead-agent", "gen": 3,
                   "ttl_remaining_seconds": 0, "transferable": False}},
        {"id": "P104", "state": "completed", "department": "knowledge",
         "title": "готово", "area": [], "write_scope": [],
         "has_result": True, "completed_at": "2026-11-20T10:00:00Z",
         "max_gen": 22, "done_json": {"ok": True}},
        {"id": "P105", "state": "graveyard", "department": "formulas",
         "title": "мусор", "area": [], "write_scope": []},
        {"id": "S900", "state": "completed", "department": "knowledge",
         "title": "standing-раунд", "max_gen": 1},
    ],
    "standing_templates": [
        {"id": "S9", "department": "knowledge", "latest_round": "S900",
         "history": ["S900"]}],
    "agents": [{"agent_id": "probe", "role_md_sha256": "1" * 64,
                "boot_id": "boot-1"}],
    "events": [
        {"ts": "2026-11-26 07:00:00", "agent": "probe", "text": "claim P102"},
        {"ts": "2026-11-26 07:01:00", "agent": "probe", "text": "heartbeat"}],
    "messages": [
        {"id": "M-0001", "from": "main", "to": "probe",
         "body": "почитать единицы", "body_sha256": None, "raw_path": None,
         "read_at": "2026-11-25T00:00:00Z", "ack_at": None},
        {"id": "M-0002", "from": "main", "to": "probe", "body_sha256": "2" * 64,
         "raw_path": "mail/new/M-0002", "read_at": None, "ack_at": None}],
    "unresolved": [],
}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="lab-mig-"))
        cp = ControlPlane2(self.dir / "control.sqlite3",
                           artifacts=self.dir / "artifacts")
        cp.init()
        self.cp = cp

    def tearDown(self):
        self.cp.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def db(self):
        return self.cp.connect()


class TestImporter(Base):
    def test_expected_status_mapping(self):
        by_id = {t["id"]: expected_status(t) for t in EXPORT["tasks"]}
        self.assertEqual(by_id, {"P101": "ready", "P102": "claimed",
                                 "P103": "ready", "P104": "integrated",
                                 "P105": "deferred", "S900": "integrated"})

    def test_import_semantics_and_idempotence(self):
        imp = CoordImporter(self.cp, coord_root=None)
        out = imp.import_export(EXPORT)
        self.assertEqual(out["imported"]["tasks"], 5)   # всё, кроме graveyard
        self.assertEqual(out["imported"]["messages"], 1)  # M-0002 без тела -> deferred
        deferred = {(d["id"], d["type"]) for d in out["deferred"]}
        self.assertIn(("P105", "graveyard_task"), deferred)
        self.assertIn(("M-0002", "message_body_unavailable"), deferred)
        c = self.db()
        # статусы и эпохи (max_gen сохранён как база lease_epoch)
        row = c.execute("SELECT status,lease_epoch FROM tasks WHERE id='P102'"
                        ).fetchone()
        self.assertEqual(row["status"], "claimed")
        self.assertEqual(row["lease_epoch"], 5)
        self.assertEqual(c.execute(
            "SELECT status,lease_epoch FROM tasks WHERE id='P104'"
        ).fetchone()[0:2], ("integrated", 22))
        # transferable claim: живой lease + attempt claimed
        lease = c.execute("SELECT * FROM leases WHERE task_id='P102'").fetchone()
        self.assertEqual(lease["state"], "active")
        self.assertEqual(lease["lease_epoch"], 5)
        self.assertEqual(lease["agent_id"], "probe")
        self.assertEqual(c.execute(
            "SELECT status FROM attempts WHERE attempt_id='P102-a1'"
        ).fetchone()[0], "claimed")
        # non-transferable: lease нет, задача ready
        self.assertIsNone(c.execute(
            "SELECT 1 FROM leases WHERE task_id='P103'").fetchone())
        self.assertEqual(c.execute(
            "SELECT status FROM tasks WHERE id='P103'").fetchone()[0], "ready")
        # graveyard не в tasks, но зафиксирован
        self.assertIsNone(c.execute(
            "SELECT 1 FROM tasks WHERE id='P105'").fetchone())
        # standing template + агент + события в цепи
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM standing_templates").fetchone()[0], 1)
        self.assertEqual(c.execute(
            "SELECT agent_id FROM agents WHERE agent_id='probe'").fetchone()[0],
            "probe")
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM audit_events WHERE action='coord.legacy_event'"
        ).fetchone()[0], 2)
        self.assertTrue(self.cp.verify_audit_chain())
        # сверка Фазы 3 шаг 6
        ver = imp.verify_against_export(EXPORT)
        self.assertTrue(ver["ok"], ver["mismatches"])
        # идемпотентность: повторный импорт ничего не добавляет
        out2 = imp.import_export(EXPORT)
        self.assertGreater(out2["skipped_existing"], 0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 5)
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM audit_events WHERE action='coord.legacy_event'"
        ).fetchone()[0], 2, "события задублировались при повторном импорте")
        self.assertEqual(c.execute("SELECT COUNT(*) FROM messages"
                                  ).fetchone()[0], 1)
        self.assertTrue(imp.verify_against_export(EXPORT)["ok"])

    def test_message_body_from_raw_path(self):
        coord = self.dir / "coord"
        (coord / "mail" / "new").mkdir(parents=True)
        body = "тело письма"
        (coord / "mail" / "new" / "M-0002").write_text(body, encoding="utf-8")
        export = json.loads(json.dumps(EXPORT))
        export["messages"][1]["body"] = None
        export["messages"][1]["body_sha256"] = __import__("hashlib").sha256(
            body.encode()).hexdigest()
        imp = CoordImporter(self.cp, coord_root=coord)
        out = imp.import_export(export)
        self.assertEqual(out["imported"]["messages"], 2, out["deferred"])
        self.assertEqual(self.db().execute(
            "SELECT body FROM messages WHERE id='M-0002'").fetchone()[0], body)


class TestVerifyDetectsDrift(Base):
    def test_verify_catches_missing_task(self):
        imp = CoordImporter(self.cp)
        imp.import_export(EXPORT)
        c = self.db()
        c.execute("DELETE FROM task_versions WHERE task_id='P101'")
        c.execute("DELETE FROM tasks WHERE id='P101'")
        ver = imp.verify_against_export(EXPORT)
        self.assertFalse(ver["ok"])
        self.assertTrue(any("P101" in m for m in ver["mismatches"]))


@unittest.skipUnless(os.environ.get("COORD_TEST_SNAPSHOT")
                     and Path(os.environ["COORD_TEST_SNAPSHOT"]).is_dir(),
                     "COORD_TEST_SNAPSHOT не задан: срез живой очереди дорог")
class TestShadowCompareRealSnapshot(unittest.TestCase):
    def test_snapshot_verdict_ok(self):
        from lab.migration.shadow_compare import ShadowCompare
        rep = ShadowCompare(Path(os.environ["COORD_TEST_SNAPSHOT"]),
                            sample=15).run()
        self.assertEqual(rep["verdict"], "ok",
                         json.dumps(rep["spot_checks"], ensure_ascii=False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
