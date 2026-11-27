#!/usr/bin/env python3
"""Verify the Lean FFI test feature by compiling/listing both Cargo modes.

This intentionally performs Cargo work only when invoked. It does not run
simulation tests; \`-- --list\` forces Cargo to compile each test target and
prints the tests selected by its cfgs.

    python3 checks/lean_ffi_feature.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
FFI_PREFIX = "bridge::tests::"


def list_tests(extra: list[str]) -> tuple[int, str]:
    command = [
        "cargo", "test", "--release", "--no-default-features", "--tests",
        *extra, "--", "--list",
    ]
    completed = subprocess.run(
        command, cwd=CORE, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    return completed.returncode, completed.stdout


def test_names(output: str) -> set[str]:
    names = set()
    for line in output.splitlines():
        match = re.match(r"^([A-Za-z0-9_:]+): test$", line.strip())
        if match:
            names.add(match.group(1))
    return names


def main() -> int:
    failures = 0

    parallel_code, parallel_output = list_tests([])
    if parallel_code:
        print("FAIL parallel no-default-features test targets did not compile/list")
        print(parallel_output[-6000:])
        return 1
    parallel = test_names(parallel_output)
    parallel_ffi = sorted(name for name in parallel if name.startswith(FFI_PREFIX))
    if parallel_ffi:
        print("FAIL parallel mode contains Lean FFI tests:", parallel_ffi)
        failures += 1
    else:
        print("OK parallel mode excludes bridge::tests::*")

    ffi_code, ffi_output = list_tests(["--features", "lean-ffi"])
    if ffi_code:
        print("FAIL lean-ffi test targets did not compile/list")
        print(ffi_output[-6000:])
        return 1
    ffi = test_names(ffi_output)
    ffi_names = sorted(name for name in ffi if name.startswith(FFI_PREFIX))
    if not ffi_names:
        print("FAIL lean-ffi mode contains no bridge::tests::* tests")
        failures += 1
    else:
        print(f"OK lean-ffi mode includes {len(ffi_names)} bridge tests")
        for name in ffi_names:
            print("  ", name)

    if failures:
        return 1
    print("Both configurations compiled; selection matches the feature contract.")
    print("Note: this is a compile/list check, not an execution of the Lean-backed tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
