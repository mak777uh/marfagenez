#!/usr/bin/env python3
"""Render an outcome-conditional EXP-2026-4106 finding from frozen artifacts."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

from we_analyze import (CELLS, SCHEMA, TASK_ID, ContractError, load_task_identity,
                        read_json, require_identity, sha256_file,
                        verify_summary_artifacts)


def load(path: Path) -> dict:
    return read_json(path)


def num(value, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "non-finite"
    if number == 0:
        return "0"
    return f"{number:.{digits}g}"


def interval(value) -> str:
    if value is None:
        return "n/a"
    return f"[{num(value[0])}, {num(value[1])}]"


def verdict_text(outcome: str) -> str:
    return {
        "passed": "Первичный и подтверждающий решения выполнены; evidence поддерживает зарегистрированные направления.",
        "failed": "Инструмент прошёл gates, но одно или несколько научных решений/подтверждений нарушены.",
        "void": "Результат недействителен для научного вывода: провалён instrument/provenance/identifiability gate.",
        "insensitive_by_construction": "Эксперимент не мог возмутить носитель износа; это не evidence ни за, ни против гипотезы.",
    }[outcome]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--lease-run", required=True, type=Path)
    parser.add_argument("--task-payload", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--submission-status", default="not_submitted")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit(f"refusing to overwrite {args.out}")
    root = args.results_dir.resolve()
    identity = load_task_identity(args.task_payload)
    summary = load(root / "analysis/summary.json")
    lease_run = load(args.lease_run)
    environment = load(root / "environment.json")
    require_identity(summary, identity, "analysis summary")
    require_identity(lease_run, identity, "lease-run")
    require_identity(environment, identity, "environment")
    if summary.get("schema") != SCHEMA:
        raise SystemExit("unexpected analysis schema")
    outcome = summary.get("scientific_outcome")
    if outcome not in {"passed", "failed", "void", "insensitive_by_construction"} or \
            summary.get("outcome") != outcome:
        raise SystemExit("unknown or inconsistent scientific outcome")
    errors = verify_summary_artifacts(summary, root / "analysis")
    for cohort, expected in summary.get("raw_sha256", {}).items():
        if expected is None:
            continue
        raw = root / cohort / "raw.csv"
        if not raw.is_file() or sha256_file(raw) != expected:
            errors.append(f"raw CSV hash mismatch: {cohort}")
    if environment.get("driver_sha256") != lease_run.get("driver_sha256"):
        errors.append("environment/lease driver hash mismatch")
    if environment.get("driver_source_sha256") != lease_run.get("driver_source_sha256"):
        errors.append("environment/lease driver source hash mismatch")
    if errors:
        raise SystemExit("artifact validation failed: " + "; ".join(errors))

    primary = summary.get("primary", {})
    deferred = summary.get("deferred", {})
    point = primary.get("mean_delta_t90", {})
    ci = primary.get("ci95_bootstrap", {})
    predictions = primary.get("predictions", {})
    controls = summary.get("controls", {})
    point_table = "\n".join(
        f"| {cell} | {num(point.get(cell))} | {interval(ci.get(cell))} |"
        for cell in CELLS)
    prediction_table = "\n".join(
        f"| {name} | {num(detail.get('estimate'))} | {interval(detail.get('ci95'))} |"
        f" {num(detail.get('p_directional'))} | {num(detail.get('p_holm'))} |"
        f" {'да' if detail.get('holds') is True else 'нет' if detail.get('holds') is False else 'n/a'} |"
        for name, detail in predictions.items()) or "| n/a | n/a | n/a | n/a | n/a | n/a |"
    control_table = "\n".join(
        f"| {name} | {'да' if holds else 'НЕТ'} |"
        for name, holds in controls.items()) or "| n/a | n/a |"
    deferred_point = deferred.get("mean_delta_t90", {})
    deferred_table = "\n".join(
        f"| {cell} | {num(deferred_point.get(cell))} |"
        for cell in CELLS)
    confirmation = deferred.get("confirmation_directions", {})
    confirmation_text = (", ".join(f"{name}={'да' if value else 'нет'}"
                                   for name, value in confirmation.items())
                         if confirmation else "не анализировались")
    landmarks = summary.get("P6", {}).get("landmarks", [])
    landmark_table = "\n".join(
        f"| {row['cohort']} | {row['dimension']} | {row['stratum']} | {row['scheduled_n']} |"
        f" {row['applied_n']} | {row['collapsed_among_applied_n']} |"
        f" {num(row['collapse_given_applied'])} | {num(row['unconditional_applied_fraction'])} |"
        for row in landmarks) or "| n/a | n/a | n/a | 0 | 0 | 0 | n/a | n/a |"
    distribution = summary.get("survival_distribution", [])
    distribution_table = "\n".join(
        f"| {row['cohort']} | {row['cell']} | {row['metric']} |"
        f" {num(row['level']) if row['level'] is not None else num(row['time'])} |"
        f" {num(row['value_A'])} | {num(row['value_B'])} | {num(row['difference_A_minus_B'])} |"
        for row in distribution) or "| n/a | n/a | n/a | n/a | n/a | n/a | n/a |"
    bootstrap = summary.get("bootstrap", {})
    grid = summary.get("grid", {})
    source_hash = environment.get("driver_source_sha256") or "not provided"
    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    text = f"""# FINDING-EXP-2026-4106. Стирание износа: фактический исход `{outcome}`

