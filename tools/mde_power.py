#!/usr/bin/env python3
"""MDE audit for frozen-ceiling and protocol-capacity result environments.

The primary calculation is an optimistic two-arm binomial MDE for the observed
survival fraction. It is intentionally labelled nominal: organisms share one
environment and are not independent seed-level replicates. The true lab MDE
uses between-seed sigma (see checks/result.py), which these result records do
not estimate when each environment has one seed.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DOC = ROOT / "docs" / "MDE-POWER.md"
ALPHA = 0.05
POWER = 0.80


def proportion_mde(success_a: int, success_b: int, n: int,
                   alpha: float = ALPHA, power: float = POWER) -> float:
    """Normal-approximation MDE for difference of two survival proportions.

    A Laplace +1 pooled success and +1 pooled failure correction avoids zero variance
    when both observed arms are all-alive or all-dead. This is a nominal screen,
    not a substitute for estimating between-seed sigma.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    if not (0 < alpha < 1 and 0 < power < 1):
        raise ValueError("alpha and power must be in (0, 1)")
    if not (0 <= success_a <= n and 0 <= success_b <= n):
        raise ValueError("success counts must lie in [0, n]")
    z = NormalDist()
    zsum = z.inv_cdf(1 - alpha / 2) + z.inv_cdf(power)
    pooled = (success_a + success_b + 1.0) / (2.0 * n + 2.0)
    variance = 2.0 * pooled * (1.0 - pooled) / n
    return zsum * math.sqrt(variance)


def pair_result(label: str, a: int, b: int, n: int, group: str) -> dict:
    mde = proportion_mde(a, b, n)
    delta = abs(a - b) / n
    return {
        "group": group,
        "environment": label,
        "n_organisms_per_arm": n,
        "seq_or_a_alive": a,
        "prop_or_b_alive": b,
        "observed_abs_delta": delta,
        "nominal_mde": mde,
        "screen": "confirmed" if delta >= mde else "questionable",
        "independent_seed_replicates_per_arm": 1,
    }


def latest_json(folder: str) -> tuple[Path, dict]:
    paths = sorted((RESULTS / folder).glob("run-*.json"))
    if not paths:
        raise FileNotFoundError(f"no run-*.json in results/{folder}")
    path = paths[-1]
    return path, json.loads(path.read_text(encoding="utf-8"))


def frozen_ceiling_rows() -> tuple[Path, list[dict]]:
    path, record = latest_json("frozen-ceiling")
    conditions = record.get("conditions") or {}
    rows = []
    items = sorted(conditions.items())
    for i, (key_a, arm_a) in enumerate(items):
        for key_b, arm_b in items[i + 1:]:
            a = arm_a.get("metrics") or {}
            b = arm_b.get("metrics") or {}
            n = min(int(a.get("total", 0)), int(b.get("total", 0)))
            if n < 1:
                continue
            row = pair_result(
                f"{key_a}-{key_b}",
                int(a.get("alive", 0)),
                int(b.get("alive", 0)),
                n,
                "frozen-ceiling",
            )
            row["continuous_energy_mde"] = "not_estimable: no per-organism variance or seed replicates"
            rows.append(row)
    return path, rows


def protocol_capacity_rows() -> tuple[Path, list[dict]]:
    path, record = latest_json("protocol-capacity")
    conditions = record.get("conditions") or {}
    seq: dict[str, dict] = {}
    prop: dict[str, dict] = {}
    for key, condition in conditions.items():
        match = re.fullmatch(r"(seq|prop)(\d+)", str(key))
        if not match:
            continue
        target = seq if match.group(1) == "seq" else prop
        target[match.group(2)] = condition.get("metrics") or {}

    rows = []
    for index in sorted(seq, key=int):
        if index not in prop:
            continue
        a, b = seq[index], prop[index]
        n = int(a.get("n") or b.get("n") or 0)
        if n < 1:
            continue
        row = pair_result(
            f"case={a.get('_case', '?')}, n={n}, r={a.get('r')}, t={a.get('t')}, m={a.get('m')}",
            int(a.get("seq_alive", 0)),
            int(b.get("prop_alive", 0)),
            n,
            "protocol-capacity",
        )
        row["seq_predicted"] = a.get("seq_predicted")
        row["prop_predicted"] = b.get("prop_predicted")
        row["threshold_seq_n"] = a.get("threshold_seq_n")
        row["threshold_prop_n"] = b.get("threshold_prop_n")
        rows.append(row)
    return path, rows


