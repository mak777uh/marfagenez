"""Фаза 3.4: покрытие карты знаний литературной опорой.

Считает, у каких узлов `kg/` есть `data.lit_ref` (то есть пара с литературной картой), а у каких нет.
Ничего не придумывает: только показывает, где у наших утверждений нет внешней опоры.

Запуск: python3 tools/stitch_coverage.py [--write]
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "STITCH-COVERAGE.md"

SKIP_KINDS = {"experiment", "evidence", "definition"}  # прогоны и объекты свидетельства не «утверждения»


def main(argv: list[str]) -> int:
    nodes = [json.loads(l) for l in (ROOT / "kg" / "nodes.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    inside = [n for n in nodes if n.get("kind") not in SKIP_KINDS]

    with_ref = [n for n in inside if (n.get("data") or {}).get("lit_ref")]
    without = [n for n in inside if not (n.get("data") or {}).get("lit_ref")]

    by_kind = collections.Counter(n.get("kind") for n in inside)
    cov_kind = collections.Counter(n.get("kind") for n in with_ref)

    lines: list[str] = []
    p = lines.append
    p("# Покрытие карты знаний литературной опорой")
    p("")
    p("Сгенерировано `tools/stitch_coverage.py`. Пара = у узла `kg/` есть `data.lit_ref` (ячейки "
      "литературной карты, сшитые с ним вручную).")
    p("")
    p("Прогоны (`experiment`), объекты свидетельства (`evidence`) и определения в счёт не идут: это не "
      "утверждения о мире.")
    p("")
    p("## Сводка")
    p("")
    p(f"Утверждений, формул, дыр и соответствий: **{len(inside)}**; с литературной опорой: **{len(with_ref)}** "
      f"({len(with_ref)/max(1,len(inside)):.0%}).")
    p("")
    p("| вид | всего | с опорой |")
    p("|---|---|---|")
    for kind, total in by_kind.most_common():
        p(f"| {kind} | {total} | {cov_kind.get(kind, 0)} |")
    p("")
    p("## Узлы с опорой")
    p("")
    p("| узел | вид | опора |")
    p("|---|---|---|")
    for n in sorted(with_ref, key=lambda x: x["id"]):
        p(f"| {n['id']} | {n.get('kind')} | {', '.join((n.get('data') or {}).get('lit_ref'))} |")
    p("")
    p("## Узлы без опоры (самое важное)")
    p("")
    p("| узел | вид | статус | текст |")
    p("|---|---|---|---|")
    for n in sorted(without, key=lambda x: x["id"]):
        p(f"| {n['id']} | {n.get('kind')} | {n.get('epistemic')} | {(n.get('text') or '')[:90]} |")
    p("")
    p("## Что это значит")
    p("")
    p(f"1. **Опора есть у {len(with_ref)} из {len(inside)}** — остальные наши утверждения пока живут без")
    p("   внешней пары. Это не значит, что они неверны: часть из них — наши собственные конструкции")
    p("   (пороги, ядра, цены), которым в литературе соответствует не одна работа, а класс явлений.")
    p("2. **Без опоры остались целые механизмы:** обмен, организация, смерть, агентность. Ровно те, у")
    p("   которых в `kg/` не было хабов до круга 519, — совпадение не случайное: нет литературы, нет и связи.")
    p("3. **Самое дешёвое следующее движение** — искать литературу не под формулы (они уже сшиты), а под")
    p("   утверждения `C-00*` без опоры: у них есть проверенные числа и понятный вопрос к литературе.")
    p("")
    p("## Чего это не даёт")
    p("")
    p("- Покрытие — не подтверждение: `kg_ref` говорит «связано», а не «верно».")
    p("- Число пар зависит от моей ручной разметки, а не от полноты поиска.")

    text = "\n".join(lines) + "\n"
    print(text[:2000])
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"\nзаписано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
