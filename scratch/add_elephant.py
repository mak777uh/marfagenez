import pathlib

p = pathlib.Path('/root/marfagenez/docs/FINDING-320-price-rule-vs-derivative.md')
s = p.read_text(encoding='utf-8')
line = ('**Слону:** уточняет C-001 и C-002 в сторону осторожности: комплементарная нежёсткость подтверждается '
        '(цена ноль, когда ограничение не связывает), излом остаётся в a = I - s - r_max, но левое значение цены — '
        'ноль, не единица. Мост к химическому потенциалу не поднимается выше draft: наша сторона пересчитана, '
        'литературная не прочитана.')
marker = '## Что значит для утверждений'
if '**Слону:**' in s:
    print('already has the line')
else:
    assert marker in s
    s = s.replace(marker, line + '\n\n' + marker, 1)
    p.write_text(s, encoding='utf-8')
    print('added Слону line')
