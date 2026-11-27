"""Does the CI workflow describe a gate that can actually run?

`docs/PLAN-NEXT.md` D-3 asked for CI. There is no runner in the environment where the workflow was
written, so the honest check is not "does CI pass" but "is this file coherent": valid YAML, real
paths, and the same three stages the local gate has (Rust, Lean, Python checks). The first real run
on a runner remains an experiment, and the file says so.

    python3 checks/ci_workflow.py
"""

from __future__ import annotations

import pathlib
import sys

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    path = root / ".github" / "workflows" / "gate.yml"
    if not path.exists():
        # Open, not failed: the workflow exists but cannot be delivered with the credential this
        # repository pushes with, because GitHub refuses workflow files without the `workflow`
        # scope. A permanent red gate would hide real failures behind an owner-only permission.
        print("  OPEN  no .github/workflows/gate.yml - item D-3 waits on a credential")
        print("        with the `workflow` scope; see docs/FINDING-236.md")
        print()
        print("Пункт D-3 открыт по внешней причине, гейт не красный.")
        return 0

    text = path.read_text(encoding="utf-8")
    if yaml is None:
        print("  SKIP pyyaml is not installed; the workflow cannot be parsed here")
        return 0

    try:
        doc = yaml.safe_load(text)
    except Exception as e:
        print(f"  WRONG the workflow is not valid YAML: {e}")
        print()
        print("РАСХОЖДЕНИЙ: 1")
        return 1

    bad = 0
    jobs = doc.get("jobs") or {}
    steps = [s for j in jobs.values() for s in (j.get("steps") or [])]
    runs = " ".join((s.get("run") or "") for s in steps)

    rust_test_steps = [s for s in steps if "cargo test" in (s.get("run") or "")]
    lean_build_steps = [s for s in steps if "lake build" in (s.get("run") or "")]
    gate = (root / "run.sh").read_text(encoding="utf-8")
    checks = [
        ("the workflow is valid YAML with at least one job", bool(jobs)),
        ("the only direct Rust test step is the serialized lean-ffi suite",
         len(rust_test_steps) == 1 and "lean-ffi" in (rust_test_steps[0].get("run") or "")),
        ("Lean build is delegated to the pinned full gate", not lean_build_steps and "lake build" in gate),
        ("release bins and examples are built inside the pinned full gate",
         "cargo build --release --bins --examples" in gate),
        ("it runs the local gate", "run.sh all" in runs),
        ("it is triggered on push", "push" in (doc.get("on") or doc.get(True) or {})),
        ("the paths it uses exist",
         (root / "core").is_dir()
         and (root / "laws" / "lean-toolchain").exists()
         and (root / "run.sh").exists()),
        ("it does not claim to have been run", "NOT RUN ON A RUNNER" in text.upper()),
    ]
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}")
        if not ok:
            bad += 1

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("CI-файл согласован; на раннере он ещё не запускался, и это в нём написано.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
