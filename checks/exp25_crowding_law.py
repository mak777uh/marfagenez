"""EXP-25: the crowding law, corrected.

    the k-th organism on a cell takes  min(income, M*r - (k-1)*income)
    it survives iff that is >= maintenance + damage_rate

so    k_max = 1 + floor((M*r - maintenance - damage_rate) / income)

WHY THE FIRST VERSION OF THIS LAW WAS WRONG (kept, because the mistake is the
lesson). The first version said the k-th organism survives iff its take is
>= maintenance. That is wrong about what maintenance is. Reading
`Organism::step` (core/src/organism.rs:148-182):

    energy += min(resource, income)        then clamp to world.capacity
    energy -= maintenance_cost
    damage += damage_rate
    repair: spend energy / repair_cost on damage, so the cost is exactly
            damage_rate whenever energy > 0
    die if energy <= 0 or structure <= 0

So the per-step ledger of every organism is

    net = taken - maintenance_cost - damage_rate

and `taken` is capped at `income`. An organism survives only if
`taken >= maintenance_cost + damage_rate`. Maintenance is a fixed per-step
cost that every organism pays independently, not a minimum share of the cell.

The first version also assumed `maintenance` could be varied freely. It cannot:
with income = 0.8 and damage_rate = 0.02, any maintenance >= 0.78 kills every
organism no matter how much food there is, because the cap is `income`.

WHERE THE SHAPE OF THE LAW COMES FROM. `Life::advance`
(core/src/life.rs:429-441) draws for every organism first and calls
`regrow_all()` once, after the loop, so on one cell the draws are sequential
with no regrowth between them. The cell is drained to zero and regrows from
zero to M*r, so the step starts at c = M*r. Measured: r = 0.80 gives
field = 1.600 = 2*0.8 on every cell.

The point of this experiment is that the law is checked on parameters that took
no part in deriving it. If it only reproduced the r-sweep it came from, it
would be the p = 0.2 mistake again (LESSONS.md).

Controls (PROTOCOL.md §2):
  fires    - the derivation arms must reproduce the known jump
  silent   - a cell with one organism must never show crowding, whatever r is
  specific - on the arms that did NOT take part in deriving it, the new law must
             beat the old floor(M*r/income)

Verdicts (PROTOCOL.md §4): passed / failed / void / insensitive by construction.
"""
import subprocess, json, os, glob, hashlib

TRACE = "/root/marfagenez/core/target/release/trace"
COREDIR = "/root/marfagenez/core"
OUT = "/root/marfagenez/results/crowding-law-law3"

DAMAGE = 0.02


def k_max_law(M, r, income, maintenance, damage=DAMAGE):
    """1 + floor((M*r - maintenance - damage)/income), clamped at 0."""
    budget = M * r - maintenance - damage
    if budget < 0:
        return 0
    return 1 + int(budget / income)


def run(M, r, income, maintenance, cells, n, steps, seed, policy="stay", even=False):
    cmd = [TRACE, "--policy", policy, "--steps", str(steps), "--every", str(steps),
           "--n", str(n), "--cells", str(cells), "--capacity", str(M),
           "--regrow", str(r), "--damage-rate", str(DAMAGE),
           "--income", str(income), "--maintenance", str(maintenance),
           "--repair-cost", "0.05", "--move-cost", "0.02", "--energy", str(M),
           "--field", "uniform", "--rich", str(2 * M), "--poor", "0.0",
           "--seed", str(seed)]
    if even:
        cmd += ["--layout", "even"]
    before = set(glob.glob(os.path.join(COREDIR, "results", policy, "*.json")))
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=COREDIR)
    if p.returncode != 0:
        raise RuntimeError(f"trace failed: {p.stderr[-800:]}")
    after = set(glob.glob(os.path.join(COREDIR, "results", policy, "*.json")))
    new = sorted(after - before, key=os.path.getmtime)
    path = new[-1] if new else max(after, key=os.path.getmtime)
    with open(path, "rb") as f:
        raw = f.read()
    d = json.loads(raw)
    frame = d["frames"][-1]
    alive = [s for s in frame["samples"] if s["alive"]]
    occ = {}
    for s in alive:
        occ[s["cell"]] = occ.get(s["cell"], 0) + 1
    return {
        "alive": len(alive),
        "cells_occupied": len(occ),
        "max_per_cell": max(occ.values()) if occ else 0,
        "field_min": round(min(frame["field"]), 6),
        "field_max": round(max(frame["field"]), 6),
        "trace_hash": hashlib.sha256(raw).hexdigest()[:16],
    }


