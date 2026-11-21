"""PROTOCOL.md and the gate must describe the same set of checks — in both directions.

The old version had three holes, each found by an external review:

  1. it read "invocations" from the whole text of `run.sh`, so a check mentioned in a comment counted
     as run (and a check run through a helper did not);
  2. it only checked `invoked -> named`, never `named -> invoked`, so a dead row in PROTOCOL.md — a
     check that no longer runs — passed silently;
  3. it only looked at `.py`, while the gate also runs `.sh` and `.js` (audit.js, verify_all.js,
     stub_links.sh, two cli_refuses scripts).

Rules now:
  A. every check invoked by a command line in `run.sh` is named in a PROTOCOL.md table row;
  B. every named check is either invoked or a library imported by other checks;
  C. every named check exists on disk.

Usage:
    python3 checks/protocol_checks.py
    python3 checks/protocol_checks.py --selftest
"""

from __future__ import annotations

import pathlib
import re
import sys

JUDGES = [
    "contract.py",
    "log_check.py",
    "hash_version.py",
    "paper_numbers.py",
    "paper_claims.py",
    "paper_format.py",
    "paper_prose.py",
    "readme_features.py",
    "life_calibration.py",
    "audit.js",
    "verify_all.js",
]

# Named but never invoked directly: they are imported by other checks.
LIBRARIES = {"experiment.py", "result.py"}

NAME_RE = re.compile(r"`checks/([a-z_0-9]+\.(?:py|sh|js))`")
CALL_RE = re.compile(r"(?:python3|python|bash|node)\s+(\S*checks/[a-z_0-9]+\.(?:py|sh|js))")


def invoked_checks(run_text: str) -> set[str]:
    out: set[str] = set()
    for line in run_text.splitlines():
        code = line.split("#", 1)[0]
        for m in CALL_RE.finditer(code):
            out.add(pathlib.PurePosixPath(m.group(1)).name)
    return out


def named_checks(protocol_text: str) -> set[str]:
    out: set[str] = set()
    for line in protocol_text.splitlines():
        if not line.startswith("|"):
            continue
        for m in NAME_RE.finditer(line):
            out.add(m.group(1))
    return out


def compare(run_text: str, protocol_text: str, checks_dir: pathlib.Path) -> list[str]:
    invoked = invoked_checks(run_text)
    named = named_checks(protocol_text)
    problems: list[str] = []

    missing = sorted(invoked - named)
    if missing:
        problems.append(f"запускаются, но не названы в PROTOCOL.md: {', '.join(missing)}")

    dead = sorted(named - invoked - LIBRARIES)
    if dead:
        problems.append(f"названы в PROTOCOL.md, но не запускаются: {', '.join(dead)}")

    absent = sorted(n for n in named if checks_dir and not (checks_dir / n).exists())
    if absent:
        problems.append(f"названы, но файла нет: {', '.join(absent)}")

    return problems, invoked, named


def report(invoked: set[str], named: set[str]) -> None:
    print(f"  ok    invoked={len(invoked)}, named={len(named)}; оба направления согласованы")


def selftest() -> int:
    import tempfile

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="protocol-"))
    checks = tmp / "checks"
    checks.mkdir()
    for name in ("a.py", "b.py", "c.py", "dead.py", "lib.py"):
        (checks / name).write_text("", encoding="utf-8")

    run = "\n".join([
        "python3 checks/a.py || rc=$?",
        "bash checks/b.sh || rc=$?",          # не существует на диске, но назван
        "# python3 checks/c.py — упоминание в комментарии, не вызов",
        "node checks/d.js || rc=$?",
    ])
    proto = "\n".join([
        "| `checks/a.py` | a |",
        "| `checks/b.sh` | b |",
        "| `checks/d.js` | d |",
        "| `checks/dead.py` | больше не запускается |",
        "| `checks/lib.py` | библиотека |",
    ])

    cases = [
        ("комментарий не считается вызовом",
         compare(run, "| `checks/a.py` | a |\n| `checks/b.sh` | b |\n| `checks/d.js` | d |", checks)[0],
         []),
        ("названо, но не запускается",
         compare(run, proto, checks)[0],
         ["названы в PROTOCOL.md, но не запускаются: dead.py"]),
        ("запускается, но не названо",
         compare("python3 checks/a.py", "| `checks/b.sh` | b |", checks)[0],
         ["запускаются, но не названы в PROTOCOL.md: a.py"]),
    ]
    # файлы b.sh/d.js на диске отсутствуют: правило C обязано сработать в первом же кейсе
    total, bad = 0, 0
    for name, got, want in cases:
        total += 1
        if want and not any("файла нет" in g or want[0] in g for g in got):
            bad += 1
            print(f"  FAIL {name}: ждали {want}, получили {got}")
        elif not want and any("названы в PROTOCOL.md, но не запускаются" in g for g in got):
            bad += 1
            print(f"  FAIL {name}: лишнее срабатывание {got}")
        else:
            print(f"  ok   {name}")
    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()

    root = pathlib.Path(__file__).resolve().parent.parent
    run = (root / "run.sh").read_text(encoding="utf-8")
    proto = (root / "PROTOCOL.md").read_text(encoding="utf-8")
    checks = root / "checks"

    problems, invoked, named = compare(run, proto, checks)

    for p in problems:
        print("  WRONG " + p)
    if not problems:
        report(invoked, named)

    bad = len(problems)
    named_set = named
    absent_judges = [c for c in JUDGES if c not in named_set]
    if absent_judges:
        print(f"  WRONG judging checks absent from PROTOCOL.md: {absent_judges}")
        bad += len(absent_judges)
    else:
        print(f"  ok    all {len(JUDGES)} judging checks are named")

    # AGENTS.md states how many rules it has, and `run.sh agents` requires exactly that many sections.
    agents = root / "AGENTS.md"
    if agents.exists():
        text = agents.read_text(encoding="utf-8")
        have = sorted(int(m) for m in re.findall(r"^## §(\d+)", text, re.MULTILINE))
        required = sorted(
            int(m) for m in re.findall(r"for s in ([\d\s]+); do", run)
            for m in m.split()
        )
        stated = re.findall(r"\b([а-яё]+)\s+правил", text, re.IGNORECASE)
        words = {
            "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
            "четыре": 4, "три": 3,
        }
        if have != required:
            print(f"  WRONG AGENTS.md has sections {have} but the gate requires {required}")
            bad += 1
        else:
            print(f"  ok    AGENTS.md sections match the gate: {have}")
        if stated and words.get(stated[0].lower()) != len(have):
            print(f"  WRONG AGENTS.md says «{stated[0]} правил», but has {len(have)} sections")
            bad += 1
        elif stated:
            print(f"  ok    the stated rule count matches: «{stated[0]}» = {len(have)}")

    if bad:
        print(f"\nPROTOCOL и гейт разошлись: {bad} проблем")
        return 1
    print("\nPROTOCOL описывает тот гейт, который есть.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
