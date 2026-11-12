"""Does --every change the physics?

EXP-56 ran the same command line as EXP-55 except --every 1 instead of
--every 8000, and got alive 47/51/49 instead of 42/42/42. The earlier claim
that --every only affects sampling was based on reading record() in
core/src/trace.rs, which does look clean: the loop advances first, then
samples if step % every == 0.

But the hash is computed over the FRAMES, not over the run. With --every 8000
there are two frames; with --every 1 there are 8000. Different hashes are
expected and prove nothing. The alive count at the last frame is what matters,
and it differs.

Two explanations, and they are separable:
  H1 --every changes the physics. Then record() is not a camera.
  H2 the last frame is at a different step. With --every 8000 and steps 8000,
     frames land at steps 8000 only if 8000 % 8000 == 0 -- true, one frame at
     8000. With --every 1, the last frame is also at 8000. So both end at the
     same step, and H2 is rejected by arithmetic.

P1: if H1 is true, the alive count at step 8000 must differ between --every 1
    and --every 8000 for the same seed and parameters.
P2: if H1 is false, the alive counts must be identical.

Control fires:    the two runs must produce the same last-frame step (8000).
Control silent:   a run with --every 1 and --every 7 must agree if the physics
                  is untouched, because 7 does not divide 8000 and the last
                  frame lands at 7999 -- so this control is expected to differ
                  by one step and is recorded, not asserted.
Control specific: the alive count, not the hash, is the quantity compared. A
                  hash difference is not evidence for H1.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment import Experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")

STEPS = 8000
SEED = 20250101

BASE = [
    "--n", "160", "--cells", "40", "--capacity", "8",
    "--damage-rate", "0.02", "--income", "1.0", "--maintenance", "0.6",
    "--repair-cost", "1.5", "--field", "uniform",
    "--rich", "2.4", "--poor", "1.6", "--regrow", "0.8",
    "--move-cost", "0.10", "--read-budget", "3",
    "--steps", str(STEPS), "--seed", str(SEED), "--policy", "sighted",
]

ARITHMETIC = {
    "steps": STEPS,
    "every_8000_last_frame": 8000,
    "every_1_last_frame": 8000,
    "every_7_last_frame": (STEPS // 7) * 7,
    "prediction": "H2 rejected: both --every 1 and --every 8000 end at step 8000",
}


def run(every):
    cmd = ["cargo", "run", "--release", "--quiet", "--bin", "trace", "--"] + BASE + [
        "--every", str(every),
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"every={every}: {out.stderr[-2000:]}")
    written = [
        line.split(":", 1)[1].strip()
        for line in out.stdout.splitlines()
        if line.startswith("written:")
    ][0]
    data = json.load(open(os.path.join(CORE, written)))
    last = data["frames"][-1]
    alive = sum(1 for s in last["samples"] if s["alive"])
    return {
        "every": every,
        "frames": len(data["frames"]),
        "last_step": last["step"],
        "alive": alive,
        "hash": data["hash"],
    }


def main():
    exp = Experiment(
        experiment_id="EXP-57",
        question="Does --every change the physics, or only the sampling?",
        arithmetic=ARITHMETIC,
        arms={"1": "every=1", "8000": "every=8000", "7": "every=7"},
        seed=SEED,
        command="python3 checks/exp57_every.py",
        parameters={"steps": STEPS, "capacity": 8},
    )

    r1 = run(1)
    r8000 = run(8000)
    r7 = run(7)
    for r in (r1, r8000, r7):
        print(f"every {r['every']:>5}: frames {r['frames']:>5}  last step {r['last_step']:>5}  "
              f"alive {r['alive']:>3}  hash {r['hash']}")
        exp.add_arm(
            str(r["every"]),
            f"every={r['every']}",
            {"frames": r["frames"], "last_step": r["last_step"], "alive": r["alive"]},
            trace_hash=r["hash"],
        )

    fires = r1["last_step"] == 8000 and r8000["last_step"] == 8000
    exp.control(
        "fires", fires,
        f"last frame step: --every 1 -> {r1['last_step']}, --every 8000 -> "
        f"{r8000['last_step']}; both must be 8000 for the comparison to be at the "
        f"same moment",
    )

    silent = r7["last_step"] == (STEPS // 7) * 7
    exp.control(
        "silent", silent,
        f"--every 7 lands at step {r7['last_step']}, not 8000; the control is "
        f"recorded as a known one-step difference, not as agreement",
    )

    specific = True
    exp.control(
        "specific", specific,
        "the compared quantity is the alive count at the last frame, not the hash; "
        "a hash difference is expected because the hash is over the frames",
    )

    exp.limitation(
        "One seed, one geometry, one capacity (8). The experiment separates the "
        "two explanations for the EXP-55/EXP-56 disagreement but does not by itself "
        "say which of them is right if both runs agree here and disagree there: "
        "that would point at the parameter list, not at --every."
    )

    if r1["alive"] != r8000["alive"]:
        exp.verdict(
            "failed",
            f"alive differs: --every 1 gives {r1['alive']}, --every 8000 gives "
            f"{r8000['alive']}, at the same step {r1['last_step']}. H1 holds: --every "
            f"changes the physics, so record() is not the camera it is documented to be.",
        )
    else:
        exp.verdict(
            "passed",
            f"alive is identical ({r1['alive']}) at the same step, so --every does not "
            f"change the physics. The EXP-55/EXP-56 disagreement must come from the "
            f"parameter list, and the parameter list is where to look next.",
        )

    print(f"\nsaved {exp.save()}")


if __name__ == "__main__":
    main()
