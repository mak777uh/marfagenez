import io

p = "laws/Medium/Child.lean"
lines = io.open(p, encoding="utf-8").read().split("\n")

# 1-based line numbers from the file as read above.
header_idx = 20 - 1
expect_header = "  | B | steps | measured spread | `B/√3` | ratio |"
assert lines[header_idx].strip() == expect_header.strip(), repr(lines[header_idx])

new_block = [
    "  | B | steps | measured spread | `B/√3` | ratio |",
    "  |---|-------|-----------------|--------|-------|",
    "  | 0.5 | 0 | 0.289 | 0.289 | 1.003 |",
    "  | 1.0 | 1 | 0.577 | 0.577 | 1.000 |",
    "  | 2.0 | 4 | 1.150 | 1.155 | 0.996 |",
    "  | 3.0 | 9 | 1.714 | 1.732 | 0.990 |",
    "  | 5.0 | 25 | 2.865 | 2.887 | 0.992 |",
    "  | 8.0 | 64 | 4.470 | 4.619 | 0.968 |",
    "",
    "  [VERIFIED: `python3 checks/room_model.py` — `μ = 0.05`, `σ = 1`, `N = 20 000`,",
    "  seed 5001, uniform start on `[-B, B]`, `steps = (B/σ)²`. PASS within 5% of",
    "  `B/√3` at every half-width. The run length here is the filling time, not a",
    "  fixed budget: the earlier table's `2 006 … 3 423` steps were not reproduced by",
    "  any script, and at 64 steps the `B = 8` row reads 0.968, not 0.998.]",
]

# Replace lines 20..26 (header, separator, 6 rows) = 8 lines.
assert lines[26].strip().startswith("| 8.0 |"), repr(lines[26])
lines[header_idx:26 + 1] = new_block

io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print("Child.lean table replaced")
