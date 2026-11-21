"""`checks/` is the gate's directory; everything else is a record and says so.

245 files accumulated in `checks/`, 178 of them neither run by the gate nor imported by anything: they are
historical experiments, kept because history is a record, not a draft. Deleting or moving them would break
the findings that name them (`checks/exp61_two_equilibria.py` and 73 other paths are written into
`docs/FINDING-*.md`), so they stay — but they stop being anonymous:

  * every file in `checks/` is either invoked by `run.sh`, imported by another check, or listed in
    `checks/LEGACY.txt` with a reason;
  * a new file that is none of those fails the gate, which is the point: the directory may not grow by
    accident;
  * a `LEGACY` entry that is actually invoked, or that no longer exists, fails too;
  * `probes/` holds new ad-hoc work and must not be invoked by the gate; its `INDEX.md` lists its files.

Usage:
    python3 checks/tree_contract.py
    python3 checks/tree_contract.py --selftest
    python3 checks/tree_contract.py --write-legacy   # regenerate LEGACY.txt from the current tree
"""

from __future__ import annotations

import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKS = ROOT / "checks"
PROBES = ROOT / "probes"
LEGACY = CHECKS / "LEGACY.txt"

CALL_RE = re.compile(r"(?:python3|python|bash|node)\s+(\S*checks/[a-z_0-9]+\.(?:py|sh|js))")


def invoked(run_text: str) -> set[str]:
    out = set()
    for line in run_text.splitlines():
        code = line.split("#", 1)[0]
        for m in CALL_RE.finditer(code):
            out.add(pathlib.PurePosixPath(m.group(1)).name)
    return out


def imported(names: set[str], checks: pathlib.Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    texts = {p.name: p.read_text(encoding="utf-8", errors="ignore") for p in checks.glob("*.py")}
    for name, text in texts.items():
        for other in names:
            if other == name or not other.endswith(".py"):
                continue
            stem = other[:-3]
            if re.search(rf"\b(import\s+{stem}\b|from\s+{stem}\s+import)", text):
                out.setdefault(other, []).append(name)
    return out


def read_legacy(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, reason = line.partition(" — ")
        out[name.strip()] = reason.strip()
    return out


def write_legacy(invoked_set: set[str], imports: dict[str, list[str]]) -> int:
    files = sorted(p.name for p in CHECKS.iterdir() if p.is_file() and p.name != LEGACY.name)
    lines = [
        "# checks/LEGACY.txt — исторические проверки, которые гейт не запускает.",
        "# Каждая строка: имя — причина. Новый файл сюда добавлять нельзя автоматически:",
        "# либо он вызывается из run.sh, либо импортируется другой проверкой, либо это запись прошлого.",
        "#",
    ]
    count = 0
    for name in files:
        if name in invoked_set or name in imports or name in ("LEGACY.txt",) or name.endswith(".txt"):
            continue
        if name.startswith("_"):
            continue
        lines.append(f"{name} — исторический зонд, оставлен как запись; гейт его не запускает")
        count += 1
    LEGACY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"LEGACY.txt: {count} записей")
    return 0


def check(root: pathlib.Path = ROOT) -> list[str]:
    checks = root / "checks"
    probes = root / "probes"
    run = (root / "run.sh").read_text(encoding="utf-8")
    invoked_set = invoked(run)
    files = {p.name for p in checks.iterdir() if p.is_file()}
    py_files = {n for n in files if n.endswith(".py")}
    imports = imported(py_files, checks)
    legacy = read_legacy(checks / "LEGACY.txt")
    errs: list[str] = []

    registered = invoked_set | set(imports) | set(legacy)
    for name in sorted(files):
        if name in ("LEGACY.txt",) or name.endswith(".txt"):
            continue
        if name not in registered:
            errs.append(f"T1 `checks/{name}` не вызывается гейтом, не импортируется и не внесён в LEGACY.txt")

    for name in sorted(legacy):
        if name not in files:
            errs.append(f"T3 `checks/LEGACY.txt` называет отсутствующий файл: {name}")
        if name in invoked_set:
            errs.append(f"T2 `{name}` внесён в LEGACY.txt, но гейт его запускает")

    if probes.exists():
        index = probes / "INDEX.md"
        index_text = index.read_text(encoding="utf-8") if index.exists() else ""
        for path in sorted(probes.iterdir()):
            if not path.is_file() or path.name in ("INDEX.md", "README.md"):
                continue
            if path.name not in index_text:
                errs.append(f"T4 `probes/{path.name}` не назван в probes/INDEX.md")
            if path.name in invoked_set:
                errs.append(f"T5 `probes/{path.name}` запускается гейтом: probes/ — не гейт")
    return errs


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="tree-contract-"))
    checks = tmp / "checks"
    checks.mkdir()
    (tmp / "run.sh").write_text("python3 checks/gate.py\n# python3 checks/commented.py\n", encoding="utf-8")
    for name in ("gate.py", "lib.py", "legacy_probe.py", "orphan.py", "commented.py"):
        (checks / name).write_text("", encoding="utf-8")
    (checks / "lib.py").write_text("x = 1\n", encoding="utf-8")
    (checks / "gate.py").write_text("import lib\n", encoding="utf-8")
    (checks / "LEGACY.txt").write_text("legacy_probe.py — старый зонд\n", encoding="utf-8")

    errs = check(tmp)
    orphan = any("orphan.py" in e for e in errs)
    commented = any("commented.py" in e for e in errs)
    print(f"  {'ok  ' if orphan else 'FAIL'} неучтённый файл ловится")
    print(f"  {'ok  ' if commented else 'FAIL'} упоминание в комментарии не считается вызовом")
    return 0 if (orphan and commented) else 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        result = selftest()
        print(f"selftest: {'ok' if result == 0 else 'провал'}")
        return result
    root = ROOT
    if "--write-legacy" in argv:
        run = (root / "run.sh").read_text(encoding="utf-8")
        files = {p.name for p in (root / "checks").iterdir() if p.is_file() and p.name.endswith(".py")}
        return write_legacy(invoked(run), imported(files, root / "checks"))
    errs = check(root)
    if errs:
        print(f"ДЕРЕВО ПРОВЕРОК: {len(errs)} нарушений")
        for e in errs[:20]:
            print("  " + e)
        return 1
    legacy = read_legacy(LEGACY)
    print(f"дерево проверок: согласовано (записей прошлого: {len(legacy)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
