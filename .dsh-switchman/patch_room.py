import io

p = "checks/room_model.py"
s = io.open(p, encoding="utf-8").read()

old_init = "    pop = rng.normal(0.0, 0.5, N)\n    for _ in range(steps):"
new_init = "    pop = rng.uniform(-b, b, N)\n    for _ in range(steps):"
assert s.count(old_init) == 1
s = s.replace(old_init, new_init, 1)

old_tail = '    print("- The scaling (B/sigma)^2 is assumed, not derived here.")'
new_tail = (
    '    print("- The scaling (B/sigma)^2 is assumed, not derived here.")\n'
    '    print("- The population starts uniform on [-B, B]; starting from a point")\n'
    '    print("  would need many more steps, which is the timescale finding.")'
)
assert s.count(old_tail) == 1
s = s.replace(old_tail, new_tail, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("patched room_model.py: uniform start")