# ---------------------------------------------------------------- arithmetic
# Every prediction is computed here, before any trace runs.
#
# The saturated setup is n = 8 x cells, so every cell starts with 8 organisms
# and the question is how many survive.
ARMS = [
    # derivation set: the r-sweep the law came from
    (2.0, 0.65, 0.8, 0.6),
    (2.0, 0.70, 0.8, 0.6),
    (2.0, 0.75, 0.8, 0.6),
    (2.0, 0.80, 0.8, 0.6),
    # new arms: none of these took part in deriving the law
    (2.0, 0.80, 0.7, 0.6),   # income down but still above maintenance+damage
    (2.0, 0.80, 0.9, 0.6),   # income up
    (3.0, 0.60, 0.8, 0.6),   # M up, r down: M*r = 1.8
    (2.5, 0.80, 0.8, 0.6),   # M up: M*r = 2.0
    (2.0, 1.00, 0.8, 0.6),   # r = 1: M*r = 2.0
    (4.0, 0.50, 0.8, 0.6),   # M up, r down: M*r = 2.0
]

CELLS = 40
N = 8 * CELLS
STEPS = 1500
SEED = 7

predicted = [k_max_law(M, r, i, m) for (M, r, i, m) in ARMS]

print("=== the law: k_max = 1 + floor((M*r - maintenance - damage)/income) ===")
print(f"{'M':<5}{'r':<6}{'inc':<6}{'mnt':<6}{'M*r':<7}{'pred':<6}{'meas':<6}{'alive':<7}{'field'}")
results = []
for (M, r, inc, mnt), pred in zip(ARMS, predicted):
    got = run(M, r, inc, mnt, CELLS, N, STEPS, SEED)
    results.append({"M": M, "r": r, "income": inc, "maintenance": mnt,
                    "predicted": pred, **got})
    print(f"{M:<5.2f}{r:<6.2f}{inc:<6.2f}{mnt:<6.2f}{M*r:<7.3f}{pred:<6}"
          f"{got['max_per_cell']:<6}{got['alive']:<7}{got['field_max']:.4f}")

# ---------------------------------------------------------------- controls
deriv = results[:4]
fires = [r["max_per_cell"] for r in deriv] == [r["predicted"] for r in deriv] \
        and len(set(r["max_per_cell"] for r in deriv)) > 1

# silent: one organism per cell can never crowd, at any r.
#
# The first version of this control used `n = cells` WITHOUT `--layout even`.
# That is not one organism per cell: the default spawn is random with
# replacement, so some cells start with two and `stay` never separates them.
# The control measured the spawn, not the law. `--layout even` is what makes
# the claim true by construction.
silent_arms = [run(2.0, r, 0.8, 0.6, CELLS, CELLS, STEPS, SEED, even=True)
               for r in (0.80, 0.95)]
silent = all(a["max_per_cell"] == 1 for a in silent_arms)

new_arms = results[4:]
law_hits = sum(1 for r in new_arms if r["predicted"] == r["max_per_cell"])
old_hits = sum(1 for r in new_arms
               if int(r["M"] * r["r"] / r["income"]) == r["max_per_cell"])
specific = law_hits > old_hits

print()
print(f"fires    : derivation arms {[(r['predicted'], r['max_per_cell']) for r in deriv]} -> {fires}")
print(f"silent   : n = cells gives {[a['max_per_cell'] for a in silent_arms]}, expected [1, 1] -> {silent}")
print(f"specific : new law {law_hits}/{len(new_arms)}, old law floor(M*r/income) "
      f"{old_hits}/{len(new_arms)} -> {specific}")

ok = all(r["predicted"] == r["max_per_cell"] for r in results)
if fires and silent and specific and ok:
    verdict_kind = "passed"
elif not (fires or silent or specific):
    verdict_kind = "void"
else:
    verdict_kind = "failed"

verdict = {
    "kind": verdict_kind,
    "reason": (
        f"The law predicted {sum(r['predicted'] == r['max_per_cell'] for r in results)}"
        f"/{len(results)} arms. On the {len(new_arms)} arms that did not take part in "
        f"deriving it the law scored {law_hits}/{len(new_arms)} and the previous "
        f"candidate floor(M*r/income) scored {old_hits}/{len(new_arms)}. "
        f"Controls: fires={fires}, silent={silent}, specific={specific}."
    ),
}

