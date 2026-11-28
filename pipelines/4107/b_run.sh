#!/usr/bin/env bash
# Reproduce EXP-2026-4107 twice. Usage:
#   b_run.sh /path/to/exp_b_unit /new/output-directory [task-payload.json] [driver-source.rs]
# The task payload is optional for standalone fixture runs; leased runs always pass it.
set -euo pipefail
export LC_ALL=C

BIN=${1:?usage: b_run.sh /path/to/exp_b_unit /new/output-directory [task-payload.json] [driver-source.rs]}
OUT=${2:?usage: b_run.sh /path/to/exp_b_unit /new/output-directory [task-payload.json] [driver-source.rs]}
TASK_PAYLOAD=${3:-${B_UNIT_TASK_PAYLOAD:-}}
DRIVER_SOURCE=${4:-${B_UNIT_DRIVER_SOURCE:-}}
SEEDS=${B_UNIT_SEEDS:-1}
SEED_BASE=${B_UNIT_SEED_BASE:-5401}
PYTHON_BIN=${B_UNIT_PYTHON:-}
if [[ -z "$PYTHON_BIN" ]]; then
  if python3 --version >/dev/null 2>&1; then PYTHON_BIN=python3; else PYTHON_BIN=python; fi
fi
if ! "$PYTHON_BIN" --version >/dev/null 2>&1; then
  printf 'no working Python interpreter (set B_UNIT_PYTHON)\n' >&2
  exit 2
fi
if ! [[ "$SEEDS" =~ ^[0-9]+$ ]] || [[ "$SEEDS" != "1" ]]; then
  printf 'B_UNIT_SEEDS must be exactly 1 for the registered B-unit contract\n' >&2
  exit 2
fi
if ! [[ "$SEED_BASE" =~ ^[0-9]+$ ]] || [[ "$SEED_BASE" != "5401" ]]; then
  printf 'B_UNIT_SEED_BASE must be exactly 5401 for the registered B-unit contract\n' >&2
  exit 2
fi
if [[ ! -f "$BIN" ]]; then
  printf 'driver is not a regular file: %s\n' "$BIN" >&2
  exit 2
fi
if [[ -n "$TASK_PAYLOAD" && ! -f "$TASK_PAYLOAD" ]]; then
  printf 'task payload is not a regular file: %s\n' "$TASK_PAYLOAD" >&2
  exit 2
fi
if [[ -n "$DRIVER_SOURCE" && ! -f "$DRIVER_SOURCE" ]]; then
  printf 'driver source is not a regular file: %s\n' "$DRIVER_SOURCE" >&2
  exit 2
fi

BIN=$(readlink -f -- "$BIN")
if [[ -n "$TASK_PAYLOAD" ]]; then TASK_PAYLOAD=$(readlink -f -- "$TASK_PAYLOAD"); fi
if [[ -n "$DRIVER_SOURCE" ]]; then DRIVER_SOURCE=$(readlink -f -- "$DRIVER_SOURCE"); fi

