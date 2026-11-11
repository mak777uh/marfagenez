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

## Четыре вердикта, не два (§4)

- `passed` — эффект есть, контроли прошли
- `failed` — эффекта нет
- `void` — манипуляция не связана с миром, контроль сломан, или плечи
  неразличимы (одинаковые хэши). **Ничего не узнали о механизме.**
- `insensitive by construction` — арифметика говорит, что плечи не могут
  различаться. **Ничего не узнали о механизме, но узнали о дизайне.**

## Правило

Визуализатор НЕ пересчитывает. Он читает.

Если чего-то нет в JSON — этого нет в визуализации.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "marfagenez.experiment-result.v2"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

#: The four outcomes. Not two (AGENTS.md §4).
VERDICTS = (
    "passed",
    "failed",
    "void",
    "insensitive by construction",
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


def save(result: dict[str, Any]) -> Path:
    """Writes the result to `results/<experiment_id>/<run_id>.json`."""
    d = RESULTS_DIR / result["experiment_id"]
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{result['run_id']}.json"
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
