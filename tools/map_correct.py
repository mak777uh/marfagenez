"""Исправление ячейки карты с записью в реестр ошибок.

Правило проекта: историю не переписывать. Поэтому исправление ячейки **не молчит**: старая формулировка
уходит в `docs/MAP-ERRATA.md` с причиной и датой, и только потом в `literature/map/atoms.jsonl` пишется
новая. Обратной операции нет — правка видна в git и в реестре.

Запуск:
    python3 tools/map_correct.py --atom DIP24-0011 \
        --set-field statement="..." --set-field formula="..." --set-field notes="..." \
        --reason "единицы относятся к давлению: это L_p, а не P_f"

Требования: `--reason` обязателен; сколько полей задано — столько будет изменено; ячейка должна
существовать; для `statement` нужна длина ≥ 30 символов.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
ERRATA = ROOT / "docs" / "MAP-ERRATA.md"
FIELDS = {"statement", "formula", "notes", "kind", "domain", "confidence", "conditions"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="исправить ячейку карты с записью в реестр")
    ap.add_argument("--atom", required=True)
    ap.add_argument("--set-field", action="append", default=[], metavar="FIELD=VALUE")
    ap.add_argument("--reason", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    patch = {}
    for item in args.set_field:
        if "=" not in item:
            print(f"ошибка: ожидалось FIELD=VALUE, получено {item!r}")
            return 2
        key, _, val = item.partition("=")
        if key not in FIELDS:
            print(f"ошибка: поле {key!r} не разрешено ({sorted(FIELDS)})")
            return 2
        patch[key] = val
    if not patch:
        print("ошибка: не задано ни одного поля")
        return 2
    if "statement" in patch and len(patch["statement"]) < 30:
        print("ошибка: statement короче 30 символов")
        return 2

    lines = ATOMS.read_text(encoding="utf-8").splitlines()
    idx = None
    old = None
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        a = json.loads(line)
        if a["atom"] == args.atom:
            idx, old = i, a
            break
    if idx is None:
        print(f"ошибка: ячейки {args.atom} нет в карте")
        return 1

    changed = {k: {"было": old.get(k), "стало": v} for k, v in patch.items() if old.get(k) != v}
    if not changed:
        print("нечего менять: значения совпадают")
        return 0

    print(f"{args.atom}: меняется полей {len(changed)} -> {sorted(changed)}")
    for k, v in changed.items():
        print(f"  {k}:")
        print(f"    было:  {str(v['было'])[:160]}")
        print(f"    стало: {str(v['стало'])[:160]}")

    if args.dry_run:
        print("dry-run: файлы не тронуты")
        return 0

    new = dict(old)
    new.update(patch)
    new["corrected"] = dt.date.today().isoformat()
    lines[idx] = json.dumps(new, ensure_ascii=False)
    ATOMS.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not ERRATA.exists():
        ERRATA.write_text("# Реестр исправлений литературной карты\n\n"
                          "Каждая запись — датированная правка ячейки с причиной. Старая формулировка "
                          "сохраняется здесь и в git.\n", encoding="utf-8")
    entry = [f"\n## {args.atom} — {dt.date.today():%d.%m.%Y}", "",
             f"**Причина:** {args.reason}", ""]
    for k, v in changed.items():
        entry += [f"**{k}**", "", "было:", "", f"> {str(v['было'])}", "", "стало:", "",
                  f"> {str(v['стало'])}", ""]
    ERRATA.write_text(ERRATA.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(entry) + "\n",
                      encoding="utf-8")
    print(f"записано в {ERRATA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
