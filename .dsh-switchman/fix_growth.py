import io

p = "laws/Medium/Growth.lean"
lines = io.open(p, encoding="utf-8").read().split("\n")
assert lines[30].startswith("  , , 25 000"), repr(lines[30])


lines[30] = "  `B = 3`, `\u03c3 = 0.3`, 25 000 steps, `N = 20 000`, `checks/tilt.py`:"
lines[38] = "  [VERIFIED: `python3 checks/tilt.py` -- PASS mean, PASS sd, PASS no-push;"
lines[39] = "  the same run is tabulated in `docs/FINDING-tilt-holds.md`]"
io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print("fixed")
