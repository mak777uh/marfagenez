"""Безопасный приём партии в литературную карту: flock, резервная копия, проверка, откат.

Зачем: `tools/map_ingest.py` перезаписывает `atoms.jsonl` и `edges.jsonl`. Два агента,
запустившие его одновременно, потеряют записи друг друга; партия, ломающая контракт, сломает карту
для всех. Поэтому приём идёт через этот файл:

  1. Linux `fcntl.flock` на `.coord/locks/map-ingest.lock` с ожиданием и таймаутом;
  2. пробный прогон `map_ingest --dry-run` под тем же замком;
  3. уникальная резервная копия `atoms.jsonl`, `edges.jsonl` и отчёта во временном каталоге;
  4. настоящий приём с отчётом; при исключении или ненулевом коде — восстановление всех трёх файлов;
  5. `checks/map_contract.py`; если красный — откат из резервной копии и повторная проверка.

Права: не-`main` может принимать только свои файлы `literature/map/inbox/<агент>-*`.

Использование:
    python3 tools/ingest_safe.py literature/map/inbox/fast-<раунд>.jsonl --agent fast
    python3 tools/ingest_safe.py <atoms.jsonl> --edges <edges.jsonl> --agent main --report docs/R.md
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import errno
import fcntl
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
COORD = ROOT / ".coord"
LOCKS = COORD / "locks"
BACKUPS = COORD / "backups"
MAP = ROOT / "literature" / "map"
ATOMS = MAP / "atoms.jsonl"
EDGES = MAP / "edges.jsonl"
LOCK_TIMEOUT_S = 300
# Согласованные Markdown-имена: docs/DIP-*.md и literature/map/ingest-*.md.
NON_MAIN_REPORTS = ((ROOT / "docs", "DIP-", ".md"), (MAP, "ingest-", ".md"))


def _load_protected() -> tuple[str, ...]:
    """Прочитать PROTECTED из tools/coord.py, не выполняя его и не создавая pyc."""
    path = ROOT / "tools" / "coord.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PROTECTED" for target in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise RuntimeError("в tools/coord.py не найдена константа PROTECTED")


PROTECTED = _load_protected()


@contextlib.contextmanager
def lock(timeout: float = LOCK_TIMEOUT_S):
    """Взаимоисключение на открытом файле; TTL и удаление lock-файла не используются."""
    LOCKS.mkdir(parents=True, exist_ok=True)
    path = LOCKS / "map-ingest.lock"
    fh = path.open("a+b")
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("приём занят слишком долго")
                time.sleep(min(0.05, remaining))
        yield
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def fsync_dir(path: pathlib.Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise
    finally:
        os.close(fd)


def atomic_restore(path: pathlib.Path, saved: pathlib.Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if saved is None:
        path.unlink(missing_ok=True)
        fsync_dir(path.parent)
        return
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.restore-", suffix=".tmp", dir=path.parent)
    tmp = pathlib.Path(name)
    try:
        with os.fdopen(fd, "wb") as fh:
            os.fchmod(fh.fileno(), mode)
            fh.write(saved.read_bytes())
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


def backup(container: pathlib.Path, report_path: pathlib.Path | None = None) -> dict[pathlib.Path, pathlib.Path | None]:
    """Точные байты таблиц и отчёта; None означает, что файла до приёма не было."""
    saved: dict[pathlib.Path, pathlib.Path | None] = {}
    paths = [ATOMS, EDGES]
    if report_path is not None:
        paths.append(report_path)
    for index, src in enumerate(dict.fromkeys(paths)):
        if src.exists():
            dst = container / f"{index}-{src.name}"
            shutil.copy2(src, dst)
            saved[src] = dst
        else:
            saved[src] = None
    return saved


def restore(saved: dict[pathlib.Path, pathlib.Path | None]) -> None:
    failures = []
    for src, dst in saved.items():
        try:
            atomic_restore(src, dst)
        except BaseException as exc:
            # Даже повторный KeyboardInterrupt не должен прервать откат остальных файлов.
            failures.append(f"{src}: {exc}")
    if failures:
        raise RuntimeError("ОТКАТ НЕ ВЫПОЛНЕН: " + "; ".join(failures))


def run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out.strip()


def duplicate_warnings(atoms_file: pathlib.Path, registry: pathlib.Path) -> list[str]:
    """Предупреждения «этот факт уже есть в карте» до приёма.

    Повод (25.11.2026): партия принесла `FAST-S2M-02`, дублирующий `DIP21B-0003` — приём этого не видел,
    дубль заметил человек. Признак тот же, что в `tools/map_duplicates.py`: тот же DOI и не меньше двух
    общих ДРОБНЫХ чисел (целые совпадают у чего угодно, а пересказ одного факта даёт сходство текста 0,1).
    """
    def fracs(text: str) -> set[str]:
        out = set()
        for m in re.finditer(r"\d+(?:[.,]\d+)?", text or ""):
            tok = m.group(0).replace(",", ".")
            if "." in tok:
                out.add(tok)
        return out

    try:
        incoming = [json.loads(line) for line in atoms_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return []
    existing = {}
    atoms_path = ROOT / "literature" / "map" / "atoms.jsonl"
    if atoms_path.exists():
        for line in atoms_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                a = json.loads(line)
                existing[a["atom"]] = a
    known = {}
    if registry.exists():
        try:
            known = json.loads(registry.read_text(encoding="utf-8"))
        except Exception:
            known = {}

    warnings: list[str] = []
    for a in incoming:
        if not isinstance(a, dict):
            continue
        works = a.get("works") if isinstance(a.get("works"), list) else []
        dois = {(w.get("doi") or "").lower() for w in works
                if isinstance(w, dict) and isinstance(w.get("doi"), str)}
        dois.discard("")
        mine = fracs(str(a.get("statement") or ""))
        for aid, b in existing.items():
            if aid == a.get("atom"):
                continue
            theirs_works = b.get("works") if isinstance(b.get("works"), list) else []
            theirs = {(w.get("doi") or "").lower() for w in theirs_works
                      if isinstance(w, dict) and isinstance(w.get("doi"), str)}
            if not (dois & theirs):
                continue
            shared = mine & fracs(str(b.get("statement") or ""))
            if len(shared) < 2:
                continue
            key1, key2 = f"{aid}|{a.get('atom')}", f"{a.get('atom')}|{aid}"
            if key1 in known or key2 in known:
                continue
            warnings.append(f"  {a.get('atom')} похож на {aid} (общие дробные: {', '.join(sorted(shared))})")
    return warnings


def looks_like_edges(path: str) -> bool:
    """Файл рёбер (`from`/`to`/`type`) в роли файла атомов — частая ошибка публикации."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                return isinstance(row, dict) and all(k in row for k in ("from", "to", "type")) and "atom" not in row
    except Exception:
        return False
    return False


