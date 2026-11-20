import pathlib
import re

src = pathlib.Path('/mnt/c/Users/Admin/Downloads/Текстовый документ (6).txt')
lines = src.read_text(encoding='utf-8', errors='replace').splitlines()
print('TOTAL LINES', len(lines))
print('CHARS', sum(len(l) for l in lines))

# structure map
for i, ln in enumerate(lines):
    if re.match(r'^#{1,4}\s', ln) or re.match(r'^\*\*[А-ЯЁA-Z0-9][^*]{0,80}\*\*$', ln) or re.match(r'^\d+\.\s+[А-ЯЁA-Z]', ln):
        print(f'{i+1}: {ln[:120]}')
