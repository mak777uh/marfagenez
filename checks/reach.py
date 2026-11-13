#!/usr/bin/env python3
"""Which .lean files does the build actually reach?

LESSONS #1: a file that sits in the repository is not necessarily compiled.
It happened twice -- 35 unreachable files on 2026-11-11, then 48 on
2026-11-13. The check "count of .olean equals count of .lean" does not
catch it, because stale .olean files from earlier runs satisfy the
equality while the build reads none of them. The check that does catch it
is reachability: walk the import graph from the entry points that
lakefile.toml names, then compare with what is on disk.

Usage:
    python3 checks/reach.py            # report
    python3 checks/reach.py --strict   # exit 1 if anything is unreachable
"""

import os
import re
import sys

LAWS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "laws")
LAWS = os.path.normpath(LAWS)

IMPORT = re.compile(r"^\s*import\s+([\w.]+)", re.M)


def module_to_path(mod):
    """`Medium.Field` -> laws/Medium/Field.lean"""
    return os.path.join(LAWS, *mod.split(".")) + ".lean"


def imports_of(path):
    if not os.path.exists(path):
        return []
    return IMPORT.findall(open(path, encoding="utf-8").read())


def entry_points():
    """Every lean_lib name in lakefile.toml, plus defaultTargets.

    defaultTargets alone is not enough: `Legacy` is a separate lean_lib that
    `lake build Legacy` builds on demand, and its files are compiled even
    though a bare `lake build` does not start there.
    """
    toml_path = os.path.join(LAWS, "lakefile.toml")
    names = []
    if os.path.exists(toml_path):
        text = open(toml_path, encoding="utf-8").read()
        for m in re.finditer(r'\[\[lean_lib\]\][^\[]*?name\s*=\s*"([^"]+)"', text):
            names.append(m.group(1))
        m = re.search(r"defaultTargets\s*=\s*\[([^\]]*)\]", text)
        if m:
            names.extend(re.findall(r'"([^"]+)"', m.group(1)))
    return names or ["Medium", "Legacy"]


def main():
    roots = entry_points()
    seen = set()
    stack = list(roots)
    missing = []

    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        path = module_to_path(mod)
        if not os.path.exists(path):
            # Mathlib, Std, Init, Lean: external packages, not our files.
            if os.sep not in mod and mod in {"Mathlib", "Std", "Init", "Lean"}:
                continue
            if mod.split(".")[0] in {"Mathlib", "Std", "Init", "Lean"}:
                continue
            missing.append(mod)
            continue
        for dep in imports_of(path):
            if dep not in seen:
                stack.append(dep)

    on_disk = set()
    for dirpath, _dirnames, filenames in os.walk(LAWS):
        if ".lake" in dirpath.split(os.sep):
            continue
        for f in filenames:
            if not f.endswith(".lean"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), LAWS)
            on_disk.add(rel[: -len(".lean")].replace(os.sep, "."))

    unreached = sorted(on_disk - seen)

    print("entry points      :", ", ".join(roots))
    print("reached modules   :", len(seen))
    print("modules on disk   :", len(on_disk))
    print("NOT reached       :", len(unreached))
    for m in unreached:
        print("   ", m)
    if missing:
        print("imported but missing on disk:", len(missing))
        for m in missing:
            print("   ", m)

    if unreached or missing:
        print("\nFAIL: every .lean file must be reachable from an entry point.")
        if "--strict" in sys.argv:
            return 1
    else:
        print("\nOK: every .lean file is reachable from an entry point.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
