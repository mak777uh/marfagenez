import io

p = "laws/Medium/Convergence.lean"
s = io.open(p, encoding="utf-8").read()
old = ("[VERIFIED: the same table is in `docs/FINDING-convergence.md`; the closed form\n"
       "`c -> c + r*(M - c) - t` with `M = 2`, `r = 0.2`, `t = 0.2` reproduces every row\n"
       "(2.000 -> 1.840 -> 1.808 and 0.200 -> 1.640 -> 1.928). The step itself is the\n"
       "Rust `field.rs` update, not a separate simulation.]")
new = ("[PARTIAL: the table is reproduced in `docs/FINDING-convergence.md` and the trace\n"
       "`results/oscillation/trace-sighted-1794434500.json` shows the same values, but no\n"
       "`checks/*.py` recomputes it. The naive closed form `c + r*(M - c) - t` with\n"
       "`M = 2`, `r = 0.2`, `t = 0.2` does NOT reproduce the poor cell (it gives\n"
       "0.200 -> 0.560 -> 0.848, not 1.640 -> 1.928); the real update takes the regrown\n"
       "field into account. Treat the numbers as a worked example, not a rerun.]")
assert s.count(old) == 1
io.open(p, "w", encoding="utf-8").write(s.replace(old, new))
print("convergence note corrected")
