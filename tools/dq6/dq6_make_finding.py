#!/usr/bin/env python3
"""Render the D-Q6 finding from frozen outputs; never run experiments."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from typing import Any

TASK_ID = "EXP-2026-4103"
SEEDS = list(range(4301, 4313))
STEPS = (100_000, 200_000, 400_000, 800_000)
TARGETS = {"alpha_D": 0.5, "alpha_deriv": 1.5, "alpha_Tlife": 0.5}
OUTCOME_MAP = {
    "passed": "passed",
    "failed": "failed",
    "void": "void",
    "horizon_limited": "failed",
    "yoked_reproduces_pole": "failed",
    "endpoint_failure": "failed",
    "specificity_not_confirmed": "failed",
}
RAW_COUNTS = {"death-reset": 1200, "cap": 48, "sham": 96}
HISTOGRAM_COUNTS = {"death-reset": 300, "cap": 12, "sham": 24}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt(value: Any, digits: int = 7) -> str:
    if value is None or value == "":
        return "n/a"
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, int):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value).replace("|", "\\|")
    if not math.isfinite(number):
        return str(value)
    if number == 0:
        return "0"
    return f"{number:.{digits}g}"


def classification_text(classification: str) -> str:
    return {
        "passed": "Все три endpoint CI прошли целевой коридор, instrument gates выполнены, а exact yoked sham не воспроизвёл полюс. Это подтверждение численного предсказания в standalone driver.",
        "void": "Instrument gate fires и/или silent провален. Научная классификация endpoint не используется как evidence; это корректный инструментальный исход, а не passed/failed гипотезы.",
        "horizon_limited": "Сходится меньше четырёх h_fit. Асимптотический наклон не оценивается по установленному правилу; это полноценный отрицательный результат, а не повод расширять горизонт после просмотра данных.",
        "yoked_reproduces_pole": "Yoked sham воспроизвёл death-reset Dbar в пределах 15% на требуемых горизонтах. Специфика death-канала не подтверждена; это полноценный отрицательный научный результат.",
        "endpoint_failure": "Один или несколько endpoint CI не прошли целевой коридор либо сработало предпрогонное правило систематического изменения alpha_D с горизонтом. Предсказание не подтверждено.",
        "specificity_not_confirmed": "Endpoint CI прошли, но exact yoking или non-reproduction comparison не поддержаны. Это не passed: специфичность осталась неподтверждённой.",
    }[classification]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--submission-status", default="not_submitted")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit(f"refusing to overwrite {args.out}")
    if args.submission_status not in {"not_submitted", "received", "duplicate"}:
        raise SystemExit("unsupported submission status")

    root = args.results_dir.resolve()
    analysis = root / "analysis"
    raw = root / "raw"
    required = [
        analysis / "summary.json", analysis / "seed_metrics.csv", analysis / "fits.csv",
        analysis / "bootstrap.csv", analysis / "controls.json",
        analysis / "analyzer.stdout.txt", analysis / "analyzer.stderr.txt",
        root / "run-manifest.json", root / "lease-run.json", root / "claim.json",
        root / "environment.json", root / "environment.txt", root / "toolchain.json",
        root / "design-pre-run.md", root / "run.stdout.log", root / "run.stderr.log",
        root / "heartbeat.log", root / "driver-source.rs", root / "dq6_analyze.py",
        root / "dq6_run.sh", root / "dq6_run_leased.py", args.task, args.design,
    ]
    for control in RAW_COUNTS:
        required.extend([
            raw / f"{control}.csv", raw / f"{control}-histogram.csv",
            raw / f"{control}.stderr.txt",
        ])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"missing finding inputs: {missing}")
    if args.design.read_bytes() != (root / "design-pre-run.md").read_bytes():
        raise SystemExit("design differs from frozen design-pre-run.md")

    summary = load(analysis / "summary.json")
    task_doc = load(args.task)
    task = task_doc.get("task", task_doc.get("payload", task_doc))
    claim_doc = load(root / "claim.json")
    claim = claim_doc.get("claimed", {})
    manifest = load(root / "run-manifest.json")
    lease = load(root / "lease-run.json")
    environment = load(root / "environment.json")
    if task.get("schema") != "task/v1" or task.get("id") != TASK_ID or int(task.get("version", -1)) < 3:
        raise SystemExit("D-Q6 task version >=3 is required")
    version = int(task["version"])
    version_hash = claim.get("task_version_sha256")
    if not isinstance(version_hash, str) or len(version_hash) != 64:
        raise SystemExit("claim task hash is absent")
    if claim.get("task_id") != TASK_ID or int(claim.get("version", -1)) != version:
        raise SystemExit("claim/task mismatch")
    canonical_task = json.dumps(task, sort_keys=True, separators=(",", ":")).encode("utf-8")
    computed_version_hash = task_doc.get("task_version_sha256") or hashlib.sha256(canonical_task).hexdigest()
    if version_hash != computed_version_hash:
        raise SystemExit("claim task hash does not match the frozen task document")
    if summary.get("task") != TASK_ID or summary.get("synthetic_data") is not False:
        raise SystemExit("summary is not non-synthetic D-Q6 evidence")
    if summary.get("analysis_version") != "dq6-analysis-1.0.1":
        raise SystemExit("unexpected analyzer version")
    configuration = summary.get("configuration", {})
    if configuration.get("N") != 100 or configuration.get("steps") != 800_000:
        raise SystemExit("N/steps mismatch")
    if configuration.get("seeds") != SEEDS or configuration.get("sample_steps") != list(STEPS):
        raise SystemExit("seed/horizon registry mismatch")
    if configuration.get("no_unseeded_random") is not True:
        raise SystemExit("no_unseeded_random is not true")

    for record, name in ((manifest, "manifest"), (lease, "lease"), (environment, "environment")):
        if record.get("task") != TASK_ID:
            raise SystemExit(f"{name} task mismatch")
        if name == "manifest":
            record_version = record.get("task_version")
        else:
            record_version = record.get("version")
        if int(record_version) != version:
            raise SystemExit(f"{name} version mismatch")
        if name != "environment" and record.get("task_version_sha256") != version_hash:
            raise SystemExit(f"{name} task hash mismatch")
        if record.get("base_commit") != task["base_commit"]:
            raise SystemExit(f"{name} base commit mismatch")
    if environment.get("task_version_sha256") != version_hash:
        raise SystemExit("environment task hash mismatch")
    if lease.get("runner_status") != 0 or lease.get("heartbeat_failure") is not None:
        raise SystemExit("lease runner did not finish successfully")
    if environment.get("network_used") is not False or environment.get("no_unseeded_random") is not True:
        raise SystemExit("environment network/randomness declaration mismatch")
    if environment.get("histogram_detail") != "global-only":
        raise SystemExit("production histogram scope mismatch")
    if manifest.get("toolchain_file", {}).get("sha256") != sha256(root / "toolchain.json"):
        raise SystemExit("toolchain hash mismatch")
    provenance = environment.get("provenance", {})
    for key, path in (
        ("source", root / "driver-source.rs"), ("analyzer", root / "dq6_analyze.py"),
        ("runner", root / "dq6_run.sh"), ("leased_runner", root / "dq6_run_leased.py"),
        ("task_file", args.task), ("run_manifest", root / "run-manifest.json"),
        ("lease_run", root / "lease-run.json"),
    ):
        if provenance.get(key, {}).get("sha256") != sha256(path):
            raise SystemExit(f"environment provenance mismatch: {key}")
    if provenance.get("source", {}).get("sha256") != manifest.get("driver_source", {}).get("sha256"):
        raise SystemExit("manifest/environment driver-source mismatch")

    input_hashes = summary.get("input_hashes", {})
    raw_info: dict[str, dict[str, Any]] = {}
    for control, expected_rows in RAW_COUNTS.items():
        summary_path = raw / f"{control}.csv"
        histogram_path = raw / f"{control}-histogram.csv"
        rows = read_csv(summary_path)
        if len(rows) != expected_rows or {int(row["seed"]) for row in rows} != set(SEEDS):
            raise SystemExit(f"{control}: raw summary registry mismatch")
        histogram_rows = read_csv(histogram_path)
        summaries = [row for row in histogram_rows if row["record_type"] == "summary"]
        if len(summaries) != HISTOGRAM_COUNTS[control]:
            raise SystemExit(f"{control}: histogram summary registry mismatch")
        if any(row["scope"] != "global-only" for row in summaries):
            raise SystemExit(f"{control}: histogram is not explicitly global-only")
        if any(row["record_type"] == "interval" and row["scope"] != "global" for row in histogram_rows):
            raise SystemExit(f"{control}: organism interval bins present in production output")
        for key, path in (("summary", summary_path), ("histogram", histogram_path)):
            hash_key = f"{control.replace('-', '_')}_{key}"
            if input_hashes.get(hash_key, {}).get("sha256") != sha256(path):
                raise SystemExit(f"{control}: summary/raw hash mismatch for {key}")
            raw_info[f"{control}/{key}"] = {"bytes": path.stat().st_size, "sha256": sha256(path)}

    seed_rows = read_csv(analysis / "seed_metrics.csv")
    if len(seed_rows) != 336 or {int(row["seed"]) for row in seed_rows} != set(SEEDS):
        raise SystemExit("seed_metrics registry mismatch")
    fit_rows = [row for row in read_csv(analysis / "fits.csv") if row["record_type"] == "fit"]
    fit_index = {row["key"]: row for row in fit_rows}
    if len(fit_index) != len(fit_rows) or not set(TARGETS).issubset(fit_index):
        raise SystemExit("fit registry mismatch")
    for endpoint, target in TARGETS.items():
        row = fit_index[endpoint]
        if float(row["target"]) != target or row["bootstrap_replicates"] != "10000":
            raise SystemExit(f"{endpoint}: target/bootstrap mismatch")
        if row["status"] == "ok" and row["valid_bootstrap_replicates"] != "10000":
            raise SystemExit(f"{endpoint}: incomplete bootstrap")
    bootstrap_rows = read_csv(analysis / "bootstrap.csv")
    if len(bootstrap_rows) != 10_000 or {row["bootstrap_seed"] for row in bootstrap_rows} != {"20261103"}:
        raise SystemExit("bootstrap registry mismatch")

    classification = summary.get("reported_scientific_classification")
    outcome = summary.get("scientific_outcome")
    if classification not in OUTCOME_MAP or outcome not in OUTCOME_MAP:
        raise SystemExit("unknown scientific classification/outcome")
    submission_outcome = OUTCOME_MAP[outcome]
    controls = summary.get("controls", {})
    if outcome != "void" and not all(controls.get(key) is True for key in ("fires", "silent")):
        raise SystemExit("non-void finding has failed instrument controls")
    endpoints = summary.get("endpoints", {})
    convergence = summary.get("convergence", {})
    horizon = summary.get("horizon_alpha_D", {})
    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    status_text = "ready_for_submission" if args.submission_status == "not_submitted" else args.submission_status
    lines = [
        f"# FINDING-{TASK_ID}. Численная проверка полюса death-reset",
        "",
        f"**Дата:** {date}. **Задача:** `{TASK_ID}` v{version}. **Научная классификация анализатора:** `{classification}`.",
        f"**Submission outcome:** `{submission_outcome}`. **Operational status:** `{status_text}`.",
        f"**Task version SHA256:** `{version_hash}`. **Base commit:** `{task['base_commit']}`.",
        f"**Analyzer:** `{summary['analysis_version']}`. **Driver source SHA256:** `{manifest['driver_source']['sha256']}`.",
        "",
        "## Зачем и что это даёт для слона",
        "",
        "Проверено аналитическое предсказание standalone death-reset механизма: при `h→1` плато "
        "`D* ~ x^(-1/2)`, его производная `|dD*/dh| ~ x^(-3/2)`, а средний интервал death-reset "
        "`T_life ~ x^(1/2)` стремится к нулю. Для слона это проверка численного контракта смертного "
        "канала и его специфичности, а не новый биологический закон, не перевод к Chao и не изменение live core.",
        "",
        "## Предсказание и правило до прогона",
        "",
        "Цели: `alpha_D=0.5`, `alpha_deriv=1.5`, `alpha_Tlife=0.5`; каждый 95% seed-bootstrap CI "
        "должен пересекать цель с допуском `0.15`. `h=1` должен расти без cap и выходить на плато с cap. "
        "Yoked sham не должен воспроизводить полюс, а удалённый диапазон `h={0.9,0.95,0.98,0.99}` — "
        "не воспроизводить все три асимптотических показателя. Сходимость: `|D800-D400|/D800 <= 0.01` "
        "минимум у 10/12 seeds; для fit требуется минимум четыре сходимых `h_fit`. Гипотеза, сетка, "
        "seeds и gates не менялись после просмотра данных.",
        "",
        "## Результат",
        "",
        f"`{classification}`: {classification_text(classification)}",
        "",
        f"Причина анализатора: {summary.get('reason')}.",
        "",
        "| endpoint | target | оценка | 95% CI | status | passes |",
        "|---|---:|---:|---|---|---|",
    ]
    for endpoint, target in TARGETS.items():
        item = endpoints.get(endpoint, {})
        ci = "n/a" if item.get("ci_low") is None else f"[{fmt(item.get('ci_low'))}, {fmt(item.get('ci_high'))}]"
        lines.append(
            f"| {endpoint} | {fmt(target)} | {fmt(item.get('point_estimate'))} | {ci} | "
            f"{item.get('status')} | {fmt(item.get('passes'))} |"
        )
    lines.extend([
        "",
        "## Сходимость и горизонт",
        "",
        f"Сходимых `h_fit`: {fmt(convergence.get('converged_fit_point_count'))}; "
        f"значения: `{convergence.get('converged_fit_h')}`.",
        f"Правило систематического сдвига `alpha_D`: estimable={fmt(horizon.get('estimable'))}, "
        f"systematic={fmt(horizon.get('systematic_shift'))}, последовательные изменения={fmt(horizon.get('successive_changes'))}.",
        "",
        "| горизонт | alpha_D | alpha_deriv |",
        "|---:|---:|---:|",
    ])
    for item in summary.get("horizon_dependence", {}).get("horizons", []):
        lines.append(
            f"| {item.get('sample_step')} | {fmt(item.get('alpha_D', {}).get('point_estimate'))} | "
            f"{fmt(item.get('alpha_deriv', {}).get('point_estimate'))} |"
        )
    lines.extend([
        "",
        "## Контроли",
        "",
        "| контроль | passed | роль |",
        "|---|---|---|",
        f"| fires | {fmt(controls.get('fires'))} | instrument gate: рост без cap и плато с cap |",
        f"| silent | {fmt(controls.get('silent'))} | instrument gate: удалённый диапазон не воспроизводит все цели |",
        f"| specific | {fmt(controls.get('specific'))} | научный контроль специфичности |",
        f"| sham_schedule_exact | {fmt(controls.get('sham_schedule_exact'))} | точность yoked schedule, включая корректные zero-event случаи |",
        "",
        "### Yoked comparison по h",
        "",
        "| h | schedule exact | median rel. diff 400k | median rel. diff 800k | воспроизводит полюс |",
        "|---:|---|---:|---:|---|",
    ])
    for item in summary.get("control_summary", {}).get("specific_per_h", []):
        lines.append(
            f"| {fmt(item.get('h'))} | {fmt(item.get('schedule_exact'))} | "
            f"{fmt(item.get('median_relative_Dbar_difference_400000'))} | "
            f"{fmt(item.get('median_relative_Dbar_difference_800000'))} | "
            f"{fmt(item.get('yoked_reproduces_pole'))} |"
        )
    lines.extend([
        "",
        "## Прогон и provenance",
        "",
        f"- Attempt: `{lease.get('attempt_id')}`; lease `{lease.get('lease_id')}` epoch `{lease.get('lease_epoch')}`.",
        f"- Старт: `{lease.get('started_utc')}`; завершение runner: `{lease.get('ended_utc')}`; heartbeat failure: `{lease.get('heartbeat_failure')}`.",
        f"- Seeds: `{SEEDS[0]}..{SEEDS[-1]}`; `N=100`; шагов `800000`; замеры `{list(STEPS)}`.",
        "- Production histogram: `global-only`; organism bins запрещены; network не использовался; unseeded randomness отсутствует.",
        f"- Bootstrap: 10000 seed-репликаций, seed `20261103`; строк `seed_metrics.csv`: {len(seed_rows)}.",
        "",
        "| артефакт | bytes | SHA256 |",
        "|---|---:|---|",
    ])
    for name, info in raw_info.items():
        lines.append(f"| {name} | {info['bytes']} | `{info['sha256']}` |")
    for label, path in (
        ("driver binary", root / "exp_dq6"), ("driver source", root / "driver-source.rs"),
        ("analyzer", root / "dq6_analyze.py"), ("runner", root / "dq6_run.sh"),
        ("lease wrapper", root / "dq6_run_leased.py"), ("task", args.task),
        ("run manifest", root / "run-manifest.json"), ("environment", root / "environment.json"),
        ("toolchain", root / "toolchain.json"),
    ):
        if path.is_file():
            lines.append(f"| {label} | {path.stat().st_size} | `{sha256(path)}` |")
    lines.extend([
        "",
        "## Ограничения",
        "",
    ])
    lines.extend(f"- {item}" for item in summary.get("limitations", []))
    lines.extend([
        "- Результат условен относительно закреплённого main-owned driver, task version, exact raw CSV и analysis code.",
        "- `received` терминален для агента; переход `received → integrated` выполняет main.",
        "",
        "## Статус сдачи",
        "",
        f"`{status_text}`. Авторитетный статус после отправки хранится в `submission-response.json`; "
        "этот FINDING не перезаписывается после sealing bundle.",
        "",
    ])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({
        "out": str(args.out), "sha256": sha256(args.out), "task_version": version,
        "analysis_classification": classification, "scientific_outcome": outcome,
        "submission_outcome": submission_outcome, "operational_status": status_text,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
