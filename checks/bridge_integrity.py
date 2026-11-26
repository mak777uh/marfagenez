#!/usr/bin/env python3
"""Изолированные regression-тесты crash/recovery контрактов обоих мостов.

Все таблицы, receipts, ack и journal живут в TemporaryDirectory. Боевой репозиторий,
живые мосты и watcher-процессы не читаются и не изменяются.
Запуск: python3 checks/bridge_integrity.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def load_tool(root: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(f'fixture_{name}_{id(root)}', root / 'tools' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_atom() -> dict:
    return {
        'atom': 'BASE-1',
        'statement': 'Базовое измерение fixture: значения 10 и 20, а также 1.25 ± 0.05 единицы в таблице 1.',
        'domain': 'fixture.domain',
        'kind': 'measurement',
        'works': [{'doi': '10.0000/fixture-base', 'locator': 'Table 1', 'quote': 'fixture base quote'}],
        'confidence': 'low',
    }


def win_atom(atom_id: str = 'WIN-001') -> dict:
    return {
        'atom': atom_id,
        'statement': 'Fixture measurement reports 2.50 ± 0.10 units in Table 2 for the stated condition.',
        'domain': 'fixture.domain',
        'kind': 'measurement',
        'confidence': 'low',
        'works': [{
            'doi': '10.0000/fixture-win',
            'locator': 'Table 2',
            'quote': 'Fixture measurement reports 2.50 ± 0.10 units.',
        }],
        'kg_ref': ['L-001'],
    }


def win_edge(atom_id: str = 'WIN-001') -> dict:
    return {'from': atom_id, 'to': 'BASE-1', 'type': 'refines', 'note': 'fixture link'}


class Fixture:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bridge-integrity-')
        self.root = pathlib.Path(self.tmp.name)
        for name in ('win_bridge.py', 'probe_bridge.py'):
            target = self.root / 'tools' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / 'tools' / name, target)
        self.map = self.root / 'literature' / 'map'
        self.inbox = self.map / 'inbox'
        self.bridge = self.root / 'bridge'
        self.outbox = self.bridge / 'outbox'
        self.ack = self.bridge / 'ack'
        for path in (self.map, self.inbox, self.outbox, self.ack, self.root / 'docs'):
            path.mkdir(parents=True, exist_ok=True)
        self.atoms = self.map / 'atoms.jsonl'
        self.edges = self.map / 'edges.jsonl'
        write_jsonl(self.atoms, [base_atom()])
        write_jsonl(self.edges, [{'from': 'BASE-1', 'to': 'BASE-1', 'type': 'requires'}])
        self.win = load_tool(self.root, 'win_bridge.py')
        self.win.configure_bridge(self.bridge)
        self.probe = load_tool(self.root, 'probe_bridge.py')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.tmp.cleanup()

    def pair(self, batch: str = 'case', atom_id: str = 'WIN-001') -> tuple[pathlib.Path, pathlib.Path]:
        atoms = self.outbox / f'{batch}.atoms.jsonl'
        edges = self.outbox / f'{batch}.edges.jsonl'
        write_jsonl(atoms, [win_atom(atom_id)])
        write_jsonl(edges, [win_edge(atom_id)])
        return atoms, edges

    def read_ack(self, batch: str = 'case') -> dict:
        return json.loads((self.ack / f'{batch}.json').read_text(encoding='utf-8'))


def completed(cmd: list[str], rc: int, output: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(cmd, rc, output, '')


class WinBridgeIntegrity(unittest.TestCase):
    def test_nonzero_partial_map_is_unknown_and_source_is_not_archived(self) -> None:
        with Fixture() as fx:
            atoms, edges = fx.pair()
            calls = []

            def partial_ingest(cmd, *, timeout, on_start):
                calls.append(cmd)
                on_start(2 ** 30)  # заведомо отсутствующая POSIX process group
                write_jsonl(fx.atoms, read_jsonl(fx.atoms) + [win_atom()])
                return completed(cmd, 1, 'принято 1 из 1\nОТКАТ НЕ ВЫПОЛНЕН: restore failed\n')

            with mock.patch.object(fx.win, 'run_isolated', side_effect=partial_ingest):
                fx.win.process_atoms('case', atoms, edges, fx.win.load_known())
                fx.win.process_atoms('case', atoms, edges, fx.win.load_known())

            self.assertEqual(len(calls), 1, 'частичная карта разрешила опасный повтор')
            ack = fx.read_ack()
            self.assertEqual(ack['status'], 'unknown')
            self.assertNotIn('not applied', json.dumps(ack).lower())
            self.assertNotIn('карта откачена', ' '.join(ack['reasons']))
            self.assertEqual(atoms.read_bytes(), (fx.outbox / atoms.name).read_bytes())
            self.assertTrue(edges.exists(), 'edges частичной партии удалены')
            self.assertFalse((fx.bridge / 'rejected' / 'case').exists())
            self.assertFalse((fx.bridge / 'processed' / 'case').exists())
            receipt = fx.win.load_receipt('atoms', 'case')
            self.assertEqual(receipt['status'], 'unknown')
            self.assertEqual(receipt['rollback'], 'unknown')

    def test_nonzero_fully_applied_map_is_processed_without_duplicate_ingest(self) -> None:
        with Fixture() as fx:
            atoms, edges = fx.pair('complete')
            calls = []

            def full_ingest(cmd, *, timeout, on_start):
                calls.append(cmd)
                on_start(2 ** 30)
                write_jsonl(fx.atoms, read_jsonl(fx.atoms) + [win_atom()])
                write_jsonl(fx.edges, read_jsonl(fx.edges) + [win_edge()])
                return completed(cmd, 1, 'ОТКАТ НЕ ВЫПОЛНЕН: restore failed\n')

            with mock.patch.object(fx.win, 'run_isolated', side_effect=full_ingest):
                fx.win.process_atoms('complete', atoms, edges, fx.win.load_known())
            self.assertEqual(len(calls), 1)
            self.assertEqual(fx.read_ack('complete')['status'], 'processed')
            self.assertFalse(atoms.exists())
            self.assertFalse(edges.exists())
            self.assertTrue((fx.bridge / 'processed' / 'complete' / atoms.name).is_file())
            self.assertEqual(len(read_jsonl(fx.atoms)), 2)
            self.assertEqual(len(read_jsonl(fx.edges)), 2)

    def test_questions_crash_after_copy_retries_without_second_copy(self) -> None:
        with Fixture() as fx:
            source = fx.outbox / 'questions.questions.jsonl'
            payload = b'{"question":"fixture?"}\n'
            source.write_bytes(payload)
            target = fx.inbox / 'win-questions.jsonl'
            with mock.patch.object(fx.win, 'atomic_copy', wraps=fx.win.atomic_copy) as copy_mock, \
                    mock.patch.object(fx.win, 'archive_files', side_effect=RuntimeError('crash before archive')):
                fx.win.process_questions('questions', source)
            self.assertEqual(copy_mock.call_count, 1)
            self.assertEqual(target.read_bytes(), payload)
            self.assertTrue(source.exists())
            self.assertEqual(fx.read_ack('questions')['status'], 'unknown')
            self.assertEqual(fx.win.load_receipt('questions', 'questions')['outcome'], 'applied')

            with mock.patch.object(fx.win, 'atomic_copy', wraps=fx.win.atomic_copy) as retry_copy, \
                    mock.patch.object(fx.win, 'archive_files', wraps=fx.win.archive_files) as archive_mock:
                fx.win.process_questions('questions', source)
            target_copies = [call for call in retry_copy.call_args_list if call.args[1] == target]
            self.assertEqual(len(target_copies), 0, 'retry повторно скопировал questions в target')
            self.assertEqual(archive_mock.call_count, 1)
            self.assertEqual(fx.read_ack('questions')['status'], 'processed')
            self.assertFalse(source.exists())
            archived = fx.bridge / 'processed' / 'questions' / source.name
            self.assertEqual(archived.read_bytes(), payload)
            self.assertEqual(len(list(fx.inbox.glob('win-questions*.jsonl'))), 1)

    def test_unknown_attempt_without_pgid_is_not_retried(self) -> None:
        with Fixture() as fx:
            atoms, edges = fx.pair('blocked')
            expected = fx.win.atoms_expected([win_atom()], edges, set())
            receipt = fx.win.begin_attempt(
                'atoms', 'blocked', [sys.executable, 'tools/ingest_safe.py'], [atoms, edges], expected,
                baseline=fx.win.map_baseline(),
            )
            self.assertNotIn('pgid', receipt['attempts'][-1])
            self.assertTrue(fx.win.receipt_group_alive(receipt))
            fx.win.record_group_stopped(receipt)
            self.assertIsNot(receipt['attempts'][-1].get('group_stopped'), True)

            with mock.patch.object(fx.win, 'run_isolated') as run_mock:
                fx.win.process_atoms('blocked', atoms, edges, fx.win.load_known())
            run_mock.assert_not_called()
            self.assertEqual(fx.read_ack('blocked')['status'], 'unknown')
            self.assertTrue(atoms.exists() and edges.exists())
            saved = fx.win.load_receipt('atoms', 'blocked')
            self.assertEqual(len(saved['attempts']), 1)
            self.assertFalse(saved['attempts'][-1].get('group_stopped'))

    def test_source_mismatch_does_not_overwrite_finalized_receipt(self) -> None:
        with Fixture() as fx:
            atoms, edges = fx.pair('mismatch')
            receipt = fx.win.begin_attempt(
                'atoms', 'mismatch', [], [atoms, edges], {'validation_rejected': True}, spawns_group=False,
            )
            result = fx.win.make_result(atoms.name, 'rejected', accepted=0, rejected=1,
                                        reasons=['fixture finalized receipt'])
            fx.win.finalize_receipt(receipt, 'rejected', 'not applied', result)
            receipt_path = fx.win.receipt_path('atoms', 'mismatch')
            before = receipt_path.read_bytes()
            write_jsonl(atoms, [win_atom('WIN-CHANGED')])
            changed = atoms.read_bytes()

            with mock.patch.object(fx.win, 'run_isolated') as run_mock:
                fx.win.process_atoms('mismatch', atoms, edges, fx.win.load_known())
            run_mock.assert_not_called()
            self.assertEqual(fx.read_ack('mismatch')['status'], 'unknown')
            self.assertEqual(atoms.read_bytes(), changed)
            self.assertEqual(receipt_path.read_bytes(), before, 'finalized receipt перезаписан')
            self.assertFalse((fx.bridge / 'rejected' / 'mismatch').exists())

    def test_tmp_pair_requires_ready_marker(self) -> None:
        with Fixture() as fx:
            atoms = fx.outbox / 'ready-case.atoms.tmp'
            edges = fx.outbox / 'ready-case.edges.tmp'
            marker = fx.outbox / 'ready-case.ready'
            write_jsonl(atoms, [win_atom('WIN-READY')])
            write_jsonl(edges, [win_edge('WIN-READY')])
            fx.win.promote_temps(fx.outbox)
            self.assertTrue(atoms.exists() and edges.exists())
            self.assertFalse((fx.outbox / 'ready-case.atoms.jsonl').exists())
            self.assertFalse((fx.outbox / 'ready-case.edges.jsonl').exists())

            temporary = fx.outbox / '.ready-case.ready.tmp'
            temporary.write_bytes(b'')
            os.replace(temporary, marker)
            fx.win.promote_temps(fx.outbox)
            self.assertFalse(atoms.exists() and edges.exists())
            self.assertTrue((fx.outbox / 'ready-case.atoms.jsonl').is_file())
            self.assertTrue((fx.outbox / 'ready-case.edges.jsonl').is_file())
            self.assertFalse(marker.exists(), 'использованный marker не удалён')

    def test_validation_reject_has_durable_receipt_before_archive(self) -> None:
        with Fixture() as fx:
            atoms, edges = fx.pair('invalid')
            write_jsonl(atoms, [{'atom': 'BAD'}])
            seen = []

            def fail_archive(paths, status, batch):
                seen.append(fx.win.load_receipt('atoms', batch))
                raise RuntimeError('crash before rejected archive')

            with mock.patch.object(fx.win, 'archive_files', side_effect=fail_archive):
                fx.win.process_atoms('invalid', atoms, edges, set())
            self.assertEqual(len(seen), 1)
            self.assertEqual(seen[0]['status'], 'rejected')
            self.assertEqual(seen[0]['outcome'], 'not applied')
            self.assertTrue(atoms.exists() and edges.exists())
            self.assertEqual(fx.read_ack('invalid')['status'], 'unknown')


class ProbeBridgeIntegrity(unittest.TestCase):
    def question(self, kind: str = 'numbers', verifiable: str = 'Recalculate both values.') -> dict:
        q = {
            'question': 'Why are the fixture values 10 and 20 different?',
            'atoms': ['BASE-1'], 'kind': kind, 'numbers': [10, 20], 'verifiable': verifiable,
        }
        if kind == 'units':
            q['recalc'] = 'Convert both values to the same unit.'
        return q

    def test_same_source_and_text_with_different_kind_has_two_events(self) -> None:
        with Fixture() as fx:
            for name in ('request', 'outbox', 'ack', 'done'):
                (fx.bridge / name).mkdir(exist_ok=True)
            source = fx.bridge / 'outbox' / 'same.jsonl'
            first = self.question('numbers')
            second = self.question('units')
            write_jsonl(source, [first])
            self.assertEqual(fx.probe.serve(fx.bridge), 0)
            journal_path = fx.root / 'docs' / 'PROBE-VERDICTS.jsonl'
            events = read_jsonl(journal_path)
            self.assertEqual(len(events), 1)
            self.assertEqual(_probe_ack(fx.bridge, 'same')['accepted'], 1)

            write_jsonl(source, [second])
            self.assertEqual(fx.probe.serve(fx.bridge), 0)
            events = read_jsonl(journal_path)
            self.assertEqual(len(events), 2, 'другой kind потерян из-за hash текста')
            self.assertEqual({event['kind'] for event in events}, {'numbers', 'units'})
            self.assertEqual(len({event['hash'] for event in events}), 2)
            self.assertEqual({event['source'] for event in events}, {'same.jsonl'})
            self.assertEqual(_probe_ack(fx.bridge, 'same')['accepted'], 1)
            self.assertEqual(len(list(fx.inbox.glob('probe-same-*.jsonl'))), 2)

            # Тот же kind и текст, но другой payload также являются новым event.
            third = self.question('numbers', verifiable='Use an independent recalculation.')
            write_jsonl(source, [third])
            self.assertEqual(fx.probe.serve(fx.bridge), 0)
            self.assertEqual(len(read_jsonl(journal_path)), 3)

    def test_legacy_text_hash_is_readable_without_hiding_new_payload(self) -> None:
        with Fixture() as fx:
            for name in ('request', 'outbox', 'ack', 'done'):
                (fx.bridge / name).mkdir(exist_ok=True)
            old = self.question('numbers')
            normalized = re.sub(r'\s+', ' ', old['question'].strip().lower())
            old_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
            journal_path = fx.root / 'docs' / 'PROBE-VERDICTS.jsonl'
            old_event = {
                'type': 'question', 'source': 'old.jsonl', 'hash': old_hash,
                'kind': old['kind'], 'question': old['question'], 'atoms': old['atoms'],
                'numbers': old['numbers'], 'payload': old,
            }
            write_jsonl(journal_path, [old_event])
            write_jsonl(fx.bridge / 'outbox' / 'exact.jsonl', [old])
            self.assertEqual(fx.probe.serve(fx.bridge), 0)
            duplicate = json.loads((fx.bridge / 'ack' / 'exact.json').read_text(encoding='utf-8'))
            self.assertEqual(duplicate['accepted'], 0)
            self.assertEqual(len(read_jsonl(journal_path)), 1)

            write_jsonl(fx.bridge / 'outbox' / 'new-kind.jsonl', [self.question('units')])
            self.assertEqual(fx.probe.serve(fx.bridge), 0)
            accepted = json.loads((fx.bridge / 'ack' / 'new-kind.json').read_text(encoding='utf-8'))
            self.assertEqual(accepted['accepted'], 1)
            self.assertEqual(len(read_jsonl(journal_path)), 2)


# Помогает не повторять путь к ack в тестах probe.
def _probe_ack(bridge: pathlib.Path, stem: str) -> dict:
    return json.loads((bridge / 'ack' / f'{stem}.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
