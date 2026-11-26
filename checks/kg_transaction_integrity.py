"""Изолированные регрессии commit/recovery/receipt для tools/kg_inbox.py.

Каждый тест копирует инбокс во временный fixture-repo. Боевые kg/, docs/, .coord/,
watcher-процессы и другие проверки не читаются и не изменяются.
Запуск: python3 checks/kg_transaction_integrity.py
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
OLD_INBOX = b'{"sentinel":"old inbox"}\n'
OLD_CHECKS = b'{"sentinel":"old checks"}\n'


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows),
                    encoding='utf-8')


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip()]


def valid_node(text: str = 'A sufficiently long isolated fixture literature claim.') -> dict:
    return {
        'kind': 'node', 'tmp': 'n1', 'type': 'literature', 'text': text,
        'quote': 'A sufficiently long isolated fixture quote.',
        'source': {'doi': '10.0000/kg-transaction-fixture', 'level': 'abstract_read'},
        'lines': ['vybor'],
    }


def valid_check() -> dict:
    return {
        'kind': 'check', 'id': 'BASE-1', 'quote': 'An isolated fixture check quote.',
        'source': {'url': 'https://example.invalid/fixture', 'level': 'fragment_read'},
        'verdict': 'supported', 'note': 'Изолированная проверка fixture.',
    }


class Fixture:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kg-transaction-integrity-')
        self.root = pathlib.Path(self.tmp.name)
        tool = self.root / 'tools/kg_inbox.py'
        tool.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'tools/kg_inbox.py', tool)
        spec = importlib.util.spec_from_file_location('fixture_kg_inbox', tool)
        self.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(self.module)
        self.module.ROOT = self.root
        self.module.NODES = self.root / 'kg/nodes.jsonl'
        self.module.LINES = self.root / 'kg/lines.json'
        self.module.INBOX = self.root / 'docs/KG-INBOX.jsonl'
        self.module.CHECKS = self.root / 'docs/KG-CHECKS.jsonl'
        self.module.INBOX.parent.mkdir(parents=True)
        write_jsonl(self.module.NODES, [{
            'id': 'BASE-1', 'kind': 'claim', 'text': 'An existing base fixture claim.',
            'epistemic': 'supported',
        }])
        self.module.LINES.write_text('{"lines": [{"id": "vybor"}]}\n', encoding='utf-8')
        self.module.INBOX.write_bytes(OLD_INBOX)
        self.module.CHECKS.write_bytes(OLD_CHECKS)
        self.source = self.root / 'bridge/outbox/transaction.kg.jsonl'
        write_jsonl(self.source, [valid_node(), valid_check()])
        self.ack_dir = self.root / 'bridge/ack'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.tmp.cleanup()

    def serve(self) -> tuple[int, dict, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = self.module.serve([self.source], self.ack_dir)
        ack_path = self.ack_dir / 'transaction-kg.json'
        ack = json.loads(ack_path.read_text(encoding='utf-8')) if ack_path.exists() else {}
        return rc, ack, stdout.getvalue() + stderr.getvalue()

    def backups(self) -> list[pathlib.Path]:
        root = self.root / '.coord/backups/kg-inbox'
        return sorted(path for path in root.glob('batch-*') if path.is_dir())

    def journal(self) -> list[dict]:
        path = self.root / '.coord/kg-inbox/transactions.jsonl'
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()
                if line.strip()]

    def committed(self) -> list[dict]:
        return [row for row in self.journal() if row.get('type') == 'committed']

    def projected_rows(self) -> tuple[list[dict], list[dict]]:
        return read_jsonl(self.module.INBOX), read_jsonl(self.module.CHECKS)


class KgTransactionIntegrity(unittest.TestCase):
    def assert_unknown(self, rc: int, ack: dict, output: str) -> None:
        self.assertNotEqual(rc, 0, output)
        self.assertEqual(ack.get('status'), 'unknown', output)
        self.assertEqual(ack.get('accepted'), 0, output)
        self.assertEqual(ack.get('rolled_back'), 0, output)
        self.assertTrue(ack.get('reasons'), output)
        self.assertNotIn('Traceback', output)

    def test_committed_projection_failure_recovers_once_on_retry(self) -> None:
        with Fixture() as fx:
            real_replace = fx.module.os.replace

            def fail_projections(src, dst):
                if pathlib.Path(dst) in (fx.module.INBOX, fx.module.CHECKS) \
                        and pathlib.Path(src).name.startswith(('.KG-INBOX.jsonl.tmp-',
                                                              '.KG-CHECKS.jsonl.tmp-')):
                    raise OSError('injected persistent projection failure')
                return real_replace(src, dst)

            # Ошибка применения и ошибка recovery не должны превращаться в processed.
            with mock.patch.object(fx.module.os, 'replace', side_effect=fail_projections):
                rc, ack, output = fx.serve()
                self.assert_unknown(rc, ack, output)
                self.assertEqual(len(fx.committed()), 1, output)
                self.assertEqual(fx.module.INBOX.read_bytes(), OLD_INBOX)
                self.assertEqual(fx.module.CHECKS.read_bytes(), OLD_CHECKS)
                self.assertFalse((fx.root / '.coord/kg-inbox/receipts').exists())
                backups = fx.backups()
                self.assertEqual(len(backups), 1, output)
                self.assertTrue(any(str(backups[0]) in reason for reason in ack['reasons']),
                                f'путь backup отсутствует в ошибке: {ack}')

                # Отдельно проверяет неуспешный recovery уже при начальном lookup.
                rc, ack, output = fx.serve()
                self.assert_unknown(rc, ack, output)
                self.assertEqual(len(fx.committed()), 1, output)
                self.assertEqual(len(fx.backups()), 1, output)

            # Retry не коммитит повторно и дописывает каждую строку ровно один раз.
            rc, ack, output = fx.serve()
            self.assertEqual(rc, 0, output)
            self.assertEqual(ack.get('status'), 'processed', output)
            self.assertEqual(ack.get('accepted'), 2, output)
            inbox, checks = fx.projected_rows()
            self.assertEqual(sum(row.get('kind') == 'node' for row in inbox), 1)
            self.assertEqual(sum(row.get('kind') == 'check' for row in checks), 1)
            self.assertEqual(len(fx.committed()), 1, output)
            self.assertEqual(fx.backups(), [], 'retry не очистил подтверждённый backup')
            receipt = fx.root / '.coord/kg-inbox/receipts' / f'{ack["request_hash"]}.json'
            self.assertTrue(receipt.is_file(), 'retry не сохранил receipt')

            before = (fx.module.INBOX.read_bytes(), fx.module.CHECKS.read_bytes())
            rc, ack, output = fx.serve()
            self.assertEqual(rc, 0, output)
            self.assertEqual(ack.get('status'), 'processed', output)
            self.assertEqual(before, (fx.module.INBOX.read_bytes(), fx.module.CHECKS.read_bytes()))
            self.assertEqual(len(fx.committed()), 1, 'повторный retry создал второй commit')

    def test_success_cleans_backup_after_receipt(self) -> None:
        with Fixture() as fx:
            rc, ack, output = fx.serve()
            self.assertEqual(rc, 0, output)
            self.assertEqual(ack.get('status'), 'processed', output)
            self.assertEqual(ack.get('accepted'), 2, output)
            self.assertEqual(fx.backups(), [], 'успешная партия оставила backup')
            receipt = fx.root / '.coord/kg-inbox/receipts' / f'{ack["request_hash"]}.json'
            self.assertTrue(receipt.is_file(), 'успешная партия не сохранила receipt')
            self.assertEqual(len(fx.committed()), 1, output)

    def test_receipt_failure_preserves_backup_until_retry(self) -> None:
        with Fixture() as fx:
            with mock.patch.object(fx.module, '_save_receipt',
                                   side_effect=OSError('injected receipt failure')):
                rc, ack, output = fx.serve()
                self.assert_unknown(rc, ack, output)
                backups = fx.backups()
                self.assertEqual(len(backups), 1, output)
                self.assertTrue(any(str(backups[0]) in reason for reason in ack['reasons']), ack)
                inbox, checks = fx.projected_rows()
                self.assertEqual(sum(row.get('kind') == 'node' for row in inbox), 1)
                self.assertEqual(sum(row.get('kind') == 'check' for row in checks), 1)

            before = (fx.module.INBOX.read_bytes(), fx.module.CHECKS.read_bytes())
            rc, ack, output = fx.serve()
            self.assertEqual(rc, 0, output)
            self.assertEqual(ack.get('status'), 'processed', output)
            self.assertEqual(before, (fx.module.INBOX.read_bytes(), fx.module.CHECKS.read_bytes()))
            self.assertEqual(fx.backups(), [], 'retry не очистил backup после сохранения receipt')
            self.assertEqual(len(fx.committed()), 1, output)

    def test_rollback_failure_preserves_backup_until_retry(self) -> None:
        with Fixture() as fx:
            real_replace = fx.module.os.replace
            checks_failed = False
            rollback_failed = False

            def fail_second_queue_and_rollback(src, dst):
                nonlocal checks_failed, rollback_failed
                src, dst = pathlib.Path(src), pathlib.Path(dst)
                if dst == fx.module.CHECKS and src.name.startswith('.KG-CHECKS.jsonl.tmp-') \
                        and not checks_failed:
                    checks_failed = True
                    raise OSError('injected second-queue failure')
                if dst == fx.module.INBOX and checks_failed and not rollback_failed:
                    rollback_failed = True
                    raise OSError('injected rollback failure')
                return real_replace(src, dst)

            updates = [(fx.module.INBOX, [{'kind': 'node'}]),
                       (fx.module.CHECKS, [{'kind': 'check'}])]
            kwargs = {'request_hash': 'fixture-rollback-request', 'receipts': []}
            with mock.patch.object(fx.module.os, 'replace',
                                   side_effect=fail_second_queue_and_rollback):
                with self.assertRaises(fx.module.ProjectionError) as caught:
                    fx.module.append_transaction(updates, **kwargs)
            message = str(caught.exception)
            backups = fx.backups()
            self.assertEqual(len(backups), 1, message)
            self.assertIn(str(backups[0]), message)
            self.assertIn('rollback', message)
            self.assertEqual((backups[0] / '0-KG-INBOX.jsonl').read_bytes(), OLD_INBOX)
            self.assertEqual((backups[0] / '1-KG-CHECKS.jsonl').read_bytes(), OLD_CHECKS)

            transaction = fx.module.append_transaction(updates, **kwargs)
            inbox, checks = fx.projected_rows()
            self.assertEqual(sum(row.get('kind') == 'node' for row in inbox), 1)
            self.assertEqual(sum(row.get('kind') == 'check' for row in checks), 1)
            self.assertEqual(len(fx.committed()), 1)
            self.assertEqual(fx.backups(), [], 'retry не очистил backup после rollback failure')

    def test_committed_kg_nonzero_never_becomes_bridge_rejected(self) -> None:
        """Межфайловая граница: nonzero kg_inbox после commit — unknown, не reject."""
        with Fixture() as fx:
            real_replace = fx.module.os.replace

            def fail_projections(src, dst):
                if pathlib.Path(dst) in (fx.module.INBOX, fx.module.CHECKS):
                    raise OSError('injected bridge projection failure')
                return real_replace(src, dst)

            with mock.patch.object(fx.module.os, 'replace', side_effect=fail_projections):
                rc, ack, output = fx.serve()
            self.assert_unknown(rc, ack, output)
            self.assertEqual(len(fx.committed()), 1, output)

            bridge_path = ROOT / 'tools/win_bridge.py'
            spec = importlib.util.spec_from_file_location('fixture_win_bridge', bridge_path)
            bridge = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(bridge)
            bridge.ROOT = fx.root
            bridge.BRIDGE = fx.root / 'bridge'
            self.assertTrue(bridge.kg_request_committed(fx.source), 'commit не распознан мостом')

            bridge.begin_attempt('kg', 'batch', ['fixture-kg-inbox'], [fx.source],
                                 {'source_rows': 0, 'inbox': [], 'checks': []},
                                 spawns_group=False)
            rejected, unknown, archived = [], [], []
            bridge.reject_atoms = lambda *args, **kwargs: rejected.append((args, kwargs))

            def record_unknown(receipt, file, reason, **kwargs):
                unknown.append(reason)
                receipt.update(status='unknown', result={'status': 'unknown'})
                receipt.setdefault('attempts', [{}])[-1].update(
                    {'status': 'unknown', 'outcome': 'unknown', 'rollback': 'unknown'})
                bridge.write_receipt(receipt)
                return receipt['result']

            original_begin_attempt = bridge.begin_attempt
            fixture_receipt = None

            def tracked_begin_attempt(*args, **kwargs):
                nonlocal fixture_receipt
                fixture_receipt = original_begin_attempt(*args, **kwargs)
                fixture_receipt['attempts'][-1]['group_stopped'] = False
                bridge.write_receipt(fixture_receipt)
                return fixture_receipt

            bridge.begin_attempt = tracked_begin_attempt
            bridge.mark_unknown = record_unknown
            bridge.archive_files = lambda *args, **kwargs: archived.append((args, kwargs))
            with mock.patch.object(bridge, 'run_isolated', return_value=mock.Mock(
                                   returncode=1, stdout='', stderr='projection recovery failed')), \
                    mock.patch.object(bridge, 'record_group_stopped'), \
                    mock.patch.object(bridge, 'receipt_group_alive', return_value=False), \
                    mock.patch.object(bridge, 'process_group_alive', return_value=False):
                bridge.process_kg('batch', fx.source)

            self.assertIsNotNone(fixture_receipt, 'process_kg не начал попытку')
            self.assertEqual(fixture_receipt['status'], 'unknown')

            self.assertFalse(rejected, 'committed KG ошибочно отправлен в rejected')
            self.assertFalse(archived, 'committed KG ошибочно архивирован как rejected')
            self.assertTrue(unknown, 'committed KG не оставлен в unknown')
            self.assertTrue(fx.source.exists(), 'исходник committed KG удалён')
            self.assertEqual(len(fx.committed()), 1, 'retry создал второй commit')


if __name__ == '__main__':
    unittest.main(verbosity=2)
