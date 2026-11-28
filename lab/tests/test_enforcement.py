"""lab/tests/test_enforcement.py — enforcement claim/submit (аудит 28.11.2026).

Цикл 861ai: publish валидирует write_scope; claim читает max_attempts,
требует received-submission нужной версии зависимости и отдаёт write_scope;
submit блокируется по blocks_submit/halt и сверяет base_commit и bundle_sha256.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.service.control import (  # noqa: E402
    Blocked, BadRequest, ControlPlane)

LEASE_SPEC = {"ttl_seconds": 120, "heartbeat_seconds": 30,
              "max_attempts": 1, "max_lease_seconds": 200}


def bundle_sha(task_id: str, artifacts) -> str:
    from lab.service.control import _canon, _sha
    return _sha(_canon({"task": task_id, "batch": task_id, "artifacts": artifacts}))


def make_task(tid: str, dept: str = "knowledge", priority: int = 5, **kw):
    return {
        "id": tid, "department": dept, "title": f"задача {tid}",
        "write_scope": [f"results/{tid}/**"],
        "spec": {"mode": "verify_value", "required_evidence": ["quote"]},
        "validators": [{"profile": "knowledge-map-v1", "version": "1.0.0"}],
        "dependencies": [], "lease": dict(LEASE_SPEC), "priority": priority,
        "base_commit": "deadbeef01", "network_profile": "none",
        "budget": {"cpu_seconds": 600, "ram_bytes": 1, "disk_bytes": 16777216,
                   "network_allowlist": []},
        "tags": [], **kw,
    }


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
        self.dir = Path(tempfile.mkdtemp(prefix="lab-enf-"))
        self.clock = Clock()
        cp = ControlPlane(self.dir / "control.sqlite3",
                          artifacts=self.dir / "artifacts",
                          wall=self.clock.wall, mono=self.clock.mono)
        cp.init()
        self.cp = cp

    def tearDown(self):
        self.cp.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def db(self):
        return self.cp.connect()


class TestPublishWriteScope(Base):
    def test_publish_rejects_bad_write_scope(self):
        for bad in ([], None, [""], ["/abs/**"], ["../escape/**"], "results/"):
            with self.assertRaises(BadRequest):
                self.cp.publish_task(make_task("KG-2026-0300", write_scope=bad))
        out = self.cp.publish_task(make_task("KG-2026-0301"))
        self.assertEqual(out["version"], 1)


class TestClaimEnforcement(Base):
    def test_claim_response_carries_write_scope(self):
        self.cp.publish_task(make_task("KG-2026-0310"))
        r = self.cp.claim("enf-01", "i", "knowledge", idem_key="c1")
        self.assertEqual(r["claimed"]["write_scope"], ["results/KG-2026-0310/**"])

    def test_max_attempts_exhausted_marks_manual_review(self):
        self.cp.publish_task(make_task("KG-2026-0311"))  # max_attempts=1
        r1 = self.cp.claim("enf-01", "i", "knowledge", idem_key="c1")
        self.assertTrue(r1["claimed"])
        self.clock.advance(1000)  # lease истёк, attempt завершён
        r2 = self.cp.claim("enf-02", "i2", "knowledge", idem_key="c2")
        self.assertIsNone(r2["claimed"])
        self.assertIn("manual_review", r2["reason"])
        st = self.db().execute(
            "SELECT status FROM tasks WHERE id='KG-2026-0311'").fetchone()[0]
        self.assertEqual(st, "manual_review")

    def test_dependency_requires_received_submission_of_version(self):
        self.cp.publish_task(make_task("KG-2026-0320"))
        self.cp.publish_task(make_task("KG-2026-0321", dependencies=[
            {"task_id": "KG-2026-0320", "required_task_version": 1,
             "required_state": "integrated", "required_artifact_sha256": "e" * 64}]))
        c = self.db()
        c.execute("UPDATE tasks SET status='integrated' WHERE id='KG-2026-0320'")
        c.execute(
            "INSERT INTO artifacts (sha256,bytes,media_type,blob_id,task_id,created_at)"
            " VALUES (?,?,?,?,?,?)",
            ("e" * 64, 7, "application/x-ndjson", "e" * 64, "KG-2026-0320",
             "2026-11-28T00:00:00Z"))
        # артефакт есть, received-submission нужной версии нет -> не выдаётся
        r1 = self.cp.claim("enf-01", "i", "knowledge", idem_key="c1")
        self.assertIsNone(r1["claimed"])
        c.execute(
            "INSERT INTO submissions (id,task_id,task_version,task_version_sha256,"
            "attempt_id,lease_id,lease_epoch,agent_id,instance_id,base_commit,"
            "bundle_sha256,artifacts_json,environment_json,toolchain_json,"
            "scientific_outcome,parent_submission_id,complied_messages_json,"
            "submitted_at,status,status_reason) VALUES ("
            "'SUB-ENF-DEP','KG-2026-0320',1,'d','a1','l1',0,'enf-00',NULL,'deadbeef01',"
            "'b','[]','{}','{}',NULL,NULL,'[]','2026-11-28T00:00:00Z','received',NULL)")
        r2 = self.cp.claim("enf-02", "i2", "knowledge", idem_key="c2")
        self.assertEqual(r2["claimed"]["task_id"], "KG-2026-0321")


class TestSubmitEnforcement(Base):
    def _setup(self, tid="KG-2026-0330"):
        self.cp.publish_task(make_task(tid))
        up = self.cp.create_upload("enf-01")
        blob = self.cp.put_blob(up, "enf-01", b"enf data", "application/x-ndjson")
        r = self.cp.claim("enf-01", "i", "knowledge", idem_key="c1")
        return r["claimed"], blob

    def _sub(self, lease, blob, **kw):
        arts = [{"sha256": blob["sha256"], "bytes": blob["bytes"],
                 "media_type": "application/x-ndjson"}]
        sub = {
            "id": "SUB-ENF-1", "task_id": lease["task_id"],
            "task_version": lease["version"],
            "task_version_sha256": lease["task_version_sha256"],
            "attempt_id": lease["attempt_id"], "lease_id": lease["lease_id"],
            "lease_epoch": lease["lease_epoch"], "agent_id": "enf-01",
            "artifacts": arts,
            "bundle_sha256": bundle_sha(lease["task_id"], arts),
            "base_commit": "deadbeef01",
            "scientific_outcome": "passed",
        }
        sub.update(kw)
        return sub

    def test_submit_ok_recomputed_bundle(self):
        lease, blob = self._setup()
        out = self.cp.submit(self._sub(lease, blob), idem_key="s1")
        self.assertEqual(out["status"], "received")

    def test_submit_rejects_wrong_bundle(self):
        lease, blob = self._setup()
        with self.assertRaises(BadRequest):
            self.cp.submit(self._sub(lease, blob, bundle_sha256="b" * 64),
                           idem_key="s1")

    def test_submit_rejects_wrong_base_commit(self):
        lease, blob = self._setup()
        with self.assertRaises(BadRequest):
            self.cp.submit(self._sub(lease, blob, base_commit="wrong0caf"),
                           idem_key="s1")

    def test_submit_blocked_by_blocks_submit_and_unblocked_by_ack(self):
        lease, blob = self._setup()
        self.cp.send_message({"id": "MSG-ENF-1", "sender": "main",
                              "recipient": "enf-01", "body": "стоп",
                              "requires_ack": True, "blocks_submit": True})
        with self.assertRaises(Blocked):
            self.cp.submit(self._sub(lease, blob), idem_key="s1")
        self.cp.ack("MSG-ENF-1", "enf-01")
        out = self.cp.submit(self._sub(lease, blob), idem_key="s2")
        self.assertEqual(out["status"], "received")

    def test_submit_blocked_by_halt(self):
        lease, blob = self._setup()
        self.cp.send_message({"id": "MSG-ENF-2", "sender": "main",
                              "recipient": "all", "body": "halt",
                              "requires_ack": True, "halt": True})
        with self.assertRaises(Blocked):
            self.cp.submit(self._sub(lease, blob), idem_key="s1")


if __name__ == "__main__":
    unittest.main()
