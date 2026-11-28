#!/usr/bin/env python3
"""Regression tests for inbox/bridge/coordinator/run.sh write integrity.

All fixtures live in TemporaryDirectory. The real worktree, live bridges and
.coord state are never written by these tests.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "checks"))
import dispatcher  # noqa: E402


def run(argv: list[str], cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def copy_tool(root: Path, name: str) -> Path:
    target = root / "tools" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "tools" / name, target)
    return target


def valid_node(tmp: str = "n1", text: str = "A sufficiently long proposed literature claim") -> dict:
    return {
        "kind": "node", "tmp": tmp, "type": "literature", "text": text,
        "quote": "A verbatim quotation from the source.",
        "source": {"url": "https://example.test/source", "level": "abstract_read"},
        "lines": ["vybor"],
    }


def valid_edge(from_id: str = "n1", to_id: str = "F-OK", kind: str = "extends") -> dict:
    return {"kind": "edge", "from": from_id, "to": to_id, "type": kind,
            "note": "This edge explains why the two endpoints are related."}


def valid_check() -> dict:
    return {
        "kind": "check", "id": "F-OK", "quote": "A verbatim quotation supporting this check.",
        "source": {"url": "https://example.test/source", "level": "fragment_read"},
        "verdict": "supported", "note": "The quotation directly supports the node.",
    }


def make_kg_repo(root: Path) -> tuple[Path, Path, Path]:
    copy_tool(root, "kg_inbox.py")
    nodes = [
        {"id": "F-OK", "text": "An established graph node", "epistemic": "hypothesis"},
        {"id": "F-REFUTED", "text": "A refuted graph node", "epistemic": "refuted"},
    ]
    write_jsonl(root / "kg" / "nodes.jsonl", nodes)
    (root / "kg" / "lines.json").write_text(
        json.dumps({"lines": [{"id": "vybor"}]}), encoding="utf-8")
    inbox, checks = root / "docs" / "KG-INBOX.jsonl", root / "docs" / "KG-CHECKS.jsonl"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    inbox.write_text('{"sentinel": "inbox"}\n', encoding="utf-8")
    checks.write_text('{"sentinel": "checks"}\n', encoding="utf-8")
    bridge = root / "bridge"
    (bridge / "outbox").mkdir(parents=True)
    (bridge / "ack").mkdir()
    return inbox, checks, bridge


def kg_serve(root: Path, path: Path, ack_dir: Path | None = None) -> subprocess.CompletedProcess:
    argv = [sys.executable, "tools/kg_inbox.py", "--serve"]
    if ack_dir is not None:
        argv += ["--ack-dir", str(ack_dir)]
    argv.append(str(path))
    return run(argv, root)


def make_coord_repo(root: Path) -> Path:
    tool = copy_tool(root, "coord.py")
    (root / ".coord" / "agents").mkdir(parents=True)
    (root / ".coord" / "agents" / "main.md").write_text("# main\n", encoding="utf-8")
    return tool


def utc_minutes_ago(minutes: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - minutes * 60))


def make_claim(root: Path, task: str, *, stale: bool = False, standing: bool = False,
               parent: str | None = None, done: bool = False) -> tuple[Path, bytes]:
    active = root / ".coord" / "active" / task
    active.mkdir(parents=True)
    card = (f"# {task} — fixture\n\n- вид: `research`\n"
            f"- постоянная: {'да' if standing else 'нет'}\n").encode()
    (active / "TASK.md").write_bytes(card)
    try:
        current_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        current_boot = "unknown"
    claim = {
        "agent": "worker", "taken_at": utc_minutes_ago(24 * 60 if stale else 1),
        "task_sha256": "fixture", "area": ["scratch/"], "kind": "research", "priority": 50,
        "gen": 1, "boot_id": "old-boot" if stale else current_boot,
        "parent": parent, "standing": standing,
    }
    claim_path = active / ".claim.json"
    claim_path.write_text(json.dumps(claim), encoding="utf-8")
    when = time.time() - (60 * 60 if stale else 5)
    os.utime(claim_path, (when, when))
    if done:
        (active / "DONE.json").write_text('{"task": "fixture"}\n', encoding="utf-8")
    return active, card


def make_probe_repo(root: Path) -> tuple[Path, Path]:
    copy_tool(root, "probe_bridge.py")
    atom = {
        "atom": "A-1", "domain": "test", "kind": "fact",
        "statement": "The measured values are 10 and 20 in the fixture.",
        "formula": "", "notes": "", "works": [{"quote": "10 and 20", "locator": "p. 1"}],
    }
    write_jsonl(root / "literature" / "map" / "atoms.jsonl", [atom])
    write_jsonl(root / "literature" / "map" / "edges.jsonl", [])
    write_jsonl(root / "kg" / "nodes.jsonl", [])
    (root / "docs").mkdir(parents=True, exist_ok=True)
    bridge = root / "bridge"
    for name in ("request", "outbox", "ack", "done"):
        (bridge / name).mkdir(parents=True)
    return root / "literature" / "map" / "atoms.jsonl", bridge


def probe_question(text: str) -> dict:
    return {
        "question": text, "atoms": ["A-1"], "kind": "numbers", "numbers": [10, 20],
        "verifiable": "Recalculate both values from A-1.",
    }


def submit_atomic(path: Path, row: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    write_jsonl(tmp, [row])
    os.replace(tmp, path)


def probe_serve(root: Path, bridge: Path) -> subprocess.CompletedProcess:
    return run([sys.executable, "tools/probe_bridge.py", "--serve", "--bridge", str(bridge)], root)


class KGInboxIntegrity(unittest.TestCase):
    def test_unknown_tmp_and_supports_refuted_are_rejected(self) -> None:
        cases = [
            ("n999", valid_edge("n999"), "n999"),
            ("supports", valid_edge("F-OK", "F-REFUTED", "supports"), "refuted"),
        ]
        for name, edge, marker in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                inbox, checks, bridge = make_kg_repo(root)
                before = inbox.read_bytes(), checks.read_bytes()
                path = bridge / "outbox" / f"{name}.kg.jsonl"
                write_jsonl(path, [edge])
                result = kg_serve(root, path)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertEqual((inbox.read_bytes(), checks.read_bytes()), before)
                ack = json.loads((bridge / "ack" / f"{name}-kg.json").read_text())
                self.assertEqual(ack["accepted"], 0)
                self.assertIn(marker, " ".join(ack["reasons"]))

    def test_non_object_and_broken_json_are_controlled_bad(self) -> None:
        payloads = ["[]\n", "42\n", "{broken json\n"]
        for payload in payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                inbox, checks, bridge = make_kg_repo(root)
                before = inbox.read_bytes(), checks.read_bytes()
                path = bridge / "outbox" / "bad-json.kg.jsonl"
                path.write_text(payload, encoding="utf-8")
                result = kg_serve(root, path)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stdout + result.stderr)
                self.assertEqual((inbox.read_bytes(), checks.read_bytes()), before)
                ack = json.loads((bridge / "ack" / "bad-json-kg.json").read_text())
                self.assertEqual(ack["accepted"], 0)
                self.assertTrue(ack["reasons"])

    def test_mixed_good_bad_batch_changes_neither_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox, checks, bridge = make_kg_repo(root)
            before = inbox.read_bytes(), checks.read_bytes()
            path = bridge / "outbox" / "mixed.kg.jsonl"
            write_jsonl(path, [valid_node(), valid_edge("n999")])
            result = kg_serve(root, path)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual((inbox.read_bytes(), checks.read_bytes()), before)
            ack = json.loads((bridge / "ack" / "mixed-kg.json").read_text())
            self.assertEqual(ack["accepted"], 0)
            self.assertEqual(ack["rolled_back"], 1)
            self.assertEqual(ack["by_kind"], {"node": 0, "edge": 0, "check": 0})

    def test_good_batch_appends_both_queues_and_infers_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox, checks, bridge = make_kg_repo(root)
            path = bridge / "outbox" / "good.kg.jsonl"
            write_jsonl(path, [valid_node(), valid_edge(), valid_check()])
            result = kg_serve(root, path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            inbox_rows, check_rows = read_jsonl(inbox), read_jsonl(checks)
            self.assertEqual(len(inbox_rows), 3)
            self.assertEqual(len(check_rows), 2)
            self.assertEqual([row["kind"] for row in inbox_rows[1:]], ["node", "edge"])
            self.assertTrue(all(row["file"] == "good.kg.jsonl" for row in inbox_rows[1:] + check_rows[1:]))
            ack_path = bridge / "ack" / "good-kg.json"
            ack = json.loads(ack_path.read_text())
            self.assertIs(type(ack["accepted"]), int)
            self.assertEqual(ack["accepted"], 3)
            self.assertEqual(ack["by_kind"], {"node": 1, "edge": 1, "check": 1})
            self.assertTrue((root / ".coord" / "locks" / "kg-inbox.lock").exists())
            self.assertFalse(list((root / "docs").glob(".*.tmp-*")))
            self.assertFalse(list((bridge / "ack").glob(".*.tmp-*")))

    def test_explicit_ack_dir_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _inbox, _checks, bridge = make_kg_repo(root)
            path = bridge / "outbox" / "custom.kg.jsonl"
            write_jsonl(path, [valid_node(), valid_edge()])
            ack_dir = root / "custom-acks"
            result = kg_serve(root, path, ack_dir)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads((ack_dir / "custom-kg.json").read_text())["accepted"], 2)
            self.assertFalse((bridge / "ack" / "custom-kg.json").exists())

    def test_second_queue_failure_rolls_back_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = importlib.util.spec_from_file_location("kg_inbox_integrity", ROOT / "tools" / "kg_inbox.py")
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            module.ROOT = root
            inbox, checks = root / "docs" / "KG-INBOX.jsonl", root / "docs" / "KG-CHECKS.jsonl"
            inbox.parent.mkdir(parents=True)
            inbox.write_bytes(b"old inbox\n")
            checks.write_bytes(b"old checks\n")
            real_replace = module.os.replace

            def fail_checks(src, dst):
                if Path(dst) == checks and Path(src).name.startswith(".KG-CHECKS.jsonl.tmp-"):
                    raise OSError("injected second-queue failure")
                return real_replace(src, dst)

            with mock.patch.object(module.os, "replace", side_effect=fail_checks):
                with self.assertRaises(RuntimeError):
                    module.append_transaction([(inbox, [{"kind": "node"}]), (checks, [{"kind": "check"}])])
            self.assertEqual(inbox.read_bytes(), b"old inbox\n")
            self.assertEqual(checks.read_bytes(), b"old checks\n")


class CoordIntegrity(unittest.TestCase):
    def test_status_is_read_only_unless_write_is_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_coord_repo(root)
            result = run([sys.executable, "tools/coord.py", "status"], root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((root / ".coord" / "STATUS.md").exists())
            status = root / ".coord" / "STATUS.md"
            status.write_text("sentinel\n", encoding="utf-8")
            before = status.read_bytes(), status.stat().st_mtime_ns
            result = run([sys.executable, "tools/coord.py", "status"], root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((status.read_bytes(), status.stat().st_mtime_ns), before)
            result = run([sys.executable, "tools/coord.py", "status", "--write"], root)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("LEGACY_COORD_READ_ONLY", result.stdout)
            self.assertEqual((status.read_bytes(), status.stat().st_mtime_ns), before)

    def test_status_on_empty_root_creates_no_coord_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_coord_repo(root)
            shutil.rmtree(root / ".coord")
            result = run([sys.executable, "tools/coord.py", "status"], root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((root / ".coord").exists())

    def test_recover_fail_closed_leaves_claims_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_coord_repo(root)
            stale, stale_card = make_claim(root, "stale", stale=True)
            fresh, _ = make_claim(root, "fresh")
            standing, _ = make_claim(root, "S-round", stale=True, standing=True, parent="S")
            finished, _ = make_claim(root, "finished", stale=True, done=True)
            pending_standing = root / ".coord" / "pending" / "S" / "TASK.md"
            pending_standing.parent.mkdir(parents=True)
            pending_standing.write_text("standing card\n", encoding="utf-8")
            live_lock = root / ".coord" / "locks" / "live.lock"
            live_lock.mkdir(parents=True)
            (live_lock / "owner.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")

            result = run([sys.executable, "tools/coord.py", "recover", "--agent", "main"], root)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("LEGACY_COORD_READ_ONLY", result.stdout)
            self.assertTrue(stale.exists())
            self.assertTrue(fresh.exists())
            self.assertTrue(standing.exists())
            self.assertTrue(finished.exists())
            self.assertTrue(live_lock.exists())
            self.assertEqual(pending_standing.read_text(), "standing card\n")
            graveyard = root / ".coord" / "graveyard"
            self.assertFalse(graveyard.exists() and any(graveyard.iterdir()))

    def test_recover_fail_closed_preserves_claims_regardless_of_boot(self) -> None:
        for claim_boot in ("current", "changed"):
            with self.subTest(claim_boot=claim_boot), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_coord_repo(root)
                active, card = make_claim(root, "long-running")
                claim_path = active / ".claim.json"
                claim = json.loads(claim_path.read_text())
                claim["taken_at"] = utc_minutes_ago(4 * 60)
                if claim_boot == "changed":
                    claim["boot_id"] = "old-boot"
                claim_path.write_text(json.dumps(claim), encoding="utf-8")
                os.utime(claim_path, None)

                stale = run([sys.executable, "tools/coord.py", "stale"], root)
                self.assertEqual(stale.returncode, 0, stale.stdout + stale.stderr)
                if claim_boot == "current":
                    self.assertIn("предупреждение", stale.stdout)
                    self.assertNotIn("просрочена:", stale.stdout)
                else:
                    self.assertIn("просрочена:", stale.stdout)
                result = run([sys.executable, "tools/coord.py", "recover", "--agent", "main"], root)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("LEGACY_COORD_READ_ONLY", result.stdout)
                self.assertTrue(active.exists())
                self.assertFalse((root / ".coord" / "pending" / "long-running").exists())
                graveyard = root / ".coord" / "graveyard"
                self.assertFalse(graveyard.exists() and any(graveyard.iterdir()))

    def test_recover_fail_closed_keeps_expired_heartbeat_claim_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_coord_repo(root)
            active, card = make_claim(root, "heartbeat-expired")
            claim_path = active / ".claim.json"
            old = time.time() - 31 * 60
            os.utime(claim_path, (old, old))

            result = run([sys.executable, "tools/coord.py", "recover", "--agent", "main"], root)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("LEGACY_COORD_READ_ONLY", result.stdout)
            self.assertTrue(active.exists())
            self.assertFalse((root / ".coord" / "pending" / "heartbeat-expired").exists())

    def test_recover_fail_closed_does_not_finish_pending_take_window(self) -> None:
        for heartbeat_age in (5, 60 * 60):
            with self.subTest(heartbeat_age=heartbeat_age), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_coord_repo(root)
                active, card = make_claim(root, "take-window")
                pending = root / ".coord" / "pending" / "take-window"
                pending.mkdir(parents=True)
                (pending / "TASK.md").write_bytes(card)
                claim_path = active / ".claim.json"
                claim = json.loads(claim_path.read_text())
                claim["task_sha256"] = hashlib.sha256(card).hexdigest()
                claim_path.write_text(json.dumps(claim), encoding="utf-8")
                when = time.time() - heartbeat_age
                os.utime(claim_path, (when, when))

                result = run([sys.executable, "tools/coord.py", "recover", "--agent", "main"], root)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("LEGACY_COORD_READ_ONLY", result.stdout)
                self.assertTrue(active.exists())
                self.assertTrue(pending.exists())
                self.assertEqual((pending / "TASK.md").read_bytes(), card)
                graveyard = root / ".coord" / "graveyard"
                self.assertFalse(graveyard.exists() and any(graveyard.iterdir()))

    def test_recover_fail_closed_on_take_window_mismatch(self) -> None:
        for claim_matches in (True, False):
            with self.subTest(claim_matches=claim_matches), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_coord_repo(root)
                active, card = make_claim(root, "take-window", stale=True)
                pending = root / ".coord" / "pending" / "take-window"
                pending.mkdir(parents=True)
                (pending / "TASK.md").write_bytes(card + b"different\n")
                if claim_matches:
                    claim_path = active / ".claim.json"
                    claim = json.loads(claim_path.read_text())
                    claim["task_sha256"] = hashlib.sha256(card).hexdigest()
                    claim_path.write_text(json.dumps(claim), encoding="utf-8")

                result = run([sys.executable, "tools/coord.py", "recover", "--agent", "main"], root)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("LEGACY_COORD_READ_ONLY", result.stdout)
                self.assertTrue(active.exists())
                self.assertEqual((active / "TASK.md").read_bytes(), card)
                self.assertEqual((pending / "TASK.md").read_bytes(), card + b"different\n")
                graveyard = root / ".coord" / "graveyard"
                self.assertFalse(graveyard.exists() and any(graveyard.iterdir()))

    def test_release_fail_closed_keeps_claim_and_no_nested_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_coord_repo(root)
            active, card = make_claim(root, "release-me")
            result = run([sys.executable, "tools/coord.py", "release", "release-me",
                          "--agent", "worker", "--reason", "fixture"], root, timeout=5)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("LEGACY_COORD_READ_ONLY", result.stdout)
            self.assertTrue(active.exists())
            self.assertFalse((root / ".coord" / "pending" / "release-me").exists())


class ProbeBridgeIntegrity(unittest.TestCase):
    def test_history_verdict_journal_and_repeat_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _atoms, bridge = make_probe_repo(root)
            triage = root / "docs" / "PROBE-TRIAGE.md"
            triage.write_text(
                "# Очередь вопросов `probe` на проверку\n\n"
                "- **[numbers]** OLD LEGACY QUESTION remains in history\n"
                "  - ячейки: A-1; числа: 10, 20\n", encoding="utf-8")
            q1 = probe_question("FIRST QUESTION: why are the values 10 and 20 different?")
            q2 = probe_question("SECOND QUESTION: how are the values 10 and 20 related?")
            submit_atomic(bridge / "outbox" / "one.jsonl", q1)
            first = probe_serve(root, bridge)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn(q1["question"], triage.read_text())

            submit_atomic(bridge / "outbox" / "two.jsonl", q2)
            verdict_tmp = bridge / "ack" / "answer.json.tmp"
            verdict_tmp.write_text(json.dumps({"verdict": "supported", "score": 0.9}), encoding="utf-8")
            os.replace(verdict_tmp, bridge / "ack" / "answer.json")
            (bridge / "ack" / "not-ready.json.tmp").write_text(
                json.dumps({"verdict": "contradicted", "score": 0.1}), encoding="utf-8")
            second = probe_serve(root, bridge)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            text = triage.read_text()
            self.assertIn(q1["question"], text)
            self.assertIn(q2["question"], text)
            self.assertIn("OLD LEGACY QUESTION", text)
            self.assertIn("supported", text)
            self.assertIn("0.9", text)
            self.assertNotIn("not-ready", text)

            journal_path = root / "docs" / "PROBE-VERDICTS.jsonl"
            journal = read_jsonl(journal_path)
            questions = [row for row in journal if row["type"] == "question"]
            verdicts = [row for row in journal if row["type"] == "verdict"]
            self.assertEqual(len(questions), 3)  # legacy + two submissions
            self.assertEqual(len(verdicts), 1)
            self.assertEqual(len({(row["source"], row["hash"]) for row in journal}), len(journal))
            self.assertTrue(all(len(row["hash"]) == 64 for row in journal))
            before = journal_path.read_bytes()
            third = probe_serve(root, bridge)
            self.assertEqual(third.returncode, 0, third.stdout + third.stderr)
            self.assertEqual(journal_path.read_bytes(), before)
            self.assertFalse(list((root / "docs").glob(".*.tmp-*")))
            self.assertFalse(list((bridge / "ack").glob(".*.tmp-*")))

    def test_tmp_is_not_ready_and_legacy_state_and_request_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _atoms, bridge = make_probe_repo(root)
            legacy_q = probe_question("LEGACY QUESTION already present in the old state file")
            normalized = re.sub(r"\s+", " ", legacy_q["question"].strip().lower())
            legacy_hash = hashlib.sha1(normalized.encode()).hexdigest()[:16]
            state = bridge / "state" / "probe-seen.json"
            state.parent.mkdir(parents=True)
            state.write_text(json.dumps([["numbers", ["A-1"], legacy_hash]]), encoding="utf-8")
            (bridge / "request" / "old.req").write_text(
                json.dumps({"kind": "cells", "args": {"ids": ["A-1"]}}), encoding="utf-8")
            pending = bridge / "outbox" / "pending.jsonl"
            submit_atomic(pending.with_name(pending.name + ".tmp"), probe_question(
                "NEW QUESTION waiting in tmp until the writer renames it"))
            first = probe_serve(root, bridge)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertTrue((bridge / "data" / "old.md").exists())
            self.assertTrue(pending.with_name(pending.name + ".tmp").exists())
            self.assertFalse((root / "docs" / "PROBE-VERDICTS.jsonl").exists())

            os.replace(pending.with_name(pending.name + ".tmp"), pending)
            write_jsonl(bridge / "outbox" / "duplicate.jsonl", [legacy_q])
            second = probe_serve(root, bridge)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            duplicate_ack = json.loads((bridge / "ack" / "duplicate.json").read_text())
            self.assertEqual(duplicate_ack["accepted"], 0)
            self.assertIn("уже принимался", " ".join(duplicate_ack["reasons"]))
            journal = read_jsonl(root / "docs" / "PROBE-VERDICTS.jsonl")
            self.assertEqual(len([row for row in journal if row["type"] == "question"]), 1)


class RunShIntegrity(unittest.TestCase):
    def test_sequential_stub_runs_have_distinct_non_truncated_traces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = dispatcher.build(root, 0, 0, 0)
            rc1, out1 = dispatcher.run(script, "agents")
            rc2, out2 = dispatcher.run(script, "agents")
            self.assertEqual((rc1, rc2), (0, 0), out1 + out2)
            traces1 = re.findall(r"^>>> трассировка: (.+)$", out1, re.MULTILINE)
            traces2 = re.findall(r"^>>> трассировка: (.+)$", out2, re.MULTILINE)
            self.assertEqual(len(traces1), 1)
            self.assertEqual(len(traces2), 1)
            self.assertNotEqual(traces1[0], traces2[0])
            first = Path(traces1[0])
            before = first.read_bytes()
            self.assertTrue(before)
            self.assertEqual(first.read_bytes(), before)
            self.assertTrue(Path(traces2[0]).exists())

    def test_nested_all_inherits_gate_and_keeps_parent_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = dispatcher.build(root, 0, 0, 0)
            child = child.rename(root / "run-child.sh")
            parent = dispatcher.build(root, 0, 0, 0)
            text = parent.read_text(encoding="utf-8")
            text = text.replace("do_dispatcher(){ :; }",
                                f"do_dispatcher(){{ bash {str(child)!r}; }}", 1)
            parent.write_text(text, encoding="utf-8")
            rc, out = dispatcher.run(parent, "all")
            self.assertEqual(rc, 0, out)
            self.assertIn("all: 13 разделов", out)
            traces = re.findall(r"^>>> трассировка: (.+)$", out, re.MULTILINE)
            self.assertGreaterEqual(len(traces), 2)
            self.assertEqual(len(set(traces)), len(traces))
            parent_trace = Path(traces[0]).read_text(encoding="utf-8")
            self.assertIn("do_agents", parent_trace)

    def test_reported_step_is_first_nonzero_rc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = dispatcher.build(root, 1, 0, 2)
            text = script.read_text(encoding="utf-8")
            text = text.replace("do_exp(){ return 1; }",
                                'do_exp(){ local rc; : exp-first; rc=1; return "$rc"; }', 1)
            text = text.replace("do_claims(){ return 2; }",
                                'do_claims(){ local rc; : claims-later; rc=2; return "$rc"; }', 1)
            script.write_text(text, encoding="utf-8")
            rc, out = dispatcher.run(script, "all")
            self.assertEqual(rc, 1, out)
            self.assertIn(">>> первый провалившийся шаг:", out)
            self.assertNotIn("последний провалившийся шаг", out)
            step = [line for line in out.splitlines() if line.startswith(">>> первый провалившийся шаг:")][0]
            self.assertIn("exp-first", step)
            self.assertNotIn("claims-later", step)


if __name__ == "__main__":
    unittest.main(verbosity=2)