**Дата:** {date}. **Задача:** `{TASK_ID}` v{identity['task_version']}, task SHA256 `{identity['task_version_sha256']}`.
**Base commit:** `{identity['base_commit']}`. **Task payload SHA256:** `{identity['task_payload_sha256']}`.
**Вердикт анализатора:** `{outcome}`. **Submission status:** `{args.submission_status}`.
**Попытка:** `{lease_run.get('attempt_id')}`, lease `{lease_run.get('lease_id')}` epoch {lease_run.get('lease_epoch')},
runner_status `{lease_run.get('runner_status')}`, heartbeats {lease_run.get('heartbeat_count')} (fail: `{lease_run.get('heartbeat_failure')}`).
**Драйвер SHA256:** `{environment.get('driver_sha256')}`. **Driver source SHA256:** `{source_hash}`.
**raw SHA256:** primary `{summary.get('raw_sha256', {}).get('primary')}`, deferred `{summary.get('raw_sha256', {}).get('deferred')}`.
**Анализатор:** `{summary.get('analyzer_version')}`, schema `{summary.get('schema')}`, SHA256 `{summary.get('analyzer_sha256')}`.

## Итог по фактическим данным

{verdict_text(outcome)}

**Причина анализатора:** {summary.get('reason')}

**Primary decision, зафиксированный до deferred:** `{summary.get('primary_decision', {}).get('outcome')}`.
**Scope:** `{summary.get('decision_scope')}`. Deferred directions: {confirmation_text}.

## Сетка и оценка

KM T90 — первое время пересечения выживаемости 0.10; смерти перед цензурой при одинаковом времени.
Горизонт {grid.get('horizon')}; primary {grid.get('primary_seeds')} сидов с {grid.get('primary_seed_base')},
deferred {grid.get('deferred_seeds')} сидов с {grid.get('deferred_seed_base')}; {grid.get('pairs')} пар на (ячейка, сид).
Seed-cluster bootstrap {bootstrap.get('draws')} draws, primary seed `{bootstrap.get('primary_seed')}`,
deferred seed `{bootstrap.get('deferred_seed')}`. Сиды и пары ресэмплируются с заменой; одинаковые
`(seed,pair)` multiplicities используются во всех ячейках и обеих руках. Неидентифицированный T90
не заменяется горизонтом и даёт `void`.

| ячейка | mean ΔT90 primary | CI95 |
|---|---:|---|
{point_table}

## Научные решения primary

| решение | estimate | CI95 | directional p | Holm p | выполнено |
|---|---:|---:|---:|---:|---|
{prediction_table}

Holm family: P2 (erase600 − base) и P5 (base < 0), alpha 0.05. P3 требует erase221 − base > 0
и нижней границы направленного 95% CI > 0. P4 — instrument gate, а не secondary hypothesis.

## Instrument/provenance gates

| control | выполнен |
|---|---|
{control_table}

## Deferred: confirmation only

| ячейка | mean ΔT90 deferred |
|---|---:|
{deferred_table}

Deferred не смешивается с primary estimates/bootstrap. Его bootstrap/Holm значения описательны;
финальное подтверждение использует зафиксированные направления после проверки instrument gates.

## P6: descriptive landmark

`collapse_given_applied` считается отдельно по бинам `t_erase` и `survival_to_erase`.
Независимость безусловной доли не требуется и не тестируется. Точный collapse среди `erand/applied=1`
и условный collapse `erase600/lifeA>=600` — instrument gates.

| cohort | стратификация | bin | scheduled n | applied n | collapsed/applied n | collapse given applied | unconditional applied |
|---|---|---|---:|---:|---:|---:|---:|
{landmark_table}

## Полное survival distribution summary

Quantiles — средние per-seed KM quantiles; tail — mean per-seed KM survival.
`difference A−B < 0` означает более низкую выживаемость A.

| cohort | cell | metric | level/time | A | B | A−B |
|---|---|---|---:|---:|---:|---:|
{distribution_table}

## Ограничения

- Standalone wear-erase/R model; это не live-core результат и не closure.
- Вывод ограничен проверенной моделью, сидами, парами и зафиксированными драйвером/анализатором artifacts.
- ΔT90 — разность KM quantiles, не поточечная разность жизней и не подмена горизонта.
- P6 описывает collapse при применении; selection по выживаемости не объявляется независимостью.
- Deferred используется только для подтверждения после фиксации primary analyzer/decision.
- Нет выхода на другие дозы, параметры, экологию или эволюцию.

## Воспроизведение

```bash
bash we_run.sh /path/to/exp_wear_erase /new/results-directory \\
  --task-payload task.json --driver-source driver.rs
# Явный запуск (только с действительным lease):
bash we_run.sh /path/to/exp_wear_erase /new/results-directory \\
  --task-payload task.json --driver-source driver.rs --execute
python we_run_leased.py --driver /path/to/exp_wear_erase --out /new/results-directory \\
  --runner we_run.sh --task-payload task.json --driver-source driver.rs \\
  --claim claim.json --db /path/to/lab/state/control.db \\
  --cli /path/to/lab/cli/main.py --agent exper --execute
python we_analyze.py --primary-raw /new/results-directory/primary/raw.csv \\
  --primary-manifest /new/results-directory/primary/raw-manifest.json \\
  --deferred-raw /new/results-directory/deferred/raw.csv \\
  --deferred-manifest /new/results-directory/deferred/raw-manifest.json \\
  --task-payload task.json --out /new/results-directory/analysis
python we_make_finding.py --results-dir /new/results-directory \\
  --lease-run /new/results-directory/lease-run.json --task-payload task.json \\
  --out FINDING-EXP-2026-4106.md --submission-status not_submitted
```

Все SHA выше вычислены из сохранённых artifacts; никакие SHA/base не выдуманы генератором.
"""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"out": str(args.out), "outcome": outcome}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, ContractError) as exc:
        raise SystemExit(str(exc)) from exc
