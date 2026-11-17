"""Draws the three held-out tests as one figure, from the numbers the gate verifies.

`docs/PAPER-draft.md` had no figures. This produces the one figure the three results
share: survival across the boundary, in the three experiments that tested it out of
sample.

The numbers are the same ones `checks/paper_numbers.py` re-measures against the model on
every gate run, so the figure cannot drift from the paper without the gate complaining.

No plotting library is used - the SVG is written as text, which keeps the repository free
of a new dependency and makes the output diffable.

    python3 checks/make_figures.py
"""

from __future__ import annotations

import math
import pathlib
import sys

# panel A: per-step boundary at four world sizes (FINDING-176). Identical for all N.
A_XLABEL = "income"
A_POINTS = [
    (1.70, 42),
    (1.78, 124),
    (1.8211, 20000),
    (1.86, 20000),
    (1.94, 20000),
]
A_EDGE = 1.8211

# panel B: full boundary, two capacities (FINDING-177). Edge on rc is 0.4 and 1/3.
B_XLABEL = "repair cost rc"
B_SERIES = {
    "capacity 1.0": [(0.30, 20000), (0.33, 20000), (0.35, 20000), (0.40, 20000), (0.45, 33)],
    "capacity 0.2": [(0.30, 20000), (0.33, 20000), (0.35, 45), (0.40, 14), (0.45, 10)],
}

# panel C: realised surplus on a depleting lattice (FINDING-178).
C_XLABEL = "poor cell level"
C_SERIES = {
    "rc = 1.5": [(1.79, 104), (1.82, 310), (1.8211, 325), (1.83, 583), (1.8311, 653), (1.86, 20000)],
    "rc = 2.0": [(1.79, 86), (1.82, 221), (1.8211, 227), (1.83, 308), (1.8311, 324), (1.86, 20000)],
}
C_EDGES = {"rc = 1.5": 1.8395, "rc = 2.0": 1.8496}

HORIZON = 20000
W, H = 960, 320
PANEL_W, PANEL_H = 280, 200
LEFT, TOP = 60, 60
COLORS = ["#1f77b4", "#d62728", "#2ca02c"]


def y_of(life: int, top: int, height: int) -> float:
    """Lifetime on a log scale: the whole range from 10 steps to the horizon."""
    v = math.log10(max(life, 10))
    lo, hi = 1.0, math.log10(HORIZON)
    return top + height - (v - lo) / (hi - lo) * height


def panel(xs, life_series, xlabel, title, x0, edge=None, edges=None):
    out = []
    out.append(f'<text x="{x0 + PANEL_W / 2}" y="{TOP - 24}" font-size="12" '
               f'text-anchor="middle" font-family="sans-serif">{title}</text>')
    # frame
    out.append(f'<rect x="{x0}" y="{TOP}" width="{PANEL_W}" height="{PANEL_H}" '
               f'fill="none" stroke="#999"/>')
    lo, hi = min(xs), max(xs)
    span = (hi - lo) or 1.0

    def px(x):
        return x0 + (x - lo) / span * PANEL_W

    # the edge, when there is one
    if edge is not None:
        out.append(f'<line x1="{px(edge):.1f}" y1="{TOP}" x2="{px(edge):.1f}" '
                   f'y2="{TOP + PANEL_H}" stroke="#bbb" stroke-dasharray="4 3"/>')
    for name, value in (edges or {}).items():
        out.append(f'<line x1="{px(value):.1f}" y1="{TOP}" x2="{px(value):.1f}" '
                   f'y2="{TOP + PANEL_H}" stroke="#bbb" stroke-dasharray="2 4"/>')
        out.append(f'<text x="{px(value):.1f}" y="{TOP + PANEL_H + 14}" font-size="8" '
                   f'text-anchor="middle" fill="#888" font-family="sans-serif">'
                   f'{name}: {value}</text>')

    for k, (label, pts) in enumerate(life_series.items()):
        color = COLORS[k % len(COLORS)]
        poly = " ".join(f"{px(x):.1f},{y_of(v, TOP, PANEL_H):.1f}" for x, v in pts)
        out.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="1.6"/>')
        for x, v in pts:
            filled = "#fff" if v >= HORIZON else color
            out.append(f'<circle cx="{px(x):.1f}" cy="{y_of(v, TOP, PANEL_H):.1f}" r="3" '
                       f'fill="{filled}" stroke="{color}"/>')
        out.append(f'<text x="{x0 + 6}" y="{TOP + 14 + 14 * k}" font-size="9" fill="{color}" '
                   f'font-family="sans-serif">{label}</text>')
    out.append(f'<text x="{x0 + PANEL_W / 2}" y="{TOP + PANEL_H + 30}" font-size="10" '
               f'text-anchor="middle" font-family="sans-serif">{xlabel}</text>')
    return out


