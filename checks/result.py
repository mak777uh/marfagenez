"""Единый формат результатов эксперимента.

## Зачем

Сейчас эксперименты печатают в консоль. Визуализировать нечего.

Этот модуль — контракт: каждый эксперимент сохраняет JSON, из которого
можно построить любое представление, не пересчитывая ничего из текста.

## Формат

    {
      "schema": "marfagenez.experiment-result.v2",
      "experiment_id": "frozen-ceiling",
      "run_id": "run-2026-11-11T10-00-00",
      "model_commit": "abc1234",
      "seed": 20250101,
      "parameters": {...},

      "arithmetic": {...},        // §1: арифметика ДО прогона
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
      "verdict": {                // §4: четыре исхода
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

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "marfagenez.experiment-result.v2"
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


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=Path(__file__).resolve().parents[1],
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def new_result(
    experiment_id: str,
    seed: int,
    parameters: dict[str, Any],
    command: str,
) -> dict[str, Any]:
    """Creates an empty result with the required metadata."""
    now = datetime.now(timezone.utc)
    return {
        "schema": SCHEMA,
        "experiment_id": experiment_id,
        "run_id": f"run-{now.strftime('%Y-%m-%dT%H-%M-%S')}",
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


def set_arithmetic(result: dict[str, Any], arithmetic: dict[str, Any]) -> None:
    """Records the pre-registration arithmetic (AGENTS.md §1).

    The arithmetic must be written **before** the run. It says what makes the
    difference: income, cost, ratio, break-even. If the whole field is above the
    threshold in both arms, the experiment is insensitive by construction.

    The arithmetic is not a guarantee. E1's arithmetic modelled two of three terms
    and predicted dissolution where every arm survived.
    """
    result["arithmetic"] = arithmetic


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
    """Sets the verdict. Four outcomes, not two (AGENTS.md §4)."""
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
    return json.dumps(body, sort_keys=True, ensure_ascii=False)


def _load(path: Path) -> dict[str, Any] | None:
    """The record in `path`, or `None` if it cannot be read as JSON."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save(result: dict[str, Any]) -> Path:
    """Writes the result to `results/<experiment_id>/<run_id>.json`.

    A re-run that reproduces an existing record **byte for byte** (apart from
    `run_id`, `created_at`, `model_commit` and `reproduced_at`) does not get a
    file of its own:

    * the same `model_commit` -- nothing to record, the file is not touched;
    * a different `model_commit` -- the current commit is appended to the
      record's `reproduced_at` list (no duplicates, in order of appearance) and
      the record is rewritten. `model_commit` stays as it was: it names the
      commit where the numbers were **first** obtained, not the last one that
      saw them again.

    This is not deduplication for tidiness. `frozen-ceiling` had 122 records on
    disk and 122 in git, most of them the same measurement written again by
    successive gate runs, so `git status` was never clean after `run.sh all` and
    a real new record was invisible among the copies. Keeping a list of commits
    inside one record is better than a file per commit: the files are identical,
    and only the list differs -- a copy turns one measurement into N measurements
    that have to be compared to see they are the same, while `reproduced_at`
    says "the same numbers, re-checked at these commits" in the place where the
    numbers already are. A re-run that changes anything else in the body is a
    new measurement and does get a new file.

    When several committed records hold the same measurement, the **newest** one
    gets the commit, so the chain of rechecks does not attach to an old copy.
    """
    d = RESULTS_DIR / result["experiment_id"]
    d.mkdir(parents=True, exist_ok=True)
    commit = result.get("model_commit")
    name = f"{result['run_id']}.json"
    for old_path in sorted(d.glob("run-*.json"), reverse=True):
        if old_path.name == name:
            continue
        old = _load(old_path)
        if old is None or _fingerprint(old) != _fingerprint(result):
            continue
        if old.get("model_commit") == commit:
            return old_path
        seen = list(old.get("reproduced_at") or [])
        if commit in seen:
            return old_path
        old["reproduced_at"] = seen + [commit]
        old_path.write_text(
            json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return old_path
    path = d / name
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


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
