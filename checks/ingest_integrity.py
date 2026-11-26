"""Самодостаточные проверки транзакционного приёма карты и Windows-моста.

Все данные создаются во временном fixture-repo; боевые literature/, docs/, kg/ и C:\\111\\graph-bridge
не читаются и не изменяются. Запуск: python3 checks/ingest_integrity.py
"""

from __future__ import annotations

import contextlib
import fcntl
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
COPY_FILES = (
    'tools/map_ingest.py',
    'tools/ingest_safe.py',
    'tools/win_bridge.py',
    'tools/coord.py',
    'tools/kg_inbox.py',
    'tools/map_orphans.py',
    'tools/map_duplicates.py',
    'checks/map_contract.py',
    'checks/stitch_coverage_floor.py',
)
ACK_KEYS = {'file', 'status', 'accepted', 'rejected', 'reasons', 'ingest'}


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def base_atom() -> dict:
    return {
        'atom': 'BASE-1',
        'statement': 'Базовое измерение fixture: 1.25 ± 0.05 единицы в таблице 1.',
        'domain': 'fixture.domain',
        'kind': 'measurement',
        'works': [{'doi': '10.0000/fixture-base', 'locator': 'Table 1', 'quote': 'fixture base quote'}],
        'confidence': 'low',
    }


def win_atom(atom_id: str = 'WIN-001', **overrides) -> dict:
    row = {
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
    row.update(overrides)
    return row


def win_edge(atom_id: str = 'WIN-001') -> dict:
    return {'from': atom_id, 'to': 'BASE-1', 'type': 'refines', 'note': 'fixture link to the base cell'}


class Fixture:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ingest-integrity-')
        self.root = pathlib.Path(self.tmp.name)
        for rel in COPY_FILES:
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        self.map = self.root / 'literature/map'
        self.bridge = self.root / 'bridge'
        self.outbox = self.bridge / 'outbox'
        self.ack = self.bridge / 'ack'
        for path in (self.map, self.outbox, self.ack, self.root / 'docs', self.root / 'scratch'):
            path.mkdir(parents=True, exist_ok=True)
        self.atoms = self.map / 'atoms.jsonl'
        self.edges = self.map / 'edges.jsonl'
        write_jsonl(self.atoms, [base_atom()])
        write_jsonl(self.edges, [{'from': 'BASE-1', 'to': 'BASE-1', 'type': 'requires'}])
        (self.root / 'docs/MAP-ORPHANS-BASELINE.json').write_text('{"orphans": 0}\n', encoding='utf-8')
        (self.root / 'docs/STITCH-COVERAGE-FLOOR.json').write_text(
            '{"s_pairs": 0, "s_nodes": 0}\n', encoding='utf-8',
        )
        (self.root / 'docs/MAP-DUPLICATES.json').write_text('{}\n', encoding='utf-8')
        (self.root / 'docs/AUTONOMOUS-PLAN.md').write_text('fixture plan\n', encoding='utf-8')
        (self.root / 'docs/UNITS-CONVENTIONS.md').write_text('fixture units\n', encoding='utf-8')
        curl = self.root / 'fake-curl'
        curl.write_text(
            '#!/usr/bin/env python3\n'
            'import json, time\n'
            'time.sleep(0.25)\n'
            'print(json.dumps({"id": "https://openalex.org/W1", "title": "Fixture work", '
            '"publication_year": 2026, "abstract_inverted_index": {}}))\n',
            encoding='utf-8',
        )
        curl.chmod(0o755)
        self.env = os.environ.copy()
        self.env['LITSEARCH_CURL'] = str(curl)
        self.env['LITSEARCH_KEY'] = str(self.root / 'missing-openalex-key')
        self.env['PYTHONDONTWRITEBYTECODE'] = '1'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.tmp.cleanup()

    def run(self, script: str, *args: str, timeout: int = 90) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.root / script), *map(str, args)],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=timeout,
        )

    def serve(self, timeout: int = 90) -> subprocess.CompletedProcess:
        return self.run('tools/win_bridge.py', '--bridge', self.bridge, '--serve', timeout=timeout)

    def snapshot(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob('*') if path.is_file()
        }


def output(proc: subprocess.CompletedProcess) -> str:
    return (proc.stdout or '') + (proc.stderr or '')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_rc(proc: subprocess.CompletedProcess, expected: int = 0) -> None:
    require(proc.returncode == expected,
            f'ожидали rc={expected}, получили rc={proc.returncode}\n{output(proc)[-3000:]}')
    require('Traceback' not in output(proc), f'неконтролируемое исключение:\n{output(proc)[-3000:]}')


def map_bytes(fx: Fixture) -> tuple[bytes, bytes]:
    return fx.atoms.read_bytes(), fx.edges.read_bytes()


def test_orphan_failure_preserves_bytes() -> None:
    with Fixture() as fx:
        # Нестандартное форматирование и отсутствие завершающего перевода строки ловят старую запись edges.
        fx.atoms.write_bytes(fx.atoms.read_bytes().rstrip(b'\n'))
        fx.edges.write_bytes(b'{ "from" : "BASE-1", "to" : "BASE-1", "type" : "requires" }')
        before = map_bytes(fx)
        incoming = fx.root / 'orphan.atoms.jsonl'
        duplicate_edge = fx.root / 'duplicate.edges.jsonl'
        report = fx.root / 'reports/orphan.md'
        write_jsonl(incoming, [win_atom('WIN-ORPHAN')])
        write_jsonl(duplicate_edge, [{'from': 'BASE-1', 'to': 'BASE-1', 'type': 'requires'}])
        proc = fx.run('tools/map_ingest.py', incoming, '--edges', duplicate_edge, '--report', report)
        require_rc(proc, 1)
        require('ОТКАЗ' in output(proc) and 'без единой связи' in output(proc), output(proc))
        require(map_bytes(fx) == before, 'orphan failure изменил байты atoms или edges')
        require(not report.exists(), 'orphan failure записал отчёт')