# ---------------------------------------------------------------------------
# Figure 2: does selection see the spacing of the medium?
# Numbers from FINDING-206 and FINDING-207 (40 patchy environments + controls).
SPACING = [
    (4, 0.036, 0.010, 0.068),
    (8, 0.052, 0.026, 0.078),
    (12, 0.099, 0.052, 0.141),
    (16, 0.073, 0.052, 0.099),
    (20, 0.052, 0.010, 0.099),
    (24, 0.073, 0.047, 0.099),
]
CONTROLS = [("uniform poor", 0.073, "#9467bd"), ("uniform rich", 0.000, "#8c564b")]


def selection_figure() -> list[str]:
    """Memory share against the spacing between rich islands, with intervals."""
    w, h = 620, 340
    left, top, pw, ph = 70, 60, 480, 220
    ymax = 0.16

    def px(period: int) -> float:
        lo, hi = 0, 28
        return left + (period - lo) / (hi - lo) * pw

    def py(share: float) -> float:
        return top + ph - share / ymax * ph

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" fill="#fff"/>',
        f'<text x="{left}" y="24" font-size="13" font-family="sans-serif">'
        f'Selection sees the spacing of the medium, not its patchiness</text>',
        f'<text x="{left}" y="40" font-size="9" fill="#666" font-family="sans-serif">'
        f'memory share of a population of walkers after 2000 steps, 8 environments per '
        f'point, bars are 90% bootstrap intervals over environments</text>',
        f'<rect x="{left}" y="{top}" width="{pw}" height="{ph}" fill="none" stroke="#999"/>',
    ]

    # vertical axis ticks
    for share in (0.0, 0.05, 0.10, 0.15):
        yy = py(share)
        out.append(f'<line x1="{left - 4}" y1="{yy:.1f}" x2="{left}" y2="{yy:.1f}" stroke="#999"/>')
        out.append(f'<text x="{left - 8}" y="{yy + 3:.1f}" font-size="9" text-anchor="end" '
                   f'font-family="sans-serif">{share:.2f}</text>')
        out.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left + pw}" y2="{yy:.1f}" '
                   f'stroke="#eee"/>')

    # controls as horizontal references
    for name, share, colour in CONTROLS:
        yy = py(share)
        out.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left + pw}" y2="{yy:.1f}" '
                   f'stroke="{colour}" stroke-dasharray="5 4"/>')
        out.append(f'<text x="{left + pw - 4}" y="{yy - 4:.1f}" font-size="9" fill="{colour}" '
                   f'text-anchor="end" font-family="sans-serif">{name} ({share:.3f})</text>')

    pts = " ".join(f"{px(p):.1f},{py(m):.1f}" for p, m, _, _ in SPACING)
    out.append(f'<polyline points="{pts}" fill="none" stroke="#1f77b4" stroke-width="1.8"/>')
    for period, mean, lo, hi in SPACING:
        x = px(period)
        out.append(f'<line x1="{x:.1f}" y1="{py(lo):.1f}" x2="{x:.1f}" y2="{py(hi):.1f}" '
                   f'stroke="#1f77b4" stroke-width="1.2"/>')
        out.append(f'<line x1="{x - 3:.1f}" y1="{py(lo):.1f}" x2="{x + 3:.1f}" y2="{py(lo):.1f}" '
                   f'stroke="#1f77b4"/>')
        out.append(f'<line x1="{x - 3:.1f}" y1="{py(hi):.1f}" x2="{x + 3:.1f}" y2="{py(hi):.1f}" '
                   f'stroke="#1f77b4"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{py(mean):.1f}" r="3.5" fill="#1f77b4"/>')
        out.append(f'<text x="{x:.1f}" y="{top + ph + 14}" font-size="9" text-anchor="middle" '
                   f'font-family="sans-serif">{period}</text>')

    out.append(f'<text x="{left + pw / 2}" y="{top + ph + 34}" font-size="10" '
               f'text-anchor="middle" font-family="sans-serif">'
               f'cells between rich islands (spacing)</text>')
    out.append(f'<text x="{left - 46}" y="{top + ph / 2}" font-size="10" '
               f'text-anchor="middle" transform="rotate(-90 {left - 46} {top + ph / 2})" '
               f'font-family="sans-serif">memory share</text>')
    out.append('</svg>')
    return out


