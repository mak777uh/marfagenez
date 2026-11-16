"""Report the two tails of the memory-versus-perception contrast separately.

`FINDING-159` reported one number - the fraction of environments where memory
beats the memoryless follower by more than a tenth of the control - and then
described the distribution from the mean, which is the wrong instrument for a
two-humped one. This script reads the stored record and reports both tails:

    win    dF >  delta      memory pays more than the threshold
    loss   dF < -delta      memory costs more than the threshold
    neutral                 the two arms are indistinguishable

Reporting only the win fraction says "memory is useful"; reporting only the mean
says "memory is harmful". Neither is true: on this prior the wins are small and
the losses are enormous, which is a third statement and the correct one.

    python3 checks/env_prior_tails.py [path-to-record]

Reads the newest `results/env-prior/run-*.json` by default. Writes nothing: it
is an analysis of a record, not a run.
"""

from __future__ import annotations

import glob
import json
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval: honest for proportions near 0 or 1 and for small n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def tails(rows: list[dict]) -> dict:
    n = len(rows)
    wins = [r["diff"] for r in rows if r["diff"] > r["delta"]]
    losses = [r["diff"] for r in rows if r["diff"] < -r["delta"]]
    neutral = n - len(wins) - len(losses)
    out = {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "neutral": neutral,
        "p_win": len(wins) / n if n else 0.0,
        "p_loss": len(losses) / n if n else 0.0,
        "win_interval": wilson(len(wins), n),
        "loss_interval": wilson(len(losses), n),
        "mean_diff": statistics.fmean([r["diff"] for r in rows]) if rows else 0.0,
    }
    if wins:
        out["win_median"] = statistics.median(wins)
        out["win_max"] = max(wins)
    if losses:
        out["loss_median"] = statistics.median(losses)
        out["loss_min"] = min(losses)
    return out


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        path = argv[1]
    else:
        found = sorted(glob.glob(os.path.join(ROOT, "results", "env-prior", "run-*.json")))
        if not found:
            print("no env-prior record: run `python3 checks/exp_env_prior.py` first")
            return 0
        path = found[-1]

    data = json.loads(open(path, encoding="utf-8").read())
    rows = data["points"]
    print(f"record: {os.path.relpath(path, ROOT)}  ({len(rows)} cases)")
    print()
    print(f"{'subset':<12} {'n':>4} {'wins':>5} {'losses':>6} {'neutral':>7} "
          f"{'mean':>9} {'win med':>8} {'loss med':>9}")

    def line(name: str, subset: list[dict]) -> None:
        t = tails(subset)
        wm = t.get("win_median")
        lm = t.get("loss_median")
        print(f"{name:<12} {t['n']:>4} {t['wins']:>5} {t['losses']:>6} "
              f"{t['neutral']:>7} {t['mean_diff']:>+9.1f} "
              f"{'—' if wm is None else f'{wm:+.0f}':>8} "
              f"{'—' if lm is None else f'{lm:+.0f}':>9}")

    line("all", rows)
    for cost in sorted({r["read_cost"] for r in rows}):
        line(f"cost={cost}", [r for r in rows if r["read_cost"] == cost])

    t = tails(rows)
    print()
    print(f"wins   {t['wins']:>3}/{t['n']} = {t['p_win']:.3f}  "
          f"Wilson 95% [{t['win_interval'][0]:.3f}, {t['win_interval'][1]:.3f}]")
    print(f"losses {t['losses']:>3}/{t['n']} = {t['p_loss']:.3f}  "
          f"Wilson 95% [{t['loss_interval'][0]:.3f}, {t['loss_interval'][1]:.3f}]")
    if "win_median" in t and "loss_median" in t:
        print(f"a win is worth {t['win_median']:+.0f} steps; "
              f"a loss costs {t['loss_median']:+.0f} — the tails are not the same size")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
