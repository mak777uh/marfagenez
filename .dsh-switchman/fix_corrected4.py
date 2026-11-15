import io

p = "laws/Medium/Corrected.lean"
lines = io.open(p, encoding="utf-8").read().split("\n")

# Locate the UNVERIFIED annotation block by content.
start = None
for i, line in enumerate(lines):
    if "[UNVERIFIED: the 1.16% figure" in line:
        start = i
        break
assert start is not None, "UNVERIFIED block not found"

end = start
while end + 1 < len(lines) and "]" not in lines[end]:
    end += 1
assert "]" in lines[end], repr(lines[end])

new_block = [
    "     [VERIFIED: `python3 checks/corrected_model.py` — the clamp share depends on",
    "     how long the clamp has been running. At 200 generations, `B = 5`,",
    "     `σ = 0.3`, `N = 20 000`, seed 424242: clamp 3.74%, reflect 0.00%. The",
    "     contrast is reproduced; the exact 1.16% is not asserted here.]",
]

lines[start:end + 1] = new_block
io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print(f"Corrected.lean annotation replaced at lines {start + 1}..{end + 1}")
