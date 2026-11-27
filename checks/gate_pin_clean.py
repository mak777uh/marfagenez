#!/usr/bin/env python3
"""Regression test: preparing a gate pin must not dirty tracked Lean sources."""
from __future__ import annotations

import re
import shlex
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "run.sh"


def extract_function(source: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(name)}\(\) \{\n.*?^\}",
        source,
    )
    if not match:
        raise RuntimeError(f"{name}() not found in run.sh")
    return match.group(0)


def command(*args: str, cwd: Path) -> None:
    subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True,timeout=15)


def selftest() -> int:
    source = RUN.read_text(encoding="utf-8")
    functions = "\n\n".join(
        extract_function(source, name)
        for name in ("pin_assert_clean", "make_pin", "drop_pin")
    )
    with tempfile.TemporaryDirectory(prefix="gate-pin-clean-") as tmp:
        root = Path(tmp) / "repo"
        (root / "core").mkdir(parents=True)
        (root / "laws").mkdir(parents=True)
        (root / ".gitignore").write_text("core/target\n",encoding="utf-8")
        (root / "core" / "Cargo.toml").write_text(
            "[package]\nname='pin-test'\nversion='0.1.0'\nedition='2021'\n",encoding="utf-8")
        (root / "laws" / ".gitignore").write_text(".lake/\n",encoding="utf-8")
        (root / "laws" / "Legacy.lean").write_text("import Std\n",encoding="utf-8")
        command("git","init","-q",cwd=root)
        command("git","config","user.name","pin selftest",cwd=root)
        command("git","config","user.email","pin-selftest@example.invalid",cwd=root)
        command("git","add",".gitignore","core/Cargo.toml","laws/.gitignore","laws/Legacy.lean",cwd=root)
        command("git","commit","-qm","pin selftest baseline",cwd=root)

        cache = root / "laws" / ".lake"
        cache.mkdir()
        (cache / "source-gitignore").symlink_to("../.gitignore")
        (cache / "source-legacy").symlink_to("../Legacy.lean")
        (root / "core" / "target").mkdir()

        head = subprocess.run(
            ["git","rev-parse","HEAD"],cwd=root,check=True,
            capture_output=True,text=True,timeout=10,
        ).stdout.strip()
        script = f"""
set -euo pipefail
ROOT={shlex.quote(str(root))}
GATE_HEAD={shlex.quote(head)}
GATE_PIN=""
PINNED_SECTIONS="test lean reach dispatcher verus build exp kg claims audit export agents lab"
{functions}
make_pin
PIN_PATH="$GATE_PIN"
pin_assert_clean "selftest"
test -f "$GATE_PIN/laws/.lake/source-gitignore"
test -f "$GATE_PIN/laws/.lake/source-legacy"
test ! -L "$GATE_PIN/laws/.lake/source-gitignore"
test ! -L "$GATE_PIN/laws/.lake/source-legacy"
test ! -L "$GATE_PIN/laws/.gitignore"
test ! -L "$GATE_PIN/laws/Legacy.lean"
status=$(git -C "$GATE_PIN" status --porcelain --untracked-files=normal -- . ':!results')
test -z "$status"
drop_pin
test ! -e "$PIN_PATH"
echo PIN_CLEAN_SELFTEST_OK
"""
        proc = subprocess.run(
            ["bash","-c",script],cwd=root,capture_output=True,text=True,timeout=45)
        output=proc.stdout+proc.stderr
        if proc.returncode != 0 or "PIN_CLEAN_SELFTEST_OK" not in output:
            print("PIN_CLEAN_SELFTEST_FAIL")
            print(output[-4000:])
            return 1
        print("PIN_CLEAN_SELFTEST_OK: tracked Lean files untouched; git status clean")
        return 0


if __name__ == "__main__":
    raise SystemExit(selftest())
