#!/usr/bin/env bash
# D-Q6 production candidate runner. Supply an already reviewed local candidate
# binary and a new output directory. This script never builds or edits source.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

usage() {
  printf 'usage: %s <new-results-dir> [local-exp_dq6-binary]\n' "$0" >&2
  exit 2
}

[[ $# -ge 1 && $# -le 2 ]] || usage
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ANALYZER="$HERE/dq6_analyze.py"
TASK="$HERE/EXP-2026-4103-task.json"
CANDIDATE_SOURCE="$HERE/exp_dq6_controls_candidate.rs"
DRIVER_SOURCE="${D_Q6_DRIVER_SOURCE:-$CANDIDATE_SOURCE}"
TOOLCHAIN="${D_Q6_TOOLCHAIN:-}"
DEATH_H='0.99,0.995,0.998,0.999,0.9995,0.9,0.95,0.98'
DEATH_CONTROLS='1.0'
SHAM_H='0.995,0.999'
COMMON=(--n 100 --steps 800000 --seed-base 4301 --seeds 12)

[[ -f "$ANALYZER" ]] || { printf 'analyzer is absent: %s\n' "$ANALYZER" >&2; exit 2; }
[[ -f "$TASK" ]] || { printf 'task is absent: %s\n' "$TASK" >&2; exit 2; }
[[ -f "$CANDIDATE_SOURCE" ]] || { printf 'candidate source is absent: %s\n' "$CANDIDATE_SOURCE" >&2; exit 2; }
[[ -f "$DRIVER_SOURCE" ]] || { printf 'driver source is absent: %s\n' "$DRIVER_SOURCE" >&2; exit 2; }
[[ -n "$TOOLCHAIN" && -f "$TOOLCHAIN" ]] || { printf 'D_Q6_TOOLCHAIN must name an existing toolchain JSON\n' >&2; exit 2; }

select_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    if command -v -- "$PYTHON" >/dev/null 2>&1 && "$PYTHON" --version >/dev/null 2>&1; then
      command -v -- "$PYTHON"
      return 0
    fi
    printf 'PYTHON is not a working interpreter: %s\n' "$PYTHON" >&2
    return 2
  fi
  local candidate
  for candidate in python python3 py; do
    if command -v -- "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
      command -v -- "$candidate"
      return 0
    fi
  done
  printf 'a working Python interpreter is required\n' >&2
  return 2
}
PYTHON_BIN="$(select_python)"
BUDGET="$("$PYTHON_BIN" - "$TASK" "$TOOLCHAIN" <<'PY'
import json, sys
from pathlib import Path
doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
task = doc.get("task", doc.get("payload", doc))
assert task.get("schema") == "task/v1" and task.get("id") == "EXP-2026-4103"
assert int(task.get("version", -1)) >= 3, "published D-Q6 version >=3 is required"
budget = int(task["budget"]["disk_bytes"])
assert budget > 0
toolchain = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert isinstance(toolchain, dict) and toolchain
print(budget)
PY
)"

