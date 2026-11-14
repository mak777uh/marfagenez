"""Every symbol `bridge.rs` declares must be defined by the stub in `build.rs`.

The stub exists for machines without Lean. On such a machine the crate must
build; if a symbol is missing, linking fails and the whole build is broken —
not skipped, broken. This check makes that failure visible at the gate.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def declared():
    """Symbols named in the `extern "C"` block of bridge.rs."""
    src = io.open(os.path.join(ROOT, "core/src/bridge.rs"), encoding="utf-8").read()
    start = src.index('extern "C" {')
    end = src.index("}", start)
    block = src[start:end]
    return sorted(set(re.findall(r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", block)))


def defined():
    """Symbols defined by the stub C source inside build.rs."""
    src = io.open(os.path.join(ROOT, "core/build.rs"), encoding="utf-8").read()
    start = src.index('let stub = r#"')
    end = src.index('"#;', start)
    stub = src[start:end]
    return sorted(set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*\{", stub)))


def main():
    want = declared()
    have = defined()
    missing = [s for s in want if s not in have]
    extra = [s for s in have if s not in want and s != "main"]

    print("declared in bridge.rs :", len(want))
    print("defined in stub       :", len(have))
    if missing:
        print("\nMISSING from the stub (the build will fail without Lean):")
        for s in missing:
            print("   ", s)
    if extra:
        print("\nDEFINED but never declared (dead stub code):")
        for s in extra:
            print("   ", s)

    # The link directive matters as much as the symbols: without it the archive
    # is built and never linked, and every symbol stays undefined.
    src = io.open(os.path.join(ROOT, "core/build.rs"), encoding="utf-8").read()
    stub_section = src[src.index("fn write_stub"):]
    if "rustc-link-lib=static=ffi" not in stub_section:
        print("\nMISSING: write_stub does not emit `cargo:rustc-link-lib=static=ffi`")
        missing.append("rustc-link-lib=static=ffi")

    if missing or extra:
        print("\nFAIL: the stub must define exactly what the bridge declares.")
        return 1
    print("\nOK: the stub covers every symbol the bridge declares.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
