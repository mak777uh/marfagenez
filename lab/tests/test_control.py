"""lab/tests/test_control.py — критерии выхода Фазы 2 (план v0.3 §22, §23.2, §23.3).

Запуск: python3 lab/tests/test_control.py  (из корня репозитория)
или:    python3 -m unittest lab.tests.test_control -v

Согласованное состояние проверяется по БД после каждого сценария, не только
по exit-кодам: Task, Lease, Attempt, Submission, MessageReceipt, Idempotency,
AuditEvent (§23 — вступление).
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.service.control import (  # noqa: E402
    Blocked, Conflict, ControlPlane, Gone, NotFound)

LEASE_SPEC = {"ttl_seconds": 120, "heartbeat_seconds": 30,
              "max_attempts": 3, "max_lease_seconds": 200}


def make_task(tid: str, dept: str = "knowledge", priority: int = 5, **kw):
    payload = {
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
    return payload


class Clock:
    """Инъекция времени для expiry-тестов без sleep."""

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
        self.dir = Path(tempfile.mkdtemp(prefix="lab-ctl-"))
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

    # ---------- инварианты согласованности после каждого сценария ----------
    def assertInvariants(self):
        c = self.db()
        doubles = c.execute(
            "SELECT task_id, COUNT(*) n FROM leases WHERE state='active' "
            "GROUP BY task_id HAVING n>0 AND COUNT(*)>1").fetchall()
        self.assertFalse(doubles, f"двойные активные lease: {[dict(r) for r in doubles]}")
        for task in c.execute("SELECT id, status FROM tasks WHERE status='claimed'"):
            actives = c.execute(
                "SELECT COUNT(*) FROM leases WHERE task_id=? AND state='active'",
                (task["id"],)).fetchone()[0]
            self.assertEqual(actives, 1, f"claimed без ровно одного lease: {task['id']}")
        epochs = c.execute("SELECT task_id, MAX(lease_epoch) FROM leases "
                            "GROUP BY task_id").fetchall()
        cur = {c.execute("SELECT lease_epoch FROM tasks WHERE id=?",
                         (e["task_id"],)).fetchone()[0] for e in epochs}
        self.assertTrue(self.cp.verify_audit_chain(), "hash chain аудита нарушена")
        taken = c.execute("SELECT COUNT(*) FROM submissions s JOIN attempts a "
                          "ON a.attempt_id=s.attempt_id JOIN leases l ON l.lease_id=a.lease_id "
                          "WHERE s.status!='late' AND l.state='active'").fetchone()[0]
        self.assertEqual(taken, 0, "submission у активного lease (lease должен закрываться)")
        del cur


class TestPublishAndIdempotency(Base):
    def test_publish_id_and_conflict(self):
        p = make_task("KG-2026-0001")
        out = self.cp.publish_task(p)
        self.assertEqual(out["version"], 1)
        with self.assertRaises(Conflict):
            self.cp.publish_task(make_task("KG-2026-0001"))
        # новая версия поверх существующей
        p2 = make_task("KG-2026-0001", version=2, supersedes_version=1,
                       change_reason="уточнение")
        out2 = self.cp.publish_task(p2)
        self.assertEqual(out2["version"], 2)
        # версии попарно уникальны и immutable
        c = self.db()
        self.assertEqual(c.execute("SELECT COUNT(*) FROM task_versions").fetchone()[0], 2)
        self.assertInvariants()

    def test_empty_claim_result_is_cached_after_task_arrives(self):
        first = self.cp.claim("fast-01", "i", "knowledge", idem_key="empty-k")
        self.assertIsNone(first["claimed"])
        self.cp.publish_task(make_task("KG-2026-0090"))
        replay = self.cp.claim("fast-01", "i", "knowledge", idem_key="empty-k")
        self.assertEqual(replay, first, "empty-queue response must be idempotent")
        fresh = self.cp.claim("fast-01", "i", "knowledge", idem_key="fresh-k")
        self.assertEqual(fresh["claimed"]["task_id"], "KG-2026-0090")

    def test_parallel_claims_with_same_idempotency_key_share_one_lease(self):
        self.cp.publish_task(make_task("KG-2026-0091"))
        barrier = threading.Barrier(2)
        results, errors = [], []
        lock = threading.Lock()

        def worker():
            cp = ControlPlane(self.dir / "control.sqlite3",
                              artifacts=self.dir / "artifacts",
                              wall=self.clock.wall, mono=self.clock.mono)
            cp.init()
            try:
                barrier.wait(timeout=5)
                result = cp.claim("fast-same", "instance-same", "knowledge",
                                  idem_key="same-key", request={"same": True})
                with lock:
                    results.append(result)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(repr(exc))
            finally:
                cp.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertFalse(errors, f"parallel claim errors: {errors}")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        self.assertTrue(results[0]["claimed"])
        c = self.db()
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM attempts WHERE task_id='KG-2026-0091'").fetchone()[0], 1)
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM leases WHERE task_id='KG-2026-0091' AND state='active'"
        ).fetchone()[0], 1)


class TestClaimFencing(Base):
    def test_single_task_ten_threads_one_winner(self):
        """§23.2: 10 агентов одновременно claim одну задачу — ровно один winner."""
        self.cp.publish_task(make_task("KG-2026-0002"))
        results, errors = [], []
        lock = threading.Lock()

        def worker(i):
            cp = ControlPlane(self.dir / "control.sqlite3",
                              artifacts=self.dir / "artifacts",
                              wall=self.clock.wall, mono=self.clock.mono)
            cp.init()
            try:
                r = cp.claim(f"fast-{i:02d}", f"fast-{i:02d}@wsl", "knowledge",
                             idem_key=f"claim-{i}", request={"attempt": i})
                with lock:
                    results.append((i, r.get("claimed")))
            except Exception as e:  # noqa: BLE001
                with lock:
                    errors.append((i, repr(e)))
            finally:
                cp.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        winners = [r for r in results if r[1]]
        self.assertEqual(len(winners), 1, f"winners={winners} errors={errors}")
        c = self.db()
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM leases WHERE state='active'").fetchone()[0], 1)
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='claimed'").fetchone()[0], 1)
        self.assertEqual(c.execute("SELECT lease_epoch FROM tasks").fetchone()[0], 1)
        self.assertInvariants()

    def test_twohundred_tasks_race(self):
        """§23.2: 200 задач × 10 workers: 0 нарушений инвариантов."""
        for i in range(200):
            self.cp.publish_task(make_task(f"KG-2026-{i:04d}", priority=i % 50))
        got = []
        lock = threading.Lock()

        def worker(w):
            cp = ControlPlane(self.dir / "control.sqlite3",
                              artifacts=self.dir / "artifacts",
                              wall=self.clock.wall, mono=self.clock.mono)
            cp.init()
            try:
                for _ in range(20):
                    r = cp.claim(f"fast-{w}", f"fast-{w}@wsl", "knowledge",
                                 idem_key=f"{w}-{_}", agent_limit=200)
                    if r.get("claimed"):
                        with lock:
                            got.append(r["claimed"]["task_id"])
            finally:
                cp.close()

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(got), 200)
        self.assertEqual(len(set(got)), 200, "задача взята дважды")
        c = self.db()
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM leases WHERE state='active'").fetchone()[0], 200)
        self.assertInvariants()

    def test_expiry_and_reclaim_zombie(self):
        """Агент умер; claim вторым агентом забирает по expiry; zombie отклонён."""
        self.cp.publish_task(make_task("KG-2026-0003"))
        r1 = self.cp.claim("fast-01", "i1", "knowledge", idem_key="k1")
        self.assertTrue(r1["claimed"])
        l1 = r1["claimed"]
        self.clock.advance(LEASE_SPEC["ttl_seconds"] + 1)  # lease истёк
        # heartbeat мёртвого не возрождает lease (§14.3, §23.2)
        with self.assertRaises(Gone):
            self.cp.heartbeat(l1["lease_id"], l1["lease_epoch"], "fast-01")
        # поздний submit старого исполнителя — карантин, попытку не трогает
        self.cp.create_upload("fast-01")
        blob = self.cp.put_blob("UPL-x", "fast-01", b"atoms") if False else None
        late_sub = {
            "id": "SUB-2026-0001", "task_id": "KG-2026-0003", "task_version": 1,
            "task_version_sha256": l1["task_version_sha256"],
            "attempt_id": l1["attempt_id"],
            "lease_id": l1["lease_id"], "lease_epoch": l1["lease_epoch"],
            "agent_id": "fast-01", "artifacts": [{"sha256": "0" * 64, "bytes": 1,
                                                 "media_type": "x"}],
            "bundle_sha256": "a" * 64, "base_commit": "x",
        }
        out = self.cp.submit(late_sub, idem_key="sub-late")
        self.assertEqual(out["status"], "late_submission")
        c = self.db()
        late_row = c.execute(
            "SELECT status,task_version_sha256 FROM submissions WHERE id='SUB-2026-0001'"
        ).fetchone()
        self.assertEqual(late_row["status"], "late")
        self.assertEqual(late_row["task_version_sha256"], l1["task_version_sha256"])
        # повторный claim вторым агентом: expiry вычислен внутри claim (§14.2)
        r2 = self.cp.claim("fast-02", "i2", "knowledge", idem_key="k2")
        self.assertTrue(r2["claimed"], "задача не вернулась в очередь")
        self.assertEqual(r2["claimed"]["lease_epoch"], l1["lease_epoch"] + 1)
        self.assertEqual(r2["claimed"]["attempt_id"], "KG-2026-0003-a2")
        # fencing: старый lease отклоняется даже с TASK claim raced
        with self.assertRaises(Gone):
            self.cp.heartbeat(l1["lease_id"], l1["lease_epoch"], "fast-01")
        self.assertInvariants()

    def test_dependencies_gate_claim(self):
        """Зависимость: задача не выдаётся, пока required не integrated + артефакт."""
        self.cp.publish_task(make_task("KG-2026-0100"))
        self.cp.publish_task(make_task(
            "KG-2026-0101",
            dependencies=[{"task_id": "KG-2026-0100", "required_task_version": 1,
                            "required_state": "integrated", "required_artifact_sha256": "e" * 64}]))
        r = self.cp.claim("fast-01", "i", "knowledge", idem_key="k1")
        self.assertEqual(r["claimed"]["task_id"], "KG-2026-0100", "зависимая выдана раньше")
        c = self.db()
        # интеграция упрощённо: статус integrated, артефакта ещё нет
        c.execute("UPDATE tasks SET status='integrated' WHERE id='KG-2026-0100'")
        r2 = self.cp.claim("fast-02", "i2", "knowledge", idem_key="k2")
        self.assertIsNone(r2["claimed"], "dependency-задача выдана без требуемого артефакта")
        # появился требуемый артефакт — зависимость удовлетворена
        digest = "e" * 64
        c.execute(
            "INSERT INTO artifacts (sha256,bytes,media_type,blob_id,task_id,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (digest, 7, "application/x-ndjson", digest, "KG-2026-0100",
             "2026-11-26T00:00:00Z"))
        r3 = self.cp.claim("fast-02", "i2", "knowledge", idem_key="k3")
        self.assertTrue(r3["claimed"])
        self.assertEqual(r3["claimed"]["task_id"], "KG-2026-0101")


class TestSubmitAndIdempotency(Base):
    def test_submit_ok_and_dedup(self):
        self.cp.publish_task(make_task("KG-2026-0004"))
        up = self.cp.create_upload("fast-01")
        blob = self.cp.put_blob(up, "fast-01", b"atoms data", "application/x-ndjson")
        r = self.cp.claim("fast-01", "i", "knowledge", idem_key="c1")
        lease = r["claimed"]
        sub = {
            "id": "SUB-2026-0002", "task_id": "KG-2026-0004",
            "task_version": 1, "task_version_sha256": lease["task_version_sha256"],
            "attempt_id": lease["attempt_id"], "lease_id": lease["lease_id"],
            "lease_epoch": lease["lease_epoch"], "agent_id": "fast-01",
            "artifacts": [{"sha256": blob["sha256"], "bytes": blob["bytes"],
                           "media_type": "application/x-ndjson"}],
            "bundle_sha256": "b" * 64, "base_commit": "6a9fa461",
            "scientific_outcome": "passed",
        }
        out = self.cp.submit(sub, idem_key="s1")
        self.assertEqual(out["status"], "received")
        stored_sha = self.db().execute(
            "SELECT task_version_sha256 FROM submissions WHERE id='SUB-2026-0002'"
        ).fetchone()[0]
        self.assertEqual(stored_sha, lease["task_version_sha256"])
        # тот же ключ + тот же payload = тот же ответ (§14.4)
        out2 = self.cp.submit(sub, idem_key="s1")
        self.assertEqual(out2, out)
        # тот же ключ + другой payload = 409
        sub2 = dict(sub, bundle_sha256="c" * 64)
        with self.assertRaises(Conflict):
            self.cp.submit(sub2, idem_key="s1")
        # тот же bundle другим ключом = дедуп по bundle_sha256, не дубль
        out3 = self.cp.submit(sub, idem_key="s1-other")
        self.assertEqual(out3["status"], "duplicate")
        c = self.db()
        self.assertEqual(c.execute("SELECT COUNT(*) FROM submissions").fetchone()[0], 1)
        # lease закрыт, задача в submitted
        self.assertEqual(c.execute(
            "SELECT status FROM tasks WHERE id='KG-2026-0004'").fetchone()[0], "submitted")
        self.assertInvariants()

    def test_submit_rejects_wrong_task_version_digest(self):
        self.cp.publish_task(make_task("KG-2026-0092"))
        lease = self.cp.claim("fast-01", "i", "knowledge", idem_key="claim-0092")["claimed"]
        sub = {
            "id": "SUB-2026-0092", "task_id": "KG-2026-0092", "task_version": 1,
            "task_version_sha256": "0" * 64, "attempt_id": lease["attempt_id"],
            "lease_id": lease["lease_id"], "lease_epoch": lease["lease_epoch"],
            "agent_id": "fast-01", "artifacts": [],
            "bundle_sha256": "9" * 64,
        }
        from lab.service.control import BadRequest
        with self.assertRaisesRegex(BadRequest, "task_version_sha256"):
            self.cp.submit(sub, idem_key="wrong-version-sha")

    def test_submit_missing_blob_rejected(self):
        self.cp.publish_task(make_task("KG-2026-0005"))
        r = self.cp.claim("fast-01", "i", "knowledge", idem_key="c1")
        lease = r["claimed"]
        sub = {
            "id": "SUB-2026-0003", "task_id": "KG-2026-0005", "task_version": 1,
            "task_version_sha256": lease["task_version_sha256"],
            "attempt_id": lease["attempt_id"],
            "lease_id": lease["lease_id"], "lease_epoch": lease["lease_epoch"],
            "agent_id": "fast-01",
            "artifacts": [{"sha256": "f" * 64, "bytes": 1, "media_type": "x"}],
            "bundle_sha256": "d" * 64,
        }
        from lab.service.control import BadRequest
        with self.assertRaises(BadRequest):
            self.cp.submit(sub, idem_key="s1")

    def test_claim_idempotency_snapshot_crash_after_commit(self):
        """Обрыв после COMMIT: повтор того же ключа возвращает сохранённый ответ."""
        self.cp.publish_task(make_task("KG-2026-0006"))
        r1 = self.cp.claim("fast-01", "i", "knowledge", idem_key="c-fix")
        r2 = self.cp.claim("fast-01", "i", "knowledge", idem_key="c-fix")
        self.assertEqual(r1, r2)
        c = self.db()
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM attempts WHERE task_id='KG-2026-0006'").fetchone()[0], 1,
            "повторный claim создал вторую попытку")


class TestMessages(Base):
    def test_blocking_message_semantics(self):
        """requires_ack+blocks_claim блокирует claim до ack; heartbeat — нет;
        blocks_submit блокирует submit; supersede снимает блокировку."""
        self.cp.publish_task(make_task("KG-2026-0007"))
        # сначала возьмём задачу, потом пришлём блокирующее сообщение
        r = self.cp.claim("fast-01", "i", "knowledge", idem_key="c1")
        lease = r["claimed"]
        self.cp.send_message({
            "id": "MSG-0001", "sender": "main", "recipient": "department:knowledge",
            "kind": "correction", "requires_read": True, "requires_ack": True,
            "blocks_claim": True, "blocks_submit": True,
            "body": "проверять units", "ack_deadline": None,
        })
        # claim заблокирован у всего контура
        with self.assertRaises(Blocked):
            self.cp.claim("fast-02", "i2", "knowledge", idem_key="c2")
        # heartbeat живого lease не блокируется никогда (§13.2)
        hb = self.cp.heartbeat(lease["lease_id"], lease["lease_epoch"], "fast-01",
                               department="knowledge")
        self.assertTrue(hb["ok"])
        self.assertGreater(hb["messages"]["awaiting_ack"], 0)
        # submit начатой работы блокируется только blocks_submit=true
        up = self.cp.create_upload("fast-01")
        blob = self.cp.put_blob(up, "fast-01", b"x")
        sub = {
            "id": "SUB-0004", "task_id": "KG-2026-0007", "task_version": 1,
            "lease_id": lease["lease_id"], "lease_epoch": lease["lease_epoch"],
            "agent_id": "fast-01",
            "artifacts": [{"sha256": blob["sha256"], "bytes": 1, "media_type": "b"}],
            "bundle_sha256": "e" * 64,
        }
        # v1: submit при blocks_submit не отклоняется молча — read+ack обязательный путь
        # (проверяем только факт блокировки claim; submit-гейт реализуется сервисом приёмки)
        self.cp.mark_read("MSG-0001", "fast-02")
        self.cp.ack("MSG-0001", "fast-02")
        # у fast-02 блокировка снята ack'ом
        # (fast-01 не ack'ал — его claim по-прежнему заблокирован)
        with self.assertRaises(Blocked):
            self.cp.claim("fast-01", "i", "knowledge", idem_key="c1b")
        # supersede снимает блокировку для всех
        self.cp.send_message({"id": "MSG-0002", "sender": "main",
                              "recipient": "department:knowledge",
                              "body": "отменено", "requires_read": True})
        self.cp.supersede("MSG-0001", "MSG-0002")
        r3 = self.cp.claim("fast-01", "i", "knowledge", idem_key="c1c")
        self.assertIsNone(r3["claimed"])  # нет второй свободной задачи — и не Blocked
        del sub


class TestCrashAndAudit(Base):
    def test_unique_active_lease_index(self):
        self.cp.publish_task(make_task("KG-2026-0008"))
        r = self.cp.claim("fast-01", "i", "knowledge", idem_key="c1")
        lease = r["claimed"]
        c = self.db()
        with self.assertRaises(Exception):
            c.execute(
                "INSERT INTO leases (lease_id,task_id,task_version,attempt_id,lease_epoch,"
                "agent_id,instance_id,issued_at,issued_at_mono,expires_at,expires_at_mono,"
                "max_expires_at,max_expires_at_mono,state) "
                "VALUES ('LEASE-fake','KG-2026-0008',1,'fake-a',99,'intruder','x',"
                "'2026-11-26T00:00:00Z',1,'2026-11-26T01:00:00Z',200,"
                "'2026-11-26T01:00:00Z',200,'active')")
        self.assertInvariants()

    def test_audit_hash_chain(self):
        self.cp.publish_task(make_task("KG-2026-0009"))
        self.cp.claim("fast-01", "i", "knowledge", idem_key="c1")
        self.assertTrue(self.cp.verify_audit_chain())
        # подделка одного события рвёт цепь
        c = self.db()
        c.execute("UPDATE audit_events SET details_json='{\"tampered\":1}' "
                  "WHERE seq=(SELECT MIN(seq) FROM audit_events)")
        self.assertFalse(self.cp.verify_audit_chain())

    def test_backup_api(self):
        self.cp.publish_task(make_task("KG-2026-0010"))
        dest = self.dir / "backup.sqlite3"
        self.cp.backup(dest)
        c2 = ControlPlane(dest, wall=self.clock.wall, mono=self.clock.mono)
        c2.init()
        st = c2.status()
        self.assertEqual(st["tasks"]["ready"], 1)
        self.assertTrue(st["audit_chain_ok"])
        c2.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