if [[ $# -eq 2 ]]; then
  DRIVER="$2"
elif [[ -x "$HERE/exp_dq6" ]]; then
  DRIVER="$HERE/exp_dq6"
elif [[ -x "$HERE/exp_dq6.exe" ]]; then
  DRIVER="$HERE/exp_dq6.exe"
else
  printf 'no local candidate binary found; pass its path as argument 2\n' >&2
  exit 2
fi
[[ -f "$DRIVER" && -x "$DRIVER" ]] || { printf 'driver is not an executable file: %s\n' "$DRIVER" >&2; exit 2; }
DRIVER="$(readlink -f -- "$DRIVER")"

OUT_ARG="$1"
while [[ "$OUT_ARG" == */ && "$OUT_ARG" != / ]]; do OUT_ARG="${OUT_ARG%/}"; done
[[ -n "$OUT_ARG" && "$OUT_ARG" != / ]] || usage
OUT_PARENT="$(dirname -- "$OUT_ARG")"
OUT_BASE="$(basename -- "$OUT_ARG")"
[[ -d "$OUT_PARENT" ]] || { printf 'output parent is absent: %s\n' "$OUT_PARENT" >&2; exit 2; }
OUT_PARENT="$(cd -- "$OUT_PARENT" && pwd)"
OUT="$OUT_PARENT/$OUT_BASE"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { printf 'refusing to overwrite existing output: %s\n' "$OUT" >&2; exit 2; }

mkdir -- "$OUT"
mkdir -- "$OUT/raw" "$OUT/analysis"
STARTED_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ACTIVE_PID=''

cleanup() {
  local status=$?
  if [[ -n "$ACTIVE_PID" ]] && kill -0 "$ACTIVE_PID" 2>/dev/null; then
    kill "$ACTIVE_PID" 2>/dev/null || true
    wait "$ACTIVE_PID" 2>/dev/null || true
  fi
  return "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

output_bytes() {
  "$PYTHON_BIN" - "$OUT" <<'PY'
import os, sys
root = sys.argv[1]
total = 0
for directory, _, files in os.walk(root, followlinks=False):
    for name in files:
        try:
            total += os.stat(os.path.join(directory, name), follow_symlinks=False).st_size
        except FileNotFoundError:
            pass
print(total)
PY
}

check_budget() {
  local bytes
  bytes="$(output_bytes)"
  if (( bytes > BUDGET )); then
    printf 'output budget exceeded: %s > %s bytes\n' "$bytes" "$BUDGET" >&2
    return 1
  fi
}

run_monitored() {
  local label="$1" stdout_path="$2" stderr_path="$3"
  shift 3
  check_budget
  "$@" >"$stdout_path" 2>"$stderr_path" &
  ACTIVE_PID=$!
  while kill -0 "$ACTIVE_PID" 2>/dev/null; do
    sleep 1
    check_budget
  done
  local status=0
  if wait "$ACTIVE_PID"; then
    status=0
  else
    status=$?
  fi
  ACTIVE_PID=''
  if (( status != 0 )); then
    printf '%s failed with status %s; see %s\n' "$label" "$status" "$stderr_path" >&2
    exit "$status"
  fi
  check_budget
  printf '%s completed\n' "$label"
}

# Exactly the planned production grid. Empty --h/--controls suppress driver
# defaults where a control mode must not inherit the death-reset grid.
run_monitored 'death-reset production mode' \
  "$OUT/raw/death-reset.csv" "$OUT/raw/death-reset.stderr.txt" \
  "$DRIVER" --h "$DEATH_H" --controls "$DEATH_CONTROLS" --derivative-neighbors \
  "${COMMON[@]}" --control death-reset --event-histogram "$OUT/raw/death-reset-histogram.csv"

run_monitored 'cap production mode' \
  "$OUT/raw/cap.csv" "$OUT/raw/cap.stderr.txt" \
  "$DRIVER" --h '' --controls '1.0' "${COMMON[@]}" \
  --control cap --event-histogram "$OUT/raw/cap-histogram.csv"

run_monitored 'sham production mode' \
  "$OUT/raw/sham.csv" "$OUT/raw/sham.stderr.txt" \
  "$DRIVER" --h "$SHAM_H" --controls '' "${COMMON[@]}" \
  --control sham --event-histogram "$OUT/raw/sham-histogram.csv"

# Use the analyzer's strict parsers for pre-analysis registry, count and hash
# validation. The manifest is an input to the subsequent full analysis.
"$PYTHON_BIN" - "$ANALYZER" "$OUT" "$TASK" "$DRIVER" "$CANDIDATE_SOURCE" "$STARTED_UTC" "$DRIVER_SOURCE" "$TOOLCHAIN" <<'PY'
import hashlib, json, os, runpy, sys
from pathlib import Path
analyzer, out, task, driver, source = map(Path, sys.argv[1:6])
started = sys.argv[6]
driver_source = Path(sys.argv[7])
toolchain_path = Path(sys.argv[8])
task_doc = json.loads(task.read_text(encoding="utf-8"))
task_payload = task_doc.get("task", task_doc.get("payload", task_doc))
canonical_task = json.dumps(task_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
task_version_sha256 = task_doc.get("task_version_sha256") or hashlib.sha256(canonical_task).hexdigest()
toolchain = json.loads(toolchain_path.read_text(encoding="utf-8"))
module = runpy.run_path(str(analyzer), run_name="dq6_runner_raw_validation")
raw = {
    "death-reset": (out / "raw/death-reset.csv", out / "raw/death-reset-histogram.csv"),
    "cap": (out / "raw/cap.csv", out / "raw/cap-histogram.csv"),
    "sham": (out / "raw/sham.csv", out / "raw/sham-histogram.csv"),
}
data = module["load_inputs"](
    raw["death-reset"][0], raw["cap"][0], raw["sham"][0],
    raw["death-reset"][1], raw["cap"][1], raw["sham"][1],
)
common = ["--n", "100", "--steps", "800000", "--seed-base", "4301", "--seeds", "12"]
commands = [
    {"control": "death-reset", "argv": [str(driver), "--h", "0.99,0.995,0.998,0.999,0.9995,0.9,0.95,0.98", "--controls", "1.0", "--derivative-neighbors", *common, "--control", "death-reset", "--event-histogram", str(raw["death-reset"][1])]},
    {"control": "cap", "argv": [str(driver), "--h", "", "--controls", "1.0", *common, "--control", "cap", "--event-histogram", str(raw["cap"][1])]},
    {"control": "sham", "argv": [str(driver), "--h", "0.995,0.999", "--controls", "", *common, "--control", "sham", "--event-histogram", str(raw["sham"][1])]},
]
files = {}
for control, paths in raw.items():
    for kind, path in zip(("summary", "histogram"), paths):
        info = module["sha256_file"](path)
        info["kind"] = kind
        info["control"] = control
        files[str(path.relative_to(out))] = info
    stderr = out / f"raw/{control}.stderr.txt"
    info = module["sha256_file"](stderr)
    info["kind"] = "driver_stderr"
    files[str(stderr.relative_to(out))] = info
raw_bytes = sum(os.stat(path, follow_symlinks=False).st_size for path in out.rglob("*") if path.is_file())
manifest = {
    "schema": "dq6-run/v1",
    "task": "EXP-2026-4103",
    "task_version": int(task_payload["version"]),
    "task_version_sha256": task_version_sha256,
    "base_commit": task_payload["base_commit"],
    "started_utc": started,
    "raw_validated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "driver": module["sha256_file"](driver),
    "driver_source": module["sha256_file"](driver_source),
    "candidate_source": module["sha256_file"](source),
    "analyzer": module["sha256_file"](analyzer),
    "task_file": module["sha256_file"](task),
    "toolchain": toolchain,
    "toolchain_file": module["sha256_file"](toolchain_path),
    "configuration": {"N": 100, "steps": 800000, "seeds": list(range(4301, 4313)), "sample_steps": [100000, 200000, 400000, 800000], "bootstrap_replicates": 10000, "histogram_detail": "global-only", "organism_histogram_opt_in": False},
    "commands": commands,
    "files": files,
    "validation": data.validation,
    "output_budget_bytes": int(task_payload["budget"]["disk_bytes"]),
    "output_bytes_at_raw_validation": raw_bytes,
    "confirmatory_execution": "only this explicitly invoked runner executes the production plan",
    "network_used": False,
}
with (out / "run-manifest.json").open("x", encoding="utf-8") as handle:
    json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    handle.write("\n")
print("DQ6_RAW_VALIDATION_OK")
PY

{
  printf 'started_utc=%s\n' "$STARTED_UTC"
  printf 'environment_recorded_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'argv0=%s\n' "$0"
  printf 'out=%s\n' "$OUT"
  printf 'driver=%s\n' "$DRIVER"
  printf 'driver_source=%s\n' "$DRIVER_SOURCE"
  printf 'toolchain=%s\n' "$TOOLCHAIN"
  printf 'python=%s\n' "$PYTHON_BIN"
  printf 'output_budget_bytes=%s\n' "$BUDGET"
  printf 'network_used=false\n'
  "$PYTHON_BIN" - "$TASK" "$TOOLCHAIN" <<'PY'
import hashlib, json, sys
from pathlib import Path
doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
task = doc.get("task", doc.get("payload", doc))
canonical = json.dumps(task, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
print(f"task_version={int(task['version'])}")
print(f"task_version_sha256={doc.get('task_version_sha256') or hashlib.sha256(canonical).hexdigest()}")
print(f"base_commit={task['base_commit']}")
print("toolchain_json=" + json.dumps(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")), ensure_ascii=False, sort_keys=True))
PY
  "$PYTHON_BIN" --version
  bash --version
  uname -a
  sha256sum "$DRIVER" "$ANALYZER" "$TASK" "$CANDIDATE_SOURCE" "$DRIVER_SOURCE" "$TOOLCHAIN"
} >"$OUT/environment.txt"

run_monitored 'D-Q6 analyzer' \
  "$OUT/analysis/analyzer.stdout.txt" "$OUT/analysis/analyzer.stderr.txt" \
  "$PYTHON_BIN" "$ANALYZER" \
  --death-reset "$OUT/raw/death-reset.csv" \
  --cap "$OUT/raw/cap.csv" \
  --sham "$OUT/raw/sham.csv" \
  --death-histogram "$OUT/raw/death-reset-histogram.csv" \
  --cap-histogram "$OUT/raw/cap-histogram.csv" \
  --sham-histogram "$OUT/raw/sham-histogram.csv" \
  --out "$OUT/analysis" \
  --task "$TASK" --driver "$DRIVER" --driver-source "$DRIVER_SOURCE" \
  --candidate-source "$CANDIDATE_SOURCE" \
  --environment "$OUT/environment.txt" --run-manifest "$OUT/run-manifest.json"

"$PYTHON_BIN" - "$OUT" "$BUDGET" <<'PY'
import json, os, sys
from pathlib import Path
out = Path(sys.argv[1])
budget = int(sys.argv[2])
required = ("seed_metrics.csv", "fits.csv", "bootstrap.csv", "controls.json", "summary.json")
assert all((out / "analysis" / name).is_file() for name in required)
summary = json.loads((out / "analysis/summary.json").read_text(encoding="utf-8"))
assert summary["scientific_outcome"] in ("passed", "failed", "void")
assert summary["reported_scientific_classification"] in ("passed", "horizon_limited", "yoked_reproduces_pole", "endpoint_failure", "specificity_not_confirmed", "void")
size = sum(os.stat(path, follow_symlinks=False).st_size for path in out.rglob("*") if path.is_file())
assert size <= budget, size
print(json.dumps({
    "out": str(out),
    "scientific_outcome": summary["scientific_outcome"],
    "reported_scientific_classification": summary["reported_scientific_classification"],
    "controls": summary["controls"],
    "output_bytes": size,
    "output_budget_bytes": budget,
}, sort_keys=True))
PY
