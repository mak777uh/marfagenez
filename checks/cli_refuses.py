"""Do the command-line programs refuse a typo instead of quietly using a default?

`docs/PLAN-NEXT.md` D-5 was filed because `args.get(i).and_then(|s| s.parse().ok()).unwrap_or(default)`
turns `--steps 50O` (letter O) into a run of the default 500 steps, with nothing in the output saying so:
the run answers a question nobody asked. The fix is in `core/src/bin/trace.rs::number` and
`core/src/bin/occupancy.rs::positional`, and this keeps it there.

Two programs take numeric arguments; both must exit non-zero with a message rather than run.

    python3 checks/cli_refuses.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    trace = root / "core" / "target" / "release" / "trace"
    occupancy = root / "core" / "target" / "release" / "occupancy"
    missing = [str(p) for p in (trace, occupancy) if not p.exists()]
    if missing:
        print(f"  SKIP binaries not built: {missing}")
        print("       (build them with `cargo build --release` in core/)")
        return 0

    cases = [
        ("trace --steps 50O", [str(trace), "--steps", "50O"]),
        ("occupancy 50O", [str(occupancy), "50O"]),
    ]
    bad = 0
    for label, cmd in cases:
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        first = out.splitlines()[0] if out else "(no output)"
        ok = r.returncode != 0 and "not a number" in out.lower()
        print(f"  {'ok   ' if ok else 'WRONG'} {label}: exit {r.returncode}, {first[:70]}")
        if not ok:
            bad += 1

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("CLI отказывается угадывать: опечатка — это ошибка, а не умолчание.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
