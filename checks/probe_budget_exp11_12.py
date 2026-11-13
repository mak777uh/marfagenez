import json
import subprocess

BIN = "./target/release/trace"


def run(args):
    p = subprocess.run([BIN, *args], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    path = [ln.split("written:", 1)[1].strip()
            for ln in p.stdout.splitlines() if ln.startswith("written:")][-1]
    d = json.load(open(path))
    s = d["frames"][-1]["samples"]
    al = [x for x in s if x["alive"]]
    cells = [x["cell"] for x in al]
    occ = len(set(cells))
    mx = max((cells.count(c) for c in set(cells)), default=0)
    fields = d["frames"][-1]["field"]
    return {
        "alive": len(al), "occ": occ, "max": mx,
        "crowd": round(len(al) / occ, 3) if occ else 0.0,
        "spread": round(max(fields) - min(fields), 4) if fields else 0.0,
        "mean_field": round(sum(fields) / len(fields), 4) if fields else 0.0,
    }


BASE = [
    "--policy", "sighted", "--steps", "2000", "--every", "2000",
    "--seed", "20250101", "--cells", "40", "--capacity", "10",
    "--move-cost", "0.1", "--maintenance", "0.6", "--repair-cost", "1.5",
    "--damage-rate", "0.02", "--income", "0.8", "--memory-life", "100000",
]

print("EXP-11: gradient vs alternating vs uniform, n=80")
for field in ("uniform", "alternating", "gradient"):
    r = run([*BASE, "--n", "80", "--field", field, "--read-budget", "3"])
    print(f"  {field:>12}: {r}")

print()
print("EXP-12: capacity curve, uniform field")
for n in (40, 60, 80, 100, 120, 160):
    r = run([*BASE, "--n", str(n), "--field", "uniform", "--rich", "2.0", "--poor", "0.2", "--read-budget", "3"])
    print(f"  n={n:>3}: {r}")

print()
print("EXP-12: capacity curve, alternating field")
for n in (40, 60, 80, 100, 120, 160):
    r = run([*BASE, "--n", str(n), "--field", "alternating", "--read-budget", "3"])
    print(f"  n={n:>3}: {r}")
