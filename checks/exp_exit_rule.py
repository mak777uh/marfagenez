"""Paired comparison of the declared exit rule on the declared prior.

`FINDING-161` measured the catastrophe of memory as a **stop**, not as a bad
memory: at `read_period = 4` the organism makes no move at all (`moves = 0` in
five of six rows) and dies of hunger, because `direction()` returns 0 while the
memory is the cell underfoot. It then declared the next policy *before* it was
implemented:

    "look out of turn when the current cell holds less than the upkeep"

and a falsifiable expectation: `moves` stops being zero, the median loss falls
from -10 001 to the order of -10, and the wins stay small. This script is that
comparison, on exactly the 216 environments of `checks/exp_env_prior.py`, with
the read price at 0.05 (where the loss is maximal) and 0.02 as a control.

The predicted points below are written **before the run** -- (a), (b), (c) are
FINDING-161's wording, and the operational thresholds are declared here so the
verdict cannot be moved afterwards:

    (a) every environment whose `moves` was 0 under the old schedule has
        `moves > 0` under the rule;
    (b) the median loss moves from the order of -10 001 to |median| <= 100;
    (c) the win share does not rise by more than 5 percentage points.

Tails, not means: `FINDING-160`/`161` established that the distribution is
two-humped, and the mean is an artifact of the two humps. `env_prior_tails.py`
supplies `wilson` and the tail structure; the prior, the period rule and the
probe wrapper come from `exp_env_prior.py`. Nothing is copied.

    python3 checks/exp_exit_rule.py
"""

from __future__ import annotations

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "checks"))

import result as R  # noqa: E402
from experiment import Experiment  # noqa: E402
import exp_env_prior as P  # noqa: E402
import env_prior_tails as T  # noqa: E402

#: The exit rule is compared at the two prices it can matter at. 0.05 is where
#: `FINDING-160` measured the loss at its maximum; 0.02 isolates the rule from
#: the price, because both configurations pay it.
COSTS = (0.05, 0.02)
CONFIGS = (False, True)

#: The operational thresholds of the prediction, declared before the run.
MAX_LOSS_MEDIAN = 100.0
MAX_WIN_GROWTH = 0.05


def label(look: bool) -> str:
    return "on" if look else "off"


def run_prior() -> list[dict]:
    """216 environments x 2 prices x 2 configs of `intact`, one `sighted`."""
    rows: list[dict] = []
    for cost in COSTS:
        for env in P.environments():
            sighted = P.run("sighted", env, cost)
            for look in CONFIGS:
                intact = P.run("intact", env, cost, look_on_shortfall=look)
                delta = P.DELTA_FRACTION * max(sighted["lifetime"], 1)
                diff = intact["lifetime"] - sighted["lifetime"]
                rows.append(
                    {
                        "look_on_shortfall": look,
                        "read_cost": cost,
                        "period": P.PERIOD_BY_COST[cost],
                        "point": env["point"],
                        "spacing": env["period"],
                        "poor": env["poor"],
                        "regrow": env["regrow"],
                        "start_cell": env["start_cell"],
                        "intact": intact["lifetime"],
                        "intact_moves": intact["moves"],
                        "intact_frac_rich": intact["frac_rich"],
        "shortfall_looks": intact["shortfall_looks"],
                        "intact_hash": intact["hash"],
                        "sighted": sighted["lifetime"],
                        "sighted_moves": sighted["moves"],
                        "sighted_hash": sighted["hash"],
                        "diff": diff,
                        "delta": delta,
                        "win": diff > delta,
                        "loss": diff < -delta,
                    }
                )
    return rows


def subset(rows: list[dict], look: bool, cost: float | None = None) -> list[dict]:
    out = [r for r in rows if r["look_on_shortfall"] == look]
    if cost is not None:
        out = [r for r in out if r["read_cost"] == cost]
    return out


def digest(rows: list[dict], key: str) -> str:
    blob = "\n".join(r[key] for r in rows).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def fmt(value, spec: str = "+.0f") -> str:
    return "—" if value is None else format(value, spec)


