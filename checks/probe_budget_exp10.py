import json
import subprocess

BIN = "./target/release/trace"
COMMON = [
    "--policy", "sighted", "--steps", "2000", "--every", "2000",
    "--seed", "20250101", "--cells", "40", "--field", "uniform", "--rich", "2.0", "--poor", "0.2",
    "--capacity", "10", "--move-cost", "0.1", "--maintenance", "0.6",
    "--repair-cost", "1.5", "--damage-rate", "0.02", "--income", "0.8",
    "--memory-life", "100000",
]

print(f"{'budget':>6} {'n':>5} {'alive':>6} {'occ':>5} {'max':>4} {'crowd':>7}")
for budget in (0, 3):
    for n in (40, 80, 120, 160):
        cmd = [BIN, *COMMON, "--n", str(n), "--read-budget", str(budget)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            print(f"{budget:>6} {n:>5}  REFUSED")
            continue
        path = [ln.split("written:", 1)[1].strip()
                for ln in p.stdout.splitlines() if ln.startswith("written:")][-1]
        d = json.load(open(path))
        s = d["frames"][-1]["samples"]
        al = [x for x in s if x["alive"]]
        cells = [x["cell"] for x in al]
        occ = len(set(cells))
        mx = max((cells.count(c) for c in set(cells)), default=0)
        crowd = len(al) / occ if occ else 0.0
        print(f"{budget:>6} {n:>5} {len(al):>6} {occ:>5} {mx:>4} {crowd:>7.3f}")
