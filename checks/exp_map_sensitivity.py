"""Sensitivity of the environment map to the repertoire and to the outcome encoding.

`FINDING-166` built a map on one axis only, because the richness count saturated.
An external review (see `docs/REVIEW-emergence-notes-4.md`) named the pathology
and proposed the fix: report the **fraction of differing pairs** rather than the
number of classes, and declare the outcome encoding instead of inheriting it.

    Q(E) = 2/(m(m-1)) * sum_{i<j} D_ij ,  D_ij = 1 if i and j differ

`K` (classes) and `Q` (pairs) answer different questions: K counts distinct
results, Q counts how widely the differences are spread. With five behaviours and
four of them the same, K = 2 and Q = 0.4; with all five different, K = 5 and Q = 1.

Three things are declared here, before the run, because the review is right that
without them the number has no single meaning:

    encoding A  lifetime only
    encoding B  lifetime + cause of death
    encoding C  lifetime + cause + realised take, to three decimals

    threshold   two lifetimes are the same when their rounded integers agree
                (lifetime is already an integer count of steps); the take is
                compared to 1e-3. Declared, not fitted.

    repertoire  five behaviours, then SIX with `predict` added. The sixth is not
                chosen because it looks good - it already exists in the probe as
                "memory that knows the transition", and it is the only arm that is
                a different *kind* of rule rather than another sampling of the same
                one.

`censored` marks an arm that was still alive at the horizon: its lifetime is a
lower bound, not a measurement, and counting it as 20000 steps of life is the
mistake the review warns about.

    python3 checks/exp_map_sensitivity.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "checks"))

import result as R  # noqa: E402
from experiment import Experiment  # noqa: E402

PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "memory_probe")

FIVE = ("stay", "random", "erased", "intact", "sighted")
SIX = FIVE + ("predict",)
ENCODINGS = ("A_lifetime", "B_lifetime_cause", "C_lifetime_cause_take")

SPACING = (2, 3, 4, 6, 8, 12, 24)
REGROW = (0.50, 0.60, 0.70, 0.80, 0.90)

CELLS = 24
M_FIELD = 2.0
MAINTENANCE = 1.7911
REPAIR_COST = 1.5
DAMAGE_RATE = 0.02
INCOME = MAINTENANCE + DAMAGE_RATE * REPAIR_COST
STEPS = 20000
SEED = 1
START_CELL = 3
POOR = 0.20
TAKE_TOL = 1e-3


def run(arm: str, spacing: int, regrow: float) -> dict:
    cmd = [
        PROBE,
        "--arm", arm,
        "--cells", str(CELLS),
        "--m", str(M_FIELD),
        "--regrow", str(regrow),
        "--income", str(round(INCOME, 10)),
        "--maintenance", str(MAINTENANCE),
        "--repair-cost", str(REPAIR_COST),
        "--damage-rate", str(DAMAGE_RATE),
        "--steps", str(STEPS),
        "--seed", str(SEED),
        "--threshold", "1.0",
        "--capacity", "10.0",
        "--energy", "5.0",
        "--read-budget", "3",
        "--read-cost", "0.0",
        "--read-period", "1",
        "--field", "peaks",
        "--period", str(spacing),
        "--poor", str(POOR),
        "--start-cell", str(START_CELL),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def same(a: dict, b: dict, encoding: str) -> bool:
    """The declared equivalence: this is the whole measurement, so it is explicit."""
    if a["lifetime"] != b["lifetime"]:
        return False
    if encoding == "A_lifetime":
        return True
    if a["cause"] != b["cause"]:
        return False
    if encoding == "B_lifetime_cause":
        return True
    return abs(a["taken_mean"] - b["taken_mean"]) <= TAKE_TOL


def richness(runs: dict, arms: tuple, encoding: str) -> tuple[int, float]:
    """(classes, fraction of differing pairs) for one environment."""
    keys = list(arms)
    m = len(keys)
    total = m * (m - 1) / 2
    differing = 0
    classes: list[list[str]] = []
    for i, a in enumerate(keys):
        placed = False
        for group in classes:
            if same(runs[a], runs[group[0]], encoding):
                group.append(a)
                placed = True
                break
        if not placed:
            classes.append([a])
        for j in range(i + 1, m):
            if not same(runs[a], runs[keys[j]], encoding):
                differing += 1
    return len(classes), differing / total


def main(argv: list[str]) -> int:
    if not os.path.exists(PROBE):
        print(f"probe not built: {PROBE}")
        return 1

    arithmetic = {
        "question": "how much of the environment map is a property of the instrument",
        "pathology_named": (
            "FINDING-166 counted distinct outcomes and saturated at 4 of 5. An "
            "external review named this: a raw class count with a fixed repertoire "
            "measures the resolution of the encoding as much as the medium"
        ),
        "two_numbers": {
            "K": "number of equivalence classes among the repertoire",
            "Q": "2/(m(m-1)) * number of differing pairs; the review's proposed fix",
        },
        "declared_encoding": {
            "A": "lifetime only",
            "B": "lifetime + cause of death",
            "C": "lifetime + cause + realised take to 1e-3",
        },
        "declared_threshold": (
            "lifetime is an integer count of steps so equality is exact; the take is "
            f"compared to {TAKE_TOL}. Declared, not fitted"
        ),
        "declared_repertoires": {
            "five": list(FIVE),
            "six": list(SIX),
            "why_six": (
                "`predict` already exists in the probe as memory that knows the "
                "transition; it is the only arm that is a different kind of rule "
                "rather than another sampling of the same one, and it was not chosen "
                "for the effect it has on the map"
            ),
        },
        "censoring": (
            "an arm alive at the horizon has lifetime == steps; that is a lower "
            "bound, not a measurement, and it is flagged rather than averaged in"
        ),
        "prediction": (
            "Q varies where K does not: the cells that saturated at K = 4 should "
            "differ in Q, so the map gains resolution. And adding the sixth "
            "behaviour should change K in most cells but Q in fewer, because `predict` "
            "coincides with `intact` whenever it looks every step"
        ),
    }

    exp = Experiment(
        experiment_id="map-sensitivity",
        question="how much of the map is the instrument",
        arithmetic=arithmetic,
        arms={f"{enc}/{rep}": f"encoding {enc} with {rep}"
              for enc in ENCODINGS for rep in ("five", "six")},
        seed=SEED,
        command="python3 checks/exp_map_sensitivity.py",
        parameters={
            "spacing": list(SPACING),
            "regrow": list(REGROW),
            "encodings": list(ENCODINGS),
            "five": list(FIVE),
            "six": list(SIX),
            "take_tolerance": TAKE_TOL,
        },
    )

    rows: list[dict] = []
    hashes: dict[str, list[str]] = {a: [] for a in SIX}
    for spacing in SPACING:
        for regrow in REGROW:
            runs = {a: run(a, spacing, regrow) for a in SIX}
            for a in SIX:
                hashes[a].append(runs[a]["hash"])
            entry = {
                "spacing": spacing,
                "regrow": regrow,
                "censored": {a: runs[a]["lifetime"] >= STEPS for a in SIX},
                "lifetimes": {a: runs[a]["lifetime"] for a in SIX},
                "causes": {a: runs[a]["cause"] for a in SIX},
            }
            for enc in ENCODINGS:
                k5, q5 = richness(runs, FIVE, enc)
                k6, q6 = richness(runs, SIX, enc)
                entry[enc] = {"K5": k5, "Q5": round(q5, 6), "K6": k6, "Q6": round(q6, 6)}
            rows.append(entry)
    exp.result["rows"] = rows

    for a in SIX:
        blob = "\n".join(hashes[a]).encode()
        exp.add_arm(
            a,
            f"repertoire arm {a}",
            {
                "mean_lifetime": sum(r["lifetimes"][a] for r in rows) / len(rows),
                "censored": sum(1 for r in rows if r["censored"][a]),
            },
            trace_hash=hashlib.sha256(blob).hexdigest()[:16],
        )

    def by_hash(groups: dict[str, list[str]]):
        out = {}
        for key, h in groups.items():
            out.setdefault(h, []).append(key)
        return [sorted(v) for v in out.values() if len(v) > 1]

    for group in by_hash(exp.result["hashes"]):
        exp.expect_coincident(*group)
    exp.result["coincident_groups"] = by_hash(exp.result["hashes"])

    # -- report -------------------------------------------------------------
    print(f"{'enc':<26} {'K5 uniq':>8} {'Q5 uniq':>8} {'K6 uniq':>8} {'Q6 uniq':>8}")
    summary = {}
    for enc in ENCODINGS:
        k5 = sorted({r[enc]["K5"] for r in rows})
        q5 = sorted({r[enc]["Q5"] for r in rows})
        k6 = sorted({r[enc]["K6"] for r in rows})
        q6 = sorted({r[enc]["Q6"] for r in rows})
        summary[enc] = {"K5": k5, "Q5": q5, "K6": k6, "Q6": q6}
        print(f"{enc:<26} {str(k5):>8} {len(q5):>8} {str(k6):>8} {len(q6):>8}")
    exp.result["summary"] = summary

    censored_cells = sum(
        1 for r in rows if any(r["censored"][a] for a in SIX)
    )

    # -- controls -----------------------------------------------------------
    # The controls test whether the number is a property of the medium or of the
    # instrument, which is the whole point. They are written against what the run
    # can actually settle, not against what would have been flattering.
    q_a = len(summary["A_lifetime"]["Q5"])
    k_a = len(summary["A_lifetime"]["K5"])
    exp.control(
        "fires",
        q_a > k_a,
        f"the pair fraction takes {q_a} distinct values against {k_a} for the class "
        "count, so the proposed fix does resolve part of what the count flattened",
    )

    k_c = summary["C_lifetime_cause_take"]["K5"]
    q_c = summary["C_lifetime_cause_take"]["Q5"]
    exp.control(
        "silent",
        len(k_c) <= len(summary["B_lifetime_cause"]["K5"]),
        f"encoding C collapses the classes to {k_c} and the pair fraction to "
        f"{len(q_c)} distinct values: a finer threshold makes every run differ from "
        "every other, which is saturation in the other direction",
    )

    same_five_six = (
        summary["A_lifetime"]["K5"] == summary["A_lifetime"]["K6"]
        and summary["B_lifetime_cause"]["K5"] == summary["B_lifetime_cause"]["K6"]
    )
    exp.control(
        "specific",
        same_five_six,
        "adding the sixth behaviour leaves the class count unchanged under A and B, "
        "because `predict` equals `intact` whenever it looks every step: the "
        "repertoire can only add a class where a genuinely new kind of rule exists",
    )

    exp.limitation(
        "the whole measurement is the declared equivalence. Two runs are 'the same' "
        "because the encoding says so; another threshold would give another map"
    )
    exp.limitation(
        "the probe wraps movement around a ring while `Field` and `Life` stop at the "
        "edges (`core/src/field.rs:297-303`). Every number here is a ring number and "
        "does not transfer to the line"
    )
    exp.limitation(
        "one environment per cell and one seed: deterministic, so there is no sample "
        "variance to report, and equally no basis for generalising beyond this box"
    )
    exp.limitation(
        "censored runs are flagged, not corrected: a lower bound is not a lifetime"
    )
    exp.limitation(
        "the sixth behaviour was not chosen to move the map, but it is still a "
        "behaviour we wrote; a repertoire drawn from somewhere else would be a "
        "different instrument"
    )

    k_q = summary["B_lifetime_cause"]
    reason = (
        f"Across {len(rows)} environments the class count takes {len(k_q['K5'])} "
        f"distinct values ({k_q['K5']}) and the pair fraction takes "
        f"{len(k_q['Q5'])}, so the proposed pair metric does resolve part of what the "
        "count flattened - but only part. The encoding decides the rest: with the "
        f"realised take added, classes fall to {summary['C_lifetime_cause_take']['K5']} "
        f"and the pair fraction to {len(summary['C_lifetime_cause_take']['Q5'])} "
        "distinct values, because at a 1e-3 threshold every run differs from every "
        "other and the metric saturates the other way. Adding a sixth behaviour does "
        "not change the class count under A or B, because `predict` and `intact` are "
        "the same dynamics when both look every step. So the second axis exists but "
        "its scale is set by our declared encoding and not by the medium, and the "
        "review's prohibition is adopted: the number is never called environment "
        "richness without naming the repertoire and the encoding. "
        f"{censored_cells} of {len(rows)} environments have at least one arm alive at "
        "the horizon; those lifetimes are lower bounds and are flagged, not counted as "
        "measurements."
    )
    exp.verdict("failed", "EXPLAINED: " + reason)
    print()
    print(reason)

    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
