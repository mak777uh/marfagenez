import pathlib

p = pathlib.Path('/root/marfagenez/laws/Medium/Capacity.lean')
s = p.read_text()

start = s.index('## The law, corrected 2026-11-12')
end = s.index('## What is proved')
mstart = s.index('## What the measurements say')
mend = s.index('namespace Medium')

keep_a = s[:start]
keep_b = s[end:mstart]
keep_c = s[mend:]

new_mid = (
    "## The law, corrected 2026-11-12 (measurement + sympy)\n"
    "\n"
    "The step is: every organism on the cell takes `min(left, income)` in turn, then\n"
    "the cell regrows once. If `k` organisms stand on the cell, the draw is `k*t`,\n"
    "so the fixed point of `cellStep M r (k*t)` is\n"
    "\n"
    "    c*(k) = M + k*t - k*t/r = M - k*t*(1-r)/r.\n"
    "\n"
    "The take of the `k`-th organism is `min(t, c*(k) - (k-1)*t)`, and it lives iff\n"
    "that is at least `maintenance`.\n"
    "\n"
    "Two old claims are wrong and are kept here only as history:\n"
    "\n"
    "* `c* = M - t/r` -- that is the *other* order of operations (regrow, then take,\n"
    "  `Medium/Feed.lean`). With take-then-regrow it is `M + t - t/r`.\n"
    "* `k_feed = 2.5` at `M = 2, r = 0.8, t0 = 0.8` -- the \"regrowth covers k full\n"
    "  portions\" story gives `M*r/t0 = 2.0` exactly, and the measurement agrees.\n"
    "  There was never a discrepancy.\n"
    "\n"
)

p.write_text(keep_a + new_mid + keep_b + keep_c)
print('ok')
