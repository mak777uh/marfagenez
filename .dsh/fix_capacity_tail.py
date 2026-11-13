import pathlib

p = pathlib.Path('/root/marfagenez/laws/Medium/Capacity.lean')
lines = p.read_text().split('\n')
idx = lines.index('namespace Medium')
print('namespace at index', idx, '-> line', idx + 1)
print([repr(l) for l in lines[idx - 4:idx + 1]])
lines.insert(idx, '-/')
p.write_text('\n'.join(lines))
print('inserted')
