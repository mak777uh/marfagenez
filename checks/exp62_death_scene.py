"""What was the cell's level when the late death happened?

EXP-56 found two late deaths, at steps 3578 and 6804, both with taken = 0.500 and
damage = 0.000, each with exactly one mate on the cell. EXP-60 showed that on an
alternating field the shares are 1.2, then the leftover, then nothing, and that
the leftover is `nominal * regrow - income`.

On a uniform field at level 2.0 with regrow 0.8 the level a taker sees is
2.0 * 0.8 = 1.6, so the first taker takes min(1.6, 1.2) = 1.2 and leaves 0.4. The
second taker should take 0.4, not 0.5.

So either the level at the death was not 1.6, or the regrowth is not what the
arithmetic assumes, or taken is not min(cell, income). This prints the cell's
level in the frame of the death and in the frames around it, together with the
mate's share and energy, so that the 0.500 can be read off the field rather than
guessed.

It is a diagnostic: it prints and does not pass or fail.
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
    print(f"frames {len(frames)}, field length {len(frames[0]['field'])}")

    # Field statistics: what levels do cells actually carry?
    levels = {}
    for f in frames[500:]:
        for v in f["field"]:
            k = round(v, 3)
            levels[k] = levels.get(k, 0) + 1
    top = sorted(levels.items(), key=lambda kv: -kv[1])[:8]
    print("most common cell levels after step 500:")
    for v, n in top:
        print(f"    {v:.3f}  n {n}")

    # Find the deaths.
    deaths = []
    prev = None
    for f in frames:
        if prev is not None:
            for s_prev, s_now in zip(prev["samples"], f["samples"]):
                if s_prev["alive"] and not s_now["alive"]:
                    mates = [
                        t for t in prev["samples"]
                        if t["alive"] and t["cell"] == s_prev["cell"]
                        and t["slot"] != s_prev["slot"]
                    ]
                    deaths.append((f["step"], s_prev, mates, prev, f))
        prev = f

    late = [d for d in deaths if d[0] > 1000]
    print(f"\ndeaths: {len(deaths)} total, {len(late)} late")
    for step, s, mates, prev, f in late:
        cell = s["cell"]
        print(f"\nstep {step} slot {s['slot']} cell {cell}")
        print(f"  dying: energy {s['energy']:.4f} damage {s['damage']:.4f} "
              f"taken {s['taken']:.4f} dir {s['direction']}")
        print(f"  cell level in frame before the death: {prev['field'][cell]:.6f}")
        print(f"  cell level in the death frame:        {f['field'][cell]:.6f}")
        for m in mates:
            print(f"  mate slot {m['slot']}: energy {m['energy']:.4f} "
                  f"damage {m['damage']:.4f} taken {m['taken']:.4f} "
                  f"dir {m['direction']}")
        # What did the same cell look like 5 steps earlier?
        idx = frames.index(f)
        for back in (5, 2, 1):
            if idx - back >= 0:
                g = frames[idx - back]
                print(f"  {back} steps earlier: level {g['field'][cell]:.6f}, "
                      f"organisms on cell "
                      f"{sum(1 for t in g['samples'] if t['alive'] and t['cell'] == cell)}")


if __name__ == "__main__":
    main()
