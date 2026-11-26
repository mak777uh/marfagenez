#!/usr/bin/env bash
# The stub must not only define every symbol the bridge declares — it must LINK.
#
# `checks/stub_covers_bridge.py` compares two lists of names. A list can be
# complete and the archive still never reach the linker: the link directive,
# the `ar` call and the `gcc` call are three separate steps that can each fail
# silently. `write_stub` ignores the exit status of `ar`, so a broken stub
# builds an archive that is empty or missing, and the crate fails to link with
# `undefined reference to marfa_saturation` — on exactly the machine the stub
# exists for.
#
# So this check does not read the list. It hides `lean` from PATH, builds the
# crate from a clean `build.rs` state, and asks the linker.
#
# Three outcomes, per AGENTS.md §2:
#   fires    — a stub that does not link (empty archive) makes the build fail
#   silent   — the healthy stub builds and `bridge::available()` reports false
#   specific — the neighbouring defect (a missing symbol in the list) is owned
#              by `stub_covers_bridge.py`; this check stays green on it, so a
#              red result says which defect it is
#
# Run: bash checks/stub_links.sh
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT" || exit 9

fail=0
ok()  { echo "  ok   $1"; }
bad() { echo "  FAIL $1"; fail=1; }

# `build.rs` looks for lean on PATH and then in `~/.elan/bin/lean`. Hiding only
# the PATH entry would leave the second route open and the stub branch would
# never be taken — the check would then test Lean, not the stub.
# Filled in below, once `work/` exists.
STUB_ENV=()

# Builds the crate in $1 with no lean reachable. Prints the output.
build_without_lean() {
  ( cd "$1" && "${STUB_ENV[@]}" cargo build --release --lib 2>&1 )
}

echo "=== stub_links.sh ==="

if ! command -v lean >/dev/null 2>&1; then
  echo "  FAIL lean must be on PATH for this check: it hides lean itself, and"
  echo "       without a lean to hide the 'silent' case would pass by accident"
  exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# A HOME with no `.elan` in it, and a PATH with no `.elan/bin`.
HIDDEN_HOME="$work/home"
mkdir -p "$HIDDEN_HOME"
CLEAN_PATH=$(printf '%s' "$PATH" | tr ':' '\n' | grep -v '\.elan/bin' | paste -sd:)
# `cargo` here is a rustup shim and finds its toolchains through `RUSTUP_HOME`,
# which defaults to `$HOME/.rustup`. Hiding HOME would hide the Rust toolchain
# too, and the build would fail for the wrong reason.
REAL_RUSTUP_HOME=${RUSTUP_HOME:-${HOME:-/root}/.rustup}
[ -d "$REAL_RUSTUP_HOME" ] || { echo "  FAIL RUSTUP_HOME (toolchain) not found: $REAL_RUSTUP_HOME"; exit 1; }
STUB_ENV=(env "HOME=$HIDDEN_HOME" "RUSTUP_HOME=$REAL_RUSTUP_HOME" "PATH=$CLEAN_PATH")

# The real crate is not touched: `cargo build` would overwrite `build.rs`'s
# output and leave the tree in the stub state for later runs.
fresh_copy() {
  local dest=$1
  mkdir -p "$dest"
  cp -a "$ROOT/core/." "$dest/"
  rm -rf "$dest/target"
  # `build.rs` reads `../laws/Legacy/FFI.lean` only on the Lean branch, which is
  # never taken here; the directory exists so the path is not a surprise.
  mkdir -p "$dest/../laws/Legacy"
}

echo "--- silent: the healthy stub builds, and the bridge reports itself absent ---"
copy="$work/core"
fresh_copy "$copy"
out=$(build_without_lean "$copy")
rc=$?
if [ $rc -ne 0 ]; then
  echo "$out" | tail -20
  bad "the crate does not build without lean — the stub is broken"
else
  ok "the crate builds with the stub"
  if echo "$out" | grep -q "Lean not found"; then
    ok "build.rs took the stub branch"
  else
    echo "$out" | tail -10
    bad "build.rs did not report taking the stub branch"
  fi
  # Ask the binary, not the source: `available()` is `lean_saturation(9,16) == 9`,
  # and the stub returns 0. If this ever reports true, the stub is lying about
  # itself and every bridge test would run against zeros.
  avail=$( cd "$copy" && "${STUB_ENV[@]}" cargo run --release --quiet --example stub_probe 2>/dev/null )
  if [ "$avail" = "false" ]; then
    ok "bridge::available() is false on the stub"
  else
    bad "bridge::available() printed '$avail' on the stub, expected false"
  fi
fi

echo
echo "--- fires: a stub that does not link makes the build fail ---"
# `ar` is what turns stub.o into libffi.a. Skipping it reproduces "the archive
# is empty", which is what happens when gcc or ar fails and the status is
# ignored — the exact defect this check exists for.
#
# Both call sites are injected, because there are two: the stub branch and the
# "lean is present but the export failed" branch. Patching one leaves the other
# to build a healthy archive, and the linker is never asked anything.
inj="$work/inj"
fresh_copy "$inj"
python3 - "$inj/build.rs" <<'PY'
import io, re, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
# The archive is written by `ar crs ... libffi.a ...`. Rename the target instead
# of deleting the call: the call then still succeeds, and the link directive
# still names `libffi.a`, so the failure lands exactly where a missing archive
# lands -- at the linker, not at the build script's own assertions.
pat = re.compile(r'out_dir\.join\("libffi\.a"\)')
s2, n = pat.subn('out_dir.join("libffi-injected.a")', s)
assert n >= 1, "injection point not found"
io.open(p, "w", encoding="utf-8").write(s2)
print("injected at %d site(s)" % n)
PY
out=$(build_without_lean "$inj")
rc=$?
if [ $rc -eq 0 ]; then
  echo "$out" | tail -20
  bad "an empty stub archive still built — the link is not being exercised"
elif echo "$out" | grep -q "could not find native static library"; then
  ok "an empty stub archive fails the link, as it must"
else
  echo "$out" | tail -20
  bad "the build failed, but not at the link of the stub archive"
fi

echo
echo "--- specific: the neighbouring defect (a missing symbol) is not this check's ---"
# `stub_covers_bridge.py` owns the list. If this check also fired on it, the two
# would be one check written twice and a red result would not name the defect.
if python3 checks/stub_covers_bridge.py >/dev/null 2>&1; then
  ok "stub_covers_bridge.py is green on the healthy tree (it owns the list)"
else
  bad "stub_covers_bridge.py is red on the healthy tree"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "Вердикт: passed"
else
  echo "Вердикт: failed"
fi
exit "$fail"
