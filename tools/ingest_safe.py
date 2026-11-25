"""Безопасный приём партии в литературную карту: замок, резервная копия, проверка, откат.

Зачем: `tools/map_ingest.py` перезаписывает `atoms.jsonl` и `edges.jsonl` целиком. Два агента,
запустившие его одновременно, потеряют записи друг друга; партия, ломающая контракт, сломает карту
для всех. Поэтому приём идёт через этот файл:

  1. замок `.coord/locks/map-ingest.lock` (mkdir; протухший ломается по возрасту);
  2. резервная копия `atoms.jsonl` и `edges.jsonl` в `.coord/backups/`;
  3. пробный прогон `map_ingest --dry-run` — если ничего не принято, дальше не идём;
  4. настоящий приём с отчётом;
  5. `checks/map_contract.py`; если красный — откат из резервной копии и повторная проверка.

Права: не-`main` может принимать только свои файлы `literature/map/inbox/<агент>-*`.

Использование:
    python3 tools/ingest_safe.py literature/map/inbox/fast-<раунд>.jsonl --agent fast
    python3 tools/ingest_safe.py <atoms.jsonl> --edges <edges.jsonl> --agent main --report docs/R.md
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
COORD = ROOT / ".coord"
LOCKS = COORD / "locks"
BACKUPS = COORD / "backups"
MAP = ROOT / "literature" / "map"
ATOMS = MAP / "atoms.jsonl"
EDGES = MAP / "edges.jsonl"
LOCK_TTL_S = 300


def now_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S")


def lock():
    LOCKS.mkdir(parents=True, exist_ok=True)
    path = LOCKS / "map-ingest.lock"
    t0 = time.time()
    while True:
        try:
            path.mkdir()
            return path
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > LOCK_TTL_S:
                    stale = path.with_name(f"map-ingest.stale-{os.getpid()}-{time.time_ns()}")
                    os.rename(path, stale)
                    shutil.rmtree(stale, ignore_errors=True)
                    continue
            except OSError:
                pass
            if time.time() - t0 > LOCK_TTL_S:
                raise TimeoutError("приём занят слишком долго")
            time.sleep(0.2)


def backup() -> dict[str, pathlib.Path]:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()
    out = {}
    for src in (ATOMS, EDGES):
        if src.exists():
            dst = BACKUPS / f"{stamp}-{src.name}"
            shutil.copy2(src, dst)
            out[str(src)] = dst
    return out


def restore(saved: dict[str, pathlib.Path]) -> None:
    for src, dst in saved.items():
        shutil.copy2(dst, src)


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
    import json as _json
    import re as _re

    def fracs(text: str) -> set[str]:
        out = set()
        for m in _re.finditer(r"\d+(?:[.,]\d+)?", text or ""):
            tok = m.group(0).replace(",", ".")
            if "." in tok:
                out.add(tok)
        return out

    try:
        incoming = [_json.loads(l) for l in atoms_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        return []
    existing = {}
    atoms_path = ROOT / "literature" / "map" / "atoms.jsonl"
    if atoms_path.exists():
        for l in atoms_path.read_text(encoding="utf-8").splitlines():
            if l.strip():
                a = _json.loads(l)
                existing[a["atom"]] = a
    known = {}
    if registry.exists():
        try:
            known = _json.loads(registry.read_text(encoding="utf-8"))
        except Exception:
            known = {}

    warnings: list[str] = []
    for a in incoming:
        dois = {(w.get("doi") or "").lower() for w in (a.get("works") or [])}
        dois.discard("")
        mine = fracs(a.get("statement") or "")
        for aid, b in existing.items():
            if aid == a.get("atom"):
                continue
            theirs = {(w.get("doi") or "").lower() for w in (b.get("works") or [])}
            if not (dois & theirs):
                continue
            shared = mine & fracs(b.get("statement") or "")
            if len(shared) < 2:
                continue
            key1, key2 = f"{aid}|{a.get('atom')}", f"{a.get('atom')}|{aid}"
            if key1 in known or key2 in known:
                continue
            warnings.append(f"  {a.get('atom')} похож на {aid} (общие дробные: {', '.join(sorted(shared))})")
    return warnings


def looks_like_edges(path: str) -> bool:
    """Файл рёбер (`from`/`to`/`type`) в роли файла атомов — частая ошибка публикации.

    Именно так рёбра партий fast были «приняты» с кодом 0 и не попали в карту: каждая строка отклонялась
    валидатором атомов, а инструмент возвращал успех.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                import json as _json
                row = _json.loads(line)
                return all(k in row for k in ("from", "to", "type")) and "atom" not in row
    except Exception:
        return False
    return False


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="ingest_safe")
    ap.add_argument("atoms_file")
    ap.add_argument("--edges", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--agent", default="main")
    ap.add_argument("--no-contract", action="store_true", help="пропустить проверку контракта (только main)")
    a = ap.parse_args(argv)

    if looks_like_edges(a.atoms_file):
        print("ошибка: это файл РЁБЕР, а не атомов — передайте его через --edges")
        return 1

    atoms_file = pathlib.Path(a.atoms_file)
    if not atoms_file.is_absolute():
        atoms_file = ROOT / atoms_file
    if not atoms_file.exists():
        print(f"ошибка: нет файла {atoms_file}")
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

    base_cmd = [sys.executable, "tools/map_ingest.py", rel]
    if a.edges:
        base_cmd += ["--edges", a.edges]

    lock_path = lock()
    try:
        print("1/4 пробный прогон…")
        rc, out = run(base_cmd + ["--dry-run"])
        print(out)
        if rc != 0:
            print("ошибка: пробный прогон не прошёл — карта не изменена")
            return rc
        warns = duplicate_warnings(atoms_file, ROOT / "docs" / "MAP-DUPLICATES.json")
        if warns:
            print("внимание: возможно, эти факты уже есть в карте (сверка по DOI и дробным числам):")
            for w in warns:
                print(w)
            print("  если это осознанный повтор — внесите пару в docs/MAP-DUPLICATES.json")
        if "принято 0 из" in out:
            print("нечего принимать: 0 новых ячеек — карта не изменена")
            return 0

        saved = backup() if not a.no_contract else {}
        print(f"2/4 резервная копия: {', '.join(p.name for p in saved.values()) or 'не нужна'}")

        print("3/4 приём…")
        cmd = base_cmd + (["--report", a.report] if a.report else [])
        rc, out = run(cmd)
        print(out)
        if rc != 0:
            if saved:
                restore(saved)
                print("ОТКАТ: приём не прошёл, карта восстановлена")
            return rc

        if a.no_contract:
            print("4/4 проверка контракта пропущена (--no-contract)")
            return 0

        print("4/4 контракт…")
        rc, out = run([sys.executable, "checks/map_contract.py"])
        if rc != 0:
            print(out[-2000:])
            restore(saved)
            rc2, out2 = run([sys.executable, "checks/map_contract.py"])
            print("ОТКАТ выполнен; контракт после отката:", "зелёный" if rc2 == 0 else "КРАСНЫЙ — нужен main")
            if rc2 != 0:
                print(out2[-1000:])
            return 1
        print("контракт зелёный; карта принята")
        print("дальше (только main): пересборка kg/ и эмбеддингов")
        return 0
    finally:
        shutil.rmtree(lock_path, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
