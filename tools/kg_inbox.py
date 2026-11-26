"""Инбокс предложений для `kg/` — «дубовый формат» из спеки внешнего агента (Часть VII).

Три типа строк, всё остальное — отказ:

    {"kind":"node","tmp":"n1","type":"literature","text":"...","quote":"...",
     "source":{"doi":"...","url":"...","level":"abstract_read"},
     "lines":["vybor"],"context":{"scope":"..."},"notes":"..."}

    {"kind":"edge","from":"n1","to":"F-016","type":"extends","note":"..."}

    {"kind":"check","id":"F-006","quote":"...","source":{"url":"...","level":"fragment_read"},
     "verdict":"supported","note":"..."}

Инбокс **не правит** `kg/`: принятые строки лежат в `docs/KG-INBOX.jsonl` (предложения) и
`docs/KG-CHECKS.jsonl` (проверки). Идентификаторы назначает коллектор (я), не автор.

Целостность партии:
    `.coord/kg-inbox/transactions.jsonl` — append-only JSONL-журнал. Запись `prepared`
    содержит стабильный `transaction_id`, `request_hash`, `batch_hash`, SHA-256 входных
    файлов и строк projections; запись `committed` ссылается на SHA-256 `prepared` и
    содержит сохранённые receipts. Обе записи fsync-ятся до применения projections.
    Строки projections несут `_kg_transaction_id` и `_kg_row_id`; recovery под flock
    дописывает только отсутствующие строки любых committed-транзакций. Prepared без
    committed не применяется. Оборванный хвост журнала запечатывается append-only
    записью `repair`, без перезаписи истории.

Receipt также зеркалируется в `.coord/kg-inbox/receipts/<request_hash>.json`, но источник
истины — commit-запись журнала. Поэтому commit и ack независимы: ошибка ack не меняет
статус committed-партии и не делает её rejected; retry с тем же содержимым/именами файлов
возвращает сохранённый receipt без повторного commit. Однако processed receipt выдаётся
только после подтверждения projections этой партии; иначе ack имеет статус `unknown`.
Backup удаляется лишь после подтверждённых projections и сохранённого receipt.

Запуск:
    python3 tools/kg_inbox.py --serve <файл>...   принять партии и ответить
    python3 tools/kg_inbox.py --state             что ждёт очереди (фронтир)

Ack: `--ack-dir` имеет приоритет; иначе для `<bridge>/outbox/<имя>.kg.jsonl` пишется
`<bridge>/ack/<имя>-kg.json`. Для прямого вызова вне `outbox` документированный fallback —
`<каталог-входного-файла>/<имя>-kg.json`. Запись ack атомарна.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import datetime as dt
import errno
import fcntl
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODES = ROOT / 'kg' / 'nodes.jsonl'
LINES = ROOT / 'kg' / 'lines.json'
INBOX = ROOT / 'docs' / 'KG-INBOX.jsonl'
CHECKS = ROOT / 'docs' / 'KG-CHECKS.jsonl'

EDGE_TYPES = {'qualifies', 'tested_in', 'stated_in', 'extends', 'analogous_to', 'normalizes_to',
              'refutes', 'refuted_by', 'supports', 'derived_from', 'bridges', 'maps_to'}
SOURCE_LEVELS = {'metadata_only', 'abstract_read', 'fragment_read', 'full_text_examined', 'secondary_only'}
NODE_TYPES = {'literature', 'claim', 'formula', 'definition', 'gap', 'correspondence'}
VERDICTS = {'supported', 'contradicted', 'not_found'}
MAX_LINES = 50
JOURNAL_VERSION = 1


def load_nodes() -> dict[str, dict]:
    out = {}
    for line in NODES.read_text(encoding='utf-8').splitlines():
        if line.strip():
            n = json.loads(line)
            out[n['id']] = n
    return out


def load_lines() -> set[str]:
    data = json.loads(LINES.read_text(encoding='utf-8'))
    return {x['id'] for x in data['lines']}


def norm(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError('normalization requires a string')
    return re.sub(r'\s+', ' ', text).strip().lower()


def _source_problems(src: object, *, require_locator: bool) -> list[str]:
    if not isinstance(src, dict):
        return ['source: нужен JSON object']
    problems = []
    if not isinstance(src.get('level'), str) or src.get('level') not in SOURCE_LEVELS:
        problems.append(f"source.level не из списка: {sorted(SOURCE_LEVELS)}")
    for field in ('doi', 'url', 'title', 'author', 'locator'):
        if field in src and not isinstance(src[field], str):
            problems.append(f'source.{field}: нужна строка')
    if require_locator and not any(isinstance(src.get(field), str) and src[field].strip()
                                   for field in ('doi', 'url')):
        problems.append('source: нужен doi или url')
    return problems


def _required_text_problems(row: dict, field: str, minimum: int) -> list[str]:
    value = row.get(field)
    if not isinstance(value, str):
        return [f'{field}: нужна строка']
    if len(value) < minimum:
        return [f'{field} короче {minimum} символов']
    return []


def preflight(path: pathlib.Path, nodes: dict[str, dict], lines: set[str], *,
              texts: set[str] | None = None, raw: bytes | None = None
              ) -> tuple[list[dict], list[str]]:
    """Проверки спеки + кап 50 строк. Возвращает (принятые, причины отказа).

    `texts` передаётся между файлами одного --serve: дубли нового текста отклоняются
    по накопительному набору. `tmp` ребра разрешён лишь после принятой node-строки
    этого же файла. Смысловые поля не приводятся к str: неверный JSON-тип — отказ.
    """
    good, bad = [], []
    if raw is None:
        try:
            raw = path.read_bytes()
        except (OSError, UnicodeError) as exc:
            return [], [f'{path.name}: не прочитать файл ({exc})']
    try:
        content = raw.decode('utf-8')
    except UnicodeError as exc:
        return [], [f'{path.name}: не прочитать файл ({exc})']
    raw_lines = [line for line in content.splitlines() if line.strip()]
    if len(raw_lines) > MAX_LINES:
        return [], [f'{path.name}: строк {len(raw_lines)}, потолок {MAX_LINES}']

    if texts is None:
        texts = {norm(n['text']) for n in nodes.values() if isinstance(n.get('text'), str)}
    tmp_seen = set()
    for i, line in enumerate(raw_lines, 1):
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError) as exc:
            bad.append(f'{path.name}:{i}: не JSON ({exc})')
            continue
        if not isinstance(row, dict):
            bad.append(f'{path.name}:{i}: нужен JSON object, получен {type(row).__name__}')
            continue
        kind = row.get('kind')
        problems = []

        if kind == 'node':
            tmp = row.get('tmp')
            if not isinstance(tmp, str) or not tmp.strip():
                problems.append('нет tmp (внутреннее имя строки)')
            elif tmp in tmp_seen:
                problems.append(f'tmp={tmp!r}: уже объявлен в этом файле')
            if not isinstance(row.get('type'), str) or row.get('type') not in NODE_TYPES:
                problems.append(f"type не из списка: {sorted(NODE_TYPES)}")
            problems.extend(_required_text_problems(row, 'text', 20))
            problems.extend(_required_text_problems(row, 'quote', 10))
            problems.extend(_source_problems(row.get('source'), require_locator=True))
            row_lines = row.get('lines')
            if not isinstance(row_lines, list) or not row_lines:
                problems.append('lines пустой: нужна линия слона')
            elif not all(isinstance(item, str) for item in row_lines):
                problems.append('lines: все идентификаторы должны быть строками')
            elif set(row_lines) - lines:
                problems.append(f"lines вне набора: {sorted(set(row_lines) - lines)}")
            if 'context' in row:
                context = row['context']
                if not isinstance(context, dict):
                    problems.append('context: нужен JSON object')
                elif 'scope' in context and not isinstance(context['scope'], str):
                    problems.append('context.scope: нужна строка')
            for field in ('note', 'notes'):
                if field in row and not isinstance(row[field], str):
                    problems.append(f'{field}: нужна строка')
            if isinstance(row.get('text'), str) and norm(row['text']) in texts:
                problems.append('такой текст уже есть в kg (дубль)')
            if not problems:
                tmp_seen.add(tmp)
                texts.add(norm(row['text']))
                good.append(row)

        elif kind == 'edge':
            edge_type = row.get('type')
            if not isinstance(edge_type, str) or edge_type not in EDGE_TYPES:
                problems.append(f"type не из 12 существующих: {sorted(EDGE_TYPES)}")
            endpoints = {}
            for side in ('from', 'to'):
                val = row.get(side)
                if not isinstance(val, str) or not val:
                    problems.append(f'нет {side}')
                elif val not in nodes and val not in tmp_seen:
                    problems.append(f'{side}={val}: нет такого узла и нет принятого tmp в этом файле')
                endpoints[side] = val
            if edge_type == 'supports':
                refuted = [f'{side}={val}' for side, val in endpoints.items()
                           if isinstance(val, str) and val in nodes
                           and nodes[val].get('epistemic') == 'refuted']
                if refuted:
                    problems.append("type='supports' запрещён: refuted endpoint " + ', '.join(refuted))
            problems.extend(_required_text_problems(row, 'note', 10))
            if not problems:
                good.append(row)

        elif kind == 'check':
            node_id = row.get('id')
            if not isinstance(node_id, str) or node_id not in nodes:
                problems.append(f'id={node_id!r}: узла нет в kg')
            verdict = row.get('verdict')
            if not isinstance(verdict, str) or verdict not in VERDICTS:
                problems.append(f"verdict не из списка: {sorted(VERDICTS)}")
            problems.extend(_required_text_problems(row, 'quote', 10))
            problems.extend(_source_problems(row.get('source'), require_locator=False))
            if 'note' in row and not isinstance(row['note'], str):
                problems.append('note: нужна строка')
            if isinstance(node_id, str) and node_id in nodes and verdict == 'supported' \
                    and nodes[node_id].get('epistemic') == 'refuted':
                problems.append('нельзя поддерживать опровергнутый узел (инвариант графа)')
            if not problems:
                good.append(row)
        else:
            problems.append(f"kind={kind!r}: допустимы node / edge / check")

        if problems:
            bad.append(f'{path.name}:{i}: ' + '; '.join(problems))
    return good, bad


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _seal_record(record: dict) -> dict:
    sealed = dict(record)
    sealed.pop('record_sha256', None)
    sealed['record_sha256'] = _digest(sealed)
    return sealed


def _parse_record(line: bytes) -> dict:
    row = json.loads(line.decode('utf-8'))
    if not isinstance(row, dict):
        raise ValueError('journal record is not an object')
    checksum = row.pop('record_sha256', None)
    if not isinstance(checksum, str) or checksum != _digest(row):
        raise ValueError('journal record checksum mismatch')
    row['record_sha256'] = checksum
    return row


def _journal_path() -> pathlib.Path:
    return ROOT / '.coord' / 'kg-inbox' / 'transactions.jsonl'


def _receipts_dir() -> pathlib.Path:
    return ROOT / '.coord' / 'kg-inbox' / 'receipts'


def _lock_path() -> pathlib.Path:
    return ROOT / '.coord' / 'locks' / 'kg-inbox.lock'


def _fsync_dir(path: pathlib.Path) -> None:
    try:
        dir_fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            try:
                os.fsync(dir_fd)
            except OSError as exc:
                if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                    raise
        finally:
            os.close(dir_fd)
    except OSError as exc:
        if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
            raise


def _staged_bytes(path: pathlib.Path, data: bytes, *, token: str | None = None) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    middle = f'.{path.name}.tmp-' + (f'{token}-' if token else '')
    fd, name = tempfile.mkstemp(prefix=middle, dir=path.parent)
    tmp = pathlib.Path(name)
    with os.fdopen(fd, 'wb') as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    return tmp


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    tmp = pathlib.Path(name)
    try:
        with os.fdopen(fd, 'wb') as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


@contextlib.contextmanager
def _transaction_lock():
    lock_path = _lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a', encoding='utf-8') as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


def _append_journal_bytes(data: bytes) -> None:
    path = _journal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError('journal write made no progress')
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(path.parent)


def _append_sealed_record(record: dict) -> dict:
    sealed = _seal_record(record)
    _append_journal_bytes(_canonical(sealed) + b'\n')
    return sealed


def _append_repair(discard_through: int, *, needs_newline: bool) -> None:
    if needs_newline:
        _append_journal_bytes(b'\n')
    _append_sealed_record({
        'version': JOURNAL_VERSION,
        'type': 'repair',
        'discard_through': discard_through,
        'created_at': dt.datetime.now().isoformat(timespec='seconds'),
    })


def _load_journal() -> list[dict]:
    """Read valid records; seal a torn tail with an append-only repair record."""
    path = _journal_path()
    if not path.exists():
        return []
    data = path.read_bytes()
    records = []
    offset = 0
    bad_start = None
    bad_needs_newline = False
    for line in data.splitlines(keepends=True):
        complete = line.endswith(b'\n')
        try:
            if not complete:
                raise ValueError('incomplete journal record')
            record = _parse_record(line)
        except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            if bad_start is not None:
                raise RuntimeError('журнал повреждён: несколько невалидных записей подряд')
            bad_start = offset
            bad_needs_newline = not complete
        else:
            if bad_start is not None:
                if record.get('type') != 'repair' or record.get('discard_through') != bad_start:
                    raise RuntimeError('журнал повреждён: невалидная запись не закрыта repair')
                bad_start = None
            else:
                records.append(record)
        offset += len(line)
    if bad_start is not None:
        _append_repair(bad_start, needs_newline=bad_needs_newline)
    return records


def _target_name(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _target_path(name: str) -> pathlib.Path:
    path = pathlib.Path(name)
    return path if path.is_absolute() else ROOT / path


def _merge_journal(records: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    prepared: dict[str, dict] = {}
    committed: dict[str, dict] = {}
    order: list[str] = []
    for record in records:
        if record.get('version') != JOURNAL_VERSION:
            raise RuntimeError('журнал: неподдерживаемая версия записи')
        kind = record.get('type')
        if kind == 'repair':
            continue
        if kind not in ('prepared', 'committed'):
            raise RuntimeError(f'журнал: неизвестный тип записи {kind!r}')
        transaction_id = record.get('transaction_id')
        if not isinstance(transaction_id, str) or not transaction_id:
            raise RuntimeError('журнал: нет transaction_id')
        if kind == 'prepared':
            if transaction_id in prepared and prepared[transaction_id] != record:
                raise RuntimeError(f'журнал: конфликтующие prepared для {transaction_id}')
            prepared[transaction_id] = record
            continue
        if transaction_id not in prepared:
            raise RuntimeError(f'журнал: committed без prepared для {transaction_id}')
        prior = prepared[transaction_id]
        if record.get('prepared_sha256') != prior['record_sha256']:
            raise RuntimeError(f'журнал: неверная ссылка prepared для {transaction_id}')
        if (record.get('request_hash') != prior.get('request_hash')
                or record.get('batch_hash') != prior.get('batch_hash')):
            raise RuntimeError(f'журнал: хэши committed не совпадают с prepared для {transaction_id}')
        if transaction_id in committed:
            raise RuntimeError(f'журнал: повторный committed для {transaction_id}')
        committed[transaction_id] = record
        order.append(transaction_id)

    transactions = []
    for transaction_id in order:
        prior = prepared[transaction_id]
        commit = committed[transaction_id]
        transactions.append({
            'transaction_id': transaction_id,
            'request_hash': prior.get('request_hash'),
            'batch_hash': prior.get('batch_hash'),
            'updates': prior['updates'],
            'receipts': commit.get('receipts', []),
            'prepared': prior,
            'committed': commit,
        })
    return prepared, transactions


def _cleanup_stages(transaction_id: str, updates: list[dict]) -> None:
    for update in updates:
        path = _target_path(update['path'])
        for stage in path.parent.glob(f'.{path.name}.tmp-{transaction_id}-*'):
            try:
                stage.unlink(missing_ok=True)
            except OSError:
                pass


def _projection_payload(rows: list[dict]) -> bytes:
    return ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode('utf-8')


def _ensure_projection(update: dict, *, repair: bool = True) -> bool:
    """Verify one committed update; append only missing rows when repair is true.

    Возвращает True только когда все ожидаемые строки этой транзакции подтверждены.
    Проверка без repair не меняет projections и потому пригодна для решения об ack.
    """
    transaction_id = update['transaction_id']
    path = _target_path(update['path'])
    old = path.read_bytes() if path.exists() else b''
    expected = {row['_kg_row_id']: row for row in update['rows']}
    seen = set()
    for line in old.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line.decode('utf-8'))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f'{path.name}: projection повреждена: {exc}') from exc
        if not isinstance(row, dict) or row.get('_kg_transaction_id') != transaction_id:
            continue
        row_id = row.get('_kg_row_id')
        if row_id not in expected:
            raise RuntimeError(f'{path.name}: неизвестная строка транзакции {transaction_id}')
        if row_id in seen:
            raise RuntimeError(f'{path.name}: дубль строки транзакции {transaction_id}')
        if row != expected[row_id]:
            raise RuntimeError(f'{path.name}: конфликт строки транзакции {transaction_id}')
        seen.add(row_id)
    missing = [row for row in update['rows'] if row['_kg_row_id'] not in seen]
    if not missing:
        return True
    if not repair:
        return False
    separator = b'\n' if old and not old.endswith(b'\n') else b''
    stage = _staged_bytes(path, old + separator + _projection_payload(missing),
                          token=transaction_id)
    try:
        os.replace(stage, path)
        _fsync_dir(path.parent)
    except BaseException:
        try:
            stage.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return True


def _projection_errors(transaction: dict, *, repair: bool) -> list[str]:
    errors = []
    for update in transaction['updates']:
        try:
            confirmed = _ensure_projection(update, repair=repair)
        except Exception as exc:
            errors.append(f"{transaction['transaction_id']}: {update['path']}: {exc}")
        else:
            if not confirmed:
                errors.append(f"{transaction['transaction_id']}: {update['path']}: "
                              'projections отсутствуют')
    if errors:
        backups = _backup_dirs(transaction['transaction_id'])
        if backups:
            errors.append(f"{transaction['transaction_id']}: backup: {backups[0]}")
    return errors


def _recover_transactions(transactions: list[dict]) -> None:
    for transaction in transactions:
        _cleanup_stages(transaction['transaction_id'], transaction['updates'])
        for update in transaction['updates']:
            _ensure_projection(update)


def _recover_best_effort(transactions: list[dict]) -> list[str]:
    errors = []
    for transaction in transactions:
        try:
            _cleanup_stages(transaction['transaction_id'], transaction['updates'])
        except Exception as exc:
            errors.append(f"{transaction['transaction_id']}: {exc}")
            continue
        errors.extend(_projection_errors(transaction, repair=True))
    return errors


def _backup_dirs(transaction_id: str) -> list[pathlib.Path]:
    backup_root = ROOT / '.coord' / 'backups' / 'kg-inbox'
    return sorted(path for path in backup_root.glob(f'batch-{transaction_id}-*')
                  if path.is_dir())


def _cleanup_transaction_backups(transaction_id: str) -> None:
    """Удалять backup только после подтверждения projections и сохранения receipt."""
    for backup_dir in _backup_dirs(transaction_id):
        shutil.rmtree(backup_dir, ignore_errors=True)


def _save_receipt(transaction: dict) -> None:
    request_hash = transaction.get('request_hash')
    if not request_hash:
        return
    receipt = {
        'version': JOURNAL_VERSION,
        'transaction_id': transaction['transaction_id'],
        'request_hash': request_hash,
        'batch_hash': transaction['batch_hash'],
        'receipts': transaction['receipts'],
    }
    atomic_write(_receipts_dir() / f'{request_hash}.json',
                 (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def _save_confirmed_receipt(transaction: dict) -> list[str]:
    try:
        _save_receipt(transaction)
    except Exception as exc:
        backups = _backup_dirs(transaction['transaction_id'])
        detail = f'; backup: {backups[0]}' if backups else ''
        return [f"{transaction['transaction_id']}: не сохранить receipt: {exc}{detail}"]
    _cleanup_transaction_backups(transaction['transaction_id'])
    return []


def _lookup_request(request_hash: str, *, recover: bool) -> tuple[dict | None, list[str]]:
    with _transaction_lock():
        prepared, transactions = _merge_journal(_load_journal())
        matches = [tx for tx in transactions if tx.get('request_hash') == request_hash]
        if len(matches) > 1:
            raise RuntimeError(f'журнал: несколько committed для request_hash={request_hash}')
        errors = _recover_best_effort(transactions) if recover else []
        transaction = matches[0] if matches else None
        if transaction is not None:
            # Saved receipt ещё не доказывает наличие projections конкретной партии.
            transaction_errors = _projection_errors(transaction, repair=False)
            if not transaction_errors and not errors:
                transaction_errors = _save_confirmed_receipt(transaction)
            transaction = {**transaction, 'projection_errors': transaction_errors,
                           'recovery_errors': errors}
        # Prepared-only stages are never applied and can be removed safely.
        committed_ids = {tx['transaction_id'] for tx in transactions}
        for transaction_id, record in prepared.items():
            if transaction_id not in committed_ids:
                _cleanup_stages(transaction_id, record['updates'])
        return transaction, errors


def _normalize_updates(updates: list[tuple[pathlib.Path, list[dict]]], *,
                       transaction_id: str, stamp: str) -> list[dict]:
    normalized = []
    for path, rows in updates:
        if not rows:
            continue
        projected = []
        for index, row in enumerate(rows):
            row_id = _digest({'transaction_id': transaction_id, 'index': index, 'row': row})
            projected.append({
                **row,
                'received_at': stamp,
                '_kg_transaction_id': transaction_id,
                '_kg_row_id': row_id,
            })
        normalized.append({
            'transaction_id': transaction_id,
            'path': _target_name(path),
            'input_rows_sha256': _digest(rows),
            'rows_sha256': _digest(projected),
            'rows': projected,
        })
    return normalized


def _transaction_id(request_hash: str | None, batch_hash: str) -> str:
    if request_hash is None:
        return 'kg-' + uuid.uuid4().hex
    return 'kg-' + _digest({'request_hash': request_hash, 'batch_hash': batch_hash})


class ProjectionError(RuntimeError):
    """Projection/receipt failed after commit; the journal, not the exception, is authoritative."""

    def __init__(self, message: str, transaction: dict, backup_dir: pathlib.Path | None = None):
        super().__init__(message)
        self.transaction = transaction
        self.backup_dir = backup_dir


def append_transaction(updates: list[tuple[pathlib.Path, list[dict]]], *,
                       request_hash: str | None = None, batch_hash: str | None = None,
                       files: list[dict] | None = None, receipts: list[dict] | None = None,
                       transaction_id: str | None = None) -> dict | None:
    """Journal one atomic batch, then apply its projections.

    The committed record is the commit point. Ordinary projection errors roll back the
    visible files for compatibility but raise ProjectionError; recovery/retry uses the
    committed journal and does not repeat the commit.
    """
    updates = [(path, rows) for path, rows in updates if rows]
    if not updates:
        return None
    files = files or []
    receipts = receipts or []
    with _transaction_lock():
        prepared, transactions = _merge_journal(_load_journal())
        if request_hash is not None:
            matches = [tx for tx in transactions if tx.get('request_hash') == request_hash]
            if len(matches) > 1:
                raise RuntimeError(f'журнал: несколько committed для request_hash={request_hash}')
            if matches:
                transaction = matches[0]
                errors = _recover_best_effort(transactions)
                projection_errors = _projection_errors(transaction, repair=False)
                if not projection_errors and not errors:
                    projection_errors = _save_confirmed_receipt(transaction)
                return {**transaction, 'replayed': True, 'recovery_errors': errors,
                        'projection_errors': projection_errors}
        # A new commit must not overtake an older committed projection needing recovery.
        _recover_transactions(transactions)

        if batch_hash is None:
            batch_hash = _digest([{'path': _target_name(path), 'rows': rows}
                                  for path, rows in updates])
        transaction_id = transaction_id or _transaction_id(request_hash, batch_hash)
        stamp = dt.datetime.now().isoformat(timespec='seconds')
        prior = prepared.get(transaction_id)
        if prior is not None:
            if (prior.get('request_hash') != request_hash
                    or prior.get('batch_hash') != batch_hash
                    or prior.get('files') != files):
                raise RuntimeError(f'журнал: prepared {transaction_id} не совпадает с партией')
            current_inputs = [{'path': _target_name(path), 'input_rows_sha256': _digest(rows)}
                              for path, rows in updates]
            prior_inputs = [{'path': item['path'], 'input_rows_sha256': item['input_rows_sha256']}
                            for item in prior['updates']]
            if current_inputs != prior_inputs:
                raise RuntimeError(f'журнал: строки prepared {transaction_id} изменились')
            normalized = prior['updates']
        else:
            normalized = _normalize_updates(updates, transaction_id=transaction_id, stamp=stamp)
            prior = _append_sealed_record({
                'version': JOURNAL_VERSION,
                'type': 'prepared',
                'transaction_id': transaction_id,
                'request_hash': request_hash,
                'batch_hash': batch_hash,
                'created_at': stamp,
                'files': files,
                'updates': normalized,
            })

        commit = _append_sealed_record({
            'version': JOURNAL_VERSION,
            'type': 'committed',
            'transaction_id': transaction_id,
            'request_hash': request_hash,
            'batch_hash': batch_hash,
            'committed_at': dt.datetime.now().isoformat(timespec='seconds'),
            'prepared_sha256': prior['record_sha256'],
            'receipts': receipts,
        })
        transaction = {
            'transaction_id': transaction_id,
            'request_hash': request_hash,
            'batch_hash': batch_hash,
            'updates': normalized,
            'receipts': receipts,
            'prepared': prior,
            'committed': commit,
        }

        backup_root = ROOT / '.coord' / 'backups' / 'kg-inbox'
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_dir = pathlib.Path(tempfile.mkdtemp(prefix=f'batch-{transaction_id}-', dir=backup_root))
        staged = []
        try:
            for index, update in enumerate(normalized):
                path = _target_path(update['path'])
                old = path.read_bytes() if path.exists() else None
                separator = b'\n' if old and not old.endswith(b'\n') else b''
                data = (old or b'') + separator + _projection_payload(update['rows'])
                stage = _staged_bytes(path, data, token=transaction_id)
                backup = None
                if old is not None:
                    backup = backup_dir / f'{index}-{path.name}'
                    atomic_write(backup, old)
                staged.append({'path': path, 'stage': stage, 'backup': backup})
            applied = []
            try:
                for item in staged:
                    os.replace(item['stage'], item['path'])
                    applied.append(item)
                for path in {item['path'] for item in staged}:
                    _fsync_dir(path.parent)
            except Exception as exc:
                rollback_errors = []
                for item in reversed(applied):
                    try:
                        if item['backup'] is None:
                            item['path'].unlink(missing_ok=True)
                        else:
                            # Не переносим backup: при ошибке restore он должен остаться на диске.
                            atomic_write(item['path'], item['backup'].read_bytes())
                        _fsync_dir(item['path'].parent)
                    except Exception as rollback_exc:
                        rollback_errors.append(f"{item['path'].name}: {rollback_exc}")
                detail = f'; rollback: {rollback_errors}' if rollback_errors else ''
                raise ProjectionError(f'не удалось записать очереди: {exc}{detail}; '
                                      f'backup: {backup_dir}', transaction, backup_dir) from exc

            projection_errors = _projection_errors(transaction, repair=False)
            if projection_errors:
                raise ProjectionError('; '.join(projection_errors), transaction, backup_dir)
            receipt_errors = _save_confirmed_receipt(transaction)
            if receipt_errors:
                raise ProjectionError('; '.join(receipt_errors), transaction, backup_dir)
            return {**transaction, 'replayed': False, 'recovery_errors': [],
                    'projection_errors': []}
        except ProjectionError:
            raise
        except Exception as exc:
            raise ProjectionError(f'ошибка транзакции после commit: {exc}; backup: {backup_dir}',
                                  transaction, backup_dir) from exc
        finally:
            for item in staged:
                try:
                    item['stage'].unlink(missing_ok=True)
                except OSError:
                    pass


def append(path: pathlib.Path, rows: list[dict], extra: dict) -> int:
    """Совместимая обёртка; serve записывает все очереди одной транзакции."""
    append_transaction([(path, [{**row, **extra} for row in rows])])
    return len(rows)


def _ack_name(path: pathlib.Path) -> str:
    return f'{path.name.split(".", 1)[0]}-kg.json'


def _ack_path(path: pathlib.Path, ack_dir: pathlib.Path | None) -> pathlib.Path:
    if ack_dir is not None:
        return ack_dir / _ack_name(path)
    if path.parent.name == 'outbox':
        return path.parent.parent / 'ack' / _ack_name(path)
    # Documented direct-CLI fallback; never silently discard the acknowledgement.
    return path.parent / _ack_name(path)


def _make_ack(path: pathlib.Path, good: list[dict], bad: list[str], *,
              committed: bool, request_hash: str, batch_hash: str,
              transaction_id: str | None = None, commit_error: str | None = None,
              unknown: bool = False) -> dict:
    if unknown:
        nodes_rows, edge_rows, check_rows = [], [], []
        status, accepted, rolled_back = 'unknown', 0, 0
        reasons = list(bad[:12])
        if commit_error:
            reasons.insert(0, commit_error)
        if not reasons:
            reasons = ['коммит мог произойти, но projections/receipt не подтверждены']
    elif committed:
        nodes_rows = [row for row in good if row['kind'] == 'node']
        edge_rows = [row for row in good if row['kind'] == 'edge']
        check_rows = [row for row in good if row['kind'] == 'check']
        status = 'processed' if good else 'no-op'
        accepted, rolled_back, reasons = len(good), 0, []
    else:
        nodes_rows, edge_rows, check_rows = [], [], []
        status, accepted, rolled_back = 'rejected', 0, len(good)
        reasons = list(bad[:12])
        if not reasons:
            reasons = [commit_error or 'партия не принята целиком: отказ в другом файле']
    ack = {
        'file': path.name,
        'status': status,
        'accepted': accepted,
        'rejected': len(bad),
        'rolled_back': rolled_back,
        'reasons': reasons,
        'ingest': 'tools/kg_inbox.py --serve',
        'by_kind': {'node': len(nodes_rows), 'edge': len(edge_rows), 'check': len(check_rows)},
        'request_hash': request_hash,
        'batch_hash': batch_hash,
        'note': ('принятое лежит в docs/KG-INBOX.jsonl (предложения) и docs/KG-CHECKS.jsonl (проверки). '
                 'Идентификаторы назначает коллектор; tmp остаётся именем строки. '
                 'Источник истины — .coord/kg-inbox/transactions.jsonl; projections восстановимы. '
                 'Commit и ack независимы; retry возвращает сохранённый receipt.'),
    }
    if unknown:
        ack['note'] = ('Коммит мог произойти, но projections этой партии и/или receipt не подтверждены. '
                       'Это не rejected и не rolled_back; retry проверит журнал и восстановит строки.')
    if transaction_id is not None:
        ack['transaction_id'] = transaction_id
    return ack


def _read_inputs(files: list[pathlib.Path]) -> tuple[list[dict], str]:
    results = []
    hashed_files = []
    for path in files:
        raw = None
        error = None
        try:
            if not path.exists():
                raise FileNotFoundError(str(path))
            raw = path.read_bytes()
        except (OSError, UnicodeError) as exc:
            error = f'{path.name}: нет файла' if isinstance(exc, FileNotFoundError) \
                else f'{path.name}: не прочитать файл ({exc})'
        entry = {'file': path.name, 'sha256': _hash_bytes(raw) if raw is not None else None}
        if error is not None:
            entry['error'] = error
        hashed_files.append(entry)
        results.append({'path': path, 'raw': raw, 'error': error, 'good': [], 'bad': []})
    request_hash = _digest({'version': JOURNAL_VERSION, 'files': hashed_files})
    return results, request_hash


def serve(files: list[pathlib.Path], ack_dir: pathlib.Path | None = None) -> int:
    results, request_hash = _read_inputs(files)
    transaction = None
    recovery_errors = []
    projection_errors = []
    transaction_errors = []
    journal_error = None
    commit_unknown = False
    if _journal_path().exists():
        try:
            transaction, recovery_errors = _lookup_request(request_hash, recover=True)
        except Exception as exc:
            journal_error = f'ошибка журнала/recovery: {exc}'
            commit_unknown = True
            transaction = None
            print(journal_error, file=sys.stderr)
        else:
            if transaction is not None:
                projection_errors = list(transaction.get('projection_errors', []))
                recovery_errors = list(transaction.get('recovery_errors', recovery_errors))
                transaction_errors = projection_errors + recovery_errors
    for error in recovery_errors + projection_errors:
        print(f'предупреждение recovery: {error}', file=sys.stderr)

    if transaction is None:
        try:
            nodes, lines = load_nodes(), load_lines()
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            print(f'ошибка чтения kg: {exc}', file=sys.stderr)
            return 1
        texts = {norm(n['text']) for n in nodes.values() if isinstance(n.get('text'), str)}
        for result in results:
            if result['error'] is not None:
                result['bad'] = [result['error']]
                continue
            good, bad = preflight(result['path'], nodes, lines, texts=texts, raw=result['raw'])
            result['good'], result['bad'] = good, bad

    batch_hash = _digest({'files': [
        {'file': result['path'].name, 'rows': result['good']} for result in results
    ]})
    any_bad = any(result['bad'] for result in results)
    commit_error = journal_error
    committed = transaction is not None
    if transaction is not None and transaction_errors:
        commit_error = '; '.join(transaction_errors)

    if transaction is None and not any_bad and commit_error is None:
        has_rows = any(result['good'] for result in results)
        if has_rows:
            transaction_id = _transaction_id(request_hash, batch_hash)
            inbox_rows, check_rows = [], []
            for result in results:
                for row in result['good']:
                    target = check_rows if row['kind'] == 'check' else inbox_rows
                    target.append({**row, 'file': result['path'].name})
            receipts = [
                _make_ack(result['path'], result['good'], result['bad'], committed=True,
                          request_hash=request_hash, batch_hash=batch_hash,
                          transaction_id=transaction_id)
                for result in results
            ]
            try:
                transaction = append_transaction(
                    [(INBOX, inbox_rows), (CHECKS, check_rows)],
                    request_hash=request_hash, batch_hash=batch_hash,
                    files=[{'file': result['path'].name,
                            'sha256': _hash_bytes(result['raw']) if result['raw'] is not None else None}
                           for result in results],
                    receipts=receipts, transaction_id=transaction_id,
                )
                committed = transaction is not None
                if transaction is None:
                    commit_error = 'партия не принята: журнал не создан'
                else:
                    projection_errors = list(transaction.get('projection_errors', []))
                    recovery_errors = list(transaction.get('recovery_errors', []))
                    transaction_errors = projection_errors + recovery_errors
                    if transaction_errors:
                        commit_error = '; '.join(transaction_errors)
            except Exception as exc:
                print(f'ошибка транзакции: {exc}', file=sys.stderr)
                append_error = str(exc)
                # Commit мог завершиться до любой ошибки staging/projection/receipt.
                # Только журнал и восстановленные projections определяют исход.
                try:
                    transaction, recovery_errors = _lookup_request(request_hash, recover=True)
                except Exception as lookup_exc:
                    journal_error = f'ошибка проверки commit/recovery: {lookup_exc}'
                    commit_unknown = True
                    commit_error = f'{append_error}; {journal_error}'
                    print(journal_error, file=sys.stderr)
                    if isinstance(exc, ProjectionError):
                        transaction = exc.transaction
                        projection_errors = [append_error]
                else:
                    if transaction is not None:
                        committed = True
                        projection_errors = list(transaction.get('projection_errors', []))
                        recovery_errors = list(transaction.get('recovery_errors', recovery_errors))
                        transaction_errors = projection_errors + recovery_errors
                        if transaction_errors:
                            commit_error = '; '.join([append_error, *transaction_errors])
                        else:
                            # Один append завершился ошибкой, но recovery полностью подтвердил партию.
                            commit_error = None
                    else:
                        # Успешный lookup доказал отсутствие committed: это обычный отказ.
                        commit_error = append_error
                if transaction is not None:
                    transaction_errors = projection_errors + recovery_errors
                    if transaction_errors and commit_unknown:
                        commit_error = '; '.join([append_error, *transaction_errors])
        else:
            # Валидная пустая партия — явный no-op, а не rejected и не транзакция.
            committed = True

    rc = 1 if any_bad or commit_error or commit_unknown or transaction_errors else 0
    for index, result in enumerate(results):
        path, good, bad = result['path'], result['good'], result['bad']
        ack_batch_hash = transaction.get('batch_hash', batch_hash) if transaction is not None \
            else batch_hash
        if transaction is not None:
            receipts = transaction.get('receipts', [])
            receipts_match = (
                len(receipts) == len(results)
                and all(receipt.get('file') == item['path'].name
                        and receipt.get('request_hash') == request_hash
                        and receipt.get('batch_hash') == transaction.get('batch_hash')
                        for receipt, item in zip(receipts, results))
            )
            if not receipts_match:
                commit_error = 'журнал: сохранённые receipts не соответствуют партии'
                rc = 1
                ack = _make_ack(path, good, bad, committed=True,
                                request_hash=request_hash, batch_hash=ack_batch_hash,
                                transaction_id=transaction.get('transaction_id'),
                                commit_error=commit_error, unknown=True)
            elif transaction_errors or commit_error or commit_unknown:
                reason = commit_error or '; '.join(transaction_errors)
                rc = 1
                ack = _make_ack(path, good, bad, committed=True,
                                request_hash=request_hash, batch_hash=ack_batch_hash,
                                transaction_id=transaction.get('transaction_id'),
                                commit_error=reason, unknown=True)
            else:
                ack = receipts[index]
        else:
            ack = _make_ack(path, good, bad,
                            committed=committed and commit_error is None and not commit_unknown,
                            request_hash=request_hash, batch_hash=batch_hash,
                            commit_error=commit_error, unknown=commit_unknown)
        out = _ack_path(path, ack_dir)
        try:
            atomic_write(out, (json.dumps(ack, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        except Exception as exc:
            # Commit и ack независимы: подтверждённый commit не становится rejected из-за ack.
            # Сохранённый journal receipt позволяет watcher/retry завершить архивирование.
            print(f'ошибка ack {out}: {exc}', file=sys.stderr)
        print(f'{path.name}: принято {ack["accepted"]}, отклонено {ack["rejected"]} ' +
              json.dumps(ack['by_kind'], ensure_ascii=False))
        for reason in ack['reasons'][:6]:
            print('   ', reason[:140])
    return rc


def state() -> int:
    nodes = load_nodes()
    extracted = [n for n in nodes.values()
                 if n.get('provenance') == 'extracted' and n.get('epistemic') != 'refuted']
    no_evidence = [n for n in nodes.values() if not (n.get('evidence') or [])]
    goals = collections.Counter(n.get('kind') for n in extracted)
    print(f'узлов: {len(nodes)}; «только извлечено»: {len(extracted)}; без свидетельств: {len(no_evidence)}')
    print('по видам (извлечённые):', dict(goals))
    print()
    print('цикл A — первые 20 целей (нужна цитата и вердикт):')
    for n in extracted[:20]:
        print(f"  {n['id']:8} {str(n.get('text'))[:70]}")
    print()
    print('цикл C — узлов, у которых нет ни одного ребра в источниках:')
    linked = set()
    for f in ('claims.jsonl', 'definitions.jsonl', 'bridges.jsonl', 'candidates.jsonl'):
        p = ROOT / 'kg' / f
        if p.exists():
            for line in p.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    for rel in (json.loads(line).get('relations') or []):
                        linked.add(str(rel.get('target')))
    lonely = [n for n in nodes.values() if n['id'] not in linked and n.get('kind') in ('claim', 'formula')]
    print(f'  кандидатов: {len(lonely)}')
    for n in lonely[:10]:
        print(f"  {n['id']:8} {str(n.get('text'))[:70]}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description='инбокс предложений для kg/ (3 типа строк)')
    ap.add_argument('--serve', action='store_true')
    ap.add_argument('--ack-dir', default=None,
                    help='каталог ack; иначе <bridge>/ack для outbox, иначе каталог входного файла')
    ap.add_argument('--state', action='store_true')
    ap.add_argument('files', nargs='*')
    args = ap.parse_args(argv)
    if args.state:
        return state()
    files = [pathlib.Path(f) for f in args.files]
    if not args.serve or not files:
        print('укажи файлы: --serve [--ack-dir <каталог>] <файл>.kg.jsonl')
        return 2
    ack_dir = pathlib.Path(args.ack_dir) if args.ack_dir else None
    return serve(files, ack_dir)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