def _is_protected(path: pathlib.Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    for entry in PROTECTED:
        protected = entry.rstrip("/")
        if rel == protected or rel.startswith(protected + "/"):
            return True
    return False


def resolve_report(value: str, agent: str, inputs: tuple[pathlib.Path | None, ...]) -> pathlib.Path:
    """Проверить лексический путь; dirfd/O_NOFOLLOW проверяются снова при записи."""
    requested = pathlib.Path(value)
    if not requested.is_absolute():
        requested = ROOT / requested
    path = pathlib.Path(os.path.abspath(requested))
    if path in (ATOMS, EDGES):
        raise ValueError("--report не может указывать на atoms.jsonl или edges.jsonl")
    if path.name in {ATOMS.name, EDGES.name}:
        raise ValueError("--report не может указывать на atoms.jsonl или edges.jsonl")
    if _is_protected(path):
        raise ValueError("--report не может указывать на PROTECTED-файл")
    if path in inputs:
        raise ValueError("--report не может перезаписать входной atoms/edges-файл")
    if path.exists() and not path.is_file():
        raise ValueError("--report должен быть файлом, а не каталогом")
    if agent != "main":
        if not path.is_relative_to(ROOT):
            raise ValueError("не-main может писать отчёт только внутри репозитория")
        allowed = False
        for directory, prefix, suffix in NON_MAIN_REPORTS:
            if path.parent == directory and path.name.startswith(prefix) and path.name.endswith(suffix):
                allowed = True
                break
        if not allowed:
            names = ", ".join(
                (directory.relative_to(ROOT).as_posix() + "/" + prefix + "*" + suffix)
                for directory, prefix, suffix in NON_MAIN_REPORTS
            )
            raise ValueError(f"не-main может писать отчёт только в: {names}")
    return path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="ingest_safe")
    ap.add_argument("atoms_file")
    ap.add_argument("--edges", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--agent", default="main")
    ap.add_argument("--no-contract", action="store_true", help="пропустить проверку контракта (только main)")
    a = ap.parse_args(argv)

    saved = None
    backup_dir = None
    preserve_backup = False
    try:
        atoms_file = pathlib.Path(a.atoms_file)
        if not atoms_file.is_absolute():
            atoms_file = ROOT / atoms_file
        atoms_file = atoms_file.resolve()
        if not atoms_file.is_file():
            print(f"ошибка: нет файла {atoms_file}")
            return 1
        if looks_like_edges(str(atoms_file)):
            print("ошибка: это файл РЁБЕР, а не атомов — передайте его через --edges")
            return 1

        rel = atoms_file.relative_to(ROOT).as_posix() if atoms_file.is_relative_to(ROOT) else str(atoms_file)
        if a.agent != "main":
            allowed = pathlib.PurePosixPath(rel)
            if allowed.parts[:3] != ("literature", "map", "inbox") or not allowed.name.startswith(f"{a.agent}-"):
                print(f"ошибка: агент {a.agent} может принимать только свои файлы "
                      f"literature/map/inbox/{a.agent}-*; получено: {rel}")
                return 1
        if a.no_contract and a.agent != "main":
            print("ошибка: --no-contract разрешён только main")
            return 1

        edges_input = None
        if a.edges:
            edges_input = pathlib.Path(a.edges)
            if not edges_input.is_absolute():
                edges_input = ROOT / edges_input
            edges_input = edges_input.resolve()

        report_path = None
        report_requested = None
        if a.report:
            try:
                report_path = resolve_report(a.report, a.agent, (atoms_file, edges_input))
                report_requested = a.report
            except (OSError, RuntimeError, ValueError) as exc:
                print(f"ошибка: {exc}", file=sys.stderr)
                return 2

        base_cmd = [sys.executable, "tools/map_ingest.py", rel]
        if edges_input is not None:
            base_cmd += ["--edges", str(edges_input)]

        with lock():
            result = 1
            check_after_rollback = False
            try:
                print("1/4 пробный прогон…")
                rc, out = run(base_cmd + ["--dry-run"])
                print(out)
                if rc != 0:
                    print("ошибка: пробный прогон не прошёл — карта не изменена")
                    return rc
                if re.search(r"^принято 0 из \d+", out, re.M):
                    if "status: duplicate-only" in out:
                        print("нечего принимать: все строки уже есть в карте — успешный повтор, не новый приём")
                        return 0
                    if "status: empty" in out:
                        print("вход пуст — приём не выполнен, карта не изменена")
                        return 0
                    print("ошибка: новых ячеек нет, но это не объявленный дубль — приём не выполнен")
                    return 1

                warns = duplicate_warnings(atoms_file, ROOT / "docs" / "MAP-DUPLICATES.json")
                if warns:
                    print("внимание: возможно, эти факты уже есть в карте (сверка по DOI и дробным числам):")
                    for w in warns:
                        print(w)
                    print("  если это осознанный повтор — внесите пару в docs/MAP-DUPLICATES.json")

                BACKUPS.mkdir(parents=True, exist_ok=True)
                backup_dir = pathlib.Path(tempfile.mkdtemp(
                    prefix=f"map-ingest-{os.getpid()}-{time.time_ns()}-", dir=BACKUPS,
                ))
                try:
                    saved = backup(backup_dir, report_path)
                except BaseException:
                    shutil.rmtree(backup_dir, ignore_errors=True)
                    backup_dir = None
                    raise
                print(f"2/4 резервная копия: {', '.join(p.name for p in saved.values() if p) or 'таблиц не было'}")

                # С этого места любое прерывание требует отката; backup нельзя удалять до его успеха.
                preserve_backup = True
                print("3/4 приём…")
                cmd = base_cmd + (["--report", str(report_requested)] if report_requested is not None else [])
                rc, out = run(cmd)
                print(out)
                if rc != 0:
                    result = rc
                elif a.no_contract:
                    print("4/4 проверка контракта пропущена (--no-contract)")
                    result = 0
                else:
                    print("4/4 контракт…")
                    rc, out = run([sys.executable, "checks/map_contract.py"])
                    if rc != 0:
                        print(out[-2000:])
                        result = 1
                        check_after_rollback = True
                    else:
                        print("контракт зелёный; карта принята")
                        print("дальше (только main): пересборка kg/ и эмбеддингов")
                        result = 0
                if result == 0:
                    preserve_backup = False
            except KeyboardInterrupt:
                result = 130
                print("ОТКАТ: приём прерван", file=sys.stderr)
            except Exception as exc:
                result = 1
                print(f"ошибка приёма: {exc}", file=sys.stderr)
            finally:
                if saved is not None and preserve_backup:
                    try:
                        restore(saved)
                    except BaseException as rollback_exc:
                        preserve_backup = True
                        print(f"КРИТИЧНО: {rollback_exc}", file=sys.stderr)
                        print(f"Резервная копия сохранена: {backup_dir}", file=sys.stderr)
                        for src, dst in saved.items():
                            if dst is not None:
                                print(f"  {src} <- {dst}", file=sys.stderr)
                        if result == 0:
                            result = 1
                    else:
                        preserve_backup = False
                        print("ОТКАТ: исходные таблицы и отчёт восстановлены", file=sys.stderr)

            if check_after_rollback and not preserve_backup:
                rc2, out2 = run([sys.executable, "checks/map_contract.py"])
                print("ОТКАТ выполнен; контракт после отката:", "зелёный" if rc2 == 0 else "КРАСНЫЙ — нужен main")
                if rc2 != 0:
                    print(out2[-1000:])
            return result
    except KeyboardInterrupt:
        print("ОТКАТ: приём прерван до изменения карты", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ошибка приёма: {exc}", file=sys.stderr)
        return 1
    finally:
        if backup_dir is not None and not preserve_backup:
            shutil.rmtree(backup_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