def test_dry_run_writes_nothing() -> None:
    with Fixture() as fx:
        incoming = fx.root / 'dry.atoms.jsonl'
        edges = fx.root / 'dry.edges.jsonl'
        report = fx.root / 'reports/dry.md'
        write_jsonl(incoming, [win_atom('WIN-DRY')])
        write_jsonl(edges, [win_edge('WIN-DRY')])
        for with_report in (False, True):
            before = fx.snapshot()
            args = [incoming, '--edges', edges]
            if with_report:
                args += ['--report', report]
            args += ['--dry-run']
            proc = fx.run('tools/map_ingest.py', *args)
            require_rc(proc)
            require(fx.snapshot() == before, 'dry-run создал или изменил файл, включая отчёт')
            require(not report.exists(), 'dry-run создал отчёт')


def test_claim_is_accepted() -> None:
    with Fixture() as fx:
        incoming = fx.root / 'claim.atoms.jsonl'
        edges = fx.root / 'claim.edges.jsonl'
        write_jsonl(incoming, [win_atom('WIN-CLAIM', kind='claim')])
        write_jsonl(edges, [win_edge('WIN-CLAIM')])
        proc = fx.run('tools/ingest_safe.py', incoming, '--edges', edges, '--agent', 'main')
        require_rc(proc)
        rows = read_jsonl(fx.atoms)
        require([row['atom'] for row in rows].count('WIN-CLAIM') == 1, 'claim не попал в карту ровно один раз')
        require(next(row for row in rows if row['atom'] == 'WIN-CLAIM')['kind'] == 'claim', 'kind claim изменён')
        require_rc(fx.run('checks/map_contract.py'))


def test_non_object_json_is_controlled() -> None:
    with Fixture() as fx:
        before = map_bytes(fx)
        for index, payload in enumerate(('[]\n', '42\n', 'null\n', '"text"\n', '{"atom":\n')):
            incoming = fx.root / f'non-object-{index}.jsonl'
            incoming.write_text(payload, encoding='utf-8')
            proc = fx.run('tools/map_ingest.py', incoming)
            require(proc.returncode != 0, f'некорректный вход {payload!r} вернул успех')
            require('Traceback' not in output(proc), f'AttributeError/трассировка на {payload!r}: {output(proc)}')
            require('ОШИБКА' in output(proc), f'нет контролируемого отказа для {payload!r}: {output(proc)}')
            require(map_bytes(fx) == before, f'вход {payload!r} изменил карту')


def test_missing_flag_values_are_controlled() -> None:
    with Fixture() as fx:
        incoming = fx.root / 'flags.atoms.jsonl'
        write_jsonl(incoming, [win_atom('WIN-FLAGS')])
        before = fx.snapshot()
        for flag in ('--report', '--edges'):
            proc = fx.run('tools/map_ingest.py', incoming, flag)
            require(proc.returncode == 2, f'{flag} без значения: ожидали rc=2, получили {proc.returncode}')
            require('Traceback' not in output(proc), output(proc))
            require(fx.snapshot() == before, f'{flag} без значения что-то записал')


def test_map_cli_natural_order_and_repeated_edges() -> None:
    with Fixture() as fx:
        report_atoms = fx.root / 'report-order.atoms.jsonl'
        report_edges = fx.root / 'report-order.edges.jsonl'
        report = fx.root / 'reports/report-order.md'
        write_jsonl(report_atoms, [win_atom('WIN-REPORT-ORDER')])
        write_jsonl(report_edges, [win_edge('WIN-REPORT-ORDER')])
        proc = fx.run('tools/map_ingest.py', '--report', report, report_atoms, '--edges', report_edges)
        require_rc(proc)
        require(report.is_file(), '--report перед atoms не создал отчёт')
        require([r['atom'] for r in read_jsonl(fx.atoms)].count('WIN-REPORT-ORDER') == 1,
                '--report поглотил позиционный atoms-файл')

        first_atoms = fx.root / 'edges-order-1.atoms.jsonl'
        second_atoms = fx.root / 'edges-order-2.atoms.jsonl'
        first_edges = fx.root / 'edges-order-1.edges.jsonl'
        second_edges = fx.root / 'edges-order-2.edges.jsonl'
        write_jsonl(first_atoms, [win_atom('WIN-EDGES-ORDER-1')])
        write_jsonl(second_atoms, [win_atom('WIN-EDGES-ORDER-2')])
        write_jsonl(first_edges, [win_edge('WIN-EDGES-ORDER-1')])
        write_jsonl(second_edges, [win_edge('WIN-EDGES-ORDER-2')])
        proc = fx.run('tools/map_ingest.py', '--edges', first_edges, '--edges', second_edges,
                      '--', first_atoms, second_atoms)
        require_rc(proc)
        ids = {r['atom'] for r in read_jsonl(fx.atoms)}
        require({'WIN-EDGES-ORDER-1', 'WIN-EDGES-ORDER-2'} <= ids,
                'повторяемый --edges перед позиционными atoms потерял атомы')
        require(len(read_jsonl(fx.edges)) == 4, 'повторяемый --edges потерял одно из рёбер')


def test_map_cli_rejects_ambiguous_and_unknown_before_writing() -> None:
    with Fixture() as fx:
        incoming = fx.root / 'cli-errors.atoms.jsonl'
        edges = fx.root / 'cli-errors.edges.jsonl'
        write_jsonl(incoming, [win_atom('WIN-CLI-ERROR')])
        write_jsonl(edges, [win_edge('WIN-CLI-ERROR')])
        before = fx.snapshot()
        cases = (
            ('--report', fx.root / 'first.md', '--report', fx.root / 'second.md', incoming, '--edges', edges),
            (incoming, '--edges', edges, '--unknown'),
            (incoming, '--edges', edges, '--rep', fx.root / 'abbreviated.md'),
            (incoming, '--edges', edges, '--dry-run', '--dry-run'),
        )
        for args in cases:
            proc = fx.run('tools/map_ingest.py', *args)
            require(proc.returncode == 2, f'неоднозначный/неизвестный CLI вернул rc={proc.returncode}: {args}')
            require('Traceback' not in output(proc), output(proc))
            require(fx.snapshot() == before, f'ошибка CLI что-то записала: {args}')


