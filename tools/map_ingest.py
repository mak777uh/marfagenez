"""Приём внешних партий в карту: нормализация, проверка, проверка локаторов, отчёт.

Внешние партии приходят в формате MAP-FORMAT, но всегда с отклонениями: другой префикс id, нет
`locator_status`, цитата обрезана, DOI не проверен. Этот инструмент приводит их к одному виду и **проверяет
каждый DOI сам** — запросом к OpenAlex, с записью найденного названия. Только после этого ячейка попадает
в `literature/map/atoms.jsonl`.

Правила:
  * атом, не прошедший `checks/map_contract.py`-валидацию, в карту не идёт — он попадает в отчёт;
  * `locator_status=verified` ставится только по результату проверки в этом прогоне;
  * если у работы нет названия в OpenAlex — она остаётся `unverified`;
  * дубли id и дубли рёбер отбрасываются; конфликт разных строк с одним id отклоняет всю партию;
    * все проверки выполняются до первой записи; atoms/edges/report имеют durable prepare+recovery;
  * `--dry-run` действительно ничего не пишет, включая отчёт.

Usage:
    python3 tools/map_ingest.py literature/map/inbox/2026-11-22/*.jsonl \
        --edges literature/map/inbox/2026-11-22/*edges*.jsonl \
        --report literature/map/ingest-2026-11-22.md
"""

from __future__ import annotations

import argparse
import collections
import errno
import fcntl
import glob
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAP = ROOT / "literature" / "map"
ATOMS = MAP / "atoms.jsonl"
EDGES = MAP / "edges.jsonl"
KEY = pathlib.Path(os.environ.get("LITSEARCH_KEY", "/mnt/c/Users/Admin/.dsh/secrets/openalex.key"))
CURL = os.environ.get("LITSEARCH_CURL", "/mnt/c/Windows/System32/curl.exe")
KINDS = {"mechanism", "formula", "condition", "contradiction", "gap", "definition", "measurement", "claim"}
JOURNAL = ROOT / ".coord" / "map-ingest"
TRANSACTION_LOCK = ROOT / ".coord" / "locks" / "map-ingest-transaction.lock"
PROTECTED = (
    "core/", "laws/", "verus/", "checks/", "run.sh", "AGENTS.md",
    "kg/nodes.jsonl", "kg/migrate.py", "kg/kg.py", "tools/coord.py",
)
LOCK_TIMEOUT_S = 300
TXN_VERSION = 1
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
if not NOFOLLOW:
    raise RuntimeError("map_ingest требует O_NOFOLLOW для безопасной записи отчёта")
DIRFLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)


class IngestError(Exception):
    """Контролируемый отказ входа или транзакции."""


class TransactionError(IngestError):
    """Не удалось безопасно завершить durable-транзакцию."""


def load_lines(paths: list[str]) -> list[dict]:
    rows = []
    for pattern in paths:
        for name in sorted(glob.glob(pattern)):
            try:
                text = pathlib.Path(name).read_text(encoding="utf-8")
            except OSError as exc:
                raise IngestError(f"не прочитать {name}: {exc}") from exc
            for lineno, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise IngestError(f"{name}:{lineno}: не JSON: {exc}") from exc
                if not isinstance(row, dict):
                    raise IngestError(
                        f"{name}:{lineno}: ожидался JSON-object, получен {type(row).__name__}"
                    )
                rows.append(row)
    return rows


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return load_lines([str(path)])


def key() -> str | None:
    try:
        return KEY.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def resolve(doi: str, api_key: str | None) -> dict | None:
    url = "https://api.openalex.org/works/https://doi.org/" + doi
    params = "?select=id,doi,title,publication_year,abstract_inverted_index"
    if api_key:
        params += "&api_key=" + api_key
    try:
        out = subprocess.run(
            [CURL, "-sS", "-L", "--compressed", "-m", "40", "-A", "map-ingest/1.0", url + params],
            capture_output=True, text=True, timeout=60,
        )
        data = json.loads(out.stdout)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict) or not data.get("id"):
        return None
    return {
        "openalex": str(data["id"]).rsplit("/", 1)[-1],
        "title": data.get("title") or "",
        "year": data.get("publication_year"),
        "abstract": reconstruct(data.get("abstract_inverted_index")),
    }


