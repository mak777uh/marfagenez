import pathlib

root = pathlib.Path('/root/marfagenez')
tick = chr(96)

# ---------------------------------------------------------------- docs/INDEX.md row
p = root / 'docs/INDEX.md'
lines = p.read_text(encoding='utf-8').splitlines(keepends=True)
row = ('| [`docs/KG-STUDY-2026-11-20.md`](KG-STUDY-2026-11-20.md) | **научная память в репозитории**: разбор '
       'существующих графов знания (OpenAlex, ORKG, OpenArx, ClaimRxiv, GraphRAG), что берём, схема и MVP | '
       'строишь связи между утверждениями |\n'
       '| [`kg/README`](../kg/kg.py) | **граф утверждений**: `kg/claims.jsonl` — источник истины, `kg/kg.py` — '
       'операции `map/find/show/expand/contradictions/trace` | нужен доступ к знанию, а не к файлам |\n')
for n, ln in enumerate(lines):
    if ln.startswith('| [`docs/CAMPAIGN-REPORT-2026-11-20.md`]'):
        lines.insert(n + 1, row)
        break
else:
    raise SystemExit('anchor not found')
p.write_text(''.join(lines), encoding='utf-8')
print('INDEX rows added')

# ---------------------------------------------------------------- 000-why: mention the graph
w = root / 'docs' / '007-where-we-are.md'
s = w.read_text(encoding='utf-8')
anchor = '## Открытые вопросы'
assert s.count(anchor) == 1
add = ('## Граф утверждений\n\n'
       'Знание хранится не только файлами: `kg/claims.jsonl` — **утверждения со связями**, а `kg/kg.py` даёт операции\n'
       '(`map`, `find`, `expand`, `contradictions`, `trace`). Схема и обоснование — `docs/KG-STUDY-2026-11-20.md`.\n\n'
       '**Правило:** `provenance = extracted` не даёт права ссылаться на утверждение как на факт.\n\n')
w.write_text(s.replace(anchor, add + anchor, 1), encoding='utf-8')
print('007 updated')

# ---------------------------------------------------------------- journal
lg = root / 'docs/agent/AGENT_LOG.md'
g = lg.read_text(encoding='utf-8')
e = ('\n### Цикл 320 — 2026-11-20 — ' + tick + '25e1ee3' + tick + ': научная память как граф утверждений\n\n'
     '- **Изучено:** OpenAlex, OpenAIRE, ORKG, SciX Agent, OpenArx, ClaimRxiv, EVI/PROV-O, GraphRAG/LightRAG/HippoRAG.\n'
     '- **Вывод:** большие системы — графы **публикаций**; единица «утверждение + контекст + свидетельство + статус» существует только как концепция и alpha-проект.\n'
     '- **Построено:** ' + tick + 'kg/' + tick + ' — ' + tick + 'claims.jsonl' + tick + ' (8 утверждений из кампании), ' + tick + 'kg.py' + tick + ' (build/map/find/show/expand/contradictions/trace), генерируемые ' + tick + 'INDEX.md' + tick + ' и ' + tick + 'graph.json' + tick + '.\n'
     '- **Проверено:** ' + tick + 'contradictions' + tick + ' нашёл опровергнутое ' + tick + '1/(m+1)' + tick + ' (C-007) и связь C-005 → C-007.\n'
     '- **Схема:** ' + tick + 'docs/KG-STUDY-2026-11-20.md' + tick + ' — происхождение и эпистемический статус как **разные оси**.\n')
lg.write_text(g + e, encoding='utf-8')
print('journal updated')
