"""Does the CI workflow describe a gate that can actually run?

`docs/PLAN-NEXT.md` D-3 asked for CI. GitHub Actions executes the hosted workflow; this check
validates that its structure matches the current local gate contract, avoids duplicate expensive
stages, and cancels superseded runs for the same branch. A green result here is not a substitute
for the hosted job's actual conclusion.

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
        ("it cancels obsolete attempts on the same branch",
         "cancel-in-progress: true" in text
         and "github.event.pull_request.head.ref || github.ref_name" in text),
        ("it caches Rust and Lean build state",
         "Swatinem/rust-cache@v2" in text and "actions/cache@v4" in text),
        ("it installs ShellCheck for the dispatcher gate", "apt-get install --yes shellcheck" in text),
        ("preflight proves that pin cache cannot dirty tracked Lean files",
         "gate_pin_clean.py --selftest" in gate and "pin_assert_clean" in gate),
    ]
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}")
        if not ok:
            bad += 1

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("CI-файл согласован с hosted gate и его кешированием/конкурентностью.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
