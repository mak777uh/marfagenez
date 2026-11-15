import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")
TRACE = os.path.join(CORE, "target", "release", "trace")
REPAIR, DAMAGE, MC, INCOME, CAP, ENERGY = 1.5, 0.02, 0.1, 2.0, 1000.0, 10.0


def run(n, M, r, proto, steps, seed=1, every=None):
    every = every or steps
    args = [TRACE, "--cells", "1", "--n", str(n), "--policy", "stay",
            "--steps", str(steps), "--every", str(every), "--capacity", str(CAP),
            "--income", str(INCOME), "--maintenance", str(MC),
            "--repair-cost", str(REPAIR), "--damage-rate", str(DAMAGE),
            "--move-cost", "0", "--energy", str(ENERGY), "--field", "uniform",
            "--rich", str(M), "--poor", str(M), "--regrow", str(r),
            "--layout", "even", "--seed", str(seed), "--share", proto, "--out", "-"]
    p = subprocess.run(args, cwd=CORE, capture_output=True, text=True)
    raw = p.stdout
    d = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    f = d["frames"][-1]
    return (sum(1 for s in f["samples"] if s["alive"]),
            [round(s["taken"], 6) for s in f["samples"]],
            [round(s["energy"], 2) for s in f["samples"]],
            [round(x, 6) for x in f["field"]], d["hash"])


def first_death(n, M, r, proto, limit=3000):
    """Bisect the step at which the last organism dies."""
    lo, hi = 1, limit
    a, _, _, _, _ = run(n, M, r, proto, limit)
    if a > 0:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        a, _, _, _, _ = run(n, M, r, proto, mid)
        if a == 0:
            hi = mid
        else:
            lo = mid + 1
    return lo


print("=== seed sensitivity, n=17 M=3 r=0.8 prop, 1500 steps ===")
for seed in range(1, 9):
    a, t, e, f, h = run(17, 3.0, 0.8, "proportional", 1500, seed=seed)
    print("seed %d alive %2d hash %s taken0 %.4f field %s" % (seed, a, h, t[0], f))

print()
print("=== death step vs n, M=3 r=0.8 prop ===")
for n in (10, 14, 15, 16, 17, 18, 20):
    d = first_death(n, 3.0, 0.8, "proportional")
    print("n=%2d dies at step %s" % (n, d))