def validate(atom: dict) -> list[str]:
    errs = []
    for field in ("atom", "statement", "domain", "kind", "confidence"):
        if not atom.get(field):
            errs.append(f"нет `{field}`")
    for field in ("atom", "statement", "domain"):
        if atom.get(field) is not None and not isinstance(atom.get(field), str):
            errs.append(f"`{field}` должен быть строкой")
    if not isinstance(atom.get("kind"), str) or atom.get("kind") not in KINDS:
        errs.append(f"вид `{atom.get('kind')}`")
    if not isinstance(atom.get("confidence"), str) or atom.get("confidence") not in {"high", "medium", "low"}:
        errs.append(f"уверенность `{atom.get('confidence')}`")

    works = atom.get("works")
    if works is not None and not isinstance(works, list):
        errs.append("`works` должен быть списком")
        works = []
    works = works or []
    gap_protocol = atom.get("kind") == "gap" and atom.get("searched") and atom.get("scope")
    if not works and not gap_protocol:
        errs.append("нет работ")
    for work in works:
        if not isinstance(work, dict):
            errs.append("работа должна быть JSON-object")
            continue
        locators = [work.get(field) for field in ("doi", "arxiv", "pmid", "isbn", "url")]
        if not any(locators):
            errs.append("работа без локатора")
        elif any(value and not isinstance(value, str) for value in locators):
            errs.append("локатор работы должен быть строкой")
        if work.get("access") in ("fragment", "full") and not work.get("quote"):
            errs.append("fragment/full без цитаты")
    if atom.get("kind") == "gap" and not (atom.get("searched") and atom.get("scope")):
        errs.append("gap без searched/scope")
    if atom.get("kind") == "contradiction" and len(works) < 2:
        errs.append("contradiction с одной работой")
    return errs


def reconstruct(inverted: dict | None) -> str | None:
    """Собрать аннотацию из abstract_inverted_index: токены по позициям, через пробел."""
    if not isinstance(inverted, dict) or not inverted:
        return None
    places = []
    try:
        for token, positions in inverted.items():
            for pos in positions:
                places.append((int(pos), token))
    except (TypeError, ValueError):
        return None
    return " ".join(token for _, token in sorted(places))


