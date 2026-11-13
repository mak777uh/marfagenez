import pathlib

p = pathlib.Path('/root/marfagenez/laws/Medium/Capacity.lean')
lines = p.read_text().split('\n')
depth = 0
for i, line in enumerate(lines):
    j = 0
    start_depth = depth
    while j < len(line):
        if line.startswith('/-', j):
            depth += 1
            j += 2
            continue
        if line.startswith('-/', j):
            depth -= 1
            j += 2
            continue
        j += 1
    if start_depth == 0 and depth > 0:
        print('OPEN at', i + 1, '->', line[:80])
    if start_depth > 0 and depth == 0:
        print('CLOSE at', i + 1, '->', line[:80])
print('final', depth)
