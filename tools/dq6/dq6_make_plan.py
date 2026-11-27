#!/usr/bin/env python3
"""Build the D-Q6 submission plan from verified artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TASK_ID = "EXP-2026-4103"
DEFAULT_MESSAGES = [
    "MSG-CUTOVER-1",
    "MSG-MAIN-EXPERIMENTS-REVIEWS-20261127-07",
    "MSG-MAIN-EXPERIMENTS-DRIVER-DQ6-20261127-12",
    "MSG-MAIN-EXPERIMENTS-TASKIDS-20261127-11",
    "MSG-MAIN-EXPERIMENTS-DQ5-CONTRACT-20261127-15",
    "MSG-MAIN-EXPERIMENTS-DQ6-CONTRACT-20261127-16",
    "MSG-MAIN-EXPERIMENTS-HARDWARE-20261127-18",
]
ARTIFACTS = [
    ("design.md", "text/markdown"),
    ("design-pre-run.md", "text/markdown"),
    ("driver-source.rs", "text/rust"),
    ("task.json", "application/json"),
    ("dq6_analyze.py", "text/x-python"),
    ("dq6_run.sh", "text/x-shellscript"),
    ("dq6_run_leased.py", "text/x-python"),
    ("dq6_record_environment.py", "text/x-python"),
    ("dq6_make_finding.py", "text/x-python"),
    ("dq6_make_plan.py", "text/x-python"),
    ("dq6_submit.py", "text/x-python"),
    ("dq6-analysis-dev-check.txt", "text/plain"),
    ("code/dq6_analyze.py", "text/x-python"),
    ("code/dq6_run.sh", "text/x-shellscript"),
    ("code/dq6_run_leased.py", "text/x-python"),
    ("code/dq6_record_environment.py", "text/x-python"),
    ("code/dq6_make_finding.py", "text/x-python"),
    ("code/dq6_make_plan.py", "text/x-python"),
    ("code/dq6_submit.py", "text/x-python"),
    ("code/exp_dq6_controls_candidate.rs", "text/rust"),
    ("claim.json", "application/json"),
    ("heartbeat.log", "text/plain"),
    ("lease-run.json", "application/json"),
    ("run.stdout.log", "text/plain"),
    ("run.stderr.log", "text/plain"),
    ("confirmatory-exit-code.txt", "text/plain"),
    ("pre-run-manifest.json", "application/json"),
    ("preflight-smoke.json", "application/json"),
    ("driver-provenance.json", "application/json"),
    ("run-manifest.json", "application/json"),
    ("environment.txt", "text/plain"),
    ("environment.json", "application/json"),
    ("toolchain.json", "application/json"),
    ("raw/death-reset.csv", "text/csv"),
    ("raw/cap.csv", "text/csv"),
    ("raw/sham.csv", "text/csv"),
    ("raw/death-reset-histogram.csv", "text/csv"),
    ("raw/cap-histogram.csv", "text/csv"),
    ("raw/sham-histogram.csv", "text/csv"),
    ("raw/death-reset.stderr.txt", "text/plain"),
    ("raw/cap.stderr.txt", "text/plain"),
    ("raw/sham.stderr.txt", "text/plain"),
    ("analysis/seed_metrics.csv", "text/csv"),
    ("analysis/fits.csv", "text/csv"),
    ("analysis/bootstrap.csv", "text/csv"),
    ("analysis/controls.json", "application/json"),
    ("analysis/summary.json", "application/json"),
    ("analysis/analyzer.stdout.txt", "text/plain"),
    ("analysis/analyzer.stderr.txt", "text/plain"),
    ("FINDING-EXP-2026-4103.md", "text/markdown"),
]
OUTCOME_MAP = {
    "passed": "passed",
    "failed": "failed",
    "void": "void",
    "not_applicable": "not_applicable",
    "horizon_limited": "failed",
    "yoked_reproduces_pole": "failed",
    "endpoint_failure": "failed",
    "specificity_not_confirmed": "failed",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--toolchain", required=True, type=Path)
    parser.add_argument("--submission-id", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--proposal-id", default="PROP-EXPER-DQ6-CONTROLS-V3-20261127-02")
    parser.add_argument("--complied-message", action="append", default=[])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    root = args.artifacts_dir.resolve()
    task_doc = load(args.task)
    task = task_doc.get("task", task_doc.get("payload", task_doc))
    claim_doc = load(args.claim)
    claim = claim_doc.get("claimed", {})
    summary = load(args.summary)
    if task.get("schema") != "task/v1" or task.get("id") != TASK_ID or int(task.get("version", -1)) < 3:
        raise SystemExit("D-Q6 task version >=3 is required")
    if claim.get("task_id") != TASK_ID or int(claim.get("version", -1)) != int(task["version"]):
        raise SystemExit("claim/task mismatch")
    if claim.get("task_version_sha256") != task_doc.get("task_version_sha256", claim.get("task_version_sha256")):
        raise SystemExit("claim/task hash mismatch")
    if summary.get("task") != TASK_ID:
        raise SystemExit("summary task mismatch")
    classification = summary.get("reported_scientific_classification")
    outcome = summary.get("scientific_outcome")
    if classification not in OUTCOME_MAP or outcome not in OUTCOME_MAP:
        raise SystemExit("unexpected scientific classification/outcome")
    submission_outcome = OUTCOME_MAP[outcome]
    if (root / "design.md").read_bytes() != (root / "design-pre-run.md").read_bytes():
        raise SystemExit("design.md differs from frozen design-pre-run.md")
    missing = [rel for rel, _ in ARTIFACTS if not (root / rel).is_file()]
    if missing:
        raise SystemExit(f"missing required artifacts: {missing}")
    total_bytes = sum((root / rel).stat().st_size for rel, _ in ARTIFACTS)
    disk_budget = int(task["budget"]["disk_bytes"])
    if total_bytes > disk_budget:
        raise SystemExit(f"artifact bytes exceed task budget: {total_bytes} > {disk_budget}")

    controls = summary.get("controls", {})
    control_text = "; ".join(
        f"{key}={controls.get(key)}" for key in ("fires", "silent", "specific", "sham_schedule_exact")
    )
    endpoints = summary.get("endpoints", {})
    endpoint_text = "; ".join(
        f"{name}: point={endpoints.get(name, {}).get('point_estimate')}, "
        f"CI95={endpoints.get(name, {}).get('ci95')}, passes={endpoints.get(name, {}).get('passes')}"
        for name in ("alpha_D", "alpha_deriv", "alpha_Tlife")
    )
    convergence = summary.get("convergence", {})
    summary_text = (
        f"D-Q6 analysis classification={classification}; submission outcome={submission_outcome}. "
        f"Reason: {summary.get('reason')}. Endpoints: {endpoint_text}. "
        f"Converged fit points={convergence.get('converged_fit_point_count')}; "
        f"converged h={convergence.get('converged_fit_h')}. Controls: {control_text}. "
        "Fires/silent are instrument gates; specific/sham are scientific controls. "
        "Для слона это проверка, возникает ли у standalone death-reset механизма предсказанный "
        "полюс повреждения и стремится ли интервал death-reset к нулю при h→1. "
        "Результат проверяет численный контракт и специфичность смертного канала, но не является "
        "новым биологическим законом и не меняет live core. Production сохраняет exact global "
        "interval histogram и yoked schedule fingerprint вместо многогигабайтного event journal; "
        "научные гипотеза, seeds, endpoints и gates не менялись."
    )
    limitations = list(summary.get("limitations", []))
    limitations.extend([
        "T_life здесь — mean global death-reset interval, а не Chao senescence time; равенство определений не предполагается.",
        "Histogram сохраняет точные интервалы и moments, но не порядок отдельных событий; yoking проверяется не криптографическим fingerprint.",
        "Это проверка аналитического результата в standalone driver, а не новый научный результат сам по себе.",
        "Synthetic self-test проверяет анализатор, но не является scientific evidence.",
        "Negative и horizon_limited исходы являются полноценными результатами и не требуют перезапуска до положительного.",
        "Main подтвердил, что experiments-v1 и candidate-sandbox для текущих задач не требуются; received терминален для агента.",
        "Результат условен относительно закреплённого main-owned driver, task version, exact raw CSV и analysis code.",
    ])
    base = task["base_commit"]
    messages = list(dict.fromkeys(DEFAULT_MESSAGES + args.complied_message))
    plan = {
        "submission_id": args.submission_id,
        "instance_id": args.instance_id,
        "scientific_outcome": submission_outcome,
        "summary": summary_text,
        "limitations": "\n".join(f"- {item}" for item in dict.fromkeys(limitations)),
        "environment": load(args.environment),
        "toolchain": load(args.toolchain),
        "reproduce": [
            f"git archive {base} | tar -x -C /path/to/clean-tree",
            "cd /path/to/clean-tree/core && cargo test --release --offline --bin exp_dq6 -- --test-threads=1",
            "cd /path/to/clean-tree/core && cargo build --release --locked --offline --bin exp_dq6",
            "python3 dq6_run_leased.py --claim claim.json --driver /path/to/target/release/exp_dq6 --source driver-source.rs --toolchain /path/to/toolchain.json --runner dq6_run.sh --out /new/results-directory --cli lab/cli/main.py --db lab/state/control.db --agent exper --version <published-version> --task-hash <claim-task-version-sha256> --heartbeat-seconds 60",
            "python3 dq6_record_environment.py --run-dir /new/results-directory --task task.json --driver /path/to/target/release/exp_dq6 --source driver-source.rs --analyzer dq6_analyze.py --runner dq6_run.sh --leased-runner dq6_run_leased.py --toolchain /path/to/toolchain.json",
            "Verify run-manifest.json, lease-run.json, environment.json, toolchain.json, raw histogram/summary files and analysis/summary.json.",
            "python3 dq6_make_finding.py --results-dir /new/results-directory --task task.json --design design.md --out FINDING-EXP-2026-4103.md",
        ],
        "links": {
            "task": TASK_ID,
            "finding": "docs/FINDING-EXP-2026-4103.md",
            "proposal": args.proposal_id,
            "kg_refs": list(task["spec"].get("kg_refs", [])),
        },
        "complied_messages": messages,
        "artifacts": [{"path": rel, "media_type": media} for rel, media in ARTIFACTS],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": str(args.out), "artifacts": len(ARTIFACTS), "artifact_bytes": total_bytes,
        "disk_budget_bytes": disk_budget, "analysis_classification": classification,
        "scientific_outcome": submission_outcome,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
