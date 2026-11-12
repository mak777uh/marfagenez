"""Where did the latecomer come from?

EXP-62 found two late deaths, each an organism with 0.0749 energy that arrived on
a shared cell one step before dying, next to a mate with the full 7.37. It could
not say where the dying organism had been, because the trace recorded only the
current cell.

The trace now records `prev_cell` on every sample. This walks the dying slot
backwards through the frames and prints its cell, energy, damage, taken and
direction at every step of its last stretch, together with the level of each cell
it stood on and how many organisms shared it.

THE ARITHMETIC THAT MUST BE CHECKED FIRST

An organism loses `taken - 0.63` per step. To fall from the full 7.37 to 0.0749
it needs a total loss of 7.2951. If it spent every step on a cell it owns alone,
`taken = 1.2` and the loss is `+0.57` -- it would gain, not lose. So it must have
spent most of its life on cells where it got nothing.

At `taken = 0` the loss is 0.63 per step, so 7.2951 / 0.63 = 11.6 steps of total
starvation. At `taken = 0.5` the loss is 0.13, so 56 steps. The path will show
which.

WHAT THIS DOES NOT DO

It does not explain why the field had no free cell for it. That is a question
about the density of the population relative to the number of cells, and it needs
its own measurement.
"""

import json
import os
import subprocess
import sys
import time

CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
TRACE = os.path.join(CORE, "target", "release", "trace")

INCOME = 1.2
MAINT = 0.6
REPAIR = 1.5
MOVE = 0.10
STEPS = 8000
SEED = 20250101
N = 160
CELLS = 40
COST = MAINT + 0.02 * REPAIR


def run(rich, poor, steps, every):
    time.sleep(1.1)
    cmd = [
        TRACE,
        "--n", str(N), "--cells", str(CELLS),
        "--rich", str(rich), "--poor", str(poor),
        "--regrow", "0.8",
        "--income", str(INCOME),
        "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--damage-rate", "0.02",
        "--steps", str(steps), "--every", str(every),
        "--seed", str(SEED),
        "--policy", "sighted",
        "--read-budget", "3",
        "--capacity", "8",
        "--field", "uniform",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr[-2000:])
    written = [
        line.split(":", 1)[1].strip()
        for line in out.stdout.splitlines()
        if line.startswith("written:")
    ][0]
    path = os.path.join(CORE, written)
    if os.path.exists(path) and os.path.getmtime(path) < time.time() - 5:
        raise SystemExit(f"refusing a stale file: {path}")
    return json.load(open(path))


def main():
    data = run(2.4, 1.6, STEPS, 1)
    frames = data["frames"]

    # Find the late deaths and the slot that died.
    deaths = []
    prev = None
    for f in frames:
        if prev is not None:
            for a, b in zip(prev["samples"], f["samples"]):
                if a["alive"] and not b["alive"] and f["step"] > 1000:
                    deaths.append((f["step"], a["slot"]))
        prev = f

    print(f"late deaths: {deaths}")

    for step, slot in deaths:
        print(f"\n{'='*70}\nslot {slot} died at step {step}")
        # Walk backwards from the death frame.
        idx = next(i for i, f in enumerate(frames) if f["step"] == step)
        rows = []
        for back in range(1, 200):
            i = idx - back
            if i < 0:
                break
            f = frames[i]
            s = next((x for x in f["samples"] if x["slot"] == slot), None)
            if s is None or not s["alive"]:
                break
            mates = [
                x for x in f["samples"]
                if x["alive"] and x["cell"] == s["cell"] and x["slot"] != slot
            ]
            rows.append({
                "step": f["step"],
                "cell": s["cell"],
                "prev_cell": s.get("prev_cell"),
                "energy": s["energy"],
                "damage": s["damage"],
                "taken": s["taken"],
                "direction": s["direction"],
                "level": f["field"][s["cell"]],
                "mates": len(mates),
                "mate_energies": [round(m["energy"], 2) for m in mates],
            })
        rows.reverse()

        print(f"{'step':>5} {'cell':>4} {'prev':>4} {'dir':>3} {'energy':>8} "
              f"{'dmg':>6} {'taken':>6} {'level':>6} {'mates':>5}")
        for r in rows:
            print(f"{r['step']:>5} {r['cell']:>4} {str(r['prev_cell']):>4} "
                  f"{r['direction']:>3} {r['energy']:>8.4f} {r['damage']:>6.4f} "
                  f"{r['taken']:>6.3f} {r['level']:>6.3f} {r['mates']:>5} "
                  f"{r['mate_energies']}")

        # Summarise the path.
        if rows:
            moved = sum(1 for r in rows if r["prev_cell"] != r["cell"])
            zero_share = sum(1 for r in rows if r["taken"] < 0.01)
            shared = sum(1 for r in rows if r["mates"] > 0)
            total_loss = rows[-1]["energy"] - rows[0]["energy"]
            print(f"\n  {len(rows)} steps traced, moved {moved} times, "
                  f"took nothing on {zero_share}, shared the cell on {shared}")
            print(f"  energy {rows[0]['energy']:.4f} -> {rows[-1]['energy']:.4f} "
                  f"(change {total_loss:+.4f})")


if __name__ == "__main__":
    main()