def norm(text: str | None) -> str:
    if not text:
        return ""
    text = str(text).casefold()
    text = re.sub(r"[^0-9a-zа-яё\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_found(quote: str | None, abstract: str | None) -> bool | None:
    """True/False — проверено по аннотации; None — проверять нечем (нет аннотации)."""
    if not quote or not abstract:
        return None
    return norm(quote) in norm(abstract)


class StoreOnce(argparse.Action):
    """Одноразовый параметр: повтор --report не оставлять «последний победил»."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"{option_string} повторён")
        setattr(namespace, self.dest, values)


class FlagOnce(argparse.Action):
    """Одноразовый булев флаг: повтор считать неоднозначным CLI."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, False):
            parser.error(f"{option_string} повторён")
        setattr(namespace, self.dest, True)


def parse_args(argv: list[str]) -> tuple[list[str], list[str], pathlib.Path | None, bool, bool] | None:
    """ATOMS должны предшествовать --edges; multi-value --edges завершается флагом или `--`.

    После --edges bare-токены считаются рёбрами до следующего known-флага. Поэтому
    естественные вызовы ingest_safe — `atoms --edges e1 [--dry-run]` — работают,
    а `--edges e1 atoms` требует явного `-- atoms` и не съедает атомы молча.
    """
    ap = argparse.ArgumentParser(prog="map_ingest", allow_abbrev=False)
    ap.add_argument("atoms", nargs="+", metavar="ATOMS", help="файлы или glob-шаблоны атомов")
    ap.add_argument("--edges", action="append", nargs="+", default=[], metavar="EDGES",
                    help="файл/glob рёбер; можно перечислить или повторить")
    ap.add_argument("--report", action=StoreOnce, type=pathlib.Path, metavar="REPORT", help="путь к отчёту")
    ap.add_argument("--dry-run", action=FlagOnce, nargs=0, default=False,
                    help="проверить без записи таблиц и отчёта")
    ap.add_argument("--allow-orphans", action=FlagOnce, nargs=0, default=False,
                    help="разрешить новые атомы без связей")
    try:
        a = ap.parse_args(normalize_cli(argv))
    except SystemExit as exc:
        if exc.code == 0:  # --help
            raise
        return None
    return a.atoms, [edge for group in a.edges for edge in group], a.report, a.dry_run, a.allow_orphans


def normalize_cli(argv: list[str]) -> list[str]:
    """Переносит ATOMS перед первым --edges, сохраняя повторы и multi-value edges."""
    value_options = {'--edges', '--report'}
    flags = {'--dry-run', '--allow-orphans'}
    normalized: list[str] = []
    positional: list[str] = []
    edge_groups: list[tuple[int, list[str]]] = []
    index = 0
    explicit_positional = False
    while index < len(argv):
        token = argv[index]
        if token in flags:
            normalized.append(token)
            index += 1
            continue
        if token == '--report':
            normalized.append(token)
            index += 1
            if index < len(argv) and not argv[index].startswith('-'):
                normalized.append(argv[index])
                index += 1
            continue
        if token == '--edges':
            index += 1
            values: list[str] = []
            while index < len(argv) and not argv[index].startswith('-'):
                values.append(argv[index])
                index += 1
            edge_groups.append((len(normalized), values))
            normalized.append(token)
            continue
        if token == '--':
            positional.extend(argv[index + 1:])
            explicit_positional = True
            break
        # Неизвестный флаг и его возможное значение остаются argparse для честного rc=2.
        if token.startswith('-'):
            normalized.append(token)
            index += 1
            continue
        positional.append(token)
        index += 1
    # ATOMS всегда идут первыми. Каждый --edges получает свои значения; порядок
    # edge-файлов сохраняется, а multi-value не зависит от соседнего ATOMS.
    out = positional
    edge_positions = {position for position, _ in edge_groups}
    for position, values in edge_groups:
        out.extend([normalized[position], *values])
    out.extend(token for i, token in enumerate(normalized) if i not in edge_positions)
    return out


def detect_conflicts(incoming: list[dict]) -> None:
    """Один id с разным содержимым — отказ всей партии, а не выбор первой строки."""
    seen: dict[str, str] = {}
    for row in incoming:
        atom_id = row.get("atom")
        if not isinstance(atom_id, str) or not atom_id:
            continue
        fingerprint = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if atom_id in seen and seen[atom_id] != fingerprint:
            raise IngestError(f"конфликт id `{atom_id}` во входе: строки различаются")
        seen[atom_id] = fingerprint


def serialize(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")


def _fsync_fd(fd: int) -> None:
    try:
        os.fsync(fd)
    except OSError as exc:
        if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
            raise


def fsync_dir(path: pathlib.Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        _fsync_fd(fd)
    finally:
        os.close(fd)


def _relative_parts(path: pathlib.Path, anchor: pathlib.Path) -> tuple[str, ...]:
    try:
        return path.absolute().relative_to(anchor.absolute()).parts
    except ValueError as exc:
        raise IngestError(f"выход {path} находится вне разрешённого каталога {anchor}") from exc


def _open_parent(path: pathlib.Path, anchor: pathlib.Path, create: bool = False) -> int:
    """Открыть каждую компоненту каталога через dirfd, без symlink/hardlink."""
    parts = _relative_parts(path, anchor)
    if not parts:
        raise IngestError("выход не может быть корнем")
    flags = DIRFLAGS | NOFOLLOW
    fd = os.open(anchor, flags)
    try:
        for part in parts[:-1]:
            if create:
                try:
                    os.mkdir(part, 0o755, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _check_leaf(fd: int, name: str, protected: bool) -> tuple[bool, int]:
    """Вернуть (существует, mode) для обычного файла; symlink всегда запрещён."""
    if protected and name in {ATOMS.name, EDGES.name}:
        raise IngestError(f"запрещённая запись в таблицу: {name}")
    try:
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return False, 0o644
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise IngestError(f"выход должен быть обычным файлом без hardlink: {name}")
    return True, stat.S_IMODE(info.st_mode)


def _report_parents(path: pathlib.Path, create: bool = False) -> int:
    """Закрепить внешний report по первому реальному каталогу, не создавая его."""
    if path.parent == ROOT or path.parent == MAP:
        return _open_parent(path, path.parent)
    missing = []
    anchor = path.parent
    while not anchor.exists():
        missing.append(anchor.name)
        if anchor == anchor.parent:
            raise IngestError(f"нет каталога для отчёта: {path.parent}")
        anchor = anchor.parent
    fd = _open_parent(path.parent, anchor, create=False)
    try:
        if not path.parent.is_dir():
            raise IngestError(f"нет каталога для отчёта: {path.parent}")
    finally:
        os.close(fd)
    return _open_parent(path, path.parent, create=True)


def validate_output_path(path: pathlib.Path) -> None:
    """Политика и dirfd-проверка выхода; запись повторяет проверку перед replace."""
    for anchor in (ROOT, MAP):
        try:
            rel = path.absolute().relative_to(anchor.absolute())
        except ValueError:
            continue
        is_table = path in {ATOMS, EDGES}
        if rel.parts and rel.parts[0] in PROTECTED:
            raise IngestError("--report не может указывать на PROTECTED-файл")
        if not is_table and rel.name in {ATOMS.name, EDGES.name}:
            raise IngestError("--report не может указывать на atoms.jsonl или edges.jsonl")
        if path.parent == anchor or path in {ATOMS, EDGES}:
            fd = _open_parent(path, anchor)
        else:
            try:
                fd = _open_parent(path, anchor)
            except FileNotFoundError:
                # Каталог отчёта будет создан только на commit через nofollow-dirfd.
                # Не открываем отсутствующий parent как корень: иначе path==parent
                # выглядит как запись в каталог и ломает отчёты reports/orphan.md.
                missing = []
                parent = path.parent
                while not parent.exists() and parent != parent.parent:
                    missing.append(parent.name)
                    parent = parent.parent
                fd = _open_parent(path.parent, parent, create=False)
        try:
            _check_leaf(fd, rel.name, not is_table)
        finally:
            os.close(fd)
        return
    fd = _report_parents(path)
    try:
        _check_leaf(fd, path.name, False)
    finally:
        os.close(fd)


def validate_report_path(path: pathlib.Path, inputs: tuple[pathlib.Path, ...] = ()) -> None:
    if path in inputs:
        raise IngestError("--report не может перезаписать входной atoms/edges-файл")
    validate_output_path(path)


def prepare_output(path: pathlib.Path, data: bytes, anchor: pathlib.Path) -> dict:
    """Durable staged-файл; конечный каталог ещё не создаётся и не изменяется."""
    validate_output_path(path)
    txn_id = f"txn-{os.getpid()}-{time.time_ns()}-{uuid.uuid4().hex}"
    stage_dir = JOURNAL / txn_id
    stage_dir.mkdir(parents=True, mode=0o700)
    target_fd = _open_parent(path, pathlib.Path(path.anchor or "/"), create=path not in {ATOMS, EDGES})
    try:
        exists, mode = _check_leaf(target_fd, path.name, path not in {ATOMS, EDGES})
    finally:
        os.close(target_fd)
    fd, name = tempfile.mkstemp(prefix=f"0-{path.name}.stage-", dir=stage_dir)
    tmp = pathlib.Path(name)
    try:
        with os.fdopen(fd, "wb") as fh:
            os.fchmod(fh.fileno(), mode)
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return {
        "path": str(path), "data_hex": data.hex(), "staged": str(tmp),
        "existed": exists, "mode": mode, "txn_dir": str(stage_dir),
    }


def apply_prepared(item: dict) -> None:
    """Проверить путь заново и заменить только закреплённый dirfd."""
    path = pathlib.Path(item["path"])
    data = bytes.fromhex(item["data_hex"])
    staged = pathlib.Path(item["staged"])
    stage_dir = staged.parent
    if stage_dir.parent != JOURNAL:
        raise TransactionError(f"staged output вне журнала: {staged}")
    journal_fd = os.open(JOURNAL, DIRFLAGS | NOFOLLOW)
    fd = None
    try:
        fd = os.open(stage_dir.name, DIRFLAGS | NOFOLLOW, dir_fd=journal_fd)
        target_fd = _open_parent(path, pathlib.Path(path.anchor or "/"))
        try:
            validate_output_path(path)
            _check_leaf(target_fd, path.name, path not in {ATOMS, EDGES})
            stage_fd = os.open(staged.name, os.O_RDONLY | NOFOLLOW, dir_fd=fd)
            try:
                info = os.fstat(stage_fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise TransactionError(f"staged output не обычный файл: {staged}")
                chunks = []
                while True:
                    chunk = os.read(stage_fd, 1024 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                if b"".join(chunks) != data:
                    raise TransactionError(f"staged-данные изменены: {staged}")
            finally:
                os.close(stage_fd)
            os.replace(staged.name, path.name, src_dir_fd=fd, dst_dir_fd=target_fd)
            _fsync_fd(target_fd)
        finally:
            os.close(target_fd)
        _fsync_fd(fd)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(journal_fd)


def durable_write(path: pathlib.Path, data: bytes) -> None:
    """Одноразовая durable запись вне транзакции (журнал, lock, manifest)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = pathlib.Path(name)
    try:
        with os.fdopen(fd, "wb") as fh:
            os.fchmod(fh.fileno(), 0o644)
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        fsync_dir(path.parent)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _load_json(path: pathlib.Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransactionError(f"не читается {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TransactionError(f"ожидался JSON-object: {path}")
    return value


def _digest(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _validate_manifest(manifest: dict, allow_applied: bool = False) -> None:
    if manifest.get("version") != TXN_VERSION or manifest.get("state") not in {"prepared", "committing"}:
        raise TransactionError("неподдерживаемый manifest транзакции")
    for item in manifest.get("outputs", []):
        if item.get("data_hex") is None or item.get("staged") is None:
            raise TransactionError("неполный staged output")
        staged = pathlib.Path(item["staged"])
        if not staged.is_relative_to(JOURNAL) or staged.parent.parent != JOURNAL:
            raise TransactionError(f"staged output вне журнала: {staged}")
        if not staged.exists() and allow_applied:
            path = pathlib.Path(item["path"])
            if path.is_symlink() or not path.is_file() or path.read_bytes() != bytes.fromhex(item["data_hex"]):
                raise TransactionError(f"output отсутствует после commit: {item['path']}")
            continue
        if not staged.is_file() or staged.is_symlink():
            raise TransactionError(f"staged output отсутствует: {staged}")
        if _digest(staged.read_bytes()) != item.get("sha256"):
            raise TransactionError(f"staged output повреждён: {staged}")


def _recover(txn_dir: pathlib.Path, manifest: dict | None = None) -> list[str]:
    """Roll-forward prepared/committing; committed только убирает staged-файлы."""
    if manifest is None:
        manifest_path = txn_dir / "manifest.json"
        if not manifest_path.exists():
            raise TransactionError(f"транзакция без manifest: {txn_dir}")
        manifest = _load_json(manifest_path)
    _validate_manifest(manifest, allow_applied=manifest.get("state") == "committing")
    if not manifest.get("backups_ready"):
        for index, item in enumerate(manifest["outputs"]):
            path = pathlib.Path(item["path"])
            if path in {ATOMS, EDGES}:
                continue
            try:
                validate_report_path(path)
            except (OSError, TransactionError, IngestError):
                continue
            try:
                backup = txn_dir / f"backup-{index}"
                if item["existed"]:
                    shutil.copy2(path, backup)
                    with backup.open("rb") as fh:
                        _fsync_fd(fh.fileno())
                    fsync_dir(txn_dir)
                manifest["outputs"][index]["backup"] = str(backup) if item["existed"] else None
            except OSError as exc:
                raise TransactionError(f"не сохранить backup {path}: {exc}") from exc
        manifest["backups_ready"] = True
        durable_write(txn_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
        fsync_dir(txn_dir)
    if manifest.get("state") == "prepared":
        manifest["state"] = "committing"
        manifest["commit_attempt"] = manifest.get("commit_attempt", 0) + 1
        durable_write(txn_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
    recovered = []
    for item in manifest["outputs"]:
        path = pathlib.Path(item["path"])
        staged = pathlib.Path(item["staged"])
        if not staged.exists():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != bytes.fromhex(item["data_hex"]):
                raise TransactionError(f"output отсутствует после commit: {path}")
        else:
            try:
                apply_prepared(item)
            except (OSError, TransactionError, IngestError):
                if path.is_symlink() or not path.is_file() or path.read_bytes() != bytes.fromhex(item["data_hex"]):
                    raise
        recovered.append(item["path"])
    manifest["state"] = "committed"
    durable_write(txn_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
    return recovered


def recover_transactions() -> list[str]:
    """Восстановить все durable партии; вызывается под отдельным transaction flock."""
    if not JOURNAL.exists():
        return []
    recovered = []
    for txn_dir in sorted(JOURNAL.glob("txn-*")):
        if not txn_dir.is_dir() or txn_dir.is_symlink():
            continue
        manifests = list(txn_dir.glob("manifest.json"))
        if not manifests:
            # Незавершённая prepare до manifest: конечные файлы ещё не менялись.
            shutil.rmtree(txn_dir, ignore_errors=True)
            continue
        manifest = _load_json(txn_dir / "manifest.json")
        if manifest.get("state") != "committed":
            recovered += _recover(txn_dir, manifest)
        shutil.rmtree(txn_dir, ignore_errors=True)
    return recovered


def restore(path: pathlib.Path, saved: pathlib.Path | None) -> None:
    # Совместимость с прежними локальными проверками отката.
    if saved is None:
        path.unlink(missing_ok=True)
        if path.parent.exists():
            fsync_dir(path.parent)
    else:
        atomic_write(path, saved.read_bytes())



def atomic_write(path: pathlib.Path, data: bytes) -> None:
    """Совместимость: durable replace через проверенный dirfd."""
    path = path.absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    anchor = ROOT if path.is_relative_to(ROOT) else pathlib.Path(path.anchor or "/")
    fd = _open_parent(path, anchor, create=True)
    tmp_name = None
    try:
        exists, mode = _check_leaf(fd, path.name, path not in {ATOMS, EDGES})
        tmp_name = f".{path.name}.{uuid.uuid4().hex}.tmp"
        out_fd = os.open(tmp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW, mode, dir_fd=fd)
        try:
            with os.fdopen(out_fd, "wb") as fh:
                os.fchmod(fh.fileno(), mode)
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path.name, src_dir_fd=fd, dst_dir_fd=fd)
            try:
                os.fsync(fd)
            except OSError as exc:
                if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                    raise
        finally:
            if tmp_name is not None:
                try:
                    os.unlink(tmp_name, dir_fd=fd)
                except FileNotFoundError:
                    pass
    finally:
        os.close(fd)


def commit_batch(
    atoms_data: bytes | None,
    edges_data: bytes | None,
    report_path: pathlib.Path | None = None,
    report_data: bytes | None = None,
) -> list[str]:
    """Durable multi-file transaction: prepare -> commit -> recovery.

    Все outputs сначала проверяются и fsync-ятся в staged-файлах. Manifest с
    точными путями/байтами сохраняется до первого replace. SIGKILL между
    заменами оставляет prepared/committing, который следующий вызов безопасно
    доводит до конца без повторного добавления строк.
    """
    writes: list[tuple[pathlib.Path, bytes]] = []
    if atoms_data is not None:
        writes.append((ATOMS, atoms_data))
    if edges_data is not None:
        writes.append((EDGES, edges_data))
    if report_path is not None and report_data is not None:
        writes.append((report_path.absolute(), report_data))
    if not writes:
        return []

    TRANSACTION_LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock_fh = TRANSACTION_LOCK.open("a+b")
    deadline = time.monotonic() + LOCK_TIMEOUT_S
    try:
        while True:
            try:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TransactionError("другая map_ingest транзакция идёт слишком долго")
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        recovered = recover_transactions()

        txn_id = f"txn-{os.getpid()}-{time.time_ns()}-{uuid.uuid4().hex}"
        txn_dir = JOURNAL / txn_id
        txn_dir.mkdir(parents=True, mode=0o700)
        manifest = {"version": TXN_VERSION, "state": "prepared", "outputs": []}
        prepared_dirs = []
        try:
            for path, data in writes:
                item = prepare_output(path, data, JOURNAL)
                item["sha256"] = _digest(data)
                manifest["outputs"].append(item)
                prepared_dirs.append(pathlib.Path(item["txn_dir"]))
            durable_write(txn_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
            fsync_dir(JOURNAL)
            _recover(txn_dir, manifest)
        except BaseException:
            if not (txn_dir / "manifest.json").exists():
                for stage_dir in prepared_dirs:
                    shutil.rmtree(stage_dir, ignore_errors=True)
            # С сохранённым manifest/staged не удаляем ничего: retry должен
            # безопасно довести партию до конца либо явно отказать.
            raise
        shutil.rmtree(txn_dir, ignore_errors=True)
        return recovered
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fh.close()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 2
    parsed = parse_args(argv)
    if parsed is None:
        return 2
    patterns, edge_patterns, report_path, dry, allow_orphans = parsed
    if report_path is not None:
        path = pathlib.Path(os.path.abspath(report_path))
        try:
            validate_report_path(path)
        except (OSError, IngestError) as exc:
            print(f"ошибка: {exc}", file=sys.stderr)
            return 2
        report_path = path

    try:
        # Recovery выполняется и для duplicate-only/rejected: после SIGKILL карта
        # могла уже измениться, и dry-run/preflight не должны скрывать этот commit.
        recover_transactions()
        incoming = load_lines(patterns)
        detect_conflicts(incoming)
        existing = load_jsonl(ATOMS)
        known = {a.get("atom") for a in existing if isinstance(a.get("atom"), str)}

        resolved: dict[str, dict | None] = {}
        dios = set()
        for atom in incoming:
            works = atom.get("works")
            if isinstance(works, list):
                for work in works:
                    if isinstance(work, dict) and isinstance(work.get("doi"), str) and work["doi"]:
                        dios.add(work["doi"].lower())
        api_key = key()
        for doi in sorted(dios):
            resolved[doi] = resolve(doi, api_key)

        accepted, rejected = [], []
        incoming_seen = set()
        for atom in incoming:
            if atom.get("kind") == "gap" and not (atom.get("searched") and atom.get("scope")):
                note = str(atom.get("notes") or "")
                match = re.search(r"searched[:\s]+(.{3,120}?)(?:;|$)", note, re.I)
                atom["searched"] = {
                    "note": match.group(1).strip() if match else "внешняя партия", "source": "notes",
                }
                conditions = atom.get("conditions")
                scope = " ".join(str(x) for x in conditions)[:160] if isinstance(conditions, list) else ""
                atom["scope"] = atom.get("scope") or (scope or "не указано")
            errs = validate(atom)
            if errs:
                rejected.append((atom.get("atom"), "; ".join(errs)))
                continue
            atom_id = atom["atom"]
            if atom_id in known:
                rejected.append((atom_id, "дубль id"))
                continue
            if atom_id in incoming_seen:
                rejected.append((atom_id, "дубль id во входе"))
                continue

            verified = True
            quote_broken = False
            for work in atom.get("works") or []:
                doi = (work.get("doi") or "").lower()
                if not doi:
                    verified = False
                    continue
                meta = resolved.get(doi)
                if meta:
                    work["resolved_title"] = meta["title"]
                    work["resolved_year"] = meta["year"]
                    work.setdefault("locator", "doi:" + doi)
                    if work.get("access") == "abstract":
                        found = quote_found(work.get("quote"), meta.get("abstract"))
                        work["quote_found"] = found
                        if found is False:
                            quote_broken = True
                else:
                    verified = False
            atom["locator_status"] = "verified" if verified else "unverified"
            if quote_broken:
                atom["confidence"] = "low"
                atom["notes"] = str(atom.get("notes") or "") + " [цитата не найдена в аннотации: проверить текст]"
            if atom.get("confidence") == "high" and not atom.get("formula") and not any(
                    w.get("quote") for w in atom.get("works") or []):
                atom["confidence"] = "medium"
            existing.append(atom)
            known.add(atom_id)
            incoming_seen.add(atom_id)
            accepted.append(atom)

        edges_new = []
        edges_data = None
        if edge_patterns:
            have = load_jsonl(EDGES)
            seen = {(e.get("from"), e.get("to"), e.get("type")) for e in have}
            incoming_edges = load_lines(edge_patterns)
            ids = {a.get("atom") for a in existing}
            for edge in incoming_edges:
                if not all(isinstance(edge.get(field), str) and edge.get(field) for field in ("from", "to", "type")):
                    raise IngestError(f"ребро {incoming_edges.index(edge) + 1} без строковых from/to/type")
                if edge.get("from") not in ids or edge.get("to") not in ids:
                    continue
                point = (edge.get("from"), edge.get("to"), edge.get("type"))
                if point in seen:
                    continue
                have.append(edge)
                seen.add(point)
                edges_new.append(edge)
            edges_data = serialize(have)

        # Все проверки, включая orphan-rule, завершены до первой записи.
        new_ids = [a["atom"] for a in accepted]
        lonely = []
        if new_ids:
            degree = collections.Counter()
            for edge in edges_new:
                degree[edge.get("from")] += 1
                degree[edge.get("to")] += 1
            lonely = [atom_id for atom_id in new_ids if degree[atom_id] == 0]
        if lonely and not allow_orphans:
            print(f"ОТКАЗ: {len(lonely)} новых ячеек без единой связи: {', '.join(lonely[:8])}"
                  f"{' …' if len(lonely) > 8 else ''}")
            print("  правило: новая ячейка должна иметь хотя бы одну связь с существующей")
            print("  карта не изменена; обход — --allow-orphans (осознанный случай)")
            return 1

        by_domain = collections.Counter(a["domain"] for a in accepted)
        by_kind = collections.Counter(a["kind"] for a in accepted)
        verified_dois = sum(1 for meta in resolved.values() if meta)
        dup_only = bool(rejected) and all("дубль" in str(reason) for _, reason in rejected)
        all_rejected = bool(incoming) and not accepted and not dup_only

        report_data = None
        if report_path is not None:
            lines = [
                "# Приём партий в карту",
                "",
                f"Входных ячеек: {len(incoming)}; принято: **{len(accepted)}**; отклонено: **{len(rejected)}**; "
                f"рёбер добавлено: {len(edges_new)}.",
                "",
                f"DOI проверено через OpenAlex: **{verified_dois} из {len(resolved)}**; непроверенные помечены "
                "`locator_status: unverified`.",
                "",
                "## Принято по областям",
                "",
                "| область | ячеек |",
                "|---|---|",
            ]
            lines += [f"| {k} | {v} |" for k, v in sorted(by_domain.items())]
            lines += ["", "По видам: " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())), ""]
            if rejected:
                lines += ["## Отклонено", "", "| id | причина |", "|---|---|"]
                lines += [f"| {i} | {why} |" for i, why in rejected[:80]]
            report_data = ("\n".join(lines) + "\n").encode("utf-8")

        if not dry:
            recovered = commit_batch(serialize(existing) if accepted else None, edges_data, report_path, report_data)
            for name in recovered:
                print(f"recovered: {name}")

        print(f"принято {len(accepted)} из {len(incoming)}; рёбер +{len(edges_new)}")
        print(f"DOI проверено {verified_dois} из {len(resolved)}; в карте всего {len(existing)} ячеек")
        if not incoming:
            print("вход пуст: новых ячеек нет, приём не выполнен")
        if rejected:
            print(f"отклонено {len(rejected)} — см. отчёт")
            if dup_only and not accepted:
                print("все строки уже есть в карте — повторный приём, это не ошибка")
            if all_rejected:
                print("ВЕСЬ ВХОД ОТКЛОНЁН: проверьте формат (рёбра передаются через --edges, не как atoms)")
        status = "empty" if not incoming else "accepted" if accepted else "duplicate-only" if dup_only else "rejected"
        print(f"status: {status}")
        if dry:
            print("dry-run: файлы не записаны")
            return 1 if all_rejected else 0
        if report_path is not None:
            print(f"отчёт: {report_path}")
        return 1 if all_rejected else 0
    except RuntimeError as exc:
        print(f"КРИТИЧНО: {exc}", file=sys.stderr)
        return 1
    except (IngestError, OSError) as exc:
        print(f"ОШИБКА: {exc}; карта не изменена", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
