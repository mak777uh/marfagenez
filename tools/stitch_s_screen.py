"""Экран `S`-пар: где величина совпадает, а числа — нет.

`S`-вердикт означает «измеряемая величина совпадает». Для узлов-определений это значит «атом из той же
работы формулирует то же утверждение». Для измерений величины должны совпадать **и числом**, если числа
есть с обеих сторон.

Скрипт печатает `S`-пары, у которых:
  - в атоме и в узле есть числа, но НИ ОДНО не совпадает (первый кандидат на перечитывание);
  - и отдельно список пар, где чисел нет ни с одной стороны (проверить можно только чтением).

Запуск: python3 tools/stitch_s_screen.py
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
NUM = re.compile(r"\d+(?:[.,]\d+)?")


ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Za-z0-9]+)+\b")


def nums(text: str) -> set[str]:
    out = set()
    # Идентификаторы узлов и атомов (F-029, L-073, B26-01-0003) — не числа: их цифры попадали в сравнение
    # и давали ложные «расхождения» (например, «029» из ссылки «см. F-029»).
    text = ID_RE.sub(" ", text or "")
    for m in NUM.finditer(text):
        tok = m.group(0).replace(",", ".")
        # годы (1900-2099) — это ссылки на работы, а не измеренные величины
        if len(tok) == 4 and tok.isdigit() and 1900 <= int(tok) <= 2099:
            continue
        # «1», «2», «3» встречаются в любой формуле (одна ось, два класса, три условия) и совпадением
        # величины не являются — иначе признак «числа совпали» ничего не значит.
        if tok in ("1", "2", "3", "0"):
            continue
        out.add(tok)
    return out


def main() -> int:
    atoms = {json.loads(l)["atom"]: json.loads(l)
             for l in (ROOT / "literature/map/atoms.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip()}
    nodes = {json.loads(l)["id"]: json.loads(l)
             for l in (ROOT / "kg/nodes.jsonl").read_text(encoding="utf-8").splitlines()}
    ov = json.loads((ROOT / "docs/STITCH-OVERRIDES.json").read_text(encoding="utf-8"))
    verd = json.loads((ROOT / "docs/REDTEAM-STITCH-VERDICTS.json").read_text(encoding="utf-8"))
    verd.update({k: v["verdict"] for k, v in ov.items() if isinstance(v, dict) and v.get("verdict")})

    s_pairs = sorted(k for k, v in verd.items() if "|" in k and v == "S")
    no_overlap, no_numbers = [], []
    for key in s_pairs:
        atom_id, node_id = key.split("|", 1)
        a = atoms.get(atom_id) or {}
        n = nodes.get(node_id) or {}
        na = nums((a.get("statement") or "") + " " + str(a.get("formula") or ""))
        nn = nums((n.get("text") or "") + " " + str((n.get("math") or {}).get("latex") or ""))
        if na and nn and not (na & nn):
            no_overlap.append((key, sorted(na)[:6], sorted(nn)[:6]))
        elif not na or not nn:
            no_numbers.append(key)

    print(f"S-пар: {len(s_pairs)}")
    print(f"чисел нет с одной стороны: {len(no_numbers)} — проверяются только чтением")
    print(f"числа есть с обеих сторон, но не совпадают: {len(no_overlap)}")
    for key, na, nn in no_overlap:
        print(f"  {key}: атом {na} | узел {nn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