def analyse() -> dict:
    frozen_path, frozen = frozen_ceiling_rows()
    protocol_path, protocol = protocol_capacity_rows()
    if len(protocol) < 30:
        raise RuntimeError(
            f"protocol-capacity provides only {len(protocol)} paired environments; expected >=30"
        )
    return {
        "schema": "marfagenez.mde-power.v1",
        "alpha_two_sided": ALPHA,
        "target_power": POWER,
        "formula": "MDE = (z_(1-alpha/2) + z_power) * sqrt(2*p_pool*(1-p_pool)/n)",
        "pooled_proportion": "p_pool=(success_a+success_b+1)/(2*n+2), Laplace +1 pooled success and +1 pooled failure",
        "unit_warning": (
            "MDE rows use organisms within one shared environment and are optimistic. "
            "They are not independent seed-level replications. The lab's formal MDE "
            "requires sigma_between_seeds; one seed per environment leaves that value "
            "unestimated, so the true seed-level MDE is not estimable from these records."
        ),
        "sources": {
            "frozen_ceiling": str(frozen_path.relative_to(ROOT)),
            "protocol_capacity": str(protocol_path.relative_to(ROOT)),
        },
        "counts": {
            "frozen_ceiling_pairwise_contrasts": len(frozen),
            "protocol_capacity_paired_environments": len(protocol),
            "protocol_confirmed_nominal": sum(r["screen"] == "confirmed" for r in protocol),
            "protocol_questionable_nominal": sum(r["screen"] == "questionable" for r in protocol),
            "confirmed_mean_abs_delta": (
                sum(r["observed_abs_delta"] for r in protocol if r["screen"] == "confirmed")
                / max(1, sum(r["screen"] == "confirmed" for r in protocol))
            ),
            "confirmed_min_abs_delta": min(
                (r["observed_abs_delta"] for r in protocol if r["screen"] == "confirmed"),
                default=None,
            ),
            "confirmed_max_abs_delta": max(
                (r["observed_abs_delta"] for r in protocol if r["screen"] == "confirmed"),
                default=None,
            ),
        },
        "rows": frozen + protocol,
    }