# ---------------------------------------------------------------- save
os.makedirs(OUT, exist_ok=True)
doc = {
    "schema": "marfagenez.experiment-result.v2",
    "name": "exp25_crowding_law",
    "question": ("Does k_max = 1 + floor((M*r - maintenance - damage)/income) hold "
                 "on parameters that did not take part in deriving it?"),
    "arithmetic": {
        "law": "k_max = 1 + floor((M*r - maintenance - damage_rate)/income)",
        "jump_r": "r = (income + maintenance + damage_rate)/M",
        "derivation": (
            "life.rs:429-441 draws for every organism, then regrow_all() once, so "
            "on one cell the draws are sequential with no regrowth between them. "
            "The cell is drained to zero and regrows to M*r, so the step starts at "
            "c = M*r and the k-th organism gets min(income, M*r - (k-1)*income). "
            "organism.rs:148-182 gives the per-step ledger "
            "net = taken - maintenance_cost - damage_rate, so a survivor needs "
            "taken >= maintenance_cost + damage_rate."
        ),
        "first_version_was_wrong": (
            "The first version omitted damage_rate and treated maintenance as a "
            "minimum share rather than a fixed per-step cost. It also assumed "
            "maintenance could be varied freely; with income = 0.8 and "
            "damage_rate = 0.02 any maintenance >= 0.78 kills everyone, because "
            "taken is capped at income."
        ),
        "saturation": f"n = {N} = 8 x {CELLS} cells, so every cell starts crowded",
        "damage_rate": DAMAGE,
        "predicted_k_max": predicted,
    },
    "conditions": [{"label": f"M={M} r={r} inc={i} mnt={m}",
                    "params": {"M": M, "r": r, "income": i, "maintenance": m,
                               "cells": CELLS, "n": N, "steps": STEPS, "seed": SEED,
                               "damage_rate": DAMAGE},
                    "result": {k: v for k, v in res.items()
                               if k not in ("M", "r", "income", "maintenance")},
                    "trace_hash": res["trace_hash"]}
                   for (M, r, i, m), res in zip(ARMS, results)]
                  + [{"label": f"silent: n=cells={CELLS}, layout=even, r={r}",
                      "params": {"M": 2.0, "r": r, "income": 0.8, "maintenance": 0.6,
                                 "cells": CELLS, "n": CELLS, "steps": STEPS,
                                 "seed": SEED, "damage_rate": DAMAGE,
                                 "layout": "even"},
                      "result": a, "trace_hash": a["trace_hash"]}
                     for r, a in zip((0.80, 0.95), silent_arms)],
    "controls": {
        "fires": {"passed": fires,
                  "detail": f"derivation arms give {[r['max_per_cell'] for r in deriv]}, "
                            f"predicted {[r['predicted'] for r in deriv]}"},
        "silent": {"passed": silent,
                   "detail": f"n = cells = {CELLS} (one organism per cell) gives "
                             f"{[a['max_per_cell'] for a in silent_arms]}, expected [1, 1]"},
        "specific": {"passed": specific,
                     "detail": f"on the {len(new_arms)} arms that did not take part in "
                               f"deriving it: new law {law_hits}/{len(new_arms)}, old law "
                               f"floor(M*r/income) {old_hits}/{len(new_arms)}"},
    },
    "hashes": {f"M{M}-r{r}-inc{i}-mnt{m}": res["trace_hash"]
               for (M, r, i, m), res in zip(ARMS, results)},
    "verdict": verdict,
    "limitations": [
        "The law assumes the cell is drained to zero each step, which needs "
        "k*income >= M*r. It says nothing about a population too sparse to keep "
        "a cell drained, and nothing about movement: a moving population "
        "redistributes and the per-cell count becomes a distribution, not a "
        "single number. It assumes damage_rate is small enough that repair is "
        "always affordable, which holds only while energy > 0. It does not "
        "predict how long a quasi-steady state lasts: measured energies at "
        "r = 0.70 drift down (1.399 -> 0.200 over 1200 steps).",
        "The silent control needs --layout even. Without it, n = cells is a "
        "random spawn with replacement and some cells start with two organisms, "
        "which `stay` never separates. The first version of this control "
        "measured the spawn, not the law.",
    ],
    "what_this_does_not_prove": (
        "It does not prove the Lean model matches the Rust model. It does not "
        "prove anything about a field that is not uniform. It does not prove "
        "that k_max is the only thing that matters for capacity -- measured "
        "`alive` varies with seed while max_per_cell stays fixed."
    ),
}

path = os.path.join(OUT, "run-exp25.json")
with open(path, "w") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)

print()
print("verdict:", verdict_kind)
print("saved:", path)
