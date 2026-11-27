#!/usr/bin/env python3
"""Fail-closed regression test for run.sh's do_kg section."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "run.sh"

CASES = [
    ("all checks pass", {}, 0, "KG_SECTION_GREEN"),
    ("regress nonzero is preserved", {"REGRESS_RC": "1"}, 1, "regress=1"),
    ("edges nonzero is preserved", {"EDGES_RC": "3"}, 1, "edges=3"),
    ("price nonzero is preserved", {"PRICE_RC": "2"}, 1, "price=2"),
    ("KG check nonzero is preserved", {"CHECK_RC": "1"}, 1, "check=1"),
    ("FAIL transcript with rc=0 stays red", {"CHECK_FAIL": "1"}, 1, "check=1"),
    ("regress FAIL transcript with rc=0 stays red", {"REGRESS_FAIL": "1"}, 1, "regress=1"),
    ("edges FAIL transcript with rc=0 stays red", {"EDGES_FAIL": "1"}, 1, "edges=1"),
    ("price FAIL transcript with rc=0 stays red", {"PRICE_FAIL": "1"}, 1, "price=1"),
]


def extract_do_kg() -> str:
    text = RUN.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^do_kg\(\) \{\n.*?^\}", text)
    if not match:
        raise RuntimeError("do_kg() block not found in run.sh")
    return match.group(0)


def run_case(function: str, values: dict[str, str]) -> tuple[int, str]:
    fake_python = r'''
python3() {
  case "$1" in
    kg/kg.py)
      [ "$CHECK_FAIL" = 0 ] || echo "FAIL: fake KG invariant"
      return "$CHECK_RC" ;;
    kg/regress.py)
      [ "$REGRESS_FAIL" = 0 ] || echo "  FAIL: fake generated nodes drift"
      return "$REGRESS_RC" ;;
    checks/kg_edges.py)
      [ "$EDGES_FAIL" = 0 ] || echo "FAIL: fake KG edge invariant"
      return "$EDGES_RC" ;;
    checks/bridge_price_derivative.py)
      [ "$PRICE_FAIL" = 0 ] || echo "FAIL: fake KG price invariant"
      return "$PRICE_RC" ;;
    *) echo "unexpected python command: $*" >&2; return 99 ;;
  esac
}
section() { :; }
export KG_GATE_SELFTEST=1
'''
    script = "#!/usr/bin/env bash\nset +e\n" + fake_python + "\n" + function + "\ndo_kg\n"
    with tempfile.TemporaryDirectory(prefix="kg-gate-selftest-") as tmp:
        path = Path(tmp) / "case.sh"
        path.write_text(script, encoding="utf-8")
        env = os.environ.copy()
        env.update(values)
        for key in ("CHECK_FAIL", "REGRESS_FAIL", "EDGES_FAIL", "PRICE_FAIL", "CHECK_RC", "REGRESS_RC", "EDGES_RC", "PRICE_RC"):
            env.setdefault(key, "0")
        env["KG_GATE_SELFTEST"] = "1"
        proc = subprocess.run(
            ["bash", str(path)], cwd=ROOT, env=env,
            text=True, capture_output=True, timeout=10,
        )
        return proc.returncode, proc.stdout + proc.stderr


def selftest() -> int:
    function = extract_do_kg()
    failures = 0
    for name, values, expected_rc, marker in CASES:
        rc, output = run_case(function, values)
        ok = rc == expected_rc and marker in output
        if not ok:
            failures += 1
            print(f"  FAIL {name}: rc={rc}, expected={expected_rc}; marker={marker!r}")
            print("       " + "\n       ".join(output.strip().splitlines()[-5:]))
        else:
            print(f"  ok   {name}")
    print(f"KG fail-closed selftest: {len(CASES)-failures}/{len(CASES)}")
    return 1 if failures else 0


def main() -> int:
    if "--selftest" not in sys.argv and len(sys.argv) > 1:
        print("usage: python3 checks/gate_kg_fail_closed.py [--selftest]", file=sys.stderr)
        return 2
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
