import io
p = '/root/marfagenez/literature/dips/reports/dip-2026-11-23-46.md'
s = open(p, encoding='utf-8').read()
s = s.replace('| ~120 скачанных текстов из пакетного поиска |',
              '| 160 скачанных и просканированных текстов из пакетного поиска |')
open(p, 'w', encoding='utf-8').write(s)
print('ok', len(s))
