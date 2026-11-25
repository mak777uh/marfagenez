"""Поиск дублей в литературной карте: один и тот же факт, внесённый дважды.

Повод (25.11.2026): партия `S2` принесла атом `FAST-S2M-02`, который повторяет уже существующий
`DIP21B-0003` — та же работа (`10.1186/s12934-016-0501-z`) и то же число `0,63 ± 0,04`. Дубль заметил
`fast`, а не приём: `ingest_safe` проверяет структуру и DOI, но не «этот факт уже есть».

Что делает скрипт: группирует атомы по DOI, внутри группы ищет совпадение числовых токенов в `statement`
(не менее двух общих чисел) и печатает пары-кандидаты. Принятые дубли перечисляются в
`docs/MAP-DUPLICATES.json` с причиной и датой, чтобы не всплывали снова.

Запуск:
    python3 tools/map_duplicates.py            # отчёт
    python3 tools/map_duplicates.py --strict   # код 1, если есть необъявленный дубль
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
KNOWN = ROOT / "docs" / "MAP-DUPLICATES.json"

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def numbers(text: str) -> set[str]:
    return {m.group(0).replace(",", ".") for m in NUM_RE.finditer(text)}


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    atoms = [json.loads(l) for l in ATOMS.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_doi: dict[str, list[dict]] = collections.defaultdict(list)
    for a in atoms:
        seen = set()
        for w in a.get("works") or []:
            doi = (w.get("doi") or "").strip().lower()
            if doi and doi not in seen:
                seen.add(doi)
                by_doi[doi].append(a)

    known = {}
    if KNOWN.exists():
        known = json.loads(KNOWN.read_text(encoding="utf-8"))

    print(f"атомов: {len(atoms)}; DOI с несколькими атомами: "
          f"{sum(1 for v in by_doi.values() if len(v) > 1)}")
    flagged = []
    for doi, group in sorted(by_doi.items()):
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                shared = numbers(a.get("statement") or "") & numbers(b.get("statement") or "")
                # «0» и «1» встречаются где угодно; интересны содержательные совпадения
                shared = {s for s in shared if s not in ("0", "1", "2", "3")}
                # Признак дубля — совпадение ДРОБНЫХ чисел: из одной работы берут разные величины, но
                # «0,63 ± 0,04» — это конкретный факт. Целые числа (12, 15, 20) совпадают у чего угодно и
                # дали 20 ложных пар. Текст тоже не спасает: два пересказа одного факта дают Jaccard 0,10.
                frac_shared = {x for x in shared if "." in x}
                if len(frac_shared) >= 2:
                    wa = set(re.findall(r"[\wа-яА-Яё]{4,}", (a.get("statement") or "").lower()))
                    wb = set(re.findall(r"[\wа-яА-Яё]{4,}", (b.get("statement") or "").lower()))
                    jac = len(wa & wb) / max(1, len(wa | wb))
                    key = f"{a['atom']}|{b['atom']}"
                    flagged.append((doi, a["atom"], b["atom"], sorted(frac_shared), key in known, jac))

    hard = [f for f in flagged if not f[4]]
    for doi, a1, a2, sh, is_known, jac in flagged:
        mark = "объявлен" if is_known else "НОВЫЙ"
        print(f"  [{mark}] {a1} ~ {a2} | doi {doi} | сходство текста {jac:.2f} | "
              f"совпавшие дробные: {', '.join(sh)}")
    if not flagged:
        print("  пар-кандидатов нет")

    print()
    if hard:
        print(f"необъявленных дублей: {len(hard)} — внесите в docs/MAP-DUPLICATES.json с причиной")
        return 1 if strict else 0
    print("необъявленных дублей нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
