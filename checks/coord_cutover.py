"""Fail-closed test for the archived `.coord` CLI.

Every legacy mutator must refuse before creating or modifying any state.
Read-only diagnostics remain available for historical inspection.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COORD_SCRIPT = ROOT / "tools" / "coord.py"


def load_coord():
    spec = importlib.util.spec_from_file_location("legacy_coord_cutover_test", COORD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {COORD_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return "ABSENT"
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        if path.is_symlink():
            digest.update(b"L\0" + rel + b"\0" + str(path.readlink()).encode("utf-8"))
        elif path.is_file():
            digest.update(b"F\0" + rel + b"\0" + hashlib.sha256(path.read_bytes()).digest())
        elif path.is_dir():
            digest.update(b"D\0" + rel + b"\0")
    return digest.hexdigest()


def run() -> int:
    coord = load_coord()
    write_cases = {
        "register": ["register", "--agent", "legacy-test"],
        "add": ["add", "--id", "CUTOVER-TEST", "--title", "test",
                "--area", "results", "--accept", "python3 checks/test.py"],
        "take": ["take", "CUTOVER-TEST", "--agent", "legacy-test"],
        "heartbeat": ["heartbeat", "CUTOVER-TEST", "--agent", "legacy-test"],
        "finish": ["finish", "CUTOVER-TEST", "--agent", "legacy-test"],
        "verify": ["verify", "CUTOVER-TEST", "--agent", "main"],
        "close": ["close", "CUTOVER-TEST", "--agent", "main"],
        "release": ["release", "CUTOVER-TEST", "--agent", "legacy-test", "--reason", "test"],
        "drop": ["drop", "CUTOVER-TEST", "--agent", "legacy-test", "--reason", "test"],
        "recover": ["recover", "--agent", "main"],
        "note": ["note", "--agent", "legacy-test", "--to", "main", "--text", "test"],
        # `read` moves a message to the read/ directory and is therefore a write.
        "read": ["read", "message.md", "--agent", "main"],
        "board": ["board", "--agent", "main", "--text", "test"],
        "status --write": ["status", "--write"],
    }

    read_only_cases = {
        "list": ["list"],
        "stale": ["stale"],
        "status": ["status"],
        "inbox": ["inbox", "--agent", "main"],
        "unread": ["unread"],
    }

    with tempfile.TemporaryDirectory(prefix="coord-cutover-") as temp:
        root = Path(temp)
        coord.ROOT = root
        coord.COORD = root / ".coord"
        for name in ("PENDING", "ACTIVE", "DONE", "EVENTS", "AGENTS", "STANDING",
                     "LOCKS", "GRAVEYARD", "GENS", "MAIL"):
            setattr(coord, name, coord.COORD / name.lower())
        coord.BOARD = coord.COORD / "board.md"

        before = tree_digest(coord.COORD)
        failures = []
        for name, argv in write_cases.items():
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = coord.main(argv)
            after = tree_digest(coord.COORD)
            if rc == 0 or after != before or "LEGACY_COORD_READ_ONLY" not in stdout.getvalue():
                failures.append(f"{name}: rc={rc}, tree_unchanged={after == before}")

        for name, argv in read_only_cases.items():
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = coord.main(argv)
            after = tree_digest(coord.COORD)
            if rc != 0 or after != before:
                failures.append(f"read-only {name}: rc={rc}, tree_unchanged={after == before}")

        if failures:
            print("legacy coord cutover: FAIL")
            for failure in failures:
                print("  " + failure)
            return 1
        print(f"legacy coord cutover: PASS ({len(write_cases)} mutators fail closed; "
              f"{len(read_only_cases)} read-only commands stay read-only)")
        return 0


if __name__ == "__main__":
    raise SystemExit(run())

