import pathlib

root = pathlib.Path('/root/marfagenez')

r = root / 'kg' / 'eval' / 'README.md'
lines = r.read_text(encoding='utf-8').splitlines(keepends=True)
add = '''### Вердикт, а не отчёт

`score.py` возвращает три исхода и код 0 только для `PASS`:

| вердикт | значение |
|---|---|
| `INVALID` | покрытие неполное (нужно 28 вопросов × 3 сида), есть дубли или неизвестные id, либо assert-пункты не оценены судьёй |
| `FAIL` | покрытие полное, но цель не достигнута (recall, precision, токены, файлы, reject-пункт, незаземлённое число, цитата отсутствующего) |
| `PASS` | всё измеримое в норме и судья оценил assert-пункты |

`--report-only` печатает отчёт и выходит с нулём: это для отладки, а не для зачёта.
`expected_absent` **не** входит в список разрешённых ссылок: цитирование отсутствующего штрафуется.

'''
if 'Вердикт, а не отчёт' not in ''.join(lines):
    for i, ln in enumerate(lines):
        if ln.strip() == '```bash' and 'score.py' in ''.join(lines[i:i + 3]):
            lines.insert(i, add)
            break
    else:
        raise SystemExit('README anchor not found')
    r.write_text(''.join(lines), encoding='utf-8')
    print('eval README documents the verdict')
else:
    print('README already documents it')

plan = root / 'docs' / 'AUTONOMY-PLAN.md'
q = plan.read_text(encoding='utf-8')
marker2 = '## §6. Инструкция автономной работы'
progress = '''### Отметки выполнения

**2026-11-21, круг 1 — сделано:**

- [x] D6 — резолв `FINDING-<num>` без префиксного glob; подложенный `FINDING-14` не разрешается, `FINDING-320` — да.
- [x] D7 — гейт запускает `check --refs`; подложенная битая ссылка даёт код 1.
- [x] D8 — `regress.py` сравнивает канонические объекты целиком; подложенная правка текста ловится.
- [x] D9 — `score.py`: покрытие 28×3, дубли, `PASS/FAIL/INVALID`, `rubric_pending` в отчёте, `expected_absent` вне `allow`.
- [x] D4 — `built_at` из текущего времени.
- [x] D13 — `atlas` ведёт десятью линиями, K1–K5 остаются алиасами.

**Дальше (круг 2):** D10 (неравные маргиналы в `kappa_sim`), D11 (очередь `human_confirmed`), D15 (устаревшие числа
`CLAIMS.md`).

'''
if 'Отметки выполнения' not in q:
    q = q.replace(marker2, progress + marker2, 1)
    plan.write_text(q, encoding='utf-8')
    print('plan progress updated')

st = root / 'docs' / 'agent' / 'AGENT_STATE.md'
state = st.read_text(encoding='utf-8')
anchor = '- **Мосты и разрывы:**'
extra = ('- **Экзамен выдаёт вердикт:** `kg/eval/score.py` — `PASS/FAIL/INVALID` и код 0 только для `PASS`; '
         'подложенные случаи в `checks/eval_verdict.py`; подложенные дефекты графа — `checks/planted_defects.py` '
         '(оба диагностические, не в гейте).\n'
         '- **Резолв находок точный:** `FINDING-<num>.md` или `FINDING-<num>-*.md`; префиксный glob снят.\n')
if 'Экзамен выдаёт вердикт' not in state:
    state = state.replace(anchor, extra + anchor, 1)
    st.write_text(state, encoding='utf-8')
    print('state updated')

idx = root / 'docs' / 'INDEX.md'
it = idx.read_text(encoding='utf-8').splitlines(keepends=True)
row = ('| [`docs/FINDING-321-exam-verdict.md`](FINDING-321-exam-verdict.md) | **экзамен получил вердикт**: '
       'покрытие, дубли, `PASS/FAIL/INVALID`, штраф за цитирование отсутствующего | проверяем экзамен |\n')
if 'FINDING-321' not in ''.join(it):
    for n, ln in enumerate(it):
        if ln.startswith('| [`docs/FINDING-320-price-rule-vs-derivative.md`]'):
            it.insert(n + 1, row)
            break
    else:
        raise SystemExit('INDEX anchor not found')
    idx.write_text(''.join(it), encoding='utf-8')
    print('INDEX row added')
