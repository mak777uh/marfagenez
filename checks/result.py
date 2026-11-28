"""Единый формат результатов эксперимента.

## Зачем

Сейчас эксперименты печатают в консоль. Визуализировать нечего.

Этот модуль — контракт: каждый эксперимент сохраняет JSON, из которого
можно построить любое представление, не пересчитывая ничего из текста.

## Формат

    {
      "schema": "marfagenez.experiment-result.v3",  # v2 is accepted as legacy input
      "experiment_id": "frozen-ceiling",
      "run_id": "run-2026-11-11T10-00-00",
      "model_commit": "abc1234",
      "seed": 20250101,
      "parameters": {...},

      "arithmetic": {...},        // §1: арифметика ДО прогона
      "mde": {...},               // §1: минимально детектируемый эффект
      "conditions": {             // плечи
        "A": {"label": "...", "metrics": {...}, "hash": "..."},
        "B": {...}
      },
      "series": {...},
      "controls": {               // §2: три теста контроля
        "fires":    {"passed": true, "evidence": "..."},
        "silent":   {"passed": true, "evidence": "..."},
        "specific": {"passed": true, "evidence": "..."}
      },
      "verdict": {                // §4: пять исходов
        "kind": "passed",
        "reason": "..."
      },
      "hashes": {"A": "...", "B": "...", "C": "..."},  // §5
      "limitations": [...],       // §6
      "command": "python3 checks/exp05_frozen.py"
    }

## Пять вердиктов, не два (§4)

- `passed` — эффект есть, контроли прошли
- `failed` — эффекта нет
- `void` — манипуляция не связана с миром, контроль сломан, или плечи
  неразличимы (одинаковые хэши). **Ничего не узнали о механизме.**
- `insensitive by construction` — арифметика говорит, что плечи не могут
  различаться. **Ничего не узнали о механизме, но узнали о дизайне.**
- `not applicable` — носителя вопроса нет: событие недостижимо, окно не
  стационарно, предикат не зависит от состояния. **Вопрос не был задан.**
  Отличать от `void`: там инструмент сломался, здесь измерять нечего.

## Правило

Визуализатор НЕ пересчитывает. Он читает.

Если чего-то нет в JSON — этого нет в визуализации.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any

SCHEMA_V2 = "marfagenez.experiment-result.v2"
SCHEMA = "marfagenez.experiment-result.v3"

ROLES = ("verification", "validation")
PHASES = ("confirmatory", "exploratory")


def validate_design_fields(role: str, phase: str) -> None:
    """Check role/phase semantics for a newly-created record."""
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; expected one of {ROLES}")
    if phase not in PHASES:
        raise ValueError(f"unknown phase {phase!r}; expected one of {PHASES}")
    if role == "validation" and phase == "confirmatory":
        raise ValueError(
            "validation cannot be confirmatory under the current lab policy"
        )


def set_design(result: dict[str, Any], role: str, phase: str) -> None:
    """Assign the epistemic role and phase to a new result record."""
    validate_design_fields(role, phase)
    result["role"] = role
    result["phase"] = phase
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

#: The Rust source that owns the hash's version.
TRACE_RS = Path(__file__).resolve().parents[1] / "core" / "src" / "trace.rs"

#: The declaration of `HASH_VERSION` in `core/src/trace.rs`.
_HASH_VERSION_RE = re.compile(r'pub const HASH_VERSION: &str = "([^"]+)";')


def _read_hash_version() -> str:
    """The hash version, read out of the Rust source instead of copied here.

    A constant repeated in Python is a claim, and it drifts the moment
    somebody bumps the Rust one. Reading it back makes a divergence a crash
    here instead of a quiet lie in the record: an unversioned hash cannot be
    compared to a versioned one, and a wrongly labelled one cannot either.
    `checks/hash_version.py` performs the same read independently; it exists
    because a second reader is what turns the agreement into a check.
    """
    text = TRACE_RS.read_text(encoding="utf-8")
    m = _HASH_VERSION_RE.search(text)
    if m is None:
        raise RuntimeError(
            f"{TRACE_RS}: no `pub const HASH_VERSION: &str = \"...\";` "
            "found. The version is part of the record contract; a record "
            "written without it cannot be compared to a newer one."
        )
    return m.group(1)


HASH_VERSION_PY = _read_hash_version()

#: The five outcomes. Not two (AGENTS.md §4).
VERDICTS = (
    "passed",
    "failed",
    "void",
    "insensitive by construction",
    "not applicable",
)

#: The three control tests every control must pass (AGENTS.md §2).
CONTROL_TESTS = ("fires", "silent", "specific")


def _git_state() -> tuple[str, bool]:
    """Return the source commit and whether the source tree is dirty.

    `results/` is excluded because saved run records are output artifacts: a
    result must not make the *next* result dirty merely by being written.
    Git failures are fail-closed; an unpinned result is not reproducible.
    """
    root = Path(__file__).resolve().parents[1]
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=root, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal",
             "--", ".", ":!results"],
            capture_output=True, text=True, timeout=5, cwd=root, check=True,
        ).stdout
    except Exception as exc:
        raise RuntimeError(
            "cannot pin experiment result: git HEAD/status is unavailable"
        ) from exc
    if not head:
        raise RuntimeError("cannot pin experiment result: git returned an empty HEAD")
    return head, bool(status.strip())


def _git_commit() -> str:
    """Commit label for a new result; dirty source trees are explicit."""
    head, dirty = _git_state()
    return f"{head}+dirty" if dirty else head


def new_result(
    experiment_id: str,
    seed: int,
    parameters: dict[str, Any],
    command: str,
    *,
    question: str = "",
    role: str = "verification",
    phase: str = "exploratory",
) -> dict[str, Any]:
    """Create a v3 result; default conservatively to exploratory verification.

    Confirmatory status must be opted into explicitly after preregistration.
    Validation is reserved for independent external empirical comparisons.
    """
    validate_design_fields(role, phase)
    if not isinstance(experiment_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", experiment_id
    ):
        raise ValueError("experiment_id must be a safe 1-128 character identifier")
    if not isinstance(question, str):
        raise ValueError("question must be a string")
    now = datetime.now(timezone.utc)
    result = {
        "schema": SCHEMA,
        "role": role,
        "phase": phase,
        "experiment_id": experiment_id,
        "run_id": f"run-{now.strftime('%Y-%m-%dT%H-%M-%S')}-{uuid.uuid4().hex[:12]}",
        "model_commit": _git_commit(),
        "hash_version": HASH_VERSION_PY,
        "seed": seed,
        "parameters": parameters,
        "arithmetic": {},
        "conditions": {},
        "series": {},
        "controls": {},
        "verdict": None,
        "hashes": {},
        "limitations": [],
        "command": command,
        "created_at": now.isoformat(),
    }
    # Keep the exact legacy fingerprint for callers that haven't supplied a
    # research question. Experiment requires a non-empty question and always
    # persists it, so new scientific runs are identified by their question.
    if question:
        result["question"] = question
    return result


def set_arithmetic(result: dict[str, Any], arithmetic: dict[str, Any]) -> None:
    """Records the pre-registration arithmetic (AGENTS.md §1).

    The arithmetic must be written **before** the run. It says what makes the
    difference: income, cost, ratio, break-even. If the whole field is above the
    threshold in both arms, the experiment is insensitive by construction.

    The arithmetic is not a guarantee. E1's arithmetic modelled two of three terms
    and predicted dissolution where every arm survived.
    """
    result["arithmetic"] = arithmetic


def _z(p: float) -> float:
    """The standard-normal quantile at `p` (inverse CDF)."""
    return NormalDist().inv_cdf(p)


def arms_needed(
    sigma: float,
    effect: float,
    power: float = 0.8,
    alpha: float = 0.05,
) -> int:
    """How many arms (seeds) are needed to detect `effect` against `sigma`.

    The two-sample size for a difference of means, in the form `PROTOCOL-0`
    п. 3 records next to `arithmetic`:

        n = 2·(z_{α/2} + z_β)²·σ² / Δ²

    * `sigma` — the spread of the measured quantity **between seeds**, not
      within one run. It is measured, not assumed.
    * `effect` — `Δ`, the smallest difference worth calling a result, in the
      same units as `sigma`.
    * `alpha` — two-sided significance (0.05 -> z ≈ 1.96).
    * `power` — 1 − β (0.8 -> z ≈ 0.84).

    At `sigma = 0.2` this gives 6280 arms for `Δ = 1 %`, 252 for 5 % and 63 for
    10 %: 30 seeds can only separate effects of about 10 % or larger. An effect
    below that is `void` (the instrument could not see it), not `failed` (the
    world said no) — see `docs/REVIEW-emergence-notes.md` §3.1.

    Raises `ValueError` for a non-positive or non-finite `sigma` / `effect`,
    or probabilities outside `(0, 1)`: those are not questions.
    """
    for name, value in (("sigma", sigma), ("effect", effect)):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be finite and positive, got {value!r}")
    for name, value in (("alpha", alpha), ("power", power)):
        if not 0.0 < value < 1.0:
            raise ValueError(f"{name} must be in (0, 1), got {value!r}")
    z_alpha = _z(1.0 - alpha / 2.0)
    z_power = _z(power)
    return math.ceil(2.0 * (z_alpha + z_power) ** 2 * sigma**2 / effect**2)


def set_mde(
    result: dict[str, Any],
    sigma: float,
    effect: float,
    power: float = 0.8,
    alpha: float = 0.05,
) -> int:
    """Records the minimum detectable effect (`mde`) in `result`.

    `n = 2·(z_{α/2} + z_β)²·σ² / Δ²`; `sigma` is the between-seeds spread and
    `effect` is `Δ` in the same units. See `arms_needed` for the names and
    `docs/PROTOCOL-0.md` п. 3 for why the field is mandatory next to
    `arithmetic`: an effect the arm count cannot resolve is `void`, not
    `failed`.

    The key appears **only when this is called**, so records written before the
    rule existed keep their fingerprint and `save()` does not split them into a
    second file. A record written with `mde` is a different measurement: the
    field says how finely it could see.

    Returns the number of arms, so a caller can print it without recomputing.
    """
    n = arms_needed(sigma, effect, power=power, alpha=alpha)
    result["mde"] = {
        "sigma_between_seeds": sigma,
        "effect": effect,
        "alpha": alpha,
        "power": power,
        "arms_needed": n,
        "formula": "n = 2*(z_{alpha/2}+z_{power})^2*sigma^2/effect^2",
        "rule": (
            "an effect smaller than `effect` at `sigma_between_seeds` and "
            "`arms_needed` is `void`, not `failed`: the instrument could not "
            "see it, the world did not answer no"
        ),
    }
    return n


def add_condition(
    result: dict[str, Any],
    key: str,
    label: str,
    metrics: dict[str, Any],
    trace_hash: str | None = None,
) -> None:
    """Adds one condition (A/B/C) with its metrics and its dynamics hash.

    The hash is rule 5: two arms with the same hash are one arm.
    """
    entry: dict[str, Any] = {"label": label, "metrics": metrics}
    if trace_hash is not None:
        entry["hash"] = trace_hash
        result["hashes"][key] = trace_hash
    result["conditions"][key] = entry


def add_control(
    result: dict[str, Any],
    test: str,
    passed: bool,
    evidence: str,
) -> None:
    """Records one of the three control tests (AGENTS.md §2).

    - `fires`    — the control fires where the effect is known to be present
    - `silent`   — the control stays silent where the effect is known to be absent
    - `specific` — the control separates the mechanism under test from every other
                   mechanism that produces the same direction

    A control that fails (1) is broken. A control that fails (2) is broken.
    A control that passes both but fails (3) is blind.
    """
    if test not in CONTROL_TESTS:
        raise ValueError(
            f"unknown control test: {test!r}; expected one of {CONTROL_TESTS}"
        )
    result["controls"][test] = {"passed": bool(passed), "evidence": evidence}


def set_verdict(result: dict[str, Any], kind: str, reason: str) -> None:
    """Sets the verdict. Five outcomes, not two (AGENTS.md §4)."""
    if kind not in VERDICTS:
        raise ValueError(f"unknown verdict: {kind!r}; expected one of {VERDICTS}")
    result["verdict"] = {"kind": kind, "reason": reason}


def add_series(
    result: dict[str, Any],
    key: str,
    steps: list[float],
    values: list[float],
) -> None:
    """Adds a time series for one condition."""
    result["series"][key] = {"steps": steps, "values": values}


def add_limitation(result: dict[str, Any], text: str) -> None:
    """Records what the result does NOT show."""
    result["limitations"].append(text)


#: The fields that differ between two runs of the *same* measurement, or that
#: record re-runs of it. They are stripped before comparing, because none of
#: them says anything about the numbers.
#: Сколько последних коммитов хранить в `reproduced_at`. Хвост важнее начала: он
#: показывает, что результат воспроизводится и сейчас.
REPRODUCED_CAP = 20

_VOLATILE = ("run_id", "created_at", "model_commit", "reproduced_at")

#: Record metadata that is **not part of the measurement**. `hash_version`
#: says what computed the hashes, not what was measured: the same run
#: written before and after versioning has the same body and the same
#: hashes, and differs only in this field. Leaving it in the fingerprint
#: would make `save()` read every old record as a different measurement and
#: write a second file beside it instead of appending to `reproduced_at` --
#: the defect that once left `frozen-ceiling` with 122 copies of one
#: measurement. If the body matched, the hashes matched; the version is a
#: label on the measuring instrument, not a reading.
_NOT_PART_OF_THE_MEASUREMENT = ("hash_version",)


def _fingerprint(result: dict[str, Any]) -> str:
    """The result minus what changed only because it was written again.

    `model_commit` is stripped along with `run_id` and `created_at`: a re-run at
    a new commit that reproduces the same numbers is the same measurement, and
    its commit belongs inside the record (`reproduced_at`), not in a new file
    beside it.
    """
    body = {
        k: v
        for k, v in result.items()
        if k not in _VOLATILE and k not in _NOT_PART_OF_THE_MEASUREMENT
    }
    # For ordinary clean reruns, commit remains volatile as before. A dirty
    # marker changes the provenance class, so it must not deduplicate into a
    # clean, citable record with otherwise identical measurements.
    if str(result.get("model_commit", "")).endswith("+dirty"):
        body["model_commit"] = result["model_commit"]
    return json.dumps(body, sort_keys=True, ensure_ascii=False)


def _load(path: Path) -> dict[str, Any] | None:
    """The record in `path`, or `None` if it cannot be read as JSON."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _results_lock() -> int:
    """Serialize deduplication and result publication across gate processes."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if RESULTS_DIR.is_symlink() or not RESULTS_DIR.is_dir():
        raise RuntimeError(f"results root must be a real directory: {RESULTS_DIR}")
    token = hashlib.sha256(os.fsencode(str(RESULTS_DIR.resolve()))).hexdigest()[:20]
    lock_path = Path(tempfile.gettempdir()) / f"marfagenez-results-{token}.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError("results lock must be a regular file")
        fcntl.flock(fd, fcntl.LOCK_EX)
    except Exception:
        os.close(fd)
        raise
    return fd


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_temp_file(path: Path, payload: bytes) -> Path:
    """Write and fsync a temp file next to its eventual destination."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    fd = os.open(tmp, flags, 0o644)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise
    return tmp


