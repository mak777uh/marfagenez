"""Единый формат результатов эксперимента.

## Зачем

Сейчас эксперименты печатают в консоль. Визуализировать нечего.

Этот модуль — контракт: каждый эксперимент сохраняет JSON, из которого
можно построить любое представление, не пересчитывая ничего из текста.

## Формат

    {
      "schema": "marfagenez.experiment-result.v1",
      "experiment_id": "observe-vs-act",
      "run_id": "run-2026-11-11T10-00-00",
      "model_commit": "abc1234",
      "seed": 20250101,
      "parameters": {...},
      "conditions": {
        "A": {"label": "...", "metrics": {...}},
        "B": {...}
      },
      "series": {
        "A": {"steps": [...], "values": [...]}
      },
      "limitations": [...],
      "command": "python3 checks/observe_vs_act.py"
    }

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

SCHEMA = "marfagenez.experiment-result.v1"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


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
        "conditions": {},
        "series": {},
        "limitations": [],
        "command": command,
        "created_at": now.isoformat(),
    }


def add_condition(
    result: dict[str, Any],
    key: str,
    label: str,
    metrics: dict[str, Any],
) -> None:
    """Adds one condition (A/B/C) with its metrics."""
    result["conditions"][key] = {"label": label, "metrics": metrics}


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
