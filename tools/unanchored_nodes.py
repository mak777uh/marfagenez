"""Какие узлы дерева ни на что не опираются?

Опора может быть любой из четырёх: `lit_ref` (ссылка на карту), `evidence`, `relations` (связи с другими
узлами) или `math.checked` (числовая проверка). Узел без всех четырёх — **заготовка**: его нельзя ни
подтвердить, ни опровергнуть, и он не связан с остальным деревом.

Повод: `F-011` («ниша и её изменение») — `lit_ref: None`, `evidence: []`, `relations: []`,
`math.checked: none`, а запись `ΔR = R_original − R_modified` не определяет, что такое `R`.

Запуск: python3 tools/unanchored_nodes.py [--strict]
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"
KINDS = ("claim", "formula", "definition", "correspondence")


def main(argv: list[str]) -> int:
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines() if l.strip()]

    # Пятая форма опоры — пара сшивки с вердиктом `S`. Без неё счёт был завышен: 27 «без опоры» включали
    # узлы, у которых есть прочитанная пара (F-005, F-006, F-012, F-013, F-026) — первая версия это
    # проглядела, потому что смотрела только поля узла, а не файлы сшивки.
    stitch_s = set()
    for name in ("REDTEAM-STITCH-VERDICTS.json", "STITCH-OVERRIDES.json"):
        f = ROOT / "docs" / name
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for key, val in data.items():
            if "|" not in key or not isinstance(key, str):
                continue
            verdict = val.get("verdict") if isinstance(val, dict) else val
            if verdict == "S":
                stitch_s.add(key.split("|")[1])
    rows = []
    for n in nodes:
        if n.get("kind") not in KINDS:
            continue
        # `lit_ref` живёт в `data` (так его кладёт `apply_lit_refs` в kg/migrate.py), а не в корне узла.
        # Первая версия смотрела `n.get("lit_ref")` и не видела ни одной ссылки — счёт оставался 20 даже
        # после проставления refs.
        data = n.get("data") or {}
        has_lit = bool(n.get("lit_ref") or data.get("lit_ref"))
        has_ev = bool(n.get("evidence"))
        has_rel = bool(n.get("relations"))
        checked = (n.get("math") or {}).get("checked") or {}
        has_checked = bool(checked.get("kind")) and checked.get("kind") != "none"
        has_stitch = n.get("id") in stitch_s
        if not (has_lit or has_ev or has_rel or has_checked or has_stitch):
            rows.append(n)

    print(f"узлов утверждающего типа: {sum(1 for n in nodes if n.get('kind') in KINDS)}")
    exempt = {}
    ef = ROOT / "docs" / "ANCHOR-EXEMPTIONS.json"
    if ef.exists():
        try:
            exempt = {k: v for k, v in json.loads(ef.read_text(encoding="utf-8")).items()
                      if not k.startswith("_")}
        except Exception:
            exempt = {}
    if exempt:
        before = len(rows)
        rows = [r for r in rows if r["id"] not in exempt]
        print(f"объявлены собственными конструкциями: {before - len(rows)} "
              f"(осталось без опоры: {len(rows)})")

    base_file = ROOT / "docs" / "ANCHOR-BASELINE.json"
    base = {}
    if base_file.exists():
        try:
            base = json.loads(base_file.read_text(encoding="utf-8"))
        except Exception:
            base = {}
    ceiling = int(base.get("without_anchor") or 0)

    print(f"без опоры (ни lit_ref, ни evidence, ни relations, ни math.checked, ни S-пара): {len(rows)}"
          + (f" (потолок {ceiling})" if ceiling else ""))
    for n in rows:
        print(f"  {n['id']:8} [{n['kind']:11}] {n.get('epistemic'):11} {str(n.get('text'))[:70]}")
    if not rows:
        return 0
    print()
    print("Что делать: найти источник (lit_ref/evidence), связать с деревом (relations) или объявить пробел.")
    if "--strict" in argv:
        if ceiling and len(rows) > ceiling:
            print(f"СТРОГИЙ РЕЖИМ: без опоры стало больше потолка ({len(rows)} > {ceiling})")
            return 1
        if ceiling:
            print("СТРОГИЙ РЕЖИМ: потолок не превышен (долг не вырос)")
            return 0
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
