"""Семьи экспериментов: сжать сотни прогонов в семейства, не теряя исходные записи.

Задача `P9-experiment-families`. Семейство = (имя эксперимента, канонические параметры).
Прогоны внутри семейства — повторы одного и того же опыта; они сохраняются все.

Запуск:
    python3 tools/exp_families.py           # печать сводки
    python3 tools/exp_families.py --write   # обновить docs/FAMILIES-DRAFT.md
"""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"
OUT = ROOT / "docs" / "FAMILIES-DRAFT.md"

RUN_RE = re.compile(r"^X-(?P<exp>.+?)-run-(?P<ts>.+)$")


def load_experiments() -> list[dict]:
    out = []
    for line in NODES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n = json.loads(line)
        if n.get("kind") == "experiment":
            out.append(n)
    return out


def exp_name(node: dict) -> str:
    m = RUN_RE.match(node["id"])
    if m:
        return m.group("exp")
    return node["id"].split("-run-")[0]


def params_key(node: dict) -> str:
    raw = node.get("context", {}).get("parameters", "")
    try:
        return json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False)
    except (ValueError, TypeError):
        return raw


def verdict(node: dict) -> str:
    """Вердикт — только passed/failed; `void` и `not applicable` вердиктами НЕ являются.

    Раньше они попадали в «unknown» и считались расхождением, из-за чего число «конфликтных»
    семейств было завышено. Это была ошибка нашего же подсчёта, а не свойство данных.
    """
    text = node.get("text", "")
    if text.endswith("passed"):
        return "passed"
    if text.endswith("failed"):
        return "failed"
    if text.endswith("void") or text.endswith("not applicable"):
        return "no-verdict"
    return "unknown"


def family_id(exp: str, key: str) -> str:
    h = hashlib.sha256((exp + "|" + key).encode("utf-8")).hexdigest()[:8]
    return f"{exp}-{h}"


def collect(nodes: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for n in nodes:
        groups[(exp_name(n), params_key(n))].append(n)
    return groups


def main(argv: list[str]) -> int:
    write = "--write" in argv
    nodes = load_experiments()
    groups = collect(nodes)

    sizes = collections.Counter(len(v) for v in groups.values())
    def is_conflict(runs: list[dict]) -> bool:
        kinds = {verdict(n) for n in runs}
        return "passed" in kinds and "failed" in kinds

    mixed = {k: v for k, v in groups.items() if is_conflict(v)}
    singles = [k for k, v in groups.items() if len(v) == 1]
    top = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:5]

    lines: list[str] = []
    a = lines.append
    a("# Семьи экспериментов: черновик (сгенерировано `tools/exp_families.py`)")
    a("")
    a("**Что это.** Предложение, как сжать записи прогонов в семейства, **не удаляя** ни одного прогона.")
    a("Семейство = имя эксперимента + канонические параметры (JSON с сортированными ключами).")
    a("")
    a("## Числа")
    a("")
    a(f"- прогонов: **{len(nodes)}**")
    a(f"- разных имён экспериментов: **{len({exp_name(n) for n in nodes})}**")
    a(f"- семейств (имя + параметры): **{len(groups)}**")
    a(f"- семейств из одного прогона: **{len(singles)}**")
    a(f"- семейств, где РАЗНЫЕ вердикты (passed и failed) при одинаковых параметрах: **{len(mixed)}**")
    a(f"- семейств без вердикта (void / not applicable) — не конфликт: "
      f"**{len({k for k, v in groups.items() if any(verdict(n) == 'no-verdict' for n in v)})}**")
    a("")
    a("### Размеры семейств")
    a("")
    a("| прогонов в семействе | сколько семейств |")
    a("|---|---|")
    for size, count in sorted(sizes.items()):
        a(f"| {size} | {count} |")
    a("")
    a("### Крупнейшие семейства (повторы одного и того же опыта)")
    a("")
    a("| эксперимент | повторов | параметры |")
    a("|---|---|---|")
    for (exp, key), runs in top:
        short = key if len(key) <= 110 else key[:107] + "…"
        a(f"| `{exp}` | {len(runs)} | `{short}` |")
    a("")
    a("## Семейства с расходящимися вердиктами")
    a("")
    if mixed:
        a("Одинаковые параметры — разные вердикты. Это либо недетерминизм прогона, либо разные версии кода")
        a("(`commit unknown` в условиях). Пока не разрешено, такие семейства **нельзя** считать семейством")
        a("с одним выводом.")
        a("")
        a("| эксперимент | прогонов | вердикты | пример id |")
        a("|---|---|---|---|")
        for (exp, key), runs in sorted(mixed.items(), key=lambda kv: -len(kv[1])):
            verdicts = collections.Counter(verdict(n) for n in runs)
            pretty = ", ".join(f"{v}×{c}" for v, c in sorted(verdicts.items()))
            a(f"| `{exp}` | {len(runs)} | {pretty} | `{runs[0]['id']}` |")
    else:
        a("нет")
    a("")
    a("## Предложение для `kg/`")
    a("")
    a("1. Каждому узлу-прогону добавить поле `data.family` = `<эксперимент>-<8 hex>` (вычисляется")
    a("   детерминированно, скрипт выше). Прогоны **не удаляются**.")
    a("2. Не вводить новый вид узла: семейство читается группировкой по `data.family`.")
    a("3. Если у семейства вердикты расходятся — поле `data.family_conflict: true`, чтобы фронт")
    a("   `kg/frontier` это видел.")
    a("4. Семейство с прогонами только одного вердикта считается воспроизведённым; с одним прогоном —")
    a("   нет (записано как ограничение).")
    a("")
    a("## Чего этот черновик не делает")
    a("")
    a("- Не меняет `kg/` (правка узлов — отдельный шаг `main`).")
    a("- Не решает, что считать «семьёй» по смыслу: здесь только механическая группировка по параметрам.")
    a("- Не проверяет, что параметры описывают опыт полностью (часть записей — `commit unknown`).")
    text = "\n".join(lines) + "\n"

    if write:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано: {OUT} ({len(text)} символов)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
