"""Check executable Verus/Rust copies that have an actual shared counterpart.

The check is deliberately conservative: remove comments, then normalise whitespace.
It does not attempt semantic equivalence, and it does not pretend that a Verus
function with no same-named Rust body has been compared.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERUS = ROOT / "verus" / "integer_laws.rs"
BRIDGE = ROOT / "core" / "src" / "bridge.rs"

# Only these shared functions have pure executable bodies with no Verus proof
# assertions embedded in their bodies. rust_fill_time is a shared name, but its
# Verus body also contains proof assertions; it is intentionally reported as
# un-compared rather than weakened by stripping proof code.
COMPARABLE = ("rust_saturation", "rust_fold_shifted")
PROOF_ONLY = ("rust_fill_time",)


def _without_comments(source: str) -> str:
    """Remove Rust line/block comments for these arithmetic-only functions."""
    source = re.sub(r"//[^\n]*", "", source)
    return re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)


def function_body(source: str, name: str) -> str | None:
    """Extract a function body by name, balancing braces after its signature."""
    clean = _without_comments(source)
    match = re.search(r"\bfn\s+" + re.escape(name) + r"\s*\(", clean)
    if not match:
        return None
    open_brace = clean.find("{", match.end())
    if open_brace < 0:
        return None
    depth = 0
    for i in range(open_brace, len(clean)):
        if clean[i] == "{":
            depth += 1
        elif clean[i] == "}":
            depth -= 1
            if depth == 0:
                return re.sub(r"\s+", "", clean[open_brace+1:i])
    return None


def compare(verus_text: str, bridge_text: str) -> list[str]:
    problems = []
    for name in COMPARABLE:
        left = function_body(verus_text, name)
        right = function_body(bridge_text, name)
        if left is None or right is None:
            problems.append(f"{name}: counterpart missing from one source")
        elif left != right:
            problems.append(f"{name}: executable bodies drifted")
    return problems


def selftest() -> list[str]:
    problems = []
    v = "fn sample(x:u64)->u64 {\n // comment\n if x == 0 { 0 } else { x }\n}"
    r = "pub fn sample(x:u64)->u64 { /* comment */ if x==0{0}else{x} }"
    if function_body(v, "sample") != function_body(r, "sample"):
        problems.append("whitespace/comment normalisation selftest failed")
    changed = "pub fn sample(x:u64)->u64 { if x==1{0}else{x} }"
    if function_body(v, "sample") == function_body(changed, "sample"):
        problems.append("body drift selftest failed to detect a changed expression")
    return problems


def main() -> int:
    problems = selftest()
    if problems:
        for problem in problems:
            print("FAIL selftest:", problem)
        return 1
    try:
        v = VERUS.read_text(encoding="utf-8")
        b = BRIDGE.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL cannot read source: {exc}")
        return 1
    problems.extend(compare(v, b))
    if problems:
        for problem in problems:
            print("FAIL", problem)
        return 1
    print(f"OK: {len(COMPARABLE)} shared executable bodies match after comment/whitespace normalisation")
    print(f"OPEN: {len(PROOF_ONLY)} shared function contains Verus proof code and is not text-compared")
    print("OPEN: remaining Verus-only functions have no same-named Rust body in bridge.rs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