def test_duplicates_and_conflicting_ids() -> None:
    with Fixture() as fx:
        incoming = fx.root / 'duplicates.atoms.jsonl'
        edges = fx.root / 'duplicates.edges.jsonl'
        row = win_atom('WIN-DUP')
        write_jsonl(incoming, [row, row])
        write_jsonl(edges, [win_edge('WIN-DUP')])
        proc = fx.run('tools/ingest_safe.py', incoming, '--edges', edges, '--agent', 'main')
        require_rc(proc)
        require([r['atom'] for r in read_jsonl(fx.atoms)].count('WIN-DUP') == 1,
                'точный дубль создал две ячейки')

    with Fixture() as fx:
        before = map_bytes(fx)
        incoming = fx.root / 'conflict.atoms.jsonl'
        write_jsonl(incoming, [win_atom('WIN-CONFLICT'), win_atom('WIN-CONFLICT', statement='Different statement ' + 'x' * 50)])
        proc = fx.run('tools/map_ingest.py', incoming, '--allow-orphans')
        require_rc(proc, 1)
        require('конфликт id' in output(proc), output(proc))
        require(map_bytes(fx) == before, 'конфликт id создал частичное состояние')


def test_second_write_failure_stays_pending_until_retry() -> None:
    """Сбой второй записи не теряет партию: durable txn остаётся pending,
    а recover_transactions() доводит atoms+edges до согласованной пары."""
    with Fixture() as fx:
        spec = importlib.util.spec_from_file_location('fixture_map_ingest_pending', fx.root / 'tools/map_ingest.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_apply = module.apply_prepared
        failed = False

        def fail_edges_once(item):
            nonlocal failed
            if pathlib.Path(item['path']) == module.EDGES and not failed:
                failed = True
                raise OSError('injected edges replace failure')
            return original_apply(item)

        module.apply_prepared = fail_edges_once
        try:
            try:
                module.commit_batch(
                    module.serialize([base_atom(), win_atom('WIN-PENDING')]),
                    module.serialize([{'from': 'BASE-1', 'to': 'BASE-1', 'type': 'requires'},
                                      win_edge('WIN-PENDING')]),
                )
            except OSError as exc:
                require('injected' in str(exc), f'неожиданная ошибка: {exc}')
            else:
                raise AssertionError('инъецированная ошибка второй записи не возникла')
        finally:
            module.apply_prepared = original_apply

        pending = [p for p in module.JOURNAL.glob('txn-*') if (p / 'manifest.json').exists()]
        require(len(pending) == 1, f'ожидалась одна pending-транзакция: {pending}')
        atoms_rows = read_jsonl(fx.atoms)
        edges_rows = read_jsonl(fx.edges)
        require(any(r.get('atom') == 'WIN-PENDING' for r in atoms_rows),
                'roll-forward не применил atoms до сбоя edges')
        require(not any(r.get('from') == 'WIN-PENDING' for r in edges_rows),
                'edges изменились до завершения транзакции')

        module.recover_transactions()
        require(not list(module.JOURNAL.glob('txn-*')), 'pending-транзакция не завершена retry')
        atoms_rows = read_jsonl(fx.atoms)
        edges_rows = read_jsonl(fx.edges)
        require(any(r.get('atom') == 'WIN-PENDING' for r in atoms_rows), 'retry потерял atoms')
        require(any(r.get('from') == 'WIN-PENDING' for r in edges_rows), 'retry потерял edges')
        require(not list(fx.map.glob('.*.tmp')), 'после retry остались временные файлы')


def test_report_backup_survives_pending_transaction() -> None:
    """Pre-existing отчёт копируется в txn-backup до commit; после retry
    отчёт содержит новые данные, а backup уходит вместе с txn_dir."""
    with Fixture() as fx:
        report = fx.root / 'docs/pending-report.md'
        report.write_bytes(b'report sentinel before\n')
        spec = importlib.util.spec_from_file_location('fixture_map_report_backup', fx.root / 'tools/map_ingest.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_apply = module.apply_prepared
        failed = False

        def fail_report_once(item):
            nonlocal failed
            if pathlib.Path(item['path']) == report.absolute() and not failed:
                failed = True
                raise OSError('injected report replace failure')
            return original_apply(item)

        module.apply_prepared = fail_report_once
        try:
            try:
                module.commit_batch(
                    module.serialize([base_atom(), win_atom('WIN-REPORT')]),
                    module.serialize([{'from': 'BASE-1', 'to': 'BASE-1', 'type': 'requires'},
                                      win_edge('WIN-REPORT')]),
                    report,
                    b'report sentinel after\n',
                )
            except OSError as exc:
                require('injected' in str(exc), f'неожиданная ошибка: {exc}')
            else:
                raise AssertionError('инъецированная ошибка записи отчёта не возникла')
        finally:
            module.apply_prepared = original_apply

        pending = [p for p in module.JOURNAL.glob('txn-*') if (p / 'manifest.json').exists()]
        require(len(pending) == 1, f'ожидалась одна pending-транзакция: {pending}')
        backups = [p for p in pending[0].iterdir() if p.name.startswith('backup-')]
        require(len(backups) == 1, f'ожидался один backup отчёта: {backups}')
        require(backups[0].read_bytes() == b'report sentinel before\n',
                'backup отчёта не содержит исходные байты')

        module.recover_transactions()
        require(report.read_bytes() == b'report sentinel after\n', 'retry не применил новый отчёт')
        require(not list(module.JOURNAL.glob('txn-*')), 'pending-транзакция не завершена retry')


def test_safe_contract_failure_rolls_back() -> None:
    with Fixture() as fx:
        before = map_bytes(fx)
        incoming = fx.root / 'medium.atoms.jsonl'
        edges = fx.root / 'medium.edges.jsonl'
        # map_ingest принимает medium, но map_contract требует conditions и должен вызвать откат ingest_safe.
        write_jsonl(incoming, [win_atom('WIN-MEDIUM', confidence='medium')])
        write_jsonl(edges, [win_edge('WIN-MEDIUM')])
        proc = fx.run('tools/ingest_safe.py', incoming, '--edges', edges, '--agent', 'main')
        require_rc(proc, 1)
        require('ОТКАТ' in output(proc), output(proc))
        require(map_bytes(fx) == before, 'contract failure не восстановил обе таблицы')
        backups = fx.root / '.coord/backups'
        require(not backups.exists() or not any(backups.iterdir()), 'после отката остался backup-мусор')


def test_non_main_report_outside_repo_is_rejected() -> None:
    with Fixture() as fx, tempfile.TemporaryDirectory(prefix='ingest-outside-') as outside_name:
        incoming = fx.map / 'inbox/fast-outside.jsonl'
        edges = fx.map / 'inbox/fast-outside-edges.jsonl'
        write_jsonl(incoming, [win_atom('WIN-OUTSIDE')])
        write_jsonl(edges, [win_edge('WIN-OUTSIDE')])
        outside = pathlib.Path(outside_name) / 'report.md'
        outside.write_bytes(b'outside sentinel\n')
        before = fx.snapshot()
        proc = fx.run('tools/ingest_safe.py', incoming, '--edges', edges, '--agent', 'fast', '--report', outside)
        require(proc.returncode != 0, 'не-main смог записать отчёт вне репозитория')
        require('Traceback' not in output(proc), output(proc))
        require(outside.read_bytes() == b'outside sentinel\n', 'отчёт вне репозитория перезаписан')
        require(fx.snapshot() == before, 'отказ по outside report изменил репозиторий')


def test_non_main_report_protected_and_map_files_are_rejected() -> None:
    with Fixture() as fx:
        incoming = fx.map / 'inbox/fast-protected.jsonl'
        edges = fx.map / 'inbox/fast-protected-edges.jsonl'
        write_jsonl(incoming, [win_atom('WIN-PROTECTED')])
        write_jsonl(edges, [win_edge('WIN-PROTECTED')])
        protected = fx.root / 'AGENTS.md'
        protected.write_bytes(b'protected sentinel\n')
        before = fx.snapshot()
        for report in (protected, fx.atoms, fx.edges, fx.root / 'tools/coord.py'):
            for agent in ('fast', 'main'):
                proc = fx.run('tools/ingest_safe.py', incoming, '--edges', edges, '--agent', agent, '--report', report)
                require(proc.returncode != 0, f'агент {agent} смог перезаписать защищённый путь {report}')
                require('Traceback' not in output(proc), output(proc))
                require(fx.snapshot() == before, f'отказ по {report} изменил репозиторий')


def test_non_main_report_symlink_escape_is_rejected() -> None:
    with Fixture() as fx, tempfile.TemporaryDirectory(prefix='ingest-symlink-') as outside_name:
        incoming = fx.map / 'inbox/fast-symlink.jsonl'
        edges = fx.map / 'inbox/fast-symlink-edges.jsonl'
        write_jsonl(incoming, [win_atom('WIN-SYMLINK')])
        write_jsonl(edges, [win_edge('WIN-SYMLINK')])
        outside = pathlib.Path(outside_name)
        target = outside / 'report.md'
        target.write_bytes(b'symlink sentinel\n')
        link = fx.root / 'docs/escape'
        link.symlink_to(outside, target_is_directory=True)
        before = map_bytes(fx)
        proc = fx.run('tools/ingest_safe.py', incoming, '--edges', edges, '--agent', 'fast',
                      '--report', link / 'report.md')
        require(proc.returncode != 0, 'symlink escape разрешил отчёт не-main вне репозитория')
        require('Traceback' not in output(proc), output(proc))
        require(target.read_bytes() == b'symlink sentinel\n', 'symlink escape перезаписал внешний отчёт')
        require(map_bytes(fx) == before, 'symlink escape изменил таблицы')


def test_safe_report_rolls_back_with_pair() -> None:
    with Fixture() as fx:
        incoming = fx.map / 'inbox/fast-report-rollback.jsonl'
        edges = fx.map / 'inbox/fast-report-rollback-edges.jsonl'
        report = fx.root / 'docs/DIP-fast-report-rollback.md'
        report.write_bytes(b'report sentinel\n')
        write_jsonl(incoming, [win_atom('WIN-REPORT-ROLLBACK', confidence='medium')])
        write_jsonl(edges, [win_edge('WIN-REPORT-ROLLBACK')])
        before = map_bytes(fx)
        proc = fx.run('tools/ingest_safe.py', incoming, '--edges', edges, '--agent', 'fast', '--report', report)
        require_rc(proc, 1)
        require('ОТКАТ' in output(proc), output(proc))
        require(map_bytes(fx) == before, 'contract failure не восстановил обе таблицы')
        require(report.read_bytes() == b'report sentinel\n', 'contract failure не восстановил отчёт')
        backups = fx.root / '.coord/backups'
        require(not backups.exists() or not any(backups.iterdir()), 'успешный откат оставил backup-мусор')


def test_safe_restore_failure_preserves_backup() -> None:
    with Fixture() as fx:
        incoming = fx.map / 'inbox/fast-restore-failure.jsonl'
        edges = fx.map / 'inbox/fast-restore-failure-edges.jsonl'
        report = fx.root / 'docs/DIP-fast-restore-failure.md'
        report.write_bytes(b'report backup sentinel\n')
        write_jsonl(incoming, [win_atom('WIN-RESTORE-FAILURE', confidence='medium')])
        write_jsonl(edges, [win_edge('WIN-RESTORE-FAILURE')])
        before = map_bytes(fx)
        spec = importlib.util.spec_from_file_location('fixture_ingest_safe_restore', fx.root / 'tools/ingest_safe.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        original_restore = module.atomic_restore
        original_run = module.run

        def fail_restore(path: pathlib.Path, saved: pathlib.Path | None) -> None:
            raise OSError(f'injected restore failure: {path.name}')

        def run_fixture(cmd: list[str]) -> tuple[int, str]:
            proc = subprocess.run(cmd, cwd=module.ROOT, env=fx.env, capture_output=True, text=True)
            return proc.returncode, ((proc.stdout or '') + (proc.stderr or '')).strip()

        module.atomic_restore = fail_restore
        module.run = run_fixture
        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                rc = module.main([str(incoming), '--edges', str(edges), '--agent', 'fast', '--report', str(report)])
        finally:
            module.atomic_restore = original_restore
            module.run = original_run
        text = captured.getvalue()
        require(rc != 0, 'неудачный restore вернул нулевой код')
        require('КРИТИЧНО' in text and 'Резервная копия сохранена:' in text, text)
        backups = list(module.BACKUPS.iterdir())
        require(len(backups) == 1, f'ожидали единственный сохранённый backup: {backups}')
        backup_dir = backups[0]
        require(str(backup_dir) in text, f'путь backup не напечатан: {text}')
        saved_atoms = next(backup_dir.glob('*-atoms.jsonl'))
        saved_edges = next(backup_dir.glob('*-edges.jsonl'))
        saved_report = next(backup_dir.glob('*-DIP-fast-restore-failure.md'))
        require(saved_atoms.read_bytes() == before[0], 'backup atoms потерян при неудачном restore')
        require(saved_edges.read_bytes() == before[1], 'backup edges потерян при неудачном restore')
        require(saved_report.read_bytes() == b'report backup sentinel\n', 'backup отчёта потерян при неудачном restore')


def test_safe_keyboard_interrupt_restores_report_and_pair() -> None:
    with Fixture() as fx:
        incoming = fx.map / 'inbox/fast-interrupt.jsonl'
        edges = fx.map / 'inbox/fast-interrupt-edges.jsonl'
        report = fx.root / 'docs/DIP-fast-interrupt.md'
        report.write_bytes(b'interrupt report sentinel\n')
        write_jsonl(incoming, [win_atom('WIN-INTERRUPT')])
        write_jsonl(edges, [win_edge('WIN-INTERRUPT')])
        before = map_bytes(fx)
        spec = importlib.util.spec_from_file_location('fixture_ingest_safe_interrupt', fx.root / 'tools/ingest_safe.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        original_run = module.run

        def interrupt_after_partial_write(cmd: list[str]) -> tuple[int, str]:
            if '--dry-run' in cmd:
                return 0, 'принято 1 из 1\nstatus: accepted'
            fx.atoms.write_bytes(b'partial atoms\n')
            fx.edges.write_bytes(b'partial edges\n')
            report.write_bytes(b'partial report\n')
            raise KeyboardInterrupt

        module.run = interrupt_after_partial_write
        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                rc = module.main([str(incoming), '--edges', str(edges), '--agent', 'fast', '--report', str(report)])
        finally:
            module.run = original_run
        require(rc == 130, f'KeyboardInterrupt вернул rc={rc}: {captured.getvalue()}')
        require('ОТКАТ' in captured.getvalue(), captured.getvalue())
        require(map_bytes(fx) == before, 'KeyboardInterrupt не восстановил таблицы')
        require(report.read_bytes() == b'interrupt report sentinel\n', 'KeyboardInterrupt не восстановил отчёт')
        backups = fx.root / '.coord/backups'
        require(not backups.exists() or not any(backups.iterdir()), 'успешный откат после interrupt оставил backup')


def test_safe_lock_waits_and_times_out() -> None:
    with Fixture() as fx:
        spec = importlib.util.spec_from_file_location('fixture_ingest_safe', fx.root / 'tools/ingest_safe.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        lock_path = module.LOCKS / 'map-ingest.lock'
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open('a+b') as holder:
            fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                try:
                    with module.lock(timeout=0.05):
                        raise AssertionError('замок получен, хотя его держит другой процесс')
                except TimeoutError:
                    pass
            finally:
                fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        require(lock_path.is_file(), 'flock-замок должен быть файлом, а не TTL-каталогом')
        with module.lock(timeout=0.05):
            pass


def test_safe_nonzero_without_contract_rolls_back() -> None:
    with Fixture() as fx:
        before = map_bytes(fx)
        incoming = fx.root / 'nonzero.atoms.jsonl'
        edges = fx.root / 'nonzero.edges.jsonl'
        write_jsonl(incoming, [win_atom('WIN-NONZERO')])
        write_jsonl(edges, [win_edge('WIN-NONZERO')])
        fake = fx.root / 'tools/map_ingest.py'
        fake.write_text(
            '#!/usr/bin/env python3\n'
            'import pathlib, sys\n'
            'root = pathlib.Path(__file__).resolve().parents[1]\n'
            'if "--dry-run" not in sys.argv:\n'
            '    (root / "literature/map/atoms.jsonl").write_text("partial atoms\\n", encoding="utf-8")\n'
            '    (root / "literature/map/edges.jsonl").write_text("partial edges\\n", encoding="utf-8")\n'
            '    print("принято 1 из 1")\n'
            '    print("status: accepted")\n'
            '    raise SystemExit(7)\n'
            'print("принято 1 из 1")\n'
            'print("status: accepted")\n',
            encoding='utf-8',
        )
        proc = fx.run('tools/ingest_safe.py', incoming, '--edges', edges, '--agent', 'main', '--no-contract')
        require_rc(proc, 7)
        require('ОТКАТ' in output(proc), output(proc))
        require(map_bytes(fx) == before, 'ненулевой код без contract не восстановил обе таблицы')


def test_safe_flock_serializes_two_ingests() -> None:
    with Fixture() as fx:
        inputs = []
        for atom_id in ('WIN-SAFE-A', 'WIN-SAFE-B'):
            atoms = fx.root / f'{atom_id}.atoms.jsonl'
            edges = fx.root / f'{atom_id}.edges.jsonl'
            write_jsonl(atoms, [win_atom(atom_id)])
            write_jsonl(edges, [win_edge(atom_id)])
            inputs.append((atoms, edges))
        command = [
            [sys.executable, str(fx.root / 'tools/ingest_safe.py'), str(atoms), '--edges', str(edges), '--agent', 'main']
            for atoms, edges in inputs
        ]
        procs = [subprocess.Popen(cmd, cwd=fx.root, env=fx.env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True) for cmd in command]
        results = []
        for proc in procs:
            stdout, stderr = proc.communicate(timeout=90)
            results.append((proc.returncode, stdout + stderr))
        require(all(rc == 0 for rc, _ in results), f'один из ingest_safe упал: {results}')
        ids = [row['atom'] for row in read_jsonl(fx.atoms)]
        require(ids.count('WIN-SAFE-A') == 1 and ids.count('WIN-SAFE-B') == 1,
                f'flock не сохранил обе партии: {ids}')
        require(len(read_jsonl(fx.edges)) == 3, 'flock потерял edge одной из партий')


def bridge_pair(fx: Fixture, batch: str = 'valid') -> tuple[pathlib.Path, pathlib.Path]:
    atoms = fx.outbox / f'{batch}.atoms.tmp'
    edges = fx.outbox / f'{batch}.edges.tmp'
    write_jsonl(atoms, [win_atom('WIN-VALID')])
    write_jsonl(edges, [win_edge('WIN-VALID')])
    (fx.outbox / f'{batch}.ready').write_bytes(b'ready\n')
    return atoms, edges


def test_bridge_correct_pair() -> None:
    with Fixture() as fx:
        atoms, edges = bridge_pair(fx)
        original_atoms, original_edges = atoms.read_bytes(), edges.read_bytes()
        proc = fx.serve()
        require_rc(proc)
        require([r['atom'] for r in read_jsonl(fx.atoms)].count('WIN-VALID') == 1, 'валидная пара не применена')
        require(len(read_jsonl(fx.edges)) == 2, 'edge валидной пары потерян')
        processed = fx.bridge / 'processed/valid'
        require((processed / 'valid.atoms.jsonl').read_bytes() == original_atoms, 'atoms не архивированы')
        require((processed / 'valid.edges.jsonl').read_bytes() == original_edges, 'edges не архивированы')
        require(not atoms.exists() and not edges.exists(), 'исходники остались в outbox после архива')
        require(not (fx.outbox / 'valid.atoms.jsonl').exists() and not (fx.outbox / 'valid.edges.jsonl').exists(),
                'финальные .jsonl остались в outbox')
        acks = list(fx.ack.glob('*.json'))
        require(len(acks) == 1, f'ожидали один ack, получили {[p.name for p in acks]}')
        ack = json.loads(acks[0].read_text(encoding='utf-8'))
        require(ACK_KEYS <= set(ack), f'неполный ack: {ack}')
        require(ack['status'] == 'processed' and ack['accepted'] == 1, f'неверный ack: {ack}')
        require('ingest_safe rc=0' in ack['ingest'], f'использован не ingest_safe: {ack}')
        require_rc(fx.run('checks/map_contract.py'))
        state = (fx.bridge / 'STATE.md').read_text(encoding='utf-8')
        require('пауза опроса 30 секунд; обработка может занять дольше' in state, 'STATE не объясняет задержку')
        require('.atoms.tmp' in state and 'rejected/<имя>/' in state, 'STATE не описывает tmp/rejected')
        require((fx.bridge / 'PLAN.md').read_text(encoding='utf-8') == 'fixture plan\n', 'PLAN не скопирован')
        require((fx.bridge / 'UNITS.md').read_text(encoding='utf-8') == 'fixture units\n', 'UNITS не скопирован')
        require(not list(fx.bridge.glob('.*.tmp')), 'атомарная запись оставила временные файлы')


def test_bridge_legacy_pair() -> None:
    with Fixture() as fx:
        atoms = fx.outbox / 'legacy.atoms.jsonl'
        edges = fx.outbox / 'legacy.edges.jsonl'
        write_jsonl(atoms, [win_atom('WIN-LEGACY')])
        write_jsonl(edges, [win_edge('WIN-LEGACY')])
        proc = fx.serve()
        require_rc(proc)
        require([r['atom'] for r in read_jsonl(fx.atoms)].count('WIN-LEGACY') == 1, 'legacy .jsonl не принят')
        require((fx.bridge / 'processed/legacy/legacy.edges.jsonl').exists(), 'legacy edges не архивированы')


def test_two_servers_process_pair_once() -> None:
    with Fixture() as fx:
        bridge_pair(fx, 'race')
        command = [sys.executable, str(fx.root / 'tools/win_bridge.py'), '--bridge', str(fx.bridge), '--serve']
        procs = [subprocess.Popen(command, cwd=fx.root, env=fx.env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True) for _ in range(2)]
        outputs = []
        for proc in procs:
            stdout, stderr = proc.communicate(timeout=90)
            outputs.append((proc.returncode, stdout + stderr))
        require(all(rc == 0 for rc, _ in outputs), f'один из watcher упал: {outputs}')
        require(any('пропуск' in out for _, out in outputs), f'второй watcher не пропустил занятый проход: {outputs}')
        require([r['atom'] for r in read_jsonl(fx.atoms)].count('WIN-VALID') == 1, 'гонка создала два атома')
        require(len(read_jsonl(fx.edges)) == 2, 'гонка потеряла или продублировала edge')
        require(len(list(fx.ack.glob('*.json'))) == 1, 'гонка создала больше одного ack')
        require(not any(fx.outbox.iterdir()), 'после гонки в outbox остались файлы')


def test_rejected_pair_keeps_atoms_and_edges() -> None:
    with Fixture() as fx:
        before = map_bytes(fx)
        bad = {
            'atom': 'BAD', 'statement': 'short', 'domain': '', 'kind': 'bogus', 'confidence': 0,
            'works': [{}], 'kg_ref': [],
        }
        atoms = fx.outbox / 'rejected-case.atoms.tmp'
        edges = fx.outbox / 'rejected-case.edges.tmp'
        write_jsonl(atoms, [bad])
        write_jsonl(edges, [win_edge('WIN-REJECTED')])
        (fx.outbox / 'rejected-case.ready').write_bytes(b'ready\n')
        original_atoms, original_edges = atoms.read_bytes(), edges.read_bytes()
        proc = fx.serve()
        require_rc(proc)
        require(map_bytes(fx) == before, 'отклонённая пара изменила карту')
        rejected = fx.bridge / 'rejected/rejected-case'
        require((rejected / 'rejected-case.atoms.jsonl').read_bytes() == original_atoms,
                'отклонённые atoms не сохранены в rejected')
        require((rejected / 'rejected-case.edges.jsonl').read_bytes() == original_edges,
                'edges отклонённой партии не сохранены в rejected')
        require(not atoms.exists() and not edges.exists(), 'отклонённая пара осталась в outbox')
        ack = json.loads((fx.ack / 'rejected-case.json').read_text(encoding='utf-8'))
        require(ACK_KEYS <= set(ack), f'неполный ack: {ack}')
        require(ack['status'] == 'rejected' and ack['accepted'] == 0, f'неверный status: {ack}')
        reasons = ' '.join(ack['reasons'])
        for fragment in ('WIN-', 'statement', 'domain', 'kind', 'confidence', 'works[0].doi',
                         'works[0].locator', 'works[0].quote', 'kg_ref'):
            require(fragment in reasons, f'проверка {fragment} зависела от других ошибок: {reasons}')


def test_unknown_and_standalone_edges_remain() -> None:
    with Fixture() as fx:
        before = map_bytes(fx)
        unknown = fx.outbox / 'mystery.bin'
        unknown.write_bytes(b'unknown payload\x00')
        edge = fx.outbox / 'lonely.edges.jsonl'
        write_jsonl(edge, [win_edge('WIN-MISSING')])
        proc = fx.serve()
        require_rc(proc)
        require(unknown.read_bytes() == b'unknown payload\x00', 'неизвестный файл удалён или изменён')
        require(edge.exists(), 'отдельный edges без atoms удалён')
        require(map_bytes(fx) == before, 'неизвестный файл/отдельный edge изменили карту')
        ack = json.loads((fx.ack / 'mystery.bin.json').read_text(encoding='utf-8'))
        require(ACK_KEYS <= set(ack) and ack['status'] == 'unknown', f'неверный unknown ack: {ack}')
        pending = json.loads((fx.ack / 'lonely.json').read_text(encoding='utf-8'))
        require(pending['status'] == 'pending', f'отдельный edge не отмечен pending: {pending}')


def test_incomplete_tmp_is_not_ready() -> None:
    with Fixture() as fx:
        before = map_bytes(fx)
        atoms = fx.outbox / 'half.atoms.tmp'
        write_jsonl(atoms, [win_atom('WIN-HALF')])
        proc = fx.serve()
        require_rc(proc)
        require(atoms.exists(), 'одиночный atoms.tmp удалён')
        require(not (fx.outbox / 'half.atoms.jsonl').exists(), 'одиночный atoms.tmp прочитан как готовый')
        require(map_bytes(fx) == before, 'неполная пара изменила карту')
        ack = json.loads((fx.ack / 'half.json').read_text(encoding='utf-8'))
        require(ack['status'] == 'pending', f'неполная пара не отмечена pending: {ack}')


def test_kg_reject_is_not_lost() -> None:
    with Fixture() as fx:
        before = map_bytes(fx)
        fake = fx.root / 'tools/kg_inbox.py'
        fake.write_text(
            '#!/usr/bin/env python3\n'
            'import json, pathlib, sys\n'
            'pathlib.Path("kg-args.json").write_text(json.dumps(sys.argv[1:]), encoding="utf-8")\n'
            'print("fake kg failure", file=sys.stderr)\n'
            'raise SystemExit(1)\n',
            encoding='utf-8',
        )
        source = fx.outbox / 'kg-reject.kg.jsonl'
        original = b'{"kind":"node"}\n'
        source.write_bytes(original)
        proc = fx.serve()
        require_rc(proc)
        rejected = fx.bridge / 'rejected/kg-reject/kg-reject.kg.jsonl'
        require(rejected.read_bytes() == original, 'kg reject не сохранён в rejected')
        require(not source.exists(), 'kg reject остался в outbox вместо rejected')
        require(map_bytes(fx) == before, 'kg reject изменил карту')
        ack = json.loads((fx.ack / 'kg-reject.json').read_text(encoding='utf-8'))
        require(ACK_KEYS <= set(ack), f'неполный kg ack: {ack}')
        require(ack['status'] == 'rejected', f'kg reject получил status {ack["status"]}')
        require(ack['accepted'] is None, 'accepted=0 выставлен вслепую без счётчика kg_inbox')
        require(any('rc=1' in reason for reason in ack['reasons']), f'нет причины kg reject: {ack}')
        args = json.loads((fx.root / 'kg-args.json').read_text(encoding='utf-8'))
        require('--serve' in args and '--ack-dir' in args, f'неверная команда kg_inbox: {args}')
        require(args[args.index('--ack-dir') + 1] == str(fx.ack), f'kg_inbox пишет ack не в bridge: {args}')


def test_kg_success_is_archived() -> None:
    with Fixture() as fx:
        kg = fx.root / 'kg'
        kg.mkdir(parents=True, exist_ok=True)
        (kg / 'nodes.jsonl').write_text('', encoding='utf-8')
        (kg / 'lines.json').write_text('{"lines": [{"id": "vybor"}]}\n', encoding='utf-8')
        source = fx.outbox / 'kg-success.kg.jsonl'
        row = {
            'kind': 'node', 'tmp': 'n1', 'type': 'literature',
            'text': 'A sufficiently long fixture literature claim for the kg inbox.',
            'quote': 'A sufficiently long fixture quote.',
            'source': {'doi': '10.0000/kg-fixture', 'level': 'abstract_read'},
            'lines': ['vybor'],
        }
        original = (json.dumps(row, ensure_ascii=False) + '\n').encode('utf-8')
        source.write_bytes(original)
        proc = fx.serve()
        require_rc(proc)
        require((fx.bridge / 'processed/kg-success/kg-success.kg.jsonl').read_bytes() == original,
                'принятый kg не архивирован')
        require(not source.exists(), 'принятый kg остался в outbox')
        ack = json.loads((fx.ack / 'kg-success.json').read_text(encoding='utf-8'))
        require(ack['status'] == 'processed' and ack['accepted'] == 1, f'неверный kg ack: {ack}')
        kg_ack = json.loads((fx.ack / 'kg-success-kg.json').read_text(encoding='utf-8'))
        require(ACK_KEYS <= set(kg_ack), f'kg_inbox записал неполный ack: {kg_ack}')


def test_questions_are_copied_and_archived() -> None:
    with Fixture() as fx:
        source = fx.outbox / 'questions-case.questions.jsonl'
        payload = b'{"question":"fixture?"}\n'
        source.write_bytes(payload)
        proc = fx.serve()
        require_rc(proc)
        target = fx.root / 'literature/map/inbox/win-questions-case.jsonl'
        require(target.read_bytes() == payload, 'questions не скопированы атомарно в map/inbox')
        require((fx.bridge / 'processed/questions-case/questions-case.questions.jsonl').read_bytes() == payload,
                'questions не архивированы')
        require(not source.exists(), 'questions остались в outbox после архива')


def main() -> int:
    tests = [
        ('orphan failure сохраняет байты таблиц', test_orphan_failure_preserves_bytes),
        ('dry-run ничего не пишет', test_dry_run_writes_nothing),
        ('claim принимается', test_claim_is_accepted),
        ('JSON-массив/не-object дают контролируемый отказ', test_non_object_json_is_controlled),
        ('--report/--edges без значений дают контролируемый отказ', test_missing_flag_values_are_controlled),
        ('CLI принимает естественный порядок и повторяемый --edges', test_map_cli_natural_order_and_repeated_edges),
        ('неоднозначный/неизвестный CLI отказывает до записи', test_map_cli_rejects_ambiguous_and_unknown_before_writing),
        ('дубли и конфликтующие ID безопасны', test_duplicates_and_conflicting_ids),
        ('сбой второй записи остаётся pending до retry', test_second_write_failure_stays_pending_until_retry),
        ('backup отчёта переживает pending-транзакцию', test_report_backup_survives_pending_transaction),
        ('contract failure откатывает ingest_safe', test_safe_contract_failure_rolls_back),
        ('non-main report вне репозитория отклонён', test_non_main_report_outside_repo_is_rejected),
        ('non-main report на PROTECTED/atoms/edges отклонён', test_non_main_report_protected_and_map_files_are_rejected),
        ('symlink escape для non-main report отклонён', test_non_main_report_symlink_escape_is_rejected),
        ('contract failure откатывает отчёт вместе с парой', test_safe_report_rolls_back_with_pair),
        ('неудачный restore сохраняет backup с отчётом', test_safe_restore_failure_preserves_backup),
        ('KeyboardInterrupt откатывает отчёт и пару', test_safe_keyboard_interrupt_restores_report_and_pair),
        ('flock ждёт и имеет таймаут', test_safe_lock_waits_and_times_out),
        ('ненулевой код без contract откатывает таблицы', test_safe_nonzero_without_contract_rolls_back),
        ('flock сериализует два ingest_safe', test_safe_flock_serializes_two_ingests),
        ('корректная пара проходит мост', test_bridge_correct_pair),
        ('legacy .jsonl пара поддерживается', test_bridge_legacy_pair),
        ('два --serve обрабатывают пару ровно один раз', test_two_servers_process_pair_once),
        ('отклонённая пара и edges остаются в rejected', test_rejected_pair_keeps_atoms_and_edges),
        ('неизвестный файл и отдельные edges остаются', test_unknown_and_standalone_edges_remain),
        ('одиночный .tmp не считается готовым', test_incomplete_tmp_is_not_ready),
        ('kg reject не теряется', test_kg_reject_is_not_lost),
        ('принятый kg архивируется', test_kg_success_is_archived),
        ('questions копируются и архивируются', test_questions_are_copied_and_archived),
    ]
    failed = 0
    for name, test in tests:
        try:
            test()
        except Exception as exc:
            failed += 1
            print(f'FAIL {name}: {exc}')
            if os.environ.get('INGEST_INTEGRITY_TRACEBACK'):
                traceback.print_exc()
        else:
            print(f'ok   {name}')
    print(f'ingest_integrity: {len(tests) - failed}/{len(tests)}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