def markdown(report: dict) -> str:
    lines = [
        "# MDE / power audit",
        "",
        "**Date:** 2026-11-27. **alpha:** 0.05 two-sided. **Target power:** 0.80.",
        "",
        "## Statistical contract",
        "",
        "The nominal two-arm binomial screen is",
        "",
        r"\[ MDE = (z_{1-\alpha/2}+z_{1-\beta})\sqrt{\frac{2\hat p(1-\hat p)}{n}}. \]",
        "",
        "where n is the recorded number of organisms per arm and",
        "p-hat = (success_a + success_b + 1)/(2n + 2) uses Laplace smoothing: +1 pooled success and +1 pooled failure.",
        "The correction avoids zero estimated variance for all-alive/all-dead pairs.",
        "",
        "**Critical limitation:** this is an optimistic organism-level screen. The organisms",
        "share one finite resource field, so independence is not established. The lab's",
        "formal MDE formula in checks/result.py uses between-seed sigma. These latest",
        "environment records have one seed per environment, so true seed-level sigma and",
        "true seed-level MDE are not estimable from these rows. Do not read the nominal",
        "screen as confirmatory evidence.",
        "",
        "The confirmed / questionable labels below mean only observed delta >= nominal MDE",
        "or not. They do not upgrade a simulation finding to external validation.",
        "",
        "## Findings 176–178 and 226–229",
        "",
        "| Finding | Threshold anchor | Runs / point reported in source | MDE interpretation |",
        "|---|---|---:|---|",
        "| FINDING-176 | income = 1.8211; N = 12, 24, 48, 96 | 1 | not estimable: no between-seed sigma |",
        "| FINDING-177 | repair-cost edge = 0.4000 vs 0.3333 | 1 | not estimable: no between-seed sigma |",
        "| FINDING-178 | poor-cell edge = 1.8395 vs 1.8496 | 1 | not estimable: no between-seed sigma |",
        f"| FINDING-226 | f0 in (11, 12); 24/24 vs 0/24 | 24 | nominal binary MDE ≈ {proportion_mde(24, 0, 24):.3f}; observed contrast 1.0 |",
        f"| FINDING-227 | f0 = 11 vs 12; 8/8 vs 0/8 | 8 | nominal binary MDE ≈ {proportion_mde(8, 0, 8):.3f}; observed contrast 1.0 |",
        f"| FINDING-228 | stock0 = 100 vs 50 at f0 = 4; 8/8 vs 0/8 | 8 | nominal binary MDE ≈ {proportion_mde(8, 0, 8):.3f}; observed contrast 1.0 |",
        f"| FINDING-229 | stock0 = 50: f0 = 2 vs 4; 8/8 vs 0/8 | 8 | nominal binary MDE ≈ {proportion_mde(8, 0, 8):.3f}; observed contrast 1.0 |",
        "",
        "Interpretation: FINDING-176–178 each use one deterministic scene/seed per parameter point; the four world sizes in 176 and the different threshold points in 177–178 are not independent replicates.",
        "The table therefore records one source-reported run per point for 176–178; the 226–229 counts are reported run repetitions. Independence by seed is not inferred from a count alone.",
        "FINDING-176 uses four world sizes, not four replicate seeds;",
        "177 and 178 use different deterministic parameter points, not replicate trials.",
        "FINDING-226 records 24/24 versus 0/24 around its sharp f0 threshold. FINDING-227–229",
        "report 8 runs per point. Their large binary survival contrasts are detectable under",
        "the binomial approximation, but they do not estimate continuous between-seed",
        "variance or show power for small effects.",
        "",
        "## Frozen-ceiling contrasts",
        "",
        f"Source: {report['sources']['frozen_ceiling']}",
        "",
        "| Contrast | n/arm | Observed delta survival | Nominal MDE | Screen | Continuous energy MDE |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in report["rows"]:
        if row["group"] != "frozen-ceiling":
            continue
        lines.append(
            f"| {row['environment']} | {row['n_organisms_per_arm']} | "
            f"{row['observed_abs_delta']:.3f} | {row['nominal_mde']:.3f} | "
            f"{row['screen']} | not estimable |"
        )
    lines += [
        "",
        "The file stores means/maxima and a one-element energies summary, not per-organism",
        "energies or replicated seeds; a continuous-energy MDE cannot be back-calculated.",
        "All three pairwise survival contrasts are zero.",
        "",
        "## Protocol-capacity paired environments",
        "",
        f"Source: {report['sources']['protocol_capacity']}",
        "",
        f"Rows: {report['counts']['protocol_capacity_paired_environments']}; nominal screen: "
        f"{report['counts']['protocol_confirmed_nominal']} confirmed, "
        f"{report['counts']['protocol_questionable_nominal']} questionable.",
        f"Nominally confirmed on {report['counts']['protocol_confirmed_nominal']}/"
        f"{report['counts']['protocol_capacity_paired_environments']} environments; "
        f"mean observed delta={report['counts']['confirmed_mean_abs_delta']:.3f}, "
        f"range={report['counts']['confirmed_min_abs_delta']:.3f}-"
        f"{report['counts']['confirmed_max_abs_delta']:.3f}. These are descriptive "
        "within-environment organism contrasts, not independent-seed replication.",
        "",
        "| # | Environment (case, n, r, t, m) | Seq alive | Prop alive | delta survival | MDE | Screen |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in report["rows"]:
        if row["group"] != "protocol-capacity":
            continue
        number = row["environment"].split(",")[0].split("=")[-1]
        lines.append(
            f"| {number} | {row['environment']} | "
            f"{row['seq_or_a_alive']} | {row['prop_or_b_alive']} | "
            f"{row['observed_abs_delta']:.3f} | {row['nominal_mde']:.3f} | {row['screen']} |"
        )
    lines += [
        "",
        "## Decision",
        "",
        "Some large within-environment survival separations are much larger than the",
        "nominal organism-level MDE; the no-difference rows are below it. However, the",
        "environment/seed is the intended independent unit. The table therefore does",
        "not close the formal power requirement. Confirmatory follow-up should use",
        "predeclared independent seeds per environment, estimate sigma between those seeds,",
        "then calculate MDE with the checks/result.py:arms_needed contract before running.",
        "",
        "Reproduce with:",
        "",
        "    python3 tools/mde_power.py --selftest",
        "    python3 tools/mde_power.py --write",
        "",
    ]
    return "\n".join(lines)


def selftest() -> int:
    assert abs(proportion_mde(8, 0, 8) - 0.7004) < 0.001
    assert abs(proportion_mde(24, 0, 24) - 0.4040) < 0.001
    assert proportion_mde(30, 30, 30) > 0.0
    assert proportion_mde(30, 0, 30) < 1.0
    assert proportion_mde(0, 0, 30) > 0.0
    try:
        proportion_mde(31, 0, 30)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid success count was accepted")
    report = analyse()
    assert report["counts"]["protocol_capacity_paired_environments"] >= 30
    assert report["counts"]["protocol_confirmed_nominal"] + report["counts"]["protocol_questionable_nominal"] == len(
        [r for r in report["rows"] if r["group"] == "protocol-capacity"]
    )
    print("OK: MDE formula, boundary cases and >=30 paired environments")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--write", action="store_true", help="write docs/MDE-POWER.md")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    report = analyse()
    rendered = markdown(report)
    if args.write:
        DOC.write_text(rendered, encoding="utf-8")
        print(f"wrote {DOC.relative_to(ROOT)}")
    else:
        print(rendered)
    print(
        f"nominal protocol-capacity screen: "
        f"{report['counts']['protocol_confirmed_nominal']} confirmed / "
        f"{report['counts']['protocol_questionable_nominal']} questionable"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
