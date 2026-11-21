# tools/ — внешние инструменты, которые мы написали сами

Здесь только **наш** код, который ходит наружу. Всё стороннее (CLI-поисковики, навыки) живёт вне репозитория:
`~/.dsh/tools/sci-venv` и `~/.dsh/skills/`.

| файл | что делает | как запускать |
|---|---|---|
| `semantic_search.py` | семантический канал: пул из OpenAlex → локальные эмбеддинги BGE-small (FastEmbed/ONNX) → ранжирование по косинусу с провенансом | см. ниже |

## semantic_search.py

```powershell
$env:OPENALEX_API_KEY   = (Get-Content "$env:USERPROFILE\.dsh\secrets\openalex.key" -Raw).Trim()
$env:FASTEMBED_CACHE_PATH = "$env:USERPROFILE\.dsh\tools\models"

& "$env:USERPROFILE\.dsh\tools\sci-venv\Scripts\python.exe" tools\semantic_search.py `
    "a system that continuously produces the components that produce it" `
    --seeds "organisational closure;autopoiesis;closure of constraints" --top 8
```

- `--seeds` — фильтр области: 3–5 канонических терминов. Полисемичные (`repair`, `maintenance`, `structure`)
  тянут инженерию и социологию вместо биологии — проверено, см. `docs/SCIENCE-STACK.md` §6.
- `--from-file` — ранжировать готовый JSON вместо запроса в OpenAlex.
- Ключей не требует; модель скачивается один раз (~90 МБ) в `FASTEMBED_CACHE_PATH`.
- Ограничение: это re-ranker пула (20–50 записей на seed), а не поиск по всем публикациям.

## Правила для этого каталога

1. Один файл — одна задача; никаких «утилит на все случаи».
2. Инструмент печатает провенанс (DOI, год, источник), а не только результат.
3. Если инструмент нужен гейту, он живёт в `checks/`, а не здесь.
