#!/usr/bin/env python3
"""Render an outcome-faithful EXP-2026-4107 finding; never runs experiments."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

TASK_ID = "EXP-2026-4107"
OUTCOMES = {"passed", "failed", "void", "insensitive_by_construction"}
ARMS = (
    "A-control", "B1-sham", "B2-ko1", "B3-ko2", "rescue",
    "A-B2-cost", "A-B3-cost", "A-rescue-cost", "D-half", "D-third",
    "ghost", "placebo-k1",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def num(value, digits: int = 8) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "NaN"
    if number == 0:
        return "0"
    return f"{number:.{digits}g}"


def metric(primary: dict, field: str, arm: str) -> str:
    return num(primary.get(field, {}).get(arm))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--lease-run", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--submission-status", default="not_submitted")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit(f"refusing to overwrite {args.out}")

    root = args.results_dir.resolve()
    summary = load(root / "analysis" / "summary.json")
    lease_run = load(args.lease_run)
    environment = load(root / "environment.json")
    manifest_path = root / "raw-manifest.json"
    manifest = load(manifest_path) if manifest_path.is_file() else {}
    outcome = summary.get("scientific_outcome")
    if outcome not in OUTCOMES:
        raise SystemExit(f"unknown scientific_outcome: {outcome!r}")
    if summary.get("task_id") != TASK_ID or lease_run.get("task") != TASK_ID:
        raise SystemExit("task mismatch in summary/lease-run")
    identity = {
        "task_version": summary.get("task_version"),
        "task_version_sha256": summary.get("task_version_sha256"),
        "base_commit": summary.get("base_commit"),
    }
    for source, label in ((lease_run, "lease-run"), (manifest, "manifest")):
        for key, value in identity.items():
            if source.get(key) not in (None, value):
                raise SystemExit(f"{label} {key} mismatch")

    reason = summary.get("reason", "")
    primary = summary.get("primary", {})
    predictions = summary.get("predictions", {})
    controls = summary.get("controls", {})
    failed_controls = [key for key, value in controls.items() if not value]
    failed_predictions = [key for key, value in predictions.items() if not value]
    preds_table = "\n".join(
        f"| `{key}` | {'выполнено' if bool(value) else 'НАРУШЕНО'} |"
        for key, value in predictions.items()
    ) or "| — | не оценивались |"
    controls_table = "\n".join(
        f"| `{key}` | {'да' if bool(value) else 'НЕТ'} |"
        for key, value in controls.items()
    ) or "| — | не оценивались |"
    arms_table = "\n".join(
        f"| `{arm}` | {metric(primary, 'aurd', arm)} | {metric(primary, 'aurd_abs', arm)} | {metric(primary, 'f_final', arm)} |"
        for arm in ARMS
    )

    titles = {
        "passed": "Детерминированный B pilot: все предрегистрированные проверки выполнены",
        "failed": "Детерминированный B pilot: научное предсказание нарушено при валидных контролях",
        "void": "Детерминированный B pilot: результат неидентифицируем из-за нарушения контроля",
        "insensitive_by_construction": "Детерминированный B pilot: insensitive_by_construction",
    }
    interpretations = {
        "passed": (
            "Все научные предсказания и все инструментальные контроли выполнены. Два запуска "
            "побайтово идентичны, поэтому заявлена только точная воспроизводимость механики "
            "k-out-of-m в этом детерминированном unit-test."
        ),
        "failed": (
            "Контроли валидны, но нарушены научные предсказания: "
            + (", ".join(f"`{key}`" for key in failed_predictions) or "см. таблицу")
            + ". Это failed, а не void: реализацию следует исправить, критерии — не подгонять."
        ),
        "void": (
            "Научный результат не заявляется. Не прошли контроли: "
            + (", ".join(f"`{key}`" for key in failed_controls) or "см. таблицу")
            + ". Смерть зарегистрированного рукава, NaN в обязательной метрике, неидентичный повтор, "
            "сломанный ghost/placebo/schedule/ledger или ошибка драйвера делают вывод неидентифицируемым."
        ),
        "insensitive_by_construction": (
            "Драйвер завершился кодом 3: зарегистрированные условия чувствительности не выполнены. "
            "Это insensitive_by_construction; ни passed, ни failed здесь не присваиваются."
        ),
    }
    next_steps = {
        "passed": "Следующий этап — отдельный стохастический B pilot; этот finding не является его результатом.",
        "failed": "Следующий шаг — исправление реализации и новый независимый запуск без изменения критериев.",
        "void": "Следующий шаг — восстановление инструмента/контроля и новый запуск; интерпретация механики отложена.",
        "insensitive_by_construction": "Следующий шаг — новая предрегистрация с различимыми параметрами, а не переинтерпретация этого запуска.",
    }

    text = f"""# FINDING-EXP-2026-4107. {titles[outcome]}

