import pathlib
import re
import sys

src = pathlib.Path('/mnt/c/Users/Admin/Downloads/Текстовый документ (5).txt')
lines = src.read_text(encoding='utf-8', errors='replace').splitlines()
print('TOTAL LINES', len(lines))

mode = sys.argv[1] if len(sys.argv) > 1 else 'map'
if mode == 'map':
    for i, ln in enumerate(lines):
        if re.match(r'^#{1,3}\s', ln) or re.match(r'^\*\*[А-ЯЁ0-9]', ln) or re.match(r'^\d+\.\s', ln):
            print(f'{i+1}: {ln[:110]}')
else:
    a = int(sys.argv[2])
    b = int(sys.argv[3])
    for i in range(a - 1, min(b, len(lines))):
        print(f'{i+1}: {lines[i]}')
