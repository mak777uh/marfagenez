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
        "budget": {"cpu_seconds": 600, "ram_bytes": 1, "disk_bytes": 1_048_576,
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
        self.assertEqual(self.cp.user_version(), 6)
        tables = {r[0] for r in self.db().execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("proposals", tables)
        self.assertIn("standing_templates", tables)
        self.assertIn("submission_artifacts", tables)
        self.assertIn("upload_artifacts", tables)
        self.assertIn("validations", tables)
        self.assertIn("decisions", tables)
        self.assertIn("integrations", tables)
        # Repeated init must not rewind schema version or replay migrations.
        before = self.db().execute(
            "SELECT COUNT(*) FROM audit_events WHERE action='schema.migrate'"
        ).fetchone()[0]
        self.assertEqual(before, 5)
        self.cp.init()
        self.assertEqual(self.cp.user_version(), 6)
        after = self.db().execute(
            "SELECT COUNT(*) FROM audit_events WHERE action='schema.migrate'"
        ).fetchone()[0]
        self.assertEqual(after, before, "повторный init повторно записал миграции")
        self.assertInvariants()


    def test_v3_migration_backfills_only_resolvable_artifact_references(self):
        c = self.db()
        c.execute("DROP TABLE submission_artifacts")
        c.execute("PRAGMA user_version=3")
        task_id = "KG-2026-0401"
        self.cp.publish_task(make_task(task_id))
        c.execute(
            "INSERT INTO uploads (upload_id,agent_id,state,created_at) "
            "VALUES (?,?,?,?)",
            ("UPL-LEGACY", "legacy-agent", "open", "2026-11-28T00:00:00Z"),
        )
        digest = "a" * 64
        c.execute(
            "INSERT INTO artifacts (sha256,bytes,media_type,blob_id,upload_id,created_at) "
            "VALUES (?,?,?,?,?,?)",
            (digest, 12, "application/x-ndjson", digest, "UPL-LEGACY", "2026-11-28T00:00:00Z"),
        )
        c.execute(
            "INSERT INTO artifacts (sha256,bytes,media_type,blob_id,upload_id,created_at) "
            "VALUES (?,?,?,?,?,?)",
            ("b" * 64, 3, "application/octet-stream", "b" * 64,
             "UPL-MISSING", "2026-11-28T00:00:00Z"),
        )
        descriptors = [
            {"sha256": digest, "bytes": 12, "media_type": "application/x-ndjson"},
            {"sha256": "b" * 64, "bytes": 9, "media_type": "application/x-ndjson"},
        ]
        c.execute(
            "INSERT INTO submissions (id,task_id,task_version,agent_id,artifacts_json,"
            "submitted_at,status) VALUES (?,?,?,?,?,?,?)",
            ("SUB-2026-0401", task_id, 1, "legacy-agent",
             json.dumps(descriptors), "2026-11-28T00:00:00Z", "received"),
        )
        self.cp.init()
        links = c.execute(
            "SELECT artifact_index,sha256 FROM submission_artifacts "
            "WHERE submission_id='SUB-2026-0401' ORDER BY artifact_index"
        ).fetchall()
        self.assertEqual([(x["artifact_index"], x["sha256"]) for x in links], [(0, digest)])
        migration = c.execute(
            "SELECT details_json FROM audit_events WHERE action='schema.migrate' "
            "AND details_json LIKE '%\"to\":4%' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(migration)
        self.assertIn('"unresolved_legacy_artifacts":1', migration["details_json"])
        upload_links = c.execute(
            "SELECT upload_id,sha256,media_type FROM upload_artifacts "
            "WHERE sha256=?",
            (digest,),
        ).fetchall()
        self.assertEqual(
            [(x["upload_id"], x["sha256"], x["media_type"]) for x in upload_links],
            [("UPL-LEGACY", digest, "application/x-ndjson")],
        )
        migration_v5 = c.execute(
            "SELECT details_json FROM audit_events WHERE action='schema.migrate' "
            "AND details_json LIKE '%\"to\":5%' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(migration_v5)
        self.assertIn('"unresolved_legacy_uploads":1', migration_v5["details_json"])
        self.assertInvariants()


    def test_same_blob_can_be_referenced_by_multiple_tasks(self):
        upload = self.cp.create_upload("fast-01")
        blob = self.cp.put_blob(
            upload, "fast-01", b"shared immutable evidence", "application/x-ndjson"
        )
        arts = [{"path": "results/shared.ndjson", "sha256": blob["sha256"],
                 "bytes": blob["bytes"], "media_type": "application/x-ndjson"}]
        for index, task_id in enumerate(("KG-2026-0301", "KG-2026-0302"), start=1):
            self.cp.publish_task(make_task(task_id))
            lease = self.cp.claim(
                "fast-01", f"i{index}", "knowledge", idem_key=f"claim-shared-{index}"
            )["claimed"]
            payload = {
                "id": f"SUB-2026-03{index:02d}", "task_id": task_id,
                "task_version": 1, "task_version_sha256": lease["task_version_sha256"],
                "attempt_id": lease["attempt_id"], "lease_id": lease["lease_id"],
                "lease_epoch": lease["lease_epoch"], "agent_id": "fast-01",
                "artifacts": arts, "bundle_sha256": bundle_sha(task_id, arts),
                "base_commit": "6a9fa461",
            }
            result = self.cp.submit(payload, idem_key=f"submit-shared-{index}")
            self.assertEqual(result["status"], "received")

        links = self.db().execute(
            "SELECT s.task_id, sa.sha256 FROM submission_artifacts sa "
            "JOIN submissions s ON s.id=sa.submission_id "
            "WHERE sa.sha256=? ORDER BY s.task_id",
            (blob["sha256"],),
        ).fetchall()
        self.assertEqual(
            [(row["task_id"], row["sha256"]) for row in links],
            [("KG-2026-0301", blob["sha256"]),
             ("KG-2026-0302", blob["sha256"])],
        )
        # New submissions no longer rewrite the lossy legacy owner column.
        legacy = self.db().execute(
            "SELECT task_id FROM artifacts WHERE sha256=?", (blob["sha256"],)
        ).fetchone()
        self.assertIsNone(legacy["task_id"])
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
        arts = [{"path": "results/data.ndjson", "sha256": blob["sha256"],
                 "bytes": blob["bytes"], "media_type": "application/x-ndjson"}]
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


class TestValidationDecisionIntegration(Base):
    def _submit(self, task_id: str):
        self.cp.publish_task(make_task(task_id))
        upload = self.cp.create_upload("fast-01")
        blob = self.cp.put_blob(
            upload, "fast-01", b"validation lifecycle evidence",
            "application/x-ndjson",
        )
        lease = self.cp.claim(
            "fast-01", f"lifecycle-{task_id}", "knowledge",
            idem_key=f"lifecycle-claim-{task_id}",
        )["claimed"]
        artifacts = [{
            "path": "results/evidence.ndjson",
            "sha256": blob["sha256"],
            "media_type": "application/x-ndjson",
            "bytes": blob["bytes"],
        }]
        payload = {
            "id": f"SUB-{task_id[-4:]}",
            "task_id": task_id,
            "task_version": 1,
            "task_version_sha256": lease["task_version_sha256"],
            "attempt_id": lease["attempt_id"],
            "lease_id": lease["lease_id"],
            "lease_epoch": lease["lease_epoch"],
            "agent_id": "fast-01",
            "artifacts": artifacts,
            "bundle_sha256": bundle_sha(task_id, artifacts),
            "base_commit": "6a9fa461",
            # A negative scientific finding is not a mechanical validation failure.
            "scientific_outcome": "failed",
        }
        self.assertEqual(self.cp.submit(payload, idem_key=f"submit-{task_id}")["status"],
                         "received")
        return payload, lease

    def _validation(self, submission: dict, validation_id: str = "VAL-0801",
                    *, checks=None, recommendation: str = "accepted",
                    profile: str = "knowledge-map-v1") -> dict:
        return {
            "schema": "validation/v1",
            "id": validation_id,
            "submission_id": submission["id"],
            "bundle_sha256": submission["bundle_sha256"],
            "validator_profile": profile,
            "validator_version": "1.0.0",
            "gate_script_sha256": "a" * 64,
            "sandbox_image_digest": "sha256:0123456789abcdef",
            "toolchain": {"python": "3.12"},
            "checks": checks if checks is not None else [
                {"name": "trusted_gate", "rc": 0},
                {"name": "cross_links", "rc": 0},
            ],
            "recommendation": recommendation,
            "reason": "Проверка воспроизведена.",
            "started_at": "2026-11-28T00:00:00Z",
            "finished_at": "2026-11-28T00:01:00Z",
            "created_at": "2026-11-28T00:01:01Z",
        }

    def test_validation_is_profile_and_bundle_pinned_and_decision_is_main_only(self):
        submission, _ = self._submit("KG-2026-0801")
        bad_profile = self._validation(
            submission, "VAL-0801-BAD", profile="executor-chosen-command")
        with self.assertRaisesRegex(BadRequest, "не закреплён"):
            self.cp.record_validation(bad_profile)

        bad_bundle = self._validation(submission, "VAL-0801-BUNDLE")
        bad_bundle["bundle_sha256"] = "b" * 64
        with self.assertRaisesRegex(BadRequest, "bundle_sha256"):
            self.cp.record_validation(bad_bundle)

        validation = self._validation(submission)
        self.assertEqual(
            self.cp.record_validation(validation),
            {"status": "recorded", "validation_id": "VAL-0801"},
        )
        self.assertEqual(
            self.cp.record_validation(validation),
            {"status": "duplicate", "validation_id": "VAL-0801"},
        )
        with self.assertRaises(Conflict):
            self.cp.record_validation(dict(validation, reason="different report"))

        task = self.db().execute(
            "SELECT status FROM tasks WHERE id='KG-2026-0801'"
        ).fetchone()[0]
        sub = self.db().execute(
            "SELECT status FROM submissions WHERE id='SUB-0801'"
        ).fetchone()[0]
        self.assertEqual(task, "validating")
        self.assertEqual(sub, "validating")
        with self.assertRaisesRegex(BadRequest, "только main"):
            self.cp.decide_submission(
                "SUB-0801", "VAL-0801", "accepted", "accept", actor="subagent"
            )
        self.assertInvariants()

    def test_main_can_accept_negative_scientific_result_after_green_validation(self):
        submission, lease = self._submit("KG-2026-0802")
        self.cp.record_validation(self._validation(
            submission, "VAL-0802", recommendation="needs_work"))
        decision = self.cp.decide_submission(
            "SUB-0802", "VAL-0802", "accepted",
            "Эксперимент корректен; отрицательный исход сохранён.",
        )
        duplicate = self.cp.decide_submission(
            "SUB-0802", "VAL-0802", "accepted",
            "Эксперимент корректен; отрицательный исход сохранён.",
        )
        self.assertEqual(duplicate["status"], "duplicate")
        self.assertEqual(duplicate["decision_id"], decision["decision_id"])
        self.assertEqual(decision["status"], "accepted")
        states = self.db().execute(
            "SELECT s.status AS submission_status,t.status AS task_status,"
            "a.status AS attempt_status FROM submissions s "
            "JOIN tasks t ON t.id=s.task_id JOIN attempts a ON a.attempt_id=s.attempt_id "
            "WHERE s.id='SUB-0802'"
        ).fetchone()
        self.assertEqual(states["submission_status"], "accepted")
        self.assertEqual(states["task_status"], "accepted")
        self.assertEqual(states["attempt_status"], "accepted")
        with self.assertRaises(Conflict):
            self.cp.decide_submission(
                "SUB-0802", "VAL-0802", "rejected", "second decision"
            )
        self.assertInvariants()

    def test_skipped_or_failed_check_cannot_be_accepted_but_can_be_needs_work(self):
        submission, lease = self._submit("KG-2026-0803")
        validation = self._validation(
            submission,
            "VAL-0803",
            checks=[
                {"name": "trusted_gate", "rc": 0},
                {"name": "full_reproduction", "rc": 0,
                 "skipped_reason": "full text unavailable"},
            ],
            recommendation="needs_work",
        )
        self.cp.record_validation(validation)
        with self.assertRaisesRegex(Conflict, "passed без skipped"):
            self.cp.decide_submission(
                "SUB-0803", "VAL-0803", "accepted", "not enough evidence"
            )
        result = self.cp.decide_submission(
            "SUB-0803", "VAL-0803", "needs_work", "нужен полный прогон"
        )
        self.assertEqual(result["status"], "needs_work")
        task = self.db().execute(
            "SELECT status FROM tasks WHERE id='KG-2026-0803'"
        ).fetchone()[0]
        attempt = self.db().execute(
            "SELECT status FROM attempts WHERE attempt_id=?", (lease["attempt_id"],)
        ).fetchone()[0]
        self.assertEqual(task, "ready")
        self.assertEqual(attempt, "needs_work")
        self.assertInvariants()

    def test_accepted_submission_satisfies_exact_downstream_dependency(self):
        prerequisite, _ = self._submit("KG-2026-0806")
        digest = prerequisite["artifacts"][0]["sha256"]
        self.cp.record_validation(self._validation(
            prerequisite, "VAL-0806"))
        self.cp.decide_submission(
            "SUB-0806", "VAL-0806", "accepted", "воспроизводимый результат"
        )

        dependent = make_task(
            "KG-2026-0807",
            dependencies=[{
                "task_id": "KG-2026-0806",
                "required_task_version": 1,
                "required_state": "accepted",
                "required_artifact_sha256": digest,
            }],
        )
        self.cp.publish_task(dependent)
        claimed = self.cp.claim(
            "fast-02", "downstream", "knowledge",
            idem_key="claim-after-accepted-dependency",
        )["claimed"]
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["task_id"], "KG-2026-0807")
        self.assertEqual(
            self.db().execute(
                "SELECT status FROM submissions WHERE id='SUB-0806'"
            ).fetchone()[0],
            "accepted",
        )
        self.assertInvariants()

    def test_integration_pins_base_checks_scope_and_finishes(self):
        submission, _ = self._submit("KG-2026-0804")
        self.cp.record_validation(self._validation(submission, "VAL-0804"))
        self.cp.decide_submission(
            "SUB-0804", "VAL-0804", "accepted", "воспроизводится"
        )
        with self.assertRaises(Conflict):
            self.cp.start_integration("SUB-0804", "deadbeef")
        with self.assertRaisesRegex(BadRequest, "только main"):
            self.cp.start_integration(
                "SUB-0804", "6a9fa461", actor="subagent"
            )

        head_before = "6a9fa461" + "0" * 32
        started = self.cp.start_integration("SUB-0804", head_before)
        duplicate_start = self.cp.start_integration("SUB-0804", head_before)
        self.assertEqual(duplicate_start["status"], "duplicate")
        self.assertEqual(
            duplicate_start["integration_id"], started["integration_id"])
        integration_id = started["integration_id"]
        self.assertEqual(started["attempt_no"], 1)
        self.assertEqual(
            self.db().execute(
                "SELECT status FROM tasks WHERE id='KG-2026-0804'"
            ).fetchone()[0],
            "integrating",
        )
        head_after = "b" * 40
        with self.assertRaisesRegex(BadRequest, "PROTECTED"):
            self.cp.finish_integration(
                integration_id, head_after, ["core/src/lib.rs"])
        with self.assertRaisesRegex(BadRequest, "вне task.write_scope"):
            self.cp.finish_integration(
                integration_id, head_after, ["docs/FINDING.md"])

        finished = self.cp.finish_integration(
            integration_id, head_after, ["results/evidence.ndjson"])
        self.assertEqual(finished["status"], "integrated")
        self.assertEqual(
            self.cp.finish_integration(
                integration_id, head_after, ["results/evidence.ndjson"]
            )["status"],
            "duplicate",
        )
        states = self.db().execute(
            "SELECT t.status AS task_status,i.status AS integration_status,"
            "i.head_before,i.head_after,i.changed_files_json "
            "FROM integrations i JOIN submissions s ON s.id=i.submission_id "
            "JOIN tasks t ON t.id=s.task_id WHERE i.id=?",
            (integration_id,),
        ).fetchone()
        self.assertEqual(states["task_status"], "integrated")
        self.assertEqual(states["integration_status"], "integrated")
        self.assertEqual(states["head_before"], head_before)
        self.assertEqual(states["head_after"], head_after)
        self.assertEqual(json.loads(states["changed_files_json"]),
                         ["results/evidence.ndjson"])

        # Projections carry the whole Validation -> Decision -> Integration chain.
        projections = self.dir / "lifecycle-projections"
        projected = self.cp.write_projections(projections)
        snapshot = Path(projected["snapshot_path"])
        self.assertEqual(projected["validations"], 1)
        self.assertEqual(projected["decisions"], 1)
        self.assertEqual(projected["integrations"], 1)
        self.assertEqual(
            json.loads((snapshot / "validations.jsonl").read_text().splitlines()[0])["id"],
            "VAL-0804",
        )
        self.assertEqual(
            json.loads((snapshot / "decisions.jsonl").read_text().splitlines()[0])["decision"],
            "accepted",
        )
        self.assertEqual(
            json.loads((snapshot / "integrations.jsonl").read_text().splitlines()[0])["status"],
            "integrated",
        )
        self.assertInvariants()

    def test_failed_integration_is_audited_and_retry_creates_new_attempt(self):
        submission, _ = self._submit("KG-2026-0805")
        self.cp.record_validation(self._validation(submission, "VAL-0805"))
        self.cp.decide_submission(
            "SUB-0805", "VAL-0805", "accepted", "gate green"
        )
        first = self.cp.start_integration("SUB-0805", "6a9fa461")
        failed = self.cp.fail_integration(
            first["integration_id"], "base moved during apply"
        )
        self.assertEqual(failed["status"], "integration_failed")
        self.assertEqual(
            self.cp.fail_integration(
                first["integration_id"], "base moved during apply"
            )["status"],
            "duplicate",
        )
        retry = self.cp.start_integration("SUB-0805", "6a9fa461")
        self.assertEqual(retry["attempt_no"], 2)
        self.cp.finish_integration(
            retry["integration_id"], "c" * 40, ["results/evidence.ndjson"])
        rows = self.db().execute(
            "SELECT attempt_no,status FROM integrations "
            "WHERE submission_id='SUB-0805' ORDER BY attempt_no"
        ).fetchall()
        self.assertEqual(
            [(r["attempt_no"], r["status"]) for r in rows],
            [(1, "integration_failed"), (2, "integrated")],
        )
        self.assertEqual(
            self.db().execute(
                "SELECT status FROM tasks WHERE id='KG-2026-0805'"
            ).fetchone()[0],
            "integrated",
        )
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
        snapshot = Path(out1["snapshot_path"])
        self.assertEqual(self.cp.resolve_projections(proj), snapshot)
        h1 = dir_hash(snapshot)
        current1 = (proj / "CURRENT").read_text(encoding="ascii").strip()
        self.assertEqual(current1, out1["snapshot_id"])

        # Repeated export is byte-identical and does not mutate an immutable snapshot.
        out2 = self.cp.write_projections(proj)
        self.assertEqual(out2["snapshot_id"], current1)
        self.assertEqual(dir_hash(self.cp.resolve_projections(proj)), h1)

        # A lost immutable snapshot can be reconstructed from the DB.
        shutil.rmtree(snapshot)
        out3 = self.cp.write_projections(proj)
        rebuilt = Path(out3["snapshot_path"])
        self.assertEqual(out3["snapshot_id"], current1)
        self.assertEqual(dir_hash(rebuilt), h1)

        # Consumers read only the snapshot named by CURRENT.
        lines = (rebuilt / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
        statuses = {json.loads(l)["id"]: json.loads(l)["status"]
                    for l in lines}
        self.assertEqual(statuses["KG-2026-0030"], "claimed")
        self.assertEqual(statuses["KG-2026-0031"], "ready")
        self.assertTrue((rebuilt / "task_versions" / "KG-2026-0030" /
                        "v2.json").exists())
        head = (rebuilt / "audit_head.txt").read_text(encoding="utf-8").strip()
        self.assertNotEqual(head, "GENESIS")
        self.assertInvariants()

    def test_snapshot_resolver_detects_content_tampering(self):
        self.cp.publish_task(make_task("KG-2026-0033"))
        proj = self.dir / "tampered-proj"
        out = self.cp.write_projections(proj)
        snapshot = Path(out["snapshot_path"])
        (snapshot / "tasks.jsonl").write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(BadRequest, "hash mismatch"):
            self.cp.resolve_projections(proj)

    def test_failed_pointer_replace_keeps_previous_snapshot_available(self):
        from unittest.mock import patch

        task_id = "KG-2026-0032"
        self.cp.publish_task(make_task(task_id))
        proj = self.dir / "atomic-proj"
        first = self.cp.write_projections(proj)
        current_before = (proj / "CURRENT").read_text(encoding="ascii")
        first_snapshot = Path(first["snapshot_path"])
        self.assertTrue((first_snapshot / "tasks.jsonl").is_file())

        self.cp.claim("fast-01", "i", "knowledge", idem_key="atomic-c32")
        real_replace = os.replace

        def fail_only_current(src, dst):
            if Path(dst) == proj / "CURRENT":
                raise OSError("injected crash before CURRENT publication")
            return real_replace(src, dst)

        with patch("lab.service.v2_ops.os.replace", side_effect=fail_only_current):
            with self.assertRaisesRegex(OSError, "injected crash"):
                self.cp.write_projections(proj)

        self.assertEqual((proj / "CURRENT").read_text(encoding="ascii"), current_before)
        resolved = self.cp.resolve_projections(proj)
        self.assertEqual(resolved, first_snapshot)
        rows = (resolved / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
        states = {json.loads(line)["id"]: json.loads(line)["status"] for line in rows}
        self.assertEqual(states[task_id], "ready")
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
