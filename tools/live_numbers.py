#!/usr/bin/env python3
"""Generate/check live numeric markers in Markdown from the repository tree.

Examples:
    python3 tools/live_numbers.py --write
    python3 tools/live_numbers.py --check
    python3 tools/live_numbers.py --selftest
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tempfile

MARKER = re.compile(
    r"<!--\s*live:([a-z][a-z0-9_]*)\s*-->(\d+)<!--\s*/live\s*-->"
)
REQUIRED_DOCS = ("README.md", "laws/README.md")


def _files(path: pathlib.Path, suffix: str) -> list[pathlib.Path]:
    if not path.exists():
        return []
    return sorted(p for p in path.rglob(f"*{suffix}") if p.is_file()
                  and not any(part in {".git", "target", ".lake"} for part in p.parts))


def measure(root: pathlib.Path) -> dict[str, int]:
    core_src = root / "core" / "src"
    test_sources = _files(core_src, ".rs") + _files(root / "core" / "tests", ".rs")
    def _count_default_tests(p: pathlib.Path) -> int:
        lines = p.read_text(encoding="utf-8").splitlines()
        gated = next(
            (i for i, ln in enumerate(lines)
             if "#[cfg(" in ln and 'feature = "lean-ffi"' in ln),
            len(lines),
        )
        return sum(1 for line in lines[:gated] if "#[test]" in line)
    tests = sum(_count_default_tests(p) for p in test_sources)
    test_files = len(_files(root / "core" / "tests", ".rs"))
    src_files = len(list(core_src.glob("*.rs"))) if core_src.exists() else 0
    bin_files = len(list((core_src / "bin").glob("*.rs"))) if (core_src / "bin").exists() else 0
    medium = list((root / "laws" / "Medium").glob("*.lean"))
    legacy = list((root / "laws" / "Legacy").glob("*.lean"))

    def theorem_count(files: list[pathlib.Path]) -> int:
        return sum(
            len(re.findall(r"^(?:theorem|lemma)\s+", p.read_text(encoding="utf-8"), re.MULTILINE))
            for p in files
        )

    return {
        "tests": tests,
        "test_files": test_files,
        "src_files": src_files,
        "bin_files": bin_files,
        "medium_files": len(medium),
        "medium_theorems": theorem_count(medium),
        "lean_theorems": theorem_count(medium + legacy),
        "exp_scripts": len(list((root / "checks").glob("exp*.py"))),
    }


def scan_documents(root: pathlib.Path) -> list[pathlib.Path]:
    return _files(root, ".md")


def update_or_check(root: pathlib.Path, write: bool) -> list[str]:
    values = measure(root)
    problems: list[str] = []
    seen_docs: set[str] = set()

    for path in scan_documents(root):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            problems.append(f"{path}: cannot read: {exc}")
            continue

        matches = list(MARKER.finditer(content))
        if not matches:
            continue
        rel = path.relative_to(root).as_posix()
        seen_docs.add(rel)

        unknown = sorted({m.group(1) for m in matches if m.group(1) not in values})
        if unknown:
            problems.append(f"{rel}: unknown live marker(s): {', '.join(unknown)}")
            continue

        def replacement(match: re.Match[str]) -> str:
            return match.group(0).replace(match.group(2), str(values[match.group(1)]), 1)

        updated = MARKER.sub(replacement, content)
        if write:
            if updated != content:
                path.write_text(updated, encoding="utf-8")
                print(f"UPDATED {rel}")
        elif updated != content:
            for match in MARKER.finditer(content):
                name, found = match.group(1), int(match.group(2))
                expected = values.get(name)
                if expected is not None and found != expected:
                    line = content.count("\n", 0, match.start()) + 1
                    problems.append(f"{rel}:{line}: {name} is {found}, tree has {expected}")

    for required in REQUIRED_DOCS:
        if required not in seen_docs:
            problems.append(f"{required}: required live markers are missing")

    if write and not problems:
        print("live numbers updated:", ", ".join(f"{k}={v}" for k, v in values.items()))
    return problems


def selftest() -> list[str]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="live-numbers-") as temp:
        root = pathlib.Path(temp)
        (root / "core" / "src" / "bin").mkdir(parents=True)
        (root / "core" / "tests").mkdir(parents=True)
        (root / "laws" / "Medium").mkdir(parents=True)
        (root / "laws" / "Legacy").mkdir(parents=True)
        (root / "checks").mkdir(parents=True)
        (root / "README.md").write_text(
            "tests <!-- live:tests -->999<!-- /live -->\n"
            "bins <!-- live:bin_files -->999<!-- /live -->\n", encoding="utf-8")
        (root / "laws" / "README.md").write_text(
            "lean <!-- live:lean_theorems -->999<!-- /live -->\n", encoding="utf-8")
        (root / "core" / "src" / "lib.rs").write_text(
            "#[test]\n#[test]\n", encoding="utf-8")
        (root / "core" / "tests" / "one.rs").write_text(
            "#[test]\n", encoding="utf-8")
        (root / "core" / "src" / "bin" / "run.rs").write_text("", encoding="utf-8")
        (root / "laws" / "Medium" / "A.lean").write_text(
            "theorem a : True := by trivial\nlemma b : True := by trivial\n",
            encoding="utf-8")
        (root / "laws" / "Legacy" / "B.lean").write_text(
            "theorem c : True := by trivial\n", encoding="utf-8")
        (root / "checks" / "exp_one.py").write_text("", encoding="utf-8")

        write_errors = update_or_check(root, write=True)
        if write_errors:
            problems.extend(write_errors)
        check_errors = update_or_check(root, write=False)
        if check_errors:
            problems.extend(check_errors)
        readme = (root / "README.md").read_text(encoding="utf-8")
        if "<!-- live:tests -->3<!-- /live -->" not in readme:
            problems.append("write selftest did not update tests marker")
        (root / "README.md").write_text(
            readme.replace("<!-- live:tests -->3<!-- /live -->",
                           "<!-- live:tests -->2<!-- /live -->"),
            encoding="utf-8")
        stale = update_or_check(root, write=False)
        if not any("tests is 2, tree has 3" in p for p in stale):
            problems.append("check selftest did not detect a stale value")
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="update every live marker")
    mode.add_argument("--check", action="store_true", help="fail when a marker is stale")
    mode.add_argument("--selftest", action="store_true", help="run a temporary-tree regression test")
    args = parser.parse_args(argv)
    if args.selftest:
        problems = selftest()
    else:
        root = pathlib.Path(__file__).resolve().parents[1]
        problems = update_or_check(root, write=args.write)
    if problems:
        for problem in problems:
            print("WRONG", problem)
        return 1
    if args.check:
        print("live-number markers match the tree")
    elif args.selftest:
        print("live-number generator selftest passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
