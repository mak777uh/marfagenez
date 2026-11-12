"""Bring the two dead-law results up to the v2 contract shape.

Both files were written before checks/result.py existed in its current form:
`verdict` was a bare string, `controls` was a list, and `hashes`/`limitations`
were missing or named `limitation`.  The measurements are unchanged -- only the
envelope is rewritten, so the numbers in the finding documents still match.

Nothing here re-runs the model.  Re-running would produce new hashes and the
docs would then cite numbers no file contains.
"""
import json
import sys

ROOT = "/mnt/c/Users/Admin/Documents/Qoder/2026-10-18/82ab86cd/marfagenez/results"


def upgrade_exp21(path):
    d = json.load(open(path))
    rows = d["rows"]
    # §5 says two arms with the same hash are one arm.  Here that is literally
    # true and it is a finding, not a defect: maintenance 1.00 and 1.20 both
    # kill every organism, so they produce the identical trace.  Collapsing them
    # into one arm is the honest reading -- the second parameter value adds no
    # dynamics, only a second name for the same run.
    by_hash = {}
    for r in rows:
        by_hash.setdefault(r["trace_hash"], []).append(r["maintenance"])
    hashes = {}
    for h, mnts in by_hash.items():
        label = "mnt" + "+".join(str(m) for m in mnts)
        hashes[label] = h
    controls = {}
    for name, c in d["controls"].items():
        # Idempotent: the first pass wrote `passed`, the original wrote `ok`.
        passed = c.get("passed", c.get("ok"))
        controls[name] = {"passed": passed, "detail": c["detail"]}
    out = {
        "schema": "marfagenez.experiment-result.v2",
        "name": "exp21_crowding_law",
        "question": d.get("title") or d.get("question"),
        "arithmetic": d["arithmetic"],
        "conditions": d["conditions"],
        "rows": rows,
        "hashes": hashes,
        "controls": controls,
        "verdict": {
            "kind": "failed",
            "reason": (
                "EXPLAINED: the candidate crowding = (M - income)/maintenance "
                "predicts 3.0, 2.0 and 1.5 at maintenance 0.40, 0.60 and 0.80, "
                "and the measurement gives 1.925 at all three. The candidate was "
                "read off the maintenance = 0.60 point, so that point cannot "
                "count as evidence; the two other points miss by 1.5x and 1.4x. "
                "The `fires` control passed for the wrong reason: the metric "
                "moved only when every organism died at maintenance >= 1.00."
            ),
        },
        "limitations": d["limitations"] + [
            "maintenance 1.00 and 1.20 share one trace hash: both kill every "
            "organism, so the two parameter values are one arm, not two.",
        ],
        "what_this_does_not_prove": (
            "It does not show the crowding law is unknown, only that this "
            "candidate is not it. The law that survived is EXP-25's "
            "k_max = 1 + floor((M*r - maintenance - damage_rate)/income)."
        ),
    }
    json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
    print("rewritten:", path)


def upgrade_exp25(path):
    d = json.load(open(path))
    conds = d["conditions"]
    # Same reason as in upgrade_exp21: arms that die the same way share a hash
    # and are one arm.  The labels are kept, the hashes are collapsed.
    by_hash = {}
    for c in conds:
        by_hash.setdefault(c["trace_hash"], []).append(c["label"])
    hashes = {}
    for h, labels in by_hash.items():
        hashes["+".join(labels)] = h
    raw = d["controls"]
    if isinstance(raw, dict):
        # Already upgraded on an earlier pass.
        controls = {k: {"passed": v.get("passed"), "detail": v.get("detail")}
                    for k, v in raw.items()}
    else:
        controls = {c["name"]: {"passed": c["passed"], "detail": c["detail"]}
                    for c in raw}
    out = {
        "schema": "marfagenez.experiment-result.v2",
        "name": "exp25_crowding_law_v2",
        "question": d["question"],
        "arithmetic": d["arithmetic"],
        "conditions": conds,
        "rows": [{"label": c["label"], **c["result"]} for c in conds],
        "hashes": hashes,
        "controls": controls,
        "verdict": {
            "kind": "void",
            "reason": (
                "EXPLAINED: all three controls failed, so the measurement did "
                "not test the law. `fires` gave [1, 1, 2] on the arms the law "
                "was derived from, where it expected [1, 2, 2]. `silent` gave "
                "max_per_cell = 2 at n = cells = 40, because n = cells without "
                "--layout even is a random spawn with replacement and some cells "
                "start with two organisms. `specific` scored the new law 2/5 and "
                "the old floor(M*r/income) also 2/5, so the new law was not "
                "better than the one it was meant to replace."
            ),
        },
        "limitations": [
            "The law omits damage_rate, which is why income = 0.4 (< maintenance + damage = 0.62) gave zero survivors instead of 3 per cell.",
            "The law treats maintenance as a minimum share rather than a fixed per-step charge.",
            "The `silent` control measured the spawn, not the law.",
            "Void: no arm in this run can be used as evidence for or against the law.",
        ],
        "what_this_does_not_prove": (
            "It does not refute k_max = 1 + floor((M*r - maintenance)/income); it "
            "shows the run could not test it. The corrected law with damage_rate "
            "included is EXP-25 version 3 (results/crowding-law-law3)."
        ),
    }
    json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
    print("rewritten:", path)


if __name__ == "__main__":
    upgrade_exp21(f"{ROOT}/crowding-law/run-exp21.json")
    upgrade_exp25(f"{ROOT}/crowding-law-law2/run-exp25.json")