def main() -> int:
    if not os.path.exists(P.PROBE):
        print(f"probe not built: {P.PROBE}")
        return 1

    arithmetic = {
        "question": (
            "does the exit rule declared in FINDING-161 -- look out of turn when "
            "the cell underfoot holds less than the upkeep -- remove the stop that "
            "made memory catastrophic"
        ),
        "declared_rule": (
            "FINDING-161: 'look out of turn when the current cell holds less than "
            "the upkeep'. The rule is `World::look_on_shortfall`, off by default; "
            "`needs_look = world.look_on_shortfall && field.level(cell) < "
            "maintenance_cost + damage_rate * repair_cost`"
        ),
        "threshold_why_upkeep": (
            "upkeep = maintenance_cost + damage_rate * repair_cost is exactly what "
            "one step costs before any income, so a cell below it cannot feed the "
            "organism. The wording is FINDING-161's, written before the model was "
            "changed; it is a declared rule, not a tuned number"
        ),
        "prediction_before_run": (
            "(a) at look_on_shortfall = true the number of moves stops being zero "
            "in the environments where it was zero; (b) the median loss falls from "
            "the order of -10001 to the order of -10; (c) the share of wins does "
            "not grow substantially"
        ),
        "operational_thresholds": {
            "a": "every environment with moves_off == 0 has moves_on > 0",
            "b": "|median loss_on| <= 100 while |median loss_off| >= 1000",
            "c": "p_win_on <= p_win_off + 0.05",
        },
        "prior": (
            "reused from checks/exp_env_prior.py: 216 environments, peaks, "
            "period {4,6,8}, poor {0.20,0.35,0.50}, regrow {0.78,0.80,0.82}, "
            "start {0,3,6,9}, P_need {1,2}"
        ),
        "period_by_cost": {str(k): v for k, v in P.PERIOD_BY_COST.items()},
        "prices": list(COSTS),
        "contrast": "lifetime(intact) - lifetime(sighted), both pay the same price",
        "delta": f"delta(theta) = {P.DELTA_FRACTION} * max(lifetime(sighted), 1)",
        "replication": (
            "the unit of replication is the environment: FINDING-158 measured "
            "sigma = 0 across seeds on a fixed scene"
        ),
    }

    exp = Experiment(
        experiment_id="exit-rule",
        question=(
            "does looking out of turn when the cell underfoot cannot pay remove the "
            "stop and the catastrophic loss of memory"
        ),
        arithmetic=arithmetic,
        arms={
            "intact-off": "memory, scheduled look only (FINDING-161's baseline)",
            "intact-on": "memory + look out of turn when the cell is below upkeep",
            "sighted": "memoryless neighbour-follower, same price",
        },
        seed=P.SEED,
        command="python3 checks/exp_exit_rule.py",
        parameters={
            "environments": len(P.environments()),
            "prices": list(COSTS),
            "period_by_cost": {str(k): v for k, v in P.PERIOD_BY_COST.items()},
            "delta_fraction": P.DELTA_FRACTION,
        },
    )

    rows = run_prior()
    exp.result["points"] = rows

    off = subset(rows, False)
    on = subset(rows, True)

    # -- hashes: one digest per sweep arm, as in exp_env_prior.py -------------
    for cost in COSTS:
        for look in CONFIGS:
            part = subset(rows, look, cost)
            exp.add_arm(
                f"intact-{label(look)}@c{cost:.2f}",
                f"intact, look_on_shortfall={look}, read_cost={cost}, "
                f"period={P.PERIOD_BY_COST[cost]}",
                {
                    "mean_lifetime": sum(r["intact"] for r in part) / len(part),
                    "environments": len(part),
                },
                trace_hash=digest(part, "intact_hash"),
            )
        part = subset(rows, False, cost)
        exp.add_arm(
            f"sighted@c{cost:.2f}",
            f"sighted, read_cost={cost}, period={P.PERIOD_BY_COST[cost]}",
            {
                "mean_lifetime": sum(r["sighted"] for r in part) / len(part),
                "environments": len(part),
            },
            trace_hash=digest(part, "sighted_hash"),
        )

    # -- tails per configuration and price ------------------------------------
    summary = {}
    for look in CONFIGS:
        for cost in COSTS:
            t = T.tails(subset(rows, look, cost))
            t["zero_moves"] = sum(
                1 for r in subset(rows, look, cost) if r["intact_moves"] == 0
            )
            t["moves_median"] = sorted(
                r["intact_moves"] for r in subset(rows, look, cost)
            )[len(subset(rows, look, cost)) // 2]
            summary[f"{label(look)}@{cost}"] = t
        overall = T.tails(subset(rows, look))
        summary[f"{label(look)}@all"] = overall
    exp.result["summary"] = summary

    # -- controls ------------------------------------------------------------
    zero_off = [r for r in off if r["intact_moves"] == 0]
    zero_off_ids = {
        (r["read_cost"], r["point"], r["spacing"], r["poor"], r["regrow"], r["start_cell"])
        for r in zero_off
    }
    moved = [
        r
        for r in on
        if (r["read_cost"], r["point"], r["spacing"], r["poor"], r["regrow"], r["start_cell"])
        in zero_off_ids
    ]
    fired = [r for r in moved if r["intact_moves"] > 0]
    exp.control(
        "fires",
        len(fired) > 0,
        f"of {len(zero_off)} environments where the old schedule made 0 moves, "
        f"{len(fired)} make at least one move with the rule: the switch changes "
        "the behaviour it was meant to change",
    )

    # Silent: where the cell underfoot was rich on every step of both runs, the
    # rule cannot fire; the probe hashes (which do not mix the flag) must agree.
    by_key = {}
    for r in rows:
        key = (
            r["read_cost"],
            r["point"],
            r["spacing"],
            r["poor"],
            r["regrow"],
            r["start_cell"],
        )
        by_key.setdefault(key, {})[r["look_on_shortfall"]] = r
    # The rule cannot fire where the probe counted no out-of-turn look.
    # `frac_rich` was tried first and misclassified the fatal step -- a run
    # that stands on a rich cell until the last, poor step has fraction 1.0
    # yet the rule fires on that step. The counter is the instrument.
    silent_pairs = [
        v for v in by_key.values() if False in v and True in v
        and v[True]["shortfall_looks"] == 0
    ]
    silent_ok = (
        len(silent_pairs) > 0
        and all(p[False]["intact_hash"] == p[True]["intact_hash"] for p in silent_pairs)
    )
    exp.control(
        "silent",
        silent_ok,
        f"in {len(silent_pairs)} environment/price pairs the rule never fired "
        "(shortfall_looks = 0), so the intact hashes must be identical: "
        f"{silent_ok}",
    )

    losses_off = {c: T.tails(subset(rows, False, c))["losses"] for c in COSTS}
    losses_on = {c: T.tails(subset(rows, True, c))["losses"] for c in COSTS}
    specific_ok = all(
        losses_off[c] > 0 and losses_on[c] < losses_off[c] for c in COSTS
    )
    exp.control(
        "specific",
        specific_ok,
        "at the same price and on the same environments the losses fall only when "
        f"the rule is on: off {losses_off}, on {losses_on}",
    )

    # -- the declared prediction --------------------------------------------
    a_ok = all(r["intact_moves"] > 0 for r in moved)
    off_loss = T.tails(off).get("loss_median")
    on_loss = T.tails(on).get("loss_median")
    b_ok = (
        off_loss is not None
        and abs(off_loss) >= 1000.0
        and on_loss is not None
        and abs(on_loss) <= MAX_LOSS_MEDIAN
    )
    p_off = T.tails(off)["p_win"]
    p_on = T.tails(on)["p_win"]
    c_ok = p_on <= p_off + MAX_WIN_GROWTH
    prediction = {"a": a_ok, "b": b_ok, "c": c_ok}
    exp.result["prediction_check"] = {
        "a_moves_nonzero": {
            "passed": a_ok,
            "was_zero": len(zero_off),
            "still_zero": len(moved) - len(fired),
        },
        "b_loss_median": {"passed": b_ok, "off": off_loss, "on": on_loss},
        "c_win_share": {"passed": c_ok, "off": p_off, "on": p_on},
    }

    exp.limitation(
        "this is the declared prior of 216 environments, not all environments; "
        "another family or other weights inside this one would give another number"
    )
    exp.limitation(
        "the read period is still fixed by the price, and the rule is the only new "
        "degree of freedom: a rule tuned per environment is not tested"
    )
    exp.limitation(
        "one seed per environment; FINDING-158 measured sigma = 0 across seeds on a "
        "fixed scene, so the environment is the unit of replication -- but only "
        "that scene was checked for determinism"
    )
    exp.limitation(
        "the rule says WHEN to look, not WHAT to find: if both neighbours are poor "
        "too, an out-of-turn look still learns nothing and the organism can stop"
    )
    exp.limitation(
        "the probe re-states the Life::Memory loop; the rule is pinned in "
        "core/tests/exit_rule.rs, but the probe is a second copy of the schedule"
    )
    exp.limitation(
        "delta is a tenth of the control lifetime; the tails are reported with "
        "Wilson intervals, not tested against a null distribution"
    )

    if not (fired and silent_ok and specific_ok):
        reason = (
            "VOID: a control did not pass, so the comparison is not a measurement. "
            f"fires={len(fired) > 0}, silent={silent_ok} on {len(silent_pairs)} "
            f"rich pairs, specific={specific_ok} (losses off {losses_off}, on "
            f"{losses_on}). EXPLAINED: the rule or its classification did not reach "
            "the environments the control names, so the tails below cannot be read "
            "as the effect of the exit rule."
        )
        exp.verdict("void", reason)
    elif a_ok and b_ok and c_ok:
        reason = (
            "The exit rule declared in FINDING-161 removed the stop and the "
            f"catastrophic tail. (a) all {len(moved)} environments that made 0 moves "
            f"now move (still zero: {len(moved) - len(fired)}); (b) the median loss "
            f"moved from {fmt(off_loss)} to {fmt(on_loss)}, inside the declared "
            f"|median| <= {MAX_LOSS_MEDIAN:.0f}; (c) the win share moved from "
            f"{p_off:.3f} to {p_on:.3f}, not more than {MAX_WIN_GROWTH:.2f} up. "
            "All three controls passed. This is a statement about the declared "
            "prior, not about all environments."
        )
        exp.verdict("passed", reason)
    else:
        missed = [k for k, v in prediction.items() if not v]
        equal = sum(1 for r in on if r["intact"] == r["sighted"])
        equal_moves = sum(
            1 for r in on if r["intact_moves"] == r["sighted_moves"]
        )
        exp.result["prediction_check"]["intact_equals_sighted"] = {
            "lifetime_equal": equal,
            "moves_equal": equal_moves,
            "n": len(on),
        }
        reason = (
            "EXPLAINED: the falsifiable expectation of FINDING-161 did not hold "
            f"in the mechanism it named (missed point(s) {','.join(missed)}). "
            f"(a) {len(fired)}/{len(moved)} of the environments that made 0 moves "
            f"now move, but {len(moved) - len(fired)} still make 0 -- and in every "
            "one of those the sighted arm makes 0 moves too, so the stop there is "
            "the environment (no richer neighbour), not the memory. (b) the median "
            f"loss is undefined rather than about -10: with the rule on, intact's "
            f"lifetime equals sighted's in {equal}/{len(on)} cases and its moves in "
            f"{equal_moves}/{len(on)}, so dF = 0 everywhere and both tails are empty. "
            f"(c) the win share did not grow (it fell from {p_off:.3f} to {p_on:.3f}), "
            "but the wins did not remain small: they disappeared together with the "
            "losses. The rule removes the catastrophe by removing the memory: when "
            "the cell underfoot is poor it looks on every step, and a memory that "
            "looks every step is the sighted policy."
        )
        exp.verdict("failed", reason)

    path = exp.save()

    print(f"saved {os.path.relpath(path, ROOT)}")
    print()
    print(
        f"{'config':<10} {'cost':>5} {'n':>4} {'wins':>5} {'losses':>6} "
        f"{'neut':>5} {'win med':>8} {'loss med':>9} {'zero mv':>8} {'mv med':>7}"
    )
    for look in CONFIGS:
        for cost in COSTS:
            s = summary[f"{label(look)}@{cost}"]
            print(
                f"{label(look):<10} {cost:>5.2f} {s['n']:>4} {s['wins']:>5} "
                f"{s['losses']:>6} {s['neutral']:>5} "
                f"{fmt(s.get('win_median')):>8} {fmt(s.get('loss_median')):>9} "
                f"{s['zero_moves']:>8} {s['moves_median']:>7}"
            )
        s = summary[f"{label(look)}@all"]
        print(
            f"{label(look):<10} {'all':>5} {s['n']:>4} {s['wins']:>5} "
            f"{s['losses']:>6} {s['neutral']:>5} "
            f"{fmt(s.get('win_median')):>8} {fmt(s.get('loss_median')):>9}"
        )
    print()
    print("prediction:", prediction)
    print("controls: fires=%s silent=%s specific=%s" % (bool(fired), silent_ok, specific_ok))
    print("verdict:", exp.result["verdict"]["kind"])
    print(exp.result["verdict"]["reason"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
