"""A self-test for the guards: each one must fire on a planted fault and stay silent without it.

Five of the twelve guards written in this session were wrong on their first version - too broad (false
alarms) or too narrow (blind on exactly the case they were written for). Each was fixed only because a
fault was planted by hand and the result looked at. This makes that step part of the gate.

For each guard the table below declares one mutation that must turn it red. The self-test copies the
file, applies the mutation, runs the guard, restores the file in a `finally`, and compares the exit
codes. If a guard stops noticing its own fault, this fails.

This covers the **fires** arm only. The **silent** arm is the gate itself: every guard also runs on the
unmutated tree, where it must exit zero. Two arms in two places, which is the point - a guard that is
red on a clean tree fails the gate before this file is reached.

    python3 checks/guard_self_test.py
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

# (name, guard script, file to mutate, text to replace, replacement, must_fail)
CASES = [
    (
        "readme: a stale claim returns",
        "checks/readme_features.py",
        "README.md",
        "| **кожа** |",
        "| **кожа** (`structure ≡ 1 − damage`) |",
        True,
    ),
    (
        "goal: a field the code does not have",
        "checks/goal_features.py",
        "GOAL.md",
        "| **ноги** |",
        "| **ноги** (`stride_state`) |",
        True,
    ),
    (
        "doc numbers: a count that is not the tree's",
        "checks/doc_numbers.py",
        "NOT-CLAIMED.md",
        "| 234 FINDING",
        "| 934 FINDING",
        True,
    ),
    (
        "prose: a word written twice",
        "checks/paper_prose.py",
        "docs/PAPER-draft.md",
        "## 4. Results",
        "## 4. Results\n\nThe the experiment ran.",
        True,
    ),
    (
        "claims: the paper claims more than was measured",
        "checks/paper_claims.py",
        "docs/PAPER-draft.md",
        "## 4. Results",
        "## 4. Results\n\nThis shows that emergence is here.",
        True,
    ),
    (
        "format: a figure caption loses its number",
        "checks/paper_format.py",
        "docs/PAPER-draft.md",
        "*Figure 2.*",
        "*Figure 9.*",
        True,
    ),
    (
        "protocol: a check disappears from the protocol",
        "checks/protocol_checks.py",
        "PROTOCOL.md",
        "| `checks/doc_numbers.py` |",
        "| `checks/numbers_gone.py` |",
        True,
    ),
    (
        "unseeded random: a JS check loses its seed",
        "checks/no_unseeded_random.py",
        "checks/audit.js",
        "// A seeded PRNG",
        "const r = Math.random();\n// A seeded PRNG",
        True,
    ),
]


def run_guard(script: str, root: pathlib.Path) -> int:
    r = subprocess.run([sys.executable, script], cwd=root, capture_output=True, text=True)
    return r.returncode


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    bad = 0
    for label, guard, target, old, new, must_fail in CASES:
        path = root / target
        if not path.exists():
            print(f"  SKIP  {label}: {target} is missing")
            continue
        backup = pathlib.Path(f"/tmp/guard_selftest_{path.name}.bak")
        shutil.copy2(path, backup)
        try:
            text = path.read_text(encoding="utf-8")
            if old not in text:
                print(f"  SKIP  {label}: the anchor {old[:30]!r} is not in {target}")
                continue
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            rc = run_guard(guard, root)
        finally:
            shutil.copy2(backup, path)
            backup.unlink(missing_ok=True)
        restored = path.read_text(encoding="utf-8") == text
        fired = rc != 0
        ok = (fired == must_fail) and restored
        print(
            f"  {'ok   ' if ok else 'WRONG'} {label}: guard exit {rc}"
            f"{'' if restored else ', FILE NOT RESTORED'}"
        )
        if not ok:
            bad += 1

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Сторожа срабатывают на подложенную ошибку и молчат без неё.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
