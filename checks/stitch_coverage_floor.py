"""Пол: строгая литературная опора не должна уменьшаться.

После Red Team выяснилось, что «опора» — это пара, где совпадает **измеряемая величина** (`S`), а не
любая пара. Эта проверка фиксирует достигнутый уровень и краснеет, если он упал:

    число пар с вердиктом S   ≥ baseline
    число узлов с парой S     ≥ baseline

Почему пол, а не «должно быть 152». Покрытие растёт поиском, а не правкой проверки; требовать сто
процентов сразу — значит покрасить гейт и начать его обходить. Пол же запрещает **терять** уже
доказанное, например при переклассификации пары в `N` без замены.

Учитываются вердикты Red Team и ручной арбитраж (`docs/STITCH-OVERRIDES.json`).

Запуск: python3 checks/stitch_coverage_floor.py [--update]
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERDICTS = ROOT / "docs" / "REDTEAM-STITCH-VERDICTS.json"
OVERRIDES = ROOT / "docs" / "STITCH-OVERRIDES.json"
BASELINE = ROOT / "docs" / "STITCH-COVERAGE-FLOOR.json"


def counts() -> tuple[int, int]:
    v = json.loads(VERDICTS.read_text(encoding="utf-8")) if VERDICTS.exists() else {}
    if OVERRIDES.exists():
        for k, o in json.loads(OVERRIDES.read_text(encoding="utf-8")).items():
            if o.get("verdict"):
                v[k] = o["verdict"]
    s_pairs = sum(1 for x in v.values() if x == "S")
    by_node: dict[str, list[str]] = collections.defaultdict(list)
    for key, verdict in v.items():
        if "|" in key:
            by_node[key.split("|", 1)[1]].append(verdict)
    s_nodes = sum(1 for vs in by_node.values() if "S" in vs)
    return s_pairs, s_nodes


def main(argv: list[str]) -> int:
    s_pairs, s_nodes = counts()
    if "--update" in argv:
        BASELINE.write_text(json.dumps({"s_pairs": s_pairs, "s_nodes": s_nodes,
                                        "date": "2026-11-25"}, ensure_ascii=False,
                                       indent=2) + "\n", encoding="utf-8")
        print(f"пол обновлён: пар S = {s_pairs}, узлов S = {s_nodes}")
        return 0

    if not BASELINE.exists():
        print(f"нет файла пола {BASELINE}; создайте базовую запись через --update")
        return 1
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    bp, bn = int(base.get("s_pairs", 0)), int(base.get("s_nodes", 0))

    bad = []
    if s_pairs < bp:
        bad.append(f"пар S стало {s_pairs} против пола {bp}")
    if s_nodes < bn:
        bad.append(f"узлов S стало {s_nodes} против пола {bn}")
    if bad:
        print("ОПОРА-ПОЛ: " + "; ".join(bad))
        print("Правило: переклассификация пары в N допустима, но только с заменой или с явным")
        print("понижением пола в docs/STITCH-COVERAGE-FLOOR.json (видно в диффе).")
        return 1

    print(f"ОПОРА-ПОЛ: пар S = {s_pairs} (пол {bp}), узлов S = {s_nodes} (пол {bn}) — уровень не упал")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
