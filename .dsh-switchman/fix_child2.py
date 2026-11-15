import io

p = "laws/Medium/Child.lean"
lines = io.open(p, encoding="utf-8").read().split("\n")

# Locate the table by content, not by line number.
start = None
for i, line in enumerate(lines):
    if line.strip() == "| B | steps | measured spread | `B/√3` | ratio |":
        start = i
        break
assert start is not None, "table header not found"

end = start
while end + 1 < len(lines) and lines[end + 1].strip().startswith("|"):
    end += 1
assert lines[end].strip().startswith("| 8.0 |"), repr(lines[end])

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

lines[start:end + 1] = new_block
io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print(f"Child.lean table replaced at lines {start + 1}..{end + 1}")
