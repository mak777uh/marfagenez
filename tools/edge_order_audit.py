"""Аудит рёбер `refines`: уточнять можно величину того же порядка.

Повод: ребро `B7-09-0001 --refines--> B7-03-0002` связывало цены 72 519–1 138 246 Дж/м² и 0,12 Дж/м² —
различие 10⁵–10⁶. «Та же природа величины» без «того же порядка» даёт ложное уточнение.

Метод (грубый, только для чтения глазами):
1. Для каждого ребра типа `refines` берём дробные числа из statement+formula обеих ячеек.
2. Считаем медиану порядков величин (по модулю) с каждой стороны.
3. Если |порядок A − порядок B| ≥ 3 (то есть в 1000 раз), ребро попадает в список для чтения.

Годятся только числа, записанные как дробные (не ID, не годы) — экран их уже умеет отбрасывать.

Запуск: python3 tools/edge_order_audit.py [--strict] [--update]
"""

from __future__ import annotations

import collections
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
EDGES = ROOT / "literature" / "map" / "edges.jsonl"
BASE = ROOT / "docs" / "EDGE-ORDER-BASELINE.json"

ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Za-z0-9]+)+\b")
# Число: обычное или научное (8·10⁻⁴, 8×10^-4, 8e-4). Знак ·/× и надстрочные цифры встречаются в корпусе.
SCI_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:[·×x]\s*10\s*([⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)|e\s*([-+]?\d+))")
NUM_RE = re.compile(r"(?<![\d.,])(\d{1,6}[.,]\d+|\d{1,6})(?![\d])")


SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
       "⁻": "-", "⁺": "+"}


def numbers(text: str) -> list[float]:
    text = ID_RE.sub(" ", text or "")
    out = []
    # сначала научная запись: вырезаем её из текста, чтобы 8·10⁻⁴ не распадалось на «8» и «10»
    for m in SCI_RE.finditer(text):
        mant = float(m.group(1).replace(",", "."))
        if m.group(2):
            exp = int("".join(SUP.get(ch, "") for ch in m.group(2)))
        else:
            exp = int(m.group(3))
        out.append(mant * 10 ** exp)
    text = SCI_RE.sub(" ", text)
    for m in NUM_RE.finditer(text):
        try:
            v = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        if 1900 <= v <= 2100 and v.is_integer():   # годы
            continue
        if v == 0:
            continue
        out.append(v)
    return out


def median_order(vals: list[float]) -> float | None:
    if not vals:
        return None
    logs = sorted(math.log10(abs(v)) for v in vals)
    return logs[len(logs) // 2]


def order(vals: list[float]) -> float | None:
    """Порядок величины по МИНИМУМУ модуля, а не по медиане.

    Медиана ломается, когда в тексте есть счётчики (216 делений, 50 %) и температуры (-70,6 °C читается как
    70,6): они уводят медиану на порядки, хотя сравниваемые величины одного масштаба. Минимум модуля
    устойчивее: дробные «малые» числа — это и есть измеренные величины.
    """
    if not vals:
        return None
    return min(math.log10(abs(v)) for v in vals if v != 0)


def main(argv: list[str]) -> int:
    atoms = {json.loads(l)["atom"]: json.loads(l)
             for l in ATOMS.read_text(encoding="utf-8").splitlines() if l.strip()}
    edges = [json.loads(l) for l in EDGES.read_text(encoding="utf-8").splitlines() if l.strip()]

    def text_of(i):
        a = atoms.get(i) or {}
        return f"{a.get('statement') or ''} {a.get('formula') or ''}"

    flags = []
    refines = [e for e in edges if e.get("type") == "refines"]
    for e in refines:
        na, nb = numbers(text_of(e["from"])), numbers(text_of(e["to"]))
        oa, ob = order(na), order(nb)
        ma, mb = median_order(na), median_order(nb)
        if oa is None or ob is None or ma is None or mb is None:
            continue
        gap_min = abs(oa - ob)
        gap_med = abs(ma - mb)
        if max(gap_min, gap_med) >= 3:
            flags.append((e["from"], e["to"], gap_min, gap_med))

    print("СПИСОК ДЛЯ ЧТЕНИЯ, а не список дефектов: обе статистики шумят (см. docs/EDGE-ORDER.md).")
    print(f"рёбер `refines`: {len(refines)}; кандидатов (расхождение ≥1000 раз): {len(flags)}")
    for f, t, gmin, gmed in sorted(flags, key=lambda x: -max(x[2], x[3]))[:12]:
        print(f"  {f} -> {t}: по минимуму ×{10 ** gmin:,.0f}, по медиане ×{10 ** gmed:,.0f}")

    # --strict/--update намеренно не используются: обе статистики дают ложные срабатывания.
    if False and "--update" in argv:
        BASE.write_text(json.dumps({"flags": len(flags), "date": "2026-11-25"}, ensure_ascii=False,
                                   indent=2) + "\n", encoding="utf-8")
        print(f"потолок обновлён: {len(flags)}")
        return 0
    if "--strict" in argv:
        ceiling = 0
        if BASE.exists():
            ceiling = int(json.loads(BASE.read_text(encoding="utf-8")).get("flags") or 0)
        if len(flags) > ceiling:
            print(f"СТРОГИЙ РЕЖИМ: {len(flags)} рёбер с расхождением порядков больше потолка {ceiling}")
            return 1
        print(f"СТРОГИЙ РЕЖИМ: {len(flags)} при потолке {ceiling} — долг не вырос")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
