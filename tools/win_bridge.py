"""Мост для внешнего агента, у которого есть только Windows и GitHub (без WSL).

Агент кладёт файлы в `C:\\111\\graph-bridge\\outbox\\`, я забираю их проходом `--serve`:
валидирую, применяю, пишу ответ в `ack\\`. Никакого git из его стороны — история не ветвится.

Форматы (одна партия = один файл):

    <имя>.atoms.tmp      по строке на ячейку карты
    <имя>.edges.tmp      по строке на связь
    <имя>.ready          атомарный marker завершения обеих .tmp
    <имя>.questions.jsonl  вопросы к данным (как у probe)

Legacy `.atoms.jsonl` / `.edges.jsonl` поддерживаются. `.tmp` promotятся только с `.ready`.
Отклонённая партия сохраняется в `rejected/<имя>/`, принятая — в `processed/<имя>/`.

Запуск:
    python3 tools/win_bridge.py --state      обновить STATE.md для агента
    python3 tools/win_bridge.py --serve      забрать партии и ответить
    python3 tools/win_bridge.py --watch 30   то же в цикле
    python3 tools/win_bridge.py --bridge <каталог> --serve   изолированный мост (для проверок)
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import errno
import fcntl
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BRIDGE = pathlib.Path('/mnt/c/111/graph-bridge')
PROCESSED = BRIDGE / 'processed'
LIVE = ROOT / 'literature/map/atoms.jsonl'
EDGES = ROOT / 'literature/map/edges.jsonl'
VALID_KINDS = {
    'measurement', 'claim', 'definition', 'gap', 'mechanism', 'formula', 'condition', 'contradiction',
}
VALID_CONFIDENCE = {'high', 'medium', 'low'}
TYPE_SUFFIXES = (
    ('.atoms.jsonl', 'atoms'),
    ('.edges.jsonl', 'edges'),
    ('.questions.jsonl', 'questions'),
    ('.kg.jsonl', 'kg'),
    ('.atoms.tmp', 'atoms-tmp'),
    ('.edges.tmp', 'edges-tmp'),
)
INGEST_TIMEOUT_S = 600
TERMINATE_GRACE_S = 2


class CommandStartError(RuntimeError):
    """Дочерний процесс не был создан; никаких изменений он сделать не мог."""


class CommandOutcomeUnknown(RuntimeError):
    """Процесс был запущен, но его итог нельзя установить по выходным данным."""

    def __init__(self, message: str, *, group_stopped: bool = False):
        super().__init__(message)
        self.group_stopped = group_stopped


class CommandTimeout(CommandOutcomeUnknown):
    def __init__(self, timeout: float, output: str, *, term_sent: bool, kill_sent: bool,
                 group_stopped: bool = False):
        super().__init__(f'таймаут {timeout:g}s; outcome=unknown; rollback=unknown',
                         group_stopped=group_stopped)
        self.timeout = timeout
        self.output = output
        self.term_sent = term_sent
        self.kill_sent = kill_sent


def configure_bridge(path: pathlib.Path) -> None:
    global BRIDGE, PROCESSED
    BRIDGE = path.resolve()
    PROCESSED = BRIDGE / 'processed'


def fsync_dir(path: pathlib.Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise
    finally:
        os.close(fd)


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    tmp = pathlib.Path(name)
    try:
        with os.fdopen(fd, 'wb') as fh:
            os.fchmod(fh.fileno(), mode)
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        fsync_dir(path.parent)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def atomic_copy(src: pathlib.Path, dst: pathlib.Path) -> None:
    atomic_write(dst, src.read_bytes())


def _text_output(value) -> str:
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return value or ''


def process_group_alive(pgid) -> bool:
    """Fail-closed: неизвестный/непроверенный pgid считается потенциально живым."""
    if os.name != 'posix' or not isinstance(pgid, int) or pgid <= 0:
        return True
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True


def _signal_group(proc: subprocess.Popen, sig: int) -> bool:
    """POSIX: отдельная сессия делает pid лидера идентификатором process group."""
    if os.name == 'posix':
        try:
            os.killpg(proc.pid, sig)
            return True
        except ProcessLookupError:
            return False
    if proc.poll() is None:
        proc.send_signal(sig)
        return True
    return False


def _stop_group(proc: subprocess.Popen) -> tuple[str, bool, bool]:
    term_sent = _signal_group(proc, signal.SIGTERM)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=TERMINATE_GRACE_S)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr = b'', b''
    # Лидер мог закрыть pipes и выйти по SIGTERM, а потомок — проигнорировать
    # сигнал. Поэтому после grace проверяем всю группу, а не только лидера.
    kill_sent = _signal_group(proc, signal.SIGKILL) if _signal_group(proc, 0) else False
    if timed_out or kill_sent:
        stdout, stderr = proc.communicate()
    return _text_output(stdout) + _text_output(stderr), term_sent, kill_sent


def run_isolated(cmd: list[str], *, timeout: float, on_start=None) -> subprocess.CompletedProcess:
    """Запуск ingest/kg в своей группе; timeout убивает всю группу, а не только лидера."""
    session_args = {'start_new_session': True} if os.name == 'posix' else {}
    try:
        proc = subprocess.Popen(
            cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            **session_args,
        )
    except OSError as exc:
        raise CommandStartError(str(exc)) from exc
    try:
        if on_start is not None:
            on_start(proc.pid)
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        output, term_sent, kill_sent = _stop_group(proc)
        raise CommandTimeout(timeout, output, term_sent=term_sent, kill_sent=kill_sent,
                             group_stopped=not process_group_alive(proc.pid))
    except Exception as exc:
        _stop_group(proc)
        raise CommandOutcomeUnknown(f'не удалось дождаться дочернего процесса: {exc}',
                                    group_stopped=not process_group_alive(proc.pid)) from exc
    except BaseException:
        _stop_group(proc)
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


@contextlib.contextmanager
def bridge_lock():
    """Общий неблокирующий замок на STATE, чтение карты, ack, outbox и архивы."""
    BRIDGE.mkdir(parents=True, exist_ok=True)
    fh = (BRIDGE / '.win-bridge.lock').open('a+b')
    acquired = False
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            pass
        yield acquired
    finally:
        if acquired:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            finally:
                fh.close()
        else:
            fh.close()


def counts() -> tuple[int, int]:
    def lines(path: pathlib.Path) -> int:
        return len([line for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]) if path.exists() else 0

    return lines(LIVE), lines(EDGES)


def load_known() -> set[str]:
    if not LIVE.exists():
        return set()
    return {
        row['atom'] for row in (json.loads(line) for line in LIVE.read_text(encoding='utf-8').splitlines() if line.strip())
        if isinstance(row, dict) and isinstance(row.get('atom'), str)
    }


def _write_state() -> int:
    """Снимок состояния; вызывается только под bridge_lock."""
    outbox = BRIDGE / 'outbox'
    ack = BRIDGE / 'ack'
    outbox.mkdir(parents=True, exist_ok=True)
    ack.mkdir(parents=True, exist_ok=True)
    cells, edges = counts()
    state_path = BRIDGE / 'STATE.md'

    def run(*cmd: str) -> str:
        r = subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, timeout=600)
        out = ((r.stdout or '') + (r.stderr or '')).strip().splitlines()
        return out[-1] if out else ''

    contract = run(sys.executable, 'checks/map_contract.py')
    orphans = run(sys.executable, 'tools/map_orphans.py', '--strict')
    coverage = run(sys.executable, 'checks/stitch_coverage_floor.py')
    audit = run(sys.executable, 'tools/map_duplicates.py', '--strict')

    doi_gaps = ROOT / 'docs' / 'L-DOI-GAPS.json'
    queue = []
    if doi_gaps.exists():
        try:
            data = json.loads(doi_gaps.read_text(encoding='utf-8'))
            queue = [(r['node'], r['doi'], r['text']) for r in data['nodes'][:15]]
        except (ValueError, KeyError, TypeError):
            queue = []

    heads = subprocess.run(
        ['git', 'log', '--oneline', '-1'], cwd=ROOT, capture_output=True, text=True, timeout=30,
    ).stdout.strip()

    lines = [
        '# Состояние графа для внешнего агента',
        '',
        f'**Обновлено:** {time.strftime("%Y-%m-%d %H:%M")}. **Коммит:** `{heads}`.',
        '',
        '## Числа',
        '',
        '| величина | значение |', '|---|---|',
        f'| ячеек карты | **{cells}** |',
        f'| рёбер | **{edges}** |',
        f'| контракт | {contract[:90]} |',
        f'| сироты | {orphans[:90]} |',
        f'| покрытие | {coverage[:90]} |',
        f'| дубли | {audit[:90]} |',
        '',
        '## Что можно делать (только через этот каталог)',
        '',
        '1. `outbox\\<имя>.atoms.tmp` — новые ячейки карты (3–5 за партию, лучше один источник).',
        '2. `outbox\\<имя>.edges.tmp` — связи новых ячеек с существующими (обязательно).',
        '3. `outbox\\<имя>.questions.jsonl` — вопросы к числам в уже существующих ячейках.',
        '',
        'Ответ появится в `ack\\<имя>.json`; пауза опроса 30 секунд; обработка может занять дольше. '
        'Причины отказа — там же.',
        '',
        '## Протокол приёма',
        '',
        '- Сначала закончите `<имя>.atoms.tmp` и `<имя>.edges.tmp`, затем атомарно создайте `<имя>.ready` '
        '(готовый пустой файл через временное имя и rename). Только marker и обе `.tmp` разрешают promote '
        'в `<имя>.atoms.jsonl` / `<имя>.edges.jsonl`; до marker `.tmp` не читаются и не переименовываются.',
        '- Legacy `<имя>.atoms.jsonl` / `<имя>.edges.jsonl` поддерживаются без marker; неполные `.tmp` '
        'остаются в outbox. Не переиспользуйте batch ID для другого содержимого.',
        '- Durable intent/receipt создаётся до copy/archive для processed, rejected и questions. '
        'Crash между шагами завершается на retry без повторного архива и без потери source.',
        '- Принятая пара архивируется в `processed/<имя>/` и только затем удаляется из outbox.',
        '- Отклонённая пара сохраняется в `rejected/<имя>/` вместе с atoms и edges; rejected означает '
        'доказанное отсутствие изменений, а не просто nonzero rc.',
        '- Неуспех/таймаут ingest/kg, частичная карта или неизвестный rollback дают ack `unknown` и recovery '
        'receipt в `state/recovery/`: outbox не архивируется и не удаляется. Без подтверждённого stop/pgid '
        'повтор откладывается; source под тем же batch ID не перезаписывает finalized receipt.',
        '- Неизвестные файлы и отдельные edges без atoms остаются в outbox.',
        '',
        '## Требования к ячейке (иначе отказ)',
        '',
        '- `atom` — уникальный идентификатор, начинается с `WIN-`;',
        '- `statement` — строка не короче 40 символов, что измерено или доказано, с числами и единицами;',
        '- `domain` — непустая строка;',
        '- `kind` — measurement / claim / definition / gap / mechanism / formula / condition / contradiction;',
        '- `confidence` — high / medium / low;',
        '- `works[0]` — объект с непустыми `doi`, `locator` (раздел/таблица/уравнение), `quote` (дословная подстрока);',
        '- `kg_ref` — непустой список;',
        '- связь в `edges` для каждой новой ячейки (правило: ячейка без связи не принимается);',
        '- **никаких** пересказов без локатора и никаких чисел «по памяти».',
        '',
        '## Что делать нельзя',
        '',
        '- править `literature/map/atoms.jsonl`, `edges.jsonl`, `kg/`, `results/` — только новые файлы в `outbox`;',
        '- пушить в GitHub-ветку `master` и переписывать историю;',
        '- ставить связь типа `analogous` без обоснования в `note`;',
        '- выдавать своё восстановление за цитату источника (помечать «наша реконструкция»).',
        '',
        '## Очередь: источники, которых в карте нет',
        '',
        '| узел | DOI | о чём |', '|---|---|---|',
    ]
    for node, doi, text in queue:
        lines.append(f'| `{node}` | `{doi}` | {text[:80]} |')
    lines += ['', 'Полный список — 40 DOI, выдаётся по запросу в `ack`.', '']

    for src, dst in (('docs/AUTONOMOUS-PLAN.md', 'PLAN.md'),
                     ('docs/PROBE-INSTRUCTION.md', 'QUESTIONS-HOWTO.md'),
                     ('docs/UNITS-CONVENTIONS.md', 'UNITS.md')):
        source = ROOT / src
        if source.exists():
            atomic_copy(source, BRIDGE / dst)
    rendered = '\n'.join(lines)
    if state_path.exists() and state_path.read_text(encoding='utf-8') == rendered:
        print(f'STATE.md обновлён: {cells} ячеек, {edges} рёбер')
        return 0
    atomic_write(BRIDGE / 'STATE.md', rendered.encode('utf-8'))
    print(f'STATE.md обновлён: {cells} ячеек, {edges} рёбер')
    return 0


def write_state() -> int:
    with bridge_lock() as acquired:
        if not acquired:
            print('STATE.md: проход занят другим watcher, пропуск')
            return 0
        return _write_state()


def validate_atoms(path: pathlib.Path, known: set[str]) -> tuple[list[dict], list[str]]:
    """Все проверки независимы; kg_ref не включает и не выключает остальные."""
    good, bad = [], []
    batch_ids = set()
    for i, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            a = json.loads(line)
        except Exception as exc:
            bad.append(f'{path.name}:{i}: не JSON ({exc})')
            continue
        if not isinstance(a, dict):
            bad.append(f'{path.name}:{i}: ожидался JSON-object, получен {type(a).__name__}')
            continue
        problems = []
        atom = a.get('atom')
        if not isinstance(atom, str) or not atom.startswith('WIN-'):
            problems.append('atom должен быть строкой, начинающейся с WIN-')
        else:
            if atom in known:
                problems.append('такой atom уже есть в карте')
            if atom in batch_ids:
                problems.append('такой atom повторяется внутри партии')
            batch_ids.add(atom)

        statement = a.get('statement')
        if not isinstance(statement, str) or len(statement) < 40:
            problems.append('statement должен быть строкой не короче 40 символов')
        domain = a.get('domain')
        if not isinstance(domain, str) or not domain.strip():
            problems.append('domain обязателен и должен быть непустой строкой')
        if not isinstance(a.get('kind'), str) or a.get('kind') not in VALID_KINDS:
            problems.append('kind вне перечисления: ' + ', '.join(sorted(VALID_KINDS)))
        if not isinstance(a.get('confidence'), str) or a.get('confidence') not in VALID_CONFIDENCE:
            problems.append('confidence должен быть high / medium / low')
        if a.get('confidence') in ('high', 'medium') and not a.get('conditions'):
            problems.append('conditions обязателен при confidence high/medium (контракт карты)')

        works = a.get('works')
        if not isinstance(works, list) or not works:
            problems.append('works[0] обязателен')
        else:
            work = works[0]
            if not isinstance(work, dict):
                problems.append('works[0] должен быть JSON-object')
            else:
                for field in ('doi', 'locator', 'quote'):
                    if not isinstance(work.get(field), str) or not work.get(field).strip():
                        problems.append(f'works[0].{field} обязателен и должен быть непустой строкой')

        refs = a.get('kg_ref')
        if not isinstance(refs, list) or not refs:
            problems.append('kg_ref обязателен и должен быть непустым списком')
        if problems:
            bad.append(f'{path.name}:{i}: ' + '; '.join(problems))
        else:
            good.append(a)
    return good, bad


def classify(path: pathlib.Path) -> tuple[str, str] | None:
    for suffix, kind in TYPE_SUFFIXES:
        if path.name.endswith(suffix):
            batch = path.name[:-len(suffix)]
            return (kind, batch) if batch not in ('', '.', '..') else None
    return None


def promote_temps(outbox: pathlib.Path) -> None:
    """Promote только после marker: writer опубликовал обе законченные половины."""
    for marker in sorted(outbox.glob('*.ready')):
        if not marker.is_file():
            continue
        batch = marker.name[:-len('.ready')]
        if not batch:
            continue
        halves = []
        conflict = False
        for kind in ('atoms', 'edges'):
            tmp = outbox / f'{batch}.{kind}.tmp'
            final = outbox / f'{batch}.{kind}.jsonl'
            if tmp.is_file() and final.exists():
                conflict = True  # новый tmp не должен молча заменить legacy final
            if not tmp.is_file() and not final.is_file():
                conflict = True  # marker без одной из половин ещё не готов
            halves.append((tmp, final))
        if conflict:
            continue
        # Наличие final без tmp допускает recovery после crash между halves.
        # Конфликт tmp+final проверен до первого rename.
        for tmp, final in halves:
            if tmp.is_file():
                os.replace(tmp, final)
        marker.unlink(missing_ok=True)
    fsync_dir(outbox)


def make_result(file: str, status: str, *, accepted=None, rejected=None, reasons=None, ingest='not run') -> dict:
    return {
        'file': file,
        'status': status,
        'accepted': accepted,
        'rejected': rejected,
        'reasons': reasons or [],
        'ingest': ingest,
    }


def write_ack(batch: str, result: dict) -> None:
    ack = BRIDGE / 'ack'
    ack.mkdir(parents=True, exist_ok=True)
    atomic_write(ack / f'{batch}.json', (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_records(paths: list[pathlib.Path]) -> list[dict]:
    records = []
    for path in paths:
        if path.exists():
            data = path.read_bytes()
            records.append({'name': path.name, 'sha256': sha256_bytes(data), 'size': len(data)})
    return records


def baseline_records(paths: list[pathlib.Path]) -> list[dict]:
    records = []
    for path in paths:
        record = {'name': path.name, 'exists': path.exists()}
        if path.exists():
            data = path.read_bytes()
            record.update({'sha256': sha256_bytes(data), 'size': len(data)})
        records.append(record)
    return records


def map_baseline() -> dict:
    baseline = {'files': baseline_records([LIVE, EDGES]), 'edges_valid': True, 'edge_points': []}
    try:
        baseline['edge_points'] = [
            [row.get('from'), row.get('to'), row.get('type')]
            for row in load_json_rows(EDGES) if isinstance(row, dict)
            and all(isinstance(row.get(key), str) and row[key]
                    for key in ('from', 'to', 'type'))
        ]
    except (OSError, UnicodeError, ValueError, TypeError):
        baseline['edges_valid'] = False
    return baseline


def baseline_matches(baseline: dict | None, paths: list[pathlib.Path]) -> bool:
    if not isinstance(baseline, dict):
        return False
    try:
        return baseline.get('files') == baseline_records(paths)
    except OSError:
        return False


def kg_baseline() -> dict:
    return {'files': baseline_records([ROOT / 'docs' / 'KG-INBOX.jsonl',
                                       ROOT / 'docs' / 'KG-CHECKS.jsonl'])}


def receipt_path(kind: str, batch: str) -> pathlib.Path:
    return BRIDGE / 'state' / 'recovery' / f'{kind}-{batch}.json'


def load_receipt(kind: str, batch: str) -> dict | None:
    path = receipt_path(kind, batch)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('kind') != kind or value.get('batch') != batch:
        raise RuntimeError(f'некорректный recovery receipt: {path}')
    return value


def write_receipt(receipt: dict) -> None:
    receipt['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    atomic_write(receipt_path(receipt['kind'], receipt['batch']),
                 (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def receipt_matches(receipt: dict, paths: list[pathlib.Path]) -> bool:
    try:
        return receipt.get('sources') == source_records(paths)
    except OSError:
        return False


def receipt_group_alive(receipt: dict) -> bool:
    """Не запускать вторую партию, пока stop/pgid предыдущей не подтверждены."""
    attempts = receipt.get('attempts') or []
    attempt = attempts[-1] if attempts else {}
    if attempt.get('status') != 'unknown' or attempt.get('group_stopped'):
        return False
    if receipt.get('manual_retry') is True and receipt.get('group_stopped') is True:
        return False
    # Отсутствие pgid — не доказательство смерти группы. Такой повтор разрешён
    # только после ручной проверки процесса и явного group_stopped/manual_retry.
    return process_group_alive(attempt.get('pgid'))


def retry_requires_manual_check(receipt: dict) -> bool:
    attempts = receipt.get('attempts') or []
    attempt = attempts[-1] if attempts else {}
    return attempt.get('status') == 'unknown' and not attempt.get('group_stopped') \
        and not (receipt.get('manual_retry') is True and receipt.get('group_stopped') is True)


def begin_attempt(kind: str, batch: str, cmd: list[str], paths: list[pathlib.Path], expected: dict,
                  *, baseline: dict | None = None, spawns_group: bool = True) -> dict:
    """Durable intent до запуска; finalized receipt никогда не перезаписывается."""
    previous = load_receipt(kind, batch)
    if previous is not None and previous.get('status') in ('processed', 'rejected'):
        raise RuntimeError(f'finalized receipt нельзя перезаписать: {kind}-{batch}')
    attempts = list(previous.get('attempts', [])) if previous else []
    receipt = {
        'version': 1,
        'kind': kind,
        'batch': batch,
        'status': 'unknown',
        'outcome': 'unknown',
        'rollback': 'unknown',
        'sources': source_records(paths),
        'expected': expected,
        'attempts': attempts,
        'ack_written': False,
    }
    if baseline is not None:
        receipt['map_baseline'] = baseline
    elif previous is not None:
        receipt['map_baseline'] = previous.get('map_baseline')
    receipt['attempts'].append({
        'number': len(attempts) + 1,
        'started_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'command': cmd,
        'status': 'unknown',
        'outcome': 'unknown',
        'rollback': 'unknown',
        'group_stopped': not spawns_group,
    })
    write_receipt(receipt)
    return receipt


def defer_unknown(receipt: dict, result: dict, reason: str) -> None:
    receipt['status'] = 'unknown'
    receipt['outcome'] = 'unknown'
    receipt['rollback'] = 'unknown'
    receipt['retry'] = reason
    receipt['result'] = result
    write_receipt(receipt)
    write_ack(receipt['batch'], result)


def record_group_stopped(receipt: dict) -> None:
    """Ставим флаг только после фактического исчезновения всей process group."""
    if not receipt.get('attempts'):
        return
    attempt = receipt['attempts'][-1]
    if attempt.get('group_stopped'):
        return
    if not process_group_alive(attempt.get('pgid')):
        attempt['group_stopped'] = True
        attempt['group_stop_checked_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        write_receipt(receipt)


def protect_receipt_source(kind: str, batch: str, paths: list[pathlib.Path], file: str) -> dict | None:
    """Новый source под тем же ID не получает ни нового attempt, ни новой терминальной записи."""
    previous = load_receipt(kind, batch)
    if previous is None or previous.get('status') not in ('processed', 'rejected') \
            or receipt_matches(previous, paths):
        return None
    result = make_result(
        file, 'unknown', accepted=None, rejected=None,
        reasons=['source изменился после finalized receipt; новый attempt запрещён',
                 'исходник оставлен в outbox; receipt не перезаписан'],
        ingest='recovery deferred: finalized receipt source mismatch',
    )
    write_ack(batch, result)
    return result


def mark_unknown(receipt: dict, file: str, reason: str, *, ingest: str, exc=None) -> dict:
    receipt['status'] = 'unknown'
    receipt['outcome'] = 'unknown'
    receipt['rollback'] = 'unknown'
    receipt['retry'] = 'сверить ожидаемые строки с картой/очередями до повторного запуска'
    if receipt.get('attempts'):
        attempt = receipt['attempts'][-1]
        stopped = attempt.get('group_stopped') is True or getattr(exc, 'group_stopped', False) is True
        attempt.update({'status': 'unknown', 'outcome': 'unknown', 'rollback': 'unknown',
                        'group_stopped': stopped, 'reason': reason})
        if isinstance(exc, CommandTimeout):
            attempt.update({
                'timeout_s': exc.timeout,
                'sigterm_sent': exc.term_sent,
                'sigkill_sent': exc.kill_sent,
                'output_tail': output_tail(exc.output, 2000),
            })
    result = make_result(file, 'unknown', accepted=None, rejected=None,
                         reasons=[reason, 'исходники оставлены в outbox; rejected/processed не архивировались',
                                  'rollback не утверждается'], ingest=ingest)
    receipt['result'] = result
    write_receipt(receipt)
    write_ack(receipt['batch'], result)
    return result


def finalize_receipt(receipt: dict, status: str, outcome: str, result: dict, *,
                     rollback: str | None = None) -> None:
    receipt['status'] = status
    receipt['outcome'] = outcome
    receipt['rollback'] = rollback or ('not applicable' if status == 'processed' else 'not asserted')
    receipt['result'] = result
    receipt['archive'] = {'status': status, 'batch': receipt['batch']}
    if receipt.get('attempts'):
        receipt['attempts'][-1].update({
            'status': status, 'outcome': outcome, 'group_stopped': True,
            'rollback': receipt['rollback'], 'finished_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        })
    write_receipt(receipt)


def archive_files(paths: list[pathlib.Path], status: str, batch: str) -> None:
    """Сначала обе атомарные копии, затем удаление outbox; при ошибке копирования исходники целы."""
    if not paths:
        return
    target = BRIDGE / status / batch
    target.mkdir(parents=True, exist_ok=True)
    for src in paths:
        dst = target / src.name
        if dst.exists() and dst.read_bytes() != src.read_bytes():
            raise FileExistsError(f'в архиве уже есть другой файл {dst}')
        atomic_copy(src, dst)
    for src in paths:
        src.unlink(missing_ok=True)
    fsync_dir(target)
    fsync_dir(paths[0].parent)


def finish_processed(batch: str, paths: list[pathlib.Path], result: dict, receipt: dict,
                     known: set[str] | None = None) -> None:
    """Сначала durable итог, потом архив; сбой архива не превращает применённое в rejected."""
    finalize_receipt(receipt, 'processed', 'applied', result)
    try:
        archive_files(paths, 'processed', batch)
    except Exception as exc:
        result['status'] = 'unknown'
        result['reasons'].append(f'архив processed не завершён: {exc}; исходники не удалены')
        receipt['status'] = 'unknown'
        receipt['outcome'] = 'applied'
        receipt['rollback'] = 'not asserted'
        receipt['result'] = result
        write_receipt(receipt)
        write_ack(batch, result)
        print(f'{paths[0].name}: применено, но архив/ack требуют recovery')
        return
    if known is not None:
        known.clear()
        known.update(load_known())
    write_ack(batch, result)
    receipt['ack_written'] = True
    write_receipt(receipt)
    print(f'{paths[0].name}: принято {result["accepted"]}, отклонено {result["rejected"]}')


def recover_finalized_receipts() -> set[str]:
    """Дочитать ack/архив после смерти моста между apply, copy, archive и ack."""
    handled: set[str] = set()
    recovery = BRIDGE / 'state' / 'recovery'
    if not recovery.exists():
        return handled
    for path in sorted(recovery.glob('*.json')):
        try:
            receipt = json.loads(path.read_text(encoding='utf-8'))
            kind, batch = receipt['kind'], receipt['batch']
            archive = receipt.get('archive')
            result = receipt.get('result')
            if not isinstance(archive, dict) or not isinstance(result, dict) \
                    or archive.get('status') not in ('processed', 'rejected'):
                continue
            if receipt.get('status') not in ('processed', 'rejected') \
                    and not (receipt.get('status') == 'unknown' and receipt.get('outcome') == 'applied'):
                continue
            sources = receipt.get('sources') or []
            existing = [BRIDGE / 'outbox' / row['name'] for row in sources
                        if (BRIDGE / 'outbox' / row['name']).exists()]
            for src, row in zip((BRIDGE / 'outbox' / row['name'] for row in sources), sources):
                if src.exists() and sha256_bytes(src.read_bytes()) != row['sha256']:
                    unknown = make_result(
                        result.get('file') or batch, 'unknown', accepted=None, rejected=None,
                        reasons=['source изменился после finalized receipt; recovery не удаляет исходник',
                                 'receipt не перезаписан; нужен ручной разбор'],
                        ingest='recovery deferred: finalized receipt source mismatch',
                    )
                    write_ack(batch, unknown)
                    break
            else:
                if receipt.get('ack_written') and not existing:
                    continue
                if kind == 'questions' and archive['status'] == 'processed':
                    expected = receipt.get('expected') or {}
                    relative = expected.get('target')
                    digest = expected.get('sha256')
                    artifact = ROOT / relative if isinstance(relative, str) else None
                    if artifact is None or not artifact.is_file() \
                            or sha256_bytes(artifact.read_bytes()) != digest:
                        unknown = make_result(
                            result.get('file') or batch, 'unknown', accepted=None, rejected=None,
                            reasons=['questions target отсутствует или его hash не совпадает с receipt',
                                     'source оставлен в outbox; архив/ack не завершены'],
                            ingest='recovery deferred: questions artifact conflict',
                        )
                        write_ack(batch, unknown)
                        continue
                target = BRIDGE / archive['status'] / archive['batch']
                archived = all((target / row['name']).exists()
                               and sha256_bytes((target / row['name']).read_bytes()) == row['sha256']
                               for row in sources)
                if not archived:
                    if existing:
                        continue  # процесс ниже ещё раз попробует завершить копирование
                    unknown = make_result(
                        result.get('file') or batch, 'unknown', accepted=None, rejected=None,
                        reasons=['recovery: исходники outbox и полный архив отсутствуют; повтор не запускался'],
                        ingest='recovery archive incomplete',
                    )
                    receipt['status'] = 'unknown'
                    receipt['result'] = unknown
                    write_receipt(receipt)
                    write_ack(batch, unknown)
                    continue
                for src in existing:
                    src.unlink(missing_ok=True)
                fsync_dir(BRIDGE / 'outbox')
                if receipt.get('outcome') == 'applied':
                    result = dict(result)
                    result['status'] = 'processed'
                    result['reasons'] = [reason for reason in result.get('reasons', [])
                                         if not str(reason).startswith('архив processed не завершён')]
                    receipt['status'] = 'processed'
                    receipt['result'] = result
                write_ack(batch, result)
                receipt['ack_written'] = True
                write_receipt(receipt)
                handled.add(f'{kind}-{batch}')
                continue
            # break только при mismatch: receipt остаётся байт-в-байт прежним.
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            print(f'предупреждение: recovery {path.name}: {exc}', file=sys.stderr)
    return handled


def line_count(path: pathlib.Path) -> int:
    return len([line for line in path.read_text(encoding='utf-8').splitlines() if line.strip()])


def output_tail(out: str, limit: int = 2000) -> str:
    return out[-limit:]


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def atom_core(row: dict) -> dict:
    """Поля, которые map_ingest не обогащает и не меняет при приёме."""
    works = []
    for work in row.get('works') or []:
        if isinstance(work, dict):
            works.append({key: work[key] for key in ('doi', 'locator', 'quote') if key in work})
    return {
        'atom': row.get('atom'), 'statement': row.get('statement'), 'domain': row.get('domain'),
        'kind': row.get('kind'), 'kg_ref': row.get('kg_ref'), 'works': works,
    }


def atom_matches(expected: dict, row: dict) -> bool:
    """Сравниваем стабильное ядро; enrichment вроде resolved_* допустим."""
    if any(row.get(key) != value for key, value in expected.items() if key != 'works'):
        return False
    expected_works = expected.get('works') or []
    live_works = row.get('works') or []
    if not isinstance(live_works, list) or len(live_works) != len(expected_works):
        return False
    for wanted, live in zip(expected_works, live_works):
        if not isinstance(live, dict) or any(live.get(key) != value for key, value in wanted.items()):
            return False
    return True


def atoms_expected(good: list[dict], edges: pathlib.Path | None, known: set[str]) -> dict:
    edge_rows = []
    if edges is not None and edges.exists():
        edge_rows = [json.loads(line) for line in edges.read_text(encoding='utf-8').splitlines() if line.strip()]
    valid_ids = known | {row['atom'] for row in good}
    return {
        'atoms': [atom_core(row) for row in good],
        'edges': [
            {key: row.get(key) for key in ('from', 'to', 'type')}
            for row in edge_rows
            if isinstance(row, dict)
            and all(isinstance(row.get(key), str) and row[key] for key in ('from', 'to', 'type'))
            and row['from'] in valid_ids and row['to'] in valid_ids
        ],
    }


def kg_expected(path: pathlib.Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return {
        'source_rows': len(rows),
        'inbox': [row for row in rows if isinstance(row, dict) and row.get('kind') != 'check'],
        'checks': [row for row in rows if isinstance(row, dict) and row.get('kind') == 'check'],
    }


def load_json_rows(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def reconcile_atoms(receipt: dict, atoms: pathlib.Path, edges: pathlib.Path | None) -> dict | None:
    """None — можно повторить; dict — уже применено либо обнаружена неполная/чужая запись."""
    paths = [atoms] + ([edges] if edges is not None and edges.exists() else [])
    if not receipt_matches(receipt, paths):
        return None
    expected = receipt.get('expected') or {}
    expected_atoms = expected.get('atoms') or []
    expected_edges = expected.get('edges') or []
    try:
        live_atoms = load_json_rows(LIVE)
        live_edges = load_json_rows(EDGES)
    except (OSError, UnicodeError, ValueError, TypeError):
        return make_result(atoms.name, 'unknown', accepted=None, rejected=None,
                           reasons=['не удалось сверить карту после неизвестного исхода; исходники оставлены'],
                           ingest='recovery reconciliation failed')
    by_id = collections.defaultdict(list)
    for row in live_atoms:
        if isinstance(row, dict) and isinstance(row.get('atom'), str):
            by_id[row['atom']].append(row)
    present = [bool(by_id.get(core.get('atom'))) for core in expected_atoms]
    matches = [any(atom_matches(core, row) for row in by_id.get(core.get('atom'), []))
               for core in expected_atoms]
    conflicts = [len(by_id.get(core.get('atom'), [])) > 1 for core in expected_atoms]
    points = collections.Counter(
        (row.get('from'), row.get('to'), row.get('type')) for row in live_edges if isinstance(row, dict)
        and all(isinstance(row.get(key), str) and row[key] for key in ('from', 'to', 'type'))
    )
    baseline = receipt.get('map_baseline') or {}
    baseline_valid = baseline.get('edges_valid') is True
    old_points = collections.Counter(tuple(point) for point in baseline.get('edge_points') or [])
    wanted_points = collections.Counter(
        (row.get('from'), row.get('to'), row.get('type')) for row in expected_edges
    )
    edges_done = all(points[point] >= max(old_points[point], count)
                     for point, count in wanted_points.items())
    new_edges = any(points[point] > old_points[point] for point in wanted_points)
    if expected_atoms and all(matches) and not any(conflicts) and edges_done:
        return make_result(
            atoms.name, 'processed', accepted=len(expected_atoms), rejected=0,
            reasons=['повтор после unknown: все ожидаемые atoms/edges уже в карте, ingest не запускался'],
            ingest='recovered after unknown outcome; duplicate ingest skipped',
        )
    if any(present) or any(conflicts) or new_edges or not baseline_valid:
        return make_result(
            atoms.name, 'unknown', accepted=None, rejected=None,
            reasons=['частичная или конфликтующая запись после unknown; автоматический повтор опасен',
                     'исходники оставлены в outbox; rejected/processed не архивировались; rollback не утверждается'],
            ingest='recovery reconciliation: partial/conflicting map state',
        )
    return None


def _queued_counter(path: pathlib.Path, source: str) -> collections.Counter:
    counter = collections.Counter()
    for row in load_json_rows(path):
        if isinstance(row, dict) and row.get('file') == source:
            counter[canonical({key: value for key, value in row.items()
                               if key not in ('received_at', 'file', '_kg_transaction_id', '_kg_row_id')})] += 1
    return counter


def kg_request_committed(path: pathlib.Path) -> bool:
    """Есть ли committed-journal, который сам безопасно дописывает projections."""
    journal = ROOT / '.coord' / 'kg-inbox' / 'transactions.jsonl'
    if not journal.exists():
        return False
    try:
        request = {
            'version': 1,
            'files': [{'file': path.name, 'sha256': sha256_bytes(path.read_bytes())}],
        }
        request_hash = hashlib.sha256(canonical(request).encode('utf-8')).hexdigest()
        lines = journal.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeError, ValueError, TypeError):
        return False
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or row.get('type') != 'committed' \
                or row.get('request_hash') != request_hash:
            continue
        sealed = dict(row)
        checksum = sealed.pop('record_sha256', None)
        if checksum == hashlib.sha256(canonical(sealed).encode('utf-8')).hexdigest():
            return True
    return False


def reconcile_kg(receipt: dict, path: pathlib.Path) -> dict | None:
    if not receipt_matches(receipt, [path]):
        return None
    expected = receipt.get('expected') or {}
    rows = list(expected.get('inbox') or []) + list(expected.get('checks') or [])
    if expected.get('source_rows') != len(rows):
        return None  # невалидный JSON разберётся обычным preflight при повторе
    try:
        observed = {
            'inbox': _queued_counter(ROOT / 'docs' / 'KG-INBOX.jsonl', path.name),
            'checks': _queued_counter(ROOT / 'docs' / 'KG-CHECKS.jsonl', path.name),
        }
    except (OSError, UnicodeError, ValueError, TypeError):
        return make_result(path.name, 'unknown', accepted=None, rejected=None,
                           reasons=['не удалось сверить KG-очереди после неизвестного исхода; исходник оставлен'],
                           ingest='recovery reconciliation failed')
    wanted = {
        'inbox': collections.Counter(canonical(row) for row in expected.get('inbox') or []),
        'checks': collections.Counter(canonical(row) for row in expected.get('checks') or []),
    }
    matched = sum(min(wanted[name][key], observed[name][key]) for name in wanted for key in wanted[name])
    if rows and matched == len(rows):
        return make_result(
            path.name, 'processed', accepted=len(rows), rejected=0,
            reasons=['повтор после unknown: все ожидаемые строки уже в KG-очередях, kg_inbox не запускался'],
            ingest='recovered after unknown outcome; duplicate kg ingest skipped',
        )
    if matched:
        if kg_request_committed(path):
            return None  # kg_inbox восстановит committed transaction без дублей
        return make_result(
            path.name, 'unknown', accepted=None, rejected=None,
            reasons=['частичная запись KG-очередей после unknown; автоматический повтор опасен',
                     'исходник оставлен в outbox; rejected/processed не архивировались; rollback не утверждается'],
            ingest='recovery reconciliation: partial KG transaction',
        )
    return None


def finish_rejected(batch: str, paths: list[pathlib.Path], result: dict, receipt: dict, *,
                    rollback: str = 'not asserted') -> None:
    """Terminal intent до archive; сбой между copy/delete/ack продолжается на retry."""
    finalize_receipt(receipt, 'rejected', 'not applied', result, rollback=rollback)
    try:
        archive_files(paths, 'rejected', batch)
    except Exception as exc:
        unknown = dict(result)
        unknown['status'] = 'unknown'
        unknown['reasons'] = list(result.get('reasons') or []) + [
            f'архив rejected не завершён: {exc}; исходники не удалены повторно']
        receipt['archive_error'] = str(exc)
        write_receipt(receipt)
        write_ack(batch, unknown)
        print(f'{paths[0].name}: rejected, но archive/ack требуют recovery')
        return
    write_ack(batch, result)
    receipt['ack_written'] = True
    write_receipt(receipt)
    print(f'{paths[0].name}: rejected, исходники сохранены в rejected/{batch}/')


def reject_atoms(batch: str, atoms: pathlib.Path, edges: pathlib.Path | None, result: dict, *,
                 receipt: dict | None = None, kind: str = 'atoms',
                 rollback: str = 'not asserted') -> None:
    paths = [atoms] + ([edges] if edges is not None and edges.exists() else [])
    previous = load_receipt(kind, batch)
    if previous is not None and not receipt_matches(previous, paths):
        unknown = make_result(
            atoms.name, 'unknown', accepted=None, rejected=None,
            reasons=['source не совпадает с recovery receipt; rejected/new attempt запрещены',
                     'исходник оставлен в outbox; receipt не перезаписан'],
            ingest='recovery deferred: receipt source mismatch',
        )
        write_ack(batch, unknown)
        return
    if previous is not None and previous.get('status') == 'unknown' and receipt is None:
        unknown = make_result(
            atoms.name, 'unknown', accepted=None, rejected=None,
            reasons=['предыдущий исход не разрешён; validation reject не архивирует source',
                     'сначала проверьте process group и durable baseline'],
            ingest='recovery deferred: previous outcome unknown',
        )
        write_ack(batch, unknown)
        return
    if receipt is None:
        receipt = begin_attempt(kind, batch, [], paths, {'validation_rejected': True}, spawns_group=False)
    finish_rejected(batch, paths, result, receipt, rollback=rollback)


def process_atoms(batch: str, atoms: pathlib.Path, edges: pathlib.Path | None, known: set[str]) -> None:
    paths = [atoms] + ([edges] if edges is not None and edges.exists() else [])
    previous = load_receipt('atoms', batch)
    if protect_receipt_source('atoms', batch, paths, atoms.name) is not None:
        print(f'{atoms.name}: unknown, source mismatch; receipt сохранён')
        return
    if previous is not None and previous.get('status') in ('processed', 'rejected'):
        return  # archive/ack этого receipt завершает recover_finalized_receipts
    retrying_unknown = previous is not None and previous.get('status') == 'unknown'
    if previous is not None and not receipt_matches(previous, paths):
        unknown = make_result(
            atoms.name, 'unknown', accepted=None, rejected=None,
            reasons=['source изменился после recovery intent; новый attempt запрещён',
                     'исходник оставлен в outbox; receipt не перезаписан'],
            ingest='recovery deferred: receipt source mismatch',
        )
        write_ack(batch, unknown)
        return
    if retrying_unknown:
        if receipt_group_alive(previous) or retry_requires_manual_check(previous):
            recovered = make_result(
                atoms.name, 'unknown', accepted=None, rejected=None,
                reasons=['stop/pgid прежней process group не подтверждены; повтор не запускался',
                         'исходники оставлены в outbox; rollback не утверждается',
                         'ручной retry только после проверки.group_stopped и manual_retry'],
                ingest='recovery deferred: previous process group stop is unconfirmed',
            )
            defer_unknown(previous, recovered, 'проверить process group; затем manual_retry/group_stopped')
            print(f'{atoms.name}: unknown, ожидание подтверждённой остановки process group')
            return
        recovered = reconcile_atoms(previous, atoms, edges)
        if recovered is not None:
            if recovered['status'] == 'processed':
                finish_processed(batch, paths, recovered, previous, known)
            else:
                defer_unknown(previous, recovered, 'сверить карту; автоматический повтор опасен')
                print(f'{atoms.name}: unknown, исходники оставлены для recovery')
            return

    try:
        good, bad = validate_atoms(atoms, known)
    except Exception as exc:
        result = make_result(atoms.name, 'rejected', accepted=0, rejected=None,
                             reasons=[f'не прочитать atoms: {exc}'], ingest='validation failed')
        if retrying_unknown:
            mark_unknown(load_receipt('atoms', batch), atoms.name,
                         f'validation после unknown: {exc}', ingest='validation failed; outcome remains unknown')
        else:
            reject_atoms(batch, atoms, edges, result)
        return
    total = line_count(atoms)
    if bad or not good:
        reasons = bad[:20] or ['atoms пуст: нечего принимать']
        result = make_result(atoms.name, 'rejected', accepted=0, rejected=total, reasons=reasons,
                             ingest='validation rejected; ingest_safe not run')
        if retrying_unknown:
            mark_unknown(load_receipt('atoms', batch), atoms.name,
                         'validation после unknown не подтвердила отсутствие изменений',
                         ingest='validation rejected; outcome remains unknown')
        else:
            reject_atoms(batch, atoms, edges, result)
        return

    cmd = [sys.executable, 'tools/ingest_safe.py', str(atoms), '--agent', 'main']
    if edges is not None and edges.exists():
        cmd += ['--edges', str(edges)]
    try:
        expected = atoms_expected(good, edges, known)
    except (OSError, UnicodeError, ValueError, TypeError):
        expected = {'atoms': [atom_core(row) for row in good], 'edges': [], 'edges_valid': False}
    baseline = previous.get('map_baseline') if retrying_unknown else map_baseline()
    receipt = begin_attempt('atoms', batch, cmd, paths, expected, baseline=baseline)

    def started(pid: int) -> None:
        receipt['attempts'][-1]['pgid'] = pid
        write_receipt(receipt)

    try:
        r = run_isolated(cmd, timeout=INGEST_TIMEOUT_S, on_start=started)
        out = ((r.stdout or '') + (r.stderr or '')).strip()
        rc = r.returncode
    except CommandTimeout as exc:
        mark_unknown(receipt, atoms.name, f'ingest_safe: {exc}', ingest=f'rc=unknown; {exc.output[-1000:]}', exc=exc)
        print(f'{atoms.name}: unknown, исходники оставлены; group_stopped={exc.group_stopped}')
        return
    except CommandOutcomeUnknown as exc:
        mark_unknown(receipt, atoms.name, f'ingest_safe: {exc}', ingest=f'rc=unknown; {exc}')
        print(f'{atoms.name}: unknown, исходники оставлены; group_stopped={exc.group_stopped}')
        return
    except CommandStartError as exc:
        receipt['attempts'][-1]['group_stopped'] = True  # процесс не был создан
        write_receipt(receipt)
        result = make_result(atoms.name, 'rejected', accepted=0, rejected=total,
                             reasons=[f'ingest_safe не запустился: {exc}'], ingest='not run')
        finish_rejected(batch, paths, result, receipt, rollback='not applicable: process not started')
        return

    record_group_stopped(receipt)
    if receipt_group_alive(receipt):
        mark_unknown(receipt, atoms.name, 'лидер завершился, но process group ещё не подтверждена остановленной',
                     ingest=f'ingest_safe rc={rc}; group remains alive')
        return

    match = re.search(r'принято (\d+) из (\d+)', out)
    parsed = int(match.group(1)) if match else None
    summary = match.group(0) if match else 'счётчик приёма отсутствует'
    ingest = f'ingest_safe rc={rc}; {summary}'
    if rc == 0 and parsed is not None and parsed > 0:
        result = make_result(atoms.name, 'processed', accepted=parsed, rejected=total - parsed,
                             reasons=[], ingest=ingest)
        finish_processed(batch, paths, result, receipt, known)
        return

    # Nonzero/неподтверждённый счётчик сами по себе не доказывают rollback.
    # Сначала проверяем ожидаемые строки, затем — побайтовый durable baseline.
    recovered = reconcile_atoms(receipt, atoms, edges)
    if recovered is not None:
        if recovered['status'] == 'processed':
            finish_processed(batch, paths, recovered, receipt, known)
        else:
            mark_unknown(receipt, atoms.name, 'после неуспеха ingest_safe обнаружена частичная/конфликтная карта',
                         ingest=ingest + '; recovery reconciliation: unknown')
        return

    unchanged = baseline_matches(receipt.get('map_baseline'), [LIVE, EDGES])
    rollback_failed = 'ОТКАТ НЕ ВЫПОЛНЕН' in out
    if not unchanged or rollback_failed:
        mark_unknown(receipt, atoms.name,
                     'ingest_safe не подтвердил успех; rollback не выполнен или baseline изменился',
                     ingest=ingest + '; outcome=unknown; rollback=unknown')
        return

    reasons = []
    if rc != 0:
        reasons.append(f'ingest_safe завершился с rc={rc}; durable baseline карты побайтово не изменился')
    elif parsed is None:
        reasons.append('ingest_safe не сообщил счётчик; durable baseline карты побайтово не изменился')
    else:
        reasons.append('ingest_safe не принял ни одной новой ячейки; durable baseline карты не изменился')
    if retrying_unknown:
        reasons.append('предыдущий rollback не утверждается; отсутствие новых изменений доказано baseline')
    if out:
        reasons.append(output_tail(out))
    result = make_result(atoms.name, 'rejected', accepted=0, rejected=total, reasons=reasons, ingest=ingest)
    rollback = 'verified: durable map baseline unchanged'
    if retrying_unknown:
        rollback += '; earlier attempt rollback remains unknown'
    finish_rejected(batch, paths, result, receipt, rollback=rollback)


def process_questions(batch: str, path: pathlib.Path) -> None:
    target = ROOT / 'literature/map/inbox' / f'win-{batch}.jsonl'
    paths = [path]
    previous = load_receipt('questions', batch)
    if protect_receipt_source('questions', batch, paths, path.name) is not None:
        print(f'{path.name}: unknown, source mismatch; receipt сохранён')
        return
    if previous is not None and previous.get('status') in ('processed', 'rejected'):
        return
    if previous is not None and not receipt_matches(previous, paths):
        unknown = make_result(
            path.name, 'unknown', accepted=None, rejected=None,
            reasons=['source изменился после questions intent; новый copy/archive запрещены',
                     'исходник оставлен в outbox; receipt не перезаписан'],
            ingest='recovery deferred: receipt source mismatch',
        )
        write_ack(batch, unknown)
        return
    if previous is not None and (receipt_group_alive(previous) or retry_requires_manual_check(previous)):
        unknown = make_result(
            path.name, 'unknown', accepted=None, rejected=None,
            reasons=['предыдущая операция не подтверждена завершённой; повтор отложен',
                     'source оставлен в outbox'],
            ingest='recovery deferred: previous operation stop is unconfirmed',
        )
        defer_unknown(previous, unknown, 'проверить операцию; затем manual_retry/group_stopped')
        return

    receipt = previous
    try:
        payload = path.read_bytes()
        digest = sha256_bytes(payload)
        expected = {
            'target': str(target.relative_to(ROOT)), 'sha256': digest, 'size': len(payload),
            'lines': len([line for line in payload.splitlines() if line.strip()]),
        }
        if previous is not None:
            wanted = previous.get('expected') or {}
            if wanted.get('sha256') != digest or wanted.get('target') != expected['target']:
                raise ValueError('questions intent не совпадает с source/target')
            if target.exists() and sha256_bytes(target.read_bytes()) != digest:
                unknown = make_result(
                    path.name, 'unknown', accepted=None, rejected=None,
                    reasons=['questions target уже существует с другим hash; source оставлен',
                             'повторный copy/archive не выполнялся'],
                    ingest='recovery deferred: questions artifact conflict',
                )
                defer_unknown(previous, unknown, 'разобрать конфликт target вручную; receipt не перезаписывать')
                return
        if receipt is None:
            # Intent обязателен даже при конфликте с уже существующим target.
            receipt = begin_attempt('questions', batch, ['atomic-copy', str(target)], paths,
                                    expected, spawns_group=False)
            if target.exists() and sha256_bytes(target.read_bytes()) != digest:
                unknown = make_result(
                    path.name, 'unknown', accepted=None, rejected=None,
                    reasons=['questions target уже существует с другим hash; source оставлен',
                             'copy/archive не выполнялись'],
                    ingest='questions artifact conflict',
                )
                defer_unknown(receipt, unknown, 'разобрать конфликт target; source не архивировать')
                return
        if not target.exists():
            atomic_copy(path, target)
        if sha256_bytes(target.read_bytes()) != digest:
            raise ValueError('questions target hash после copy не совпадает с source')
        result = make_result(
            path.name, 'processed', accepted=expected['lines'], rejected=0,
            reasons=['questions target проверен по sha256'] if previous is not None else [],
            ingest=f'copied atomically to {target.relative_to(ROOT)}',
        )
        finish_processed(batch, paths, result, receipt)
    except Exception as exc:
        # Copy мог завершиться до исключения (например, при имитации crash перед
        # archive). Совпавший target — доказательство применённой операции.
        if 'payload' in locals() and target.exists() and sha256_bytes(target.read_bytes()) == sha256_bytes(payload):
            result = make_result(
                path.name, 'processed', accepted=len([line for line in payload.splitlines() if line.strip()]),
                rejected=0, reasons=['recovery: существующий questions target совпал по sha256'],
                ingest='recovered after questions copy; duplicate copy skipped',
            )
            if receipt is not None:
                finish_processed(batch, paths, result, receipt)
                return
        if receipt is None:
            unknown = make_result(
                path.name, 'unknown', accepted=None, rejected=None,
                reasons=[f'questions copy не начат/не проверен: {exc}', 'source оставлен в outbox'],
                ingest='questions outcome unknown',
            )
            write_ack(batch, unknown)
            return
        if target.exists():
            unknown = make_result(
                path.name, 'unknown', accepted=None, rejected=None,
                reasons=[f'questions target конфликтует с source: {exc}', 'source оставлен в outbox'],
                ingest='questions artifact conflict',
            )
            defer_unknown(receipt, unknown, 'разобрать questions target; archive не выполнять')
            return
        result = make_result(
            path.name, 'rejected', accepted=0, rejected=None,
            reasons=[f'questions copy не создал target: {exc}'], ingest='questions copy failed; target absent',
        )
        finish_rejected(batch, paths, result, receipt, rollback='not applicable: target absent')
    print(f'{path.name}: {result["status"]}')


def process_kg(batch: str, path: pathlib.Path) -> None:
    previous = load_receipt('kg', batch)
    if protect_receipt_source('kg', batch, [path], path.name) is not None:
        print(f'{path.name}: unknown, source mismatch; receipt сохранён')
        return
    if previous is not None and previous.get('status') in ('processed', 'rejected'):
        return
    retrying_unknown = previous is not None and previous.get('status') == 'unknown'
    if previous is not None and not receipt_matches(previous, [path]):
        unknown = make_result(
            path.name, 'unknown', accepted=None, rejected=None,
            reasons=['source изменился после recovery intent; новый attempt запрещён',
                     'исходник оставлен в outbox; receipt не перезаписан'],
            ingest='recovery deferred: receipt source mismatch',
        )
        write_ack(batch, unknown)
        return
    if retrying_unknown:
        if receipt_group_alive(previous) or retry_requires_manual_check(previous):
            recovered = make_result(
                path.name, 'unknown', accepted=None, rejected=None,
                reasons=['stop/pgid прежней process group не подтверждены; повтор не запускался',
                         'исходник оставлен в outbox; rollback не утверждается',
                         'ручной retry только после проверки.group_stopped и manual_retry'],
                ingest='recovery deferred: previous process group stop is unconfirmed',
            )
            defer_unknown(previous, recovered, 'проверить process group; затем manual_retry/group_stopped')
            print(f'{path.name}: unknown, ожидание подтверждённой остановки process group')
            return
        recovered = reconcile_kg(previous, path)
        if recovered is not None:
            if recovered['status'] == 'processed':
                finish_processed(batch, [path], recovered, previous)
            else:
                defer_unknown(previous, recovered, 'сверить KG-очереди; автоматический повтор опасен')
                print(f'{path.name}: unknown, исходник оставлен для recovery')
            return

    ack_dir = BRIDGE / 'ack'
    cmd = [sys.executable, 'tools/kg_inbox.py', '--serve', '--ack-dir', str(ack_dir), str(path)]
    try:
        expected = kg_expected(path)
    except (OSError, UnicodeError, ValueError, TypeError):
        expected = {'source_rows': 1, 'inbox': [], 'checks': [], 'valid_json': False}
    baseline = previous.get('map_baseline') if retrying_unknown else kg_baseline()
    receipt = begin_attempt('kg', batch, cmd, [path], expected, baseline=baseline)

    def started(pid: int) -> None:
        receipt['attempts'][-1]['pgid'] = pid
        write_receipt(receipt)

    try:
        r = run_isolated(cmd, timeout=INGEST_TIMEOUT_S, on_start=started)
        out = ((r.stdout or '') + (r.stderr or '')).strip()
        rc = r.returncode
    except CommandTimeout as exc:
        mark_unknown(receipt, path.name, f'kg_inbox: {exc}', ingest=f'rc=unknown; {exc.output[-1000:]}', exc=exc)
        print(f'{path.name}: unknown, исходник оставлен; group_stopped={exc.group_stopped}')
        return
    except CommandOutcomeUnknown as exc:
        mark_unknown(receipt, path.name, f'kg_inbox: {exc}', ingest=f'rc=unknown; {exc}')
        print(f'{path.name}: unknown, исходник оставлен; group_stopped={exc.group_stopped}')
        return
    except CommandStartError as exc:
        receipt['attempts'][-1]['group_stopped'] = True  # процесс не был создан
        write_receipt(receipt)
        result = make_result(path.name, 'rejected', accepted=0, rejected=None,
                             reasons=[f'kg_inbox не запустился: {exc}'], ingest='not run')
        reject_atoms(batch, path, None, result, receipt=receipt, kind='kg')
        return

    record_group_stopped(receipt)
    if receipt_group_alive(receipt):
        mark_unknown(receipt, path.name, 'лидер kg_inbox завершился, но process group ещё может писать',
                     ingest=f'kg_inbox rc={rc}; group remains alive')
        return

    # Committed journal определяет исход независимо от степени projections.
    # kg_inbox безопасно восстановит партию при retry; rejected/archive запрещены.
    committed_kg = kg_request_committed(path)

    match = re.search(r'принято (\d+), отклонено (\d+)', out)
    accepted = int(match.group(1)) if match else None
    rejected = int(match.group(2)) if match else None
    by_kind = None
    _km = None
    try:
        _km = re.search(r'(\{.*\})', out)
    except Exception:
        _km = None
    if _km is not None:
        try:
            by_kind = json.loads(_km.group(1))
        except Exception:
            by_kind = None
    reasons = []
    if rc == 0 and accepted is not None and accepted > 0:
        result = make_result(path.name, 'processed', accepted=accepted, rejected=rejected,
                             reasons=[], ingest=f'kg_inbox rc={rc}; {output_tail(out, 1000)}')
        if by_kind is not None:
            result['by_kind'] = by_kind  # разбор kg-партии по видам (journal 813)
        finish_processed(batch, [path], result, receipt)
        return

    recovered = reconcile_kg(receipt, path)
    if recovered is not None:
        if recovered['status'] == 'processed':
            finish_processed(batch, [path], recovered, receipt)
        else:
            mark_unknown(receipt, path.name, 'после неуспеха kg_inbox обнаружена частичная KG-запись',
                         ingest=f'kg_inbox rc={rc}; recovery reconciliation: unknown')
        return

    queues = [ROOT / 'docs' / 'KG-INBOX.jsonl', ROOT / 'docs' / 'KG-CHECKS.jsonl']
    if retrying_unknown or committed_kg or not baseline_matches(receipt.get('map_baseline'), queues):
        mark_unknown(receipt, path.name, 'kg_inbox не подтвердил исход; committed/baseline требуют recovery',
                     ingest=f'kg_inbox rc={rc}; outcome remains unknown; {output_tail(out, 1000)}')
        return

    if rc not in (0, None):
        reasons.append(f'kg_inbox завершился с rc={rc}; durable baseline очередей побайтово не изменился')
    elif accepted == 0:
        reasons.append('kg_inbox явно сообщил accepted=0; durable baseline очередей не изменился')
    else:
        reasons.append('kg_inbox не подтвердил accepted>0; durable baseline очередей не изменился')
    if rejected:
        reasons.extend(line for line in out.splitlines() if line.strip().startswith(('   ', 'test'))[:12])
    result = make_result(path.name, 'rejected', accepted=accepted, rejected=rejected, reasons=reasons,
                         ingest=f'kg_inbox rc={rc}; {output_tail(out, 1000)}')
    reject_atoms(batch, path, None, result, receipt=receipt, kind='kg',
                 rollback='verified: durable KG queue baseline unchanged')
    print(f'{path.name}: rejected; accepted={accepted}, rejected={rejected}')


def _serve() -> int:
    _write_state()
    outbox = BRIDGE / 'outbox'
    ack = BRIDGE / 'ack'
    outbox.mkdir(parents=True, exist_ok=True)
    ack.mkdir(parents=True, exist_ok=True)
    promote_temps(outbox)
    handled = recover_finalized_receipts()

    known = load_known()
    batches: dict[str, dict[str, pathlib.Path]] = {}
    unknown = []
    leftover_tmp: dict[str, list[pathlib.Path]] = {}
    for path in sorted(outbox.iterdir()):
        if not path.is_file() or path.name.endswith('.ready'):
            continue
        info = classify(path)
        if info is None:
            unknown.append(path)
            continue
        kind, batch = info
        if kind in ('atoms-tmp', 'edges-tmp'):
            leftover_tmp.setdefault(batch, []).append(path)
        elif kind in ('atoms', 'edges'):
            batches.setdefault(batch, {})[kind] = path

    done = 0
    for batch, files in sorted(batches.items()):
        atoms = files.get('atoms')
        edges = files.get('edges')
        if atoms is None:
            result = make_result(
                edges.name, 'pending', accepted=0, rejected=0,
                reasons=['отдельные edges без atoms не применяются и не удаляются'],
                ingest='not run: waiting for matching atoms',
            )
            write_ack(batch, result)
            print(f'{edges.name}: ждёт atoms, файл оставлен')
            done += 1
            continue
        if f'atoms-{batch}' not in handled:
            process_atoms(batch, atoms, edges, known)
            done += 1

    for batch, paths in sorted(leftover_tmp.items()):
        # Не перезаписывать ack успешно обработанной legacy-патии тем же именем.
        if not (BRIDGE / 'ack' / f'{batch}.json').exists():
            result = make_result(
                ', '.join(path.name for path in paths), 'pending', accepted=0, rejected=0,
                reasons=['неполная пара .tmp или финальный файл уже существует; .tmp не читается как готовый'],
                ingest='not run: waiting for safe promotion',
            )
            write_ack(batch, result)
        print(f'{batch}: .tmp оставлен в outbox до завершённой парии')

    for path in unknown:
        result = make_result(path.name, 'unknown', accepted=0, rejected=0,
                             reasons=['тип файла не распознан; исходник оставлен в outbox'], ingest='not run')
        write_ack(path.name, result)
        print(f'{path.name}: НЕ РАСПОЗНАН, файл оставлен')

    for path in sorted(outbox.iterdir()):
        if not path.is_file():
            continue
        info = classify(path)
        if info and info[0] in ('questions', 'kg'):
            kind, batch = info
            if f'{kind}-{batch}' in handled:
                continue
            if kind == 'questions':
                process_questions(batch, path)
            else:
                process_kg(batch, path)
            done += 1
    if not done and not unknown and not leftover_tmp:
        print('outbox пуст')
    return 0


def serve() -> int:
    with bridge_lock() as acquired:
        if not acquired:
            print('проход занят другим watcher, пропуск до следующей паузы')
            return 0
        return _serve()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description='мост для агента с доступом только к Windows')
    ap.add_argument('--bridge', default=str(BRIDGE), help='каталог моста (по умолчанию C:\\111\\graph-bridge)')
    ap.add_argument('--serve', action='store_true')
    ap.add_argument('--state', action='store_true')
    ap.add_argument('--watch', type=int, default=0, metavar='СЕК')
    args = ap.parse_args(argv)
    configure_bridge(pathlib.Path(args.bridge))
    if args.state:
        return write_state()
    if not args.watch:
        return serve()
    print(f'мост в режиме наблюдения: проход каждые {args.watch} с')
    while True:
        try:
            serve()
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f'проход упал: {exc}')
        time.sleep(args.watch)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
