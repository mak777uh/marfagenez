"""Where does the Rust take sequence differ from the mirror?

Dumps the actual per-organism energy after each of the first steps, using the
trace binary's per-frame samples, for one cell with k organisms.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/root/marfagenez")
TRACE = ROOT / "core" / "target" / "release" / "trace"


def frames(cells, n, M, r, t, maintenance, damage, steps, every=1):
    cmd = [str(TRACE), "--cells", str(cells), "--n", str(n),
           "--policy", "stay", "--steps", str(steps), "--every", str(every),
           "--capacity", "1000", "--income", str(t),
           "--maintenance", str(maintenance), "--repair-cost", "1.5",
           "--damage-rate", str(damage), "--move-cost", "0", "--energy", "10",
           "--field", "uniform", "--rich", str(M), "--poor", str(M),
           "--regrow", str(r), "--layout", "even", "--seed", "1"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT / "core"))
    if res.returncode != 0:
        print("TRACE FAILED", res.returncode, res.stderr[-500:])
        sys.exit(1)
    written = None
    for line in res.stdout.splitlines():
        if line.startswith("written:"):
            written = Path(line.split(":", 1)[1].strip())
    if written is None or not written.is_absolute():
        written = ROOT / "core" / written
    return json.loads(written.read_text())["frames"]


fs = frames(1, 5, 2.0, 0.8, 0.6, 0.1, 0.0, 12)
print("frame  field   energies")
for i, fr in enumerate(fs[:12]):
    fld = fr.get("field") or fr.get("cells")
    en = [round(s["energy"], 3) for s in fr["samples"]]
    al = [s["alive"] for s in fr["samples"]]
    print("%3d  %s  %s  %s" % (i, fld, en, al))
sys.exit(0)