**Дата:** {dt.date.today().isoformat()}. **Задача:** `{TASK_ID}` v{summary.get('task_version')}, task SHA256 `{summary.get('task_version_sha256')}`.
**Base commit:** `{summary.get('base_commit')}`.
**Вердикт анализатора:** `{outcome}`. **Submission status:** `{args.submission_status}`.
**Попытка:** `{lease_run.get('attempt_id')}`, lease `{lease_run.get('lease_id')}` epoch {lease_run.get('lease_epoch')},
runner_status `{lease_run.get('runner_status')}`, heartbeats {lease_run.get('heartbeat_count')} (fail: `{lease_run.get('heartbeat_failure')}`).
**Драйвер SHA256:** `{environment.get('driver_sha256')}`. **Исходник драйвера SHA256:** `{environment.get('driver_source_sha256')}`.
**raw.csv SHA256:** `{summary.get('raw_sha256')}`. **steps.csv SHA256:** `{summary.get('steps_sha256')}`.
**Повтор run1/run2:** `{(summary.get('repeat') or {}).get('byte_identical')}`.
**Анализатор:** `{summary.get('analyzer_version')}`, schema `{summary.get('schema')}`.

## Интерпретация исхода

{interpretations[outcome]}

{next_steps[outcome]}

## Предрегистрированные научные предсказания

| Предсказание | Статус |
|---|---|
{preds_table}

## Инструментальные контроли

| Контроль | Статус |
|---|---|
{controls_table}

## Числа (aurd / aurd_abs / f_final)

| Рукав | aurd | aurd_abs | f_final |
|---|---|---|---|
{arms_table}

Запас rescue над B2: `{num(primary.get('rescue_margin_over_b2'))}`; запас B3 над rescue: `{num(primary.get('b3_margin_over_rescue'))}` (порог 1e-6).
Расписание: t*=5, t**=10, t***=15; m=3, k=2, R0=0.1, r0=0.05, D0=0.5, T=40.

## Причина вердикта (анализатор)

{reason}

## Границы заявления

- Это детерминированный unit-test, а не статистический научный результат.
- Вероятностные отказы и replacement-поток здесь не тестируются.
- Fixed-capacity cost-yoked A-рукава отделяют Capacity от стоимости; ghost и placebo проверяют артефакты учёта и порога.
- Исход `{outcome}` не заменяет отдельную предрегистрацию стохастического B pilot.

## Воспроизведение

1. Собрать проверенный `exp_b_unit` из закреплённого `base_commit` и сохранить SHA256 бинарника и `driver.rs`.
2. Выполнить `bash b_run.sh /path/to/exp_b_unit /new/results-directory task.json /path/to/exp_b_unit.rs`; runner обязан выполнить два побайтово идентичных запуска.
3. Выполнить `python b_analyze.py --raw /new/results-directory/raw.csv --steps /new/results-directory/steps.csv --manifest /new/results-directory/raw-manifest.json --out /new/results-directory/analysis`.
4. Проверить `summary.json`, `raw-manifest.json`, `run1/`, `run2/`, `environment.json` и `toolchain.json`, затем выполнить `python -m unittest discover -s tests -v`.
"""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(json.dumps({"out": str(args.out), "outcome": outcome}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