def _atomic_replace_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically replace a regular JSON file after durable temp-file write."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        info = None
    if info is not None and (stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode)):
        raise RuntimeError(f"refusing to replace non-regular result path: {path}")
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    tmp = _write_temp_file(path, payload)
    try:
        os.replace(tmp, path)
        _fsync_directory(path.parent)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _atomic_create_json(path: Path, value: dict[str, Any]) -> bool:
    """Atomically create a result without ever overwriting an existing path."""
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    tmp = _write_temp_file(path, payload)
    try:
        try:
            # Linking a same-filesystem fsynced temp file gives an atomic
            # no-replace publication; the canonical name never contains
            # partially written JSON and a collision cannot truncate a record.
            os.link(tmp, path, follow_symlinks=False)
        except FileExistsError:
            return False
        _fsync_directory(path.parent)
        return True
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def save(result: dict[str, Any]) -> Path:
    """Save with atomic no-overwrite publication and serialized deduplication."""
    lock_fd = _results_lock()
    try:
        head, dirty = _git_state()
        commit = f"{head}+dirty" if dirty else head
        result["model_commit"] = commit
        verdict = result.get("verdict") or {}
        if dirty and verdict.get("kind") == "passed":
            raise ValueError(
                "cannot save verdict 'passed' from a dirty working tree; "
                "commit the source or record a non-passing/void outcome"
            )

        experiment_id = result.get("experiment_id")
        if (not isinstance(experiment_id, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", experiment_id)):
            raise ValueError("unsafe experiment_id")
        run_id = result.get("run_id")
        if (not isinstance(run_id, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id)):
            raise ValueError("unsafe run_id")

        d = RESULTS_DIR / experiment_id
        d.mkdir(parents=True, exist_ok=True)
        for old_path in sorted(d.glob("run-*.json"), reverse=True):
            # Never follow links out of the results tree.
            try:
                info = old_path.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                continue
            old = _load(old_path)
            if old is None or _fingerprint(old) != _fingerprint(result):
                continue
            if old.get("model_commit") == commit:
                return old_path
            seen = list(old.get("reproduced_at") or [])
            if commit in seen:
                return old_path
            old["reproduced_at"] = (seen + [commit])[-REPRODUCED_CAP:]
            _atomic_replace_json(old_path, old)
            return old_path

        for attempt in range(8):
            candidate = dict(result)
            if attempt:
                candidate["run_id"] = f"{run_id}-{uuid.uuid4().hex[:12]}"
                result["run_id"] = candidate["run_id"]
            path = d / f"{candidate['run_id']}.json"
            if _atomic_create_json(path, candidate):
                return path
        raise RuntimeError("could not allocate a unique result run_id")
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def load_all() -> list[dict[str, Any]]:
    """Loads every saved result, newest first."""
    if not RESULTS_DIR.exists():
        return []
    out = []
    for p in RESULTS_DIR.glob("*/*.json"):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    out.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return out