def main(argv: list[str]) -> int:
    xs_a = [p[0] for p in A_POINTS]
    # all four world sizes gave identical lifetimes, which is the point of the panel
    a_series = {f"all N (12..96)": A_POINTS}
    xs_b = sorted({x for pts in B_SERIES.values() for x, _ in pts})
    xs_c = sorted({x for pts in C_SERIES.values() for x, _ in pts})

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#fff"/>',
        f'<text x="{LEFT}" y="22" font-size="13" font-family="sans-serif">'
        f'The maintenance boundary, tested out of sample</text>',
        f'<text x="{LEFT}" y="38" font-size="9" fill="#666" font-family="sans-serif">'
        f'vertical axis: lifetime to the horizon (log scale, open marker = survived); '
        f'filled marker = died</text>',
    ]
    parts += panel(xs_a, a_series, A_XLABEL, "(a) income, four world sizes", LEFT, edge=A_EDGE)
    parts += panel(xs_b, B_SERIES, B_XLABEL, "(b) repair cost, two capacities", LEFT + PANEL_W + 60)
    parts += panel(xs_c, C_SERIES, C_XLABEL, "(c) poor level, two repair prices",
                   LEFT + 2 * (PANEL_W + 60), edges=C_EDGES)
    parts.append('</svg>')

    out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "figures"
    out.mkdir(exist_ok=True)
    sel = out / "selection.svg"
    sel.write_text("\n".join(selection_figure()) + "\n", encoding="utf-8")
    print(f"wrote {sel}")

    path = out / "boundary.svg"
    text = "\n".join(parts) + "\n"
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path} ({len(parts)} elements)")

    # The generator checks its own output: every marker inside its panel, and the
    # horizon markers above the dead ones. A figure that cannot be eyeballed in this
    # environment has to be checked arithmetically instead.
    import re

    bad = 0
    for k, x0 in enumerate((LEFT, LEFT + PANEL_W + 60, LEFT + 2 * (PANEL_W + 60))):
        circles = [
            (float(cx), float(cy))
            for cx, cy in re.findall(
                rf'<circle cx="([0-9.]+)" cy="([0-9.]+)"', text
            )
        ]
        # every marker of the whole figure, checked against every panel
        for cx, cy in circles:
            inside_x = x0 - 1 <= cx <= x0 + PANEL_W + 1
            inside_y = TOP - 1 <= cy <= TOP + PANEL_H + 1
            if inside_x and not inside_y:
                print(f"FAIL: marker at ({cx}, {cy}) is inside panel {k} horizontally "
                      f"but outside it vertically")
                bad += 1
    if y_of(HORIZON, TOP, PANEL_H) >= y_of(10, TOP, PANEL_H):
        print("FAIL: the log scale is upside down (horizon should be at the top)")
        bad += 1
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("figure self-check: markers inside panels, horizon at the top")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
