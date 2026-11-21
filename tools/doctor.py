"""Is this machine able to do the literature work at all? One command, honest answers.

The literature side of the repository spans two operating systems: WSL runs the gate and owns the files,
Windows owns the network. A missing venv, a missing model or a rejected key does not announce itself — it
shows up later as an empty result that looks like "nothing found". This tool checks the prerequisites and
says which ones are missing, without touching the network except for one optional budget probe.

Checks:
  venv        — the Windows venv and its console scripts (paper-search, lixplore, …);
  models      — the fastembed cache directory;
  keys        — presence and permissions of the OpenAlex key file (never prints the key);
  budget      — optional `--budget`: live `/rate-limit` through `tools/budget.py`;
  files       — registry blocks, `papers/`, `literature/runs/`, candidates;
  skills      — installed skill directories, if present.

Usage:
    python3 tools/doctor.py
    python3 tools/doctor.py --budget
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
VENV = pathlib.Path(os.environ.get("LITSEARCH_VENV", "/mnt/c/Users/Admin/.dsh/tools/sci-venv/Scripts"))
MODELS = pathlib.Path(os.environ.get("FASTEMBED_CACHE_PATH", "/mnt/c/Users/Admin/.dsh/tools/models"))
KEY = pathlib.Path(os.environ.get("LITSEARCH_KEY", "/mnt/c/Users/Admin/.dsh/secrets/openalex.key"))
SKILLS = pathlib.Path(os.environ.get("DSH_SKILLS", "/mnt/c/Users/Admin/.dsh/skills"))

TOOLS = ["paper-search.exe", "lixplore.exe", "paperseek.exe", "mosaic.exe", "scholar-mcp.exe"]


def line(ok: bool, name: str, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'MISS'} {name}{(' — ' + detail) if detail else ''}")


def check_venv() -> int:
    print("venv:")
    missing = 0
    if not VENV.exists():
        line(False, "каталог venv", str(VENV))
        return 1
    for tool in TOOLS:
        path = VENV / tool
        if path.exists():
            line(True, tool)
        else:
            line(False, tool)
            missing += 1
    return missing


def check_models() -> int:
    print("модели:")
    if not MODELS.exists():
        line(False, "каталог моделей", str(MODELS))
        return 1
    found = [p.name for p in MODELS.iterdir() if p.is_dir()]
    for name in found:
        line(True, name)
    return 0 if found else 1


def check_key() -> int:
    print("ключи:")
    if not KEY.exists():
        line(False, "OpenAlex", str(KEY))
        return 1
    size = KEY.stat().st_size
    if str(KEY).startswith("/mnt/"):
        # Windows filesystem through DrvFs: POSIX bits are always 0o777 here, so checking them would
        # report a harmless lie. Only the size is meaningful on this side.
        line(size > 10, "OpenAlex", f"размер {size} Б, права не применимы (Windows-файл)")
        return 0 if size > 10 else 1
    mode = oct(KEY.stat().st_mode & 0o777)
    ok = size > 10 and mode in ("0o600", "0o400")
    line(ok, "OpenAlex", f"размер {size} Б, права {mode}")
    return 0 if ok else 1


def check_files() -> int:
    print("файлы:")
    bad = 0
    registry = ROOT / "docs" / "ELEPHANT-LITERATURE.md"
    blocks = 0
    if registry.exists():
        blocks = registry.read_text(encoding="utf-8").count('"schema"') + registry.read_text(
            encoding="utf-8").count('"L": "L-')
    line(blocks > 0, "реестр литературы", f"блоков: {blocks}")
    papers = sorted(p.name for p in (ROOT / "papers").iterdir()) if (ROOT / "papers").exists() else []
    line(bool(papers), "papers/", f"файлов: {len(papers)}")
    runs = sorted((ROOT / "literature" / "runs").glob("*.json")) if (ROOT / "literature" / "runs").exists() else []
    line(bool(runs), "literature/runs/", f"снимков: {len(runs)}")
    cands = ROOT / "kg" / "candidates.jsonl"
    count = len(cands.read_text(encoding="utf-8").splitlines()) if cands.exists() else 0
    line(True, "карантин кандидатов", f"строк: {count}")
    if not (ROOT / "checks" / "literature_contract.py").exists():
        line(False, "литературный контракт")
        bad += 1
    return bad


def check_skills() -> int:
    print("навыки:")
    if not SKILLS.exists():
        line(False, "каталог навыков", str(SKILLS))
        return 0  # not required for the gate
    for name in ("paper-lookup", "database-lookup", "literature-review"):
        path = SKILLS / name
        line(path.exists(), name)
    return 0


def check_budget() -> int:
    print("бюджет:")
    try:
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "budget.py"), "--json"],
                             capture_output=True, text=True, timeout=120)
        data = json.loads(out.stdout)
    except Exception as exc:  # noqa: BLE001
        line(False, "живой бюджет", type(exc).__name__)
        return 1
    budget = data.get("budget") or {}
    if budget.get("known"):
        line(True, "живой бюджет", f"остаток {budget.get('daily_remaining_usd')} из {budget.get('daily_budget_usd')}")
    else:
        line(False, "живой бюджет", str(budget.get("reason")))
    return 0


def main(argv: list[str]) -> int:
    print(f"repo: {ROOT}")
    missing = 0
    missing += check_venv()
    missing += check_models()
    missing += check_key()
    missing += check_files()
    check_skills()
    if "--budget" in argv:
        missing += check_budget()
    print()
    if missing:
        print(f"не хватает: {missing} — сетевые каналы могут отвечать пусто, и это будет не «ничего не найдено»")
        return 1
    print("всё на месте (сеть не проверялась, кроме бюджета при --budget)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
