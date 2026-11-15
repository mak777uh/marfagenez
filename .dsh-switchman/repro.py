import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")
TRACE = os.path.join(CORE, "target", "release", "trace")


def alive_at(n, M, r, proto, steps, seed=1):
    args = [TRACE, "--cells", "1", "--n", str(n), "--policy", "stay",
            "--steps", str(steps), "--every", str(steps), "--capacity", "1000",
            "--income", "2.0", "--maintenance", "0.1", "--repair-cost", "1.5",
            "--damage-rate", "0.02", "--move-cost", "0", "--energy", "10",
            "--field", "uniform", "--rich", str(M), "--poor", str(M),
            "--regrow", str(r), "--layout", "even", "--seed", str(seed),
            "--share", proto, "--out", "-"]
    p = subprocess.run(args, cwd=CORE, capture_output=True, text=True)
    raw = p.stdout
    d = raw[raw.find("{"):raw.rfind("}") + 1]
    import json
    j = json.loads(d)
    f = j["frames"][-1]
    return sum(1 for s in f["samples"] if s["alive"]), f["samples"][0]["energy"]


for n in (15, 16, 17, 18):
    for steps in (1500, 2050, 2100, 2200, 3000):
        a, e = alive_at(n, 3.0, 0.8, "proportional", steps)
        print("n=%2d steps=%5d alive=%2d e0=%8.4f" % (n, steps, a, e))
    print()
