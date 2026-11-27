#!/usr/bin/env python3
"""Compile/list Rust tests in both Lean FFI feature modes.

This is a target-selection contract check, not an execution of the FFI tests.
The Lean-backed tests are executed separately after the Lean toolchain is built.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
FFI_PREFIX = "bridge::tests::"


def list_tests(features: bool) -> tuple[int, str]:
    command = [
        "cargo", "test", "--release", "--no-default-features",
        "--lib", "--tests",
    ]
    if features:
        command += ["--features", "lean-ffi"]
    command += ["--", "--list"]
    result = subprocess.run(
        command, cwd=CORE, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    return result.returncode, result.stdout


def names(output: str) -> set[str]:
    return {
        match.group(1)
        for line in output.splitlines()
        if (match := re.match(r"^([A-Za-z0-9_:]+): test$", line.strip()))
    }


def main() -> int:
    code, output = list_tests(features=False)
    if code:
        print("FAIL: no-default-features targets did not compile/list")
        print(output[-8000:])
        return 1
    default_names = names(output)
    unexpected = sorted(n for n in default_names if n.startswith(FFI_PREFIX))
    if unexpected:
        print("FAIL: parallel/default mode contains Lean FFI tests:", unexpected)
        return 1
    print("OK: default mode excludes bridge::tests::*")

    code, output = list_tests(features=True)
    if code:
        print("FAIL: lean-ffi targets did not compile/list")
        print(output[-8000:])
        return 1
    ffi_names = sorted(n for n in names(output) if n.startswith(FFI_PREFIX))
    if not ffi_names:
        print("FAIL: lean-ffi mode contains no bridge::tests::* tests")
        return 1
    print(f"OK: lean-ffi mode includes {len(ffi_names)} bridge tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
