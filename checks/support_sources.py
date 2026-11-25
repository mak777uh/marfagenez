"""Опора записи — это сумма четырёх источников, а не один.

Три раза подряд вывод «у записи нет опоры» оказывался неверным, потому что проверялось одно поле:
сначала `math.checked`, потом пары сшивки, потом `lit_ref`. Этот файл механизирует правило:

    опора = evidence ∪ math.checked ∪ lit_ref ∪ пары сшивки

Проверяет только `claim` и `formula` со статусом `established`: у них опора обязана быть. Прогоны
(`experiment`) не проверяются — у них опора-прогон и это нормально.

Краснеет только если у записи **вообще нет** ни одного источника. Слабая литературная опора — не
ошибка этой проверки: она видна в `docs/STITCH-AUDIT.md`.

Запуск: python3 checks/support_sources.py
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"
VERDICTS = ROOT / "docs" / "REDTEAM-STITCH-VERDICTS.json"
OVERRIDES = ROOT / "docs" / "STITCH-OVERRIDES.json"


def load_verdicts() -> dict[str, str]:
    v: dict[str, str] = {}
    if VERDICTS.exists():
        v.update(json.loads(VERDICTS.read_text(encoding="utf-8")))
    if OVERRIDES.exists():
        for k, o in json.loads(OVERRIDES.read_text(encoding="utf-8")).items():
            if o.get("verdict"):
                v[k] = o["verdict"]
    return v


def main() -> int:
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines() if l.strip()]
    verdicts = load_verdicts()

    stitched: dict[str, list[str]] = {}
    for key, verdict in verdicts.items():
        if "|" not in key:
            continue
        _, node = key.split("|", 1)
        stitched.setdefault(node, []).append(verdict)

    bad = []
    checked = 0
    for n in nodes:
        if n.get("kind") not in ("claim", "formula") or n.get("epistemic") != "established":
            continue
        checked += 1
        sources = []
        if n.get("evidence"):
            sources.append("evidence")
        if ((n.get("math") or {}).get("checked") or {}).get("kind") not in (None, "", "none"):
            sources.append("math.checked")
        if ((n.get("data") or {}).get("lit_ref") or []):
            sources.append("lit_ref")
        if stitched.get(n["id"]):
            sources.append("stitch")
        if not sources:
            bad.append(n["id"])

    if bad:
        print(f"ОПОРА: {len(bad)} записей со статусом established без единого источника:")
        for nid in bad:
            print(f"  {nid}")
        print("Проверено четыре источника: evidence, math.checked, lit_ref, пары сшивки.")
        return 1

    print(f"ОПОРА: у всех {checked} записей claim/formula со статусом established есть хотя бы один "
          f"источник (evidence / math.checked / lit_ref / сшивка)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