# Validate task identity before creating the output directory. A rejected draft
# or placeholder must leave no run artifacts behind.
TASK_METADATA_JSON=null
if [[ -n "$TASK_PAYLOAD" ]]; then
  TASK_METADATA_JSON=$("$PYTHON_BIN" - "$TASK_PAYLOAD" "$SEEDS" "$SEED_BASE" <<'PY'
import json
import sys
from pathlib import Path


def unwrap_task(document):
    if not isinstance(document, dict):
        raise ValueError("task payload must be a JSON object")
    if document.get("draft_only") is True or document.get("do_not_execute") is True:
        raise ValueError("draft task payload must be finalized and published before execution")
    wrapper = document
    task = document
    for key in ("payload", "task", "task_payload"):
        if isinstance(document.get(key), dict):
            task = document[key]
            break
    if task.get("schema") != "task/v1" or task.get("id") != "EXP-2026-4107":
        raise ValueError("task payload must contain task/v1 for EXP-2026-4107")
    raw_version = task.get("version")
    if not isinstance(raw_version, int) or isinstance(raw_version, bool) or raw_version < 1:
        raise ValueError("task payload version must be an integer >=1")
    task_hash = (task.get("task_version_sha256") or wrapper.get("current_sha256")
                 or wrapper.get("task_version_sha256") or wrapper.get("sha256"))
    spec = task.get("spec")
    params = spec.get("parameters", {}) if isinstance(spec, dict) else {}
    if params.get("seeds") != 1 or params.get("seed_base") != 5401 or spec.get("seeds") != [5401]:
        raise ValueError("task seed grid must be seeds=1 and seed_base=5401")
    if params.get("schedule_fingerprint") != "schedule: t*=5;t**=10;t***=15;m=3;k=2;r0=R0/2":
        raise ValueError("task schedule fingerprint does not match the B-unit contract")
    if int(sys.argv[2]) != 1 or int(sys.argv[3]) != 5401:
        raise ValueError("runner seed grid differs from the task: expected seeds=1 seed_base=5401")
    metadata = {
        "task_id": task["id"],
        "task_version": raw_version,
        "task_version_sha256": task_hash,
        "base_commit": task.get("base_commit"),
    }
    if wrapper is not task:
        if wrapper.get("task_id") not in (None, metadata["task_id"]):
            raise ValueError("task wrapper id mismatch")
        if wrapper.get("current_version") is not None and int(wrapper["current_version"]) != metadata["task_version"]:
            raise ValueError("task wrapper version mismatch")
        outer_hash = wrapper.get("current_sha256") or wrapper.get("task_version_sha256") or wrapper.get("sha256")
        if outer_hash is not None and outer_hash != task_hash:
            raise ValueError("task wrapper hash mismatch")
    if (not isinstance(metadata["task_version_sha256"], str)
            or len(metadata["task_version_sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in metadata["task_version_sha256"])):
        raise ValueError("task payload has no lowercase task-version SHA256")
    if metadata["task_version_sha256"] == "0" * 64:
        raise ValueError("task payload still has the draft task-version SHA256 placeholder")
    if not isinstance(metadata["base_commit"], str) or not (
            7 <= len(metadata["base_commit"]) <= 40
            and all(char in "0123456789abcdef" for char in metadata["base_commit"])):
        raise ValueError("task payload base_commit must be 7..40 lowercase hex characters")
    if not metadata["base_commit"].strip("0"):
        raise ValueError("task payload still has the draft base_commit placeholder")
    return metadata


document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps(unwrap_task(document), ensure_ascii=False, sort_keys=True))
PY
)
fi

mkdir -p -- "$OUT"
OUT=$(cd -- "$OUT" && pwd)
for existing in raw.csv steps.csv raw-manifest.json run1 run2; do
  if [[ -e "$OUT/$existing" ]]; then
    printf 'refusing to overwrite %s/%s\n' "$OUT" "$existing" >&2
    exit 2
  fi
done
mkdir -p -- "$OUT/run1" "$OUT/run2"

"$PYTHON_BIN" - "$OUT" "$BIN" "$SEEDS" "$SEED_BASE" "$TASK_PAYLOAD" "$DRIVER_SOURCE" "$TASK_METADATA_JSON" <<'PY'
import datetime as dt
import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys

out = Path(sys.argv[1])
binary = Path(sys.argv[2])
seeds = int(sys.argv[3])
seed_base = int(sys.argv[4])
task_path = Path(sys.argv[5]) if sys.argv[5] else None
source_path = Path(sys.argv[6]) if sys.argv[6] else None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(argv):
    try:
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        return result.stdout.strip() or "unavailable"
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


task_metadata = json.loads(sys.argv[7])
task_payload_sha256 = None
if task_path is not None:
    if task_metadata is None:
        raise ValueError("task metadata preflight did not return an identity")
    task_payload_sha256 = digest(task_path)
    shutil.copyfile(task_path, out / "task.json")

if source_path is None:
    candidate = binary.parent / "../../src/bin/exp_b_unit.rs"
    if candidate.is_file():
        source_path = candidate.resolve()

started_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
environment = {
    "os": platform.platform(),
    "kernel": platform.release(),
    "architecture": platform.machine(),
    "cpu": platform.processor() or "unknown",
    "driver_path": str(binary),
    "driver_sha256": digest(binary),
    "driver_source_path": str(source_path) if source_path else None,
    "driver_source_sha256": digest(source_path) if source_path else None,
    "started_utc": started_utc,
    "seeds": seeds,
    "seed_base": seed_base,
    "window_T": 40,
    "schedule": "t*=5;t**=10;t***=15;m=3;k=2;r0=R0/2",
    "parameters": {
        "R0": 0.1, "r0": 0.05, "D0": 0.5,
        "D_half": 0.25, "D_third": 1.0 / 6.0, "k_D": 0.3,
    },
    "no_unseeded_random": True,
    "repeat_executions": 2,
}
if task_metadata is not None:
    environment.update(task_metadata)
    environment["task_payload_sha256"] = task_payload_sha256

toolchain = {
    "rust": version(["rustc", "--version"]),
    "cargo": version(["cargo", "--version"]),
    "python": version([sys.executable, "--version"]),
    "python_executable": sys.executable,
}
for name, value in (("environment.json", environment), ("toolchain.json", toolchain)):
    (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

text_lines = [
    f"task={environment.get('task_id', 'EXP-2026-4107')}",
    f"version={environment.get('task_version', 'standalone')}",
    f"task_version_sha256={environment.get('task_version_sha256', 'unavailable')}",
    f"base_commit={environment.get('base_commit', 'unavailable')}",
    f"driver={binary}",
    f"driver_sha256={environment['driver_sha256']}",
    f"driver_source={environment['driver_source_path'] or 'unavailable'}",
    f"driver_source_sha256={environment['driver_source_sha256'] or 'unavailable'}",
    f"started_utc={started_utc}",
    f"seeds={seeds}", f"seed_base={seed_base}",
    "schedule=t*=5;t**=10;t***=15;m=3;k=2;r0=R0/2",
    f"rust={toolchain['rust']}", f"cargo={toolchain['cargo']}", f"python={toolchain['python']}",
    f"platform={environment['os']}", f"kernel={environment['kernel']}",
]
(out / "environment.txt").write_text("\n".join(text_lines) + "\n", encoding="utf-8")
PY

for run in run1 run2; do
  set +e
  "$BIN" --seeds "$SEEDS" --seed-base "$SEED_BASE" --steps-out "$OUT/$run/steps.csv" \
    > "$OUT/$run/raw.csv" 2> "$OUT/$run/driver.stderr.log"
  rc=$?
  set -euo pipefail
  printf '%s\n' "$rc" > "$OUT/$run/driver.rc"
  if [[ ! -f "$OUT/$run/steps.csv" ]]; then
    : > "$OUT/$run/steps.csv"
  fi
done

"$PYTHON_BIN" - "$OUT" "$SEEDS" "$SEED_BASE" <<'PY'
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

out = Path(sys.argv[1])
seeds = int(sys.argv[2])
seed_base = int(sys.argv[3])
environment = json.loads((out / "environment.json").read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_count(path):
    if not path.is_file() or path.stat().st_size == 0:
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return max(0, sum(1 for _ in csv.reader(handle)) - 1)


def file_record(path, rel):
    return {
        "path": rel,
        "rows": row_count(path),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def stderr_lines(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


executions = {}
for name in ("run1", "run2"):
    run_dir = out / name
    lines = stderr_lines(run_dir / "driver.stderr.log")
    executions[name] = {
        "directory": name,
        "returncode": int((run_dir / "driver.rc").read_text(encoding="utf-8").strip()),
        "argv": [
            "exp_b_unit", "--seeds", str(seeds), "--seed-base", str(seed_base),
            "--steps-out", f"{name}/steps.csv",
        ],
        "raw_csv": file_record(run_dir / "raw.csv", f"{name}/raw.csv"),
        "steps_csv": file_record(run_dir / "steps.csv", f"{name}/steps.csv"),
        "stdout_sha256": digest(run_dir / "raw.csv"),
        "stderr": file_record(run_dir / "driver.stderr.log", f"{name}/driver.stderr.log"),
        "driver_schedule_line": next((line for line in lines if line.startswith("schedule:")), None),
        "driver_sensitivity_line": next((line for line in lines if line.startswith("sensitivity:")), None),
    }
    (run_dir / "run-manifest.json").write_text(
        json.dumps({"task": environment.get("task_id", "EXP-2026-4107"), **executions[name]},
                   ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

shutil.copyfile(out / "run1/raw.csv", out / "raw.csv")
shutil.copyfile(out / "run1/steps.csv", out / "steps.csv")
raw_identical = (out / "run1/raw.csv").read_bytes() == (out / "run2/raw.csv").read_bytes()
steps_identical = (out / "run1/steps.csv").read_bytes() == (out / "run2/steps.csv").read_bytes()
rc1 = executions["run1"]["returncode"]
rc2 = executions["run2"]["returncode"]
if rc1 != 0:
    runner_rc = rc1
elif rc2 != 0:
    runner_rc = rc2
elif not (raw_identical and steps_identical):
    runner_rc = 4
else:
    runner_rc = 0

manifest = {
    "schema": "raw-manifest/v2",
    "task_id": environment.get("task_id", "EXP-2026-4107"),
    "task_version": environment.get("task_version"),
    "task_version_sha256": environment.get("task_version_sha256"),
    "base_commit": environment.get("base_commit"),
    "task_payload_sha256": environment.get("task_payload_sha256"),
    "driver_rc": rc1,
    "run2_driver_rc": rc2,
    "runner_rc": runner_rc,
    "seeds": seeds,
    "seed_base": seed_base,
    "argv": executions["run1"]["argv"],
    "driver": {
        "path": environment["driver_path"],
        "sha256": environment["driver_sha256"],
        "source_path": environment.get("driver_source_path"),
        "source_sha256": environment.get("driver_source_sha256"),
    },
    "environment": environment,
    "toolchain": json.loads((out / "toolchain.json").read_text(encoding="utf-8")),
    "expected_arms": 12,
    "expected_raw_rows": 12 * seeds,
    "expected_steps_rows": 12 * seeds * 40,
    "raw_csv": file_record(out / "raw.csv", "raw.csv"),
    "steps_csv": file_record(out / "steps.csv", "steps.csv"),
    "executions": executions,
    "repeat": {
        "raw_csv_byte_identical": raw_identical,
        "steps_csv_byte_identical": steps_identical,
        "raw_sha256_equal": executions["run1"]["raw_csv"]["sha256"] == executions["run2"]["raw_csv"]["sha256"],
        "steps_sha256_equal": executions["run1"]["steps_csv"]["sha256"] == executions["run2"]["steps_csv"]["sha256"],
        "byte_identical": raw_identical and steps_identical,
    },
}
(out / "raw-manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "driver_rc": rc1, "run2_driver_rc": rc2, "runner_rc": runner_rc,
    "raw_rows": manifest["raw_csv"]["rows"], "steps_rows": manifest["steps_csv"]["rows"],
    "repeat_byte_identical": manifest["repeat"]["byte_identical"],
}, sort_keys=True))
sys.exit(runner_rc if 0 <= runner_rc <= 255 else 1)
PY
