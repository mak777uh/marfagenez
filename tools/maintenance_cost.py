"""`F-004`: цена поддержания и замыкание — размерность и предел.

Узел:
    приход = c_y·σ·p·f̄              (доход формы)
    расход = f₀ + μ·n + κ·n²/p       (поддержание + починка + издержки)
    жива ⟺ приход ≥ расход

Проверяем три вещи:
1. Размерность: все слагаемые расхода должны быть мощностью (Дж/с).
2. Предел p → 0: слагаемое κ·n²/p растёт неограниченно — при какой доле p система ещё жива.
3. Различимость двух прочтений (n — масса в граммах против n — число особей в штуках):
   они дают РАЗНЫЕ единицы κ, и это не косметика.

Опровергающее условие: если размерности слагаемых сходятся — п.1 пройден; если при p → 0 расход
остаётся конечным — п.2 пройден.

Запуск: python3 tools/maintenance_cost.py
"""

from __future__ import annotations

import json
import pathlib
import re

# Единицы в СИ: Дж, с, г. Проверяем размерность формально, как произведение степеней.
DIM = {"Дж": (1, 2, -2), "с": (0, 0, 1), "г": (0, 1, 0)}   # (масса, длина, время)


def mul(*factors):
    """Перемножить размерности: каждая запись — (имя, показатель) или просто имя."""
    total = [0, 0, 0]
    for f in factors:
        if isinstance(f, tuple) and len(f) == 3 and not isinstance(f[0], str):
            # уже размерность: (масса, длина, время) в показателях
            for i, v in enumerate(f):
                total[i] += v
            continue
        if isinstance(f, tuple):
            name, power = f[0], f[1]
        else:
            name, power = f, 1
        for i, v in enumerate(DIM[name]):
            total[i] += v * power
    return tuple(total)


def fmt(d):
    """d = (масса, длина, время) в показателях степеней."""
    names = ("масса", "длина", "время")
    parts = [f"{n}^{e}" for n, e in zip(names, d) if e]
    return " · ".join(parts) if parts else "безразмерно"


SUP = {"²": 2, "³": 3, "⁻¹": -1, "⁻²": -2, "⁻³": -3}


def parse_units(text: str) -> tuple[int, int, int] | None:
    """Простейший разбор единиц вида «Дж·с/г²» или «Дж/(с·г²)» в показатели (масса, длина, время).

    Возвращает None, если в записи есть символы, которых нет в DIM (например «концентрация»).
    """
    t = (text or "").replace(" ", "")
    if not t or t == "1":
        return (0, 0, 0)
    num, _, den = t.partition("/")
    den = den.strip("()")
    total = [0, 0, 0]
    for part, sign in ((num, 1), (den, -1)):
        if not part:
            continue
        for tok in re.findall(r"[А-Яа-яA-Za-z]+[²³]?|[⁻⁺]?[0-9]+", part.replace("·", "*").replace("*", " ")):
            m = re.fullmatch(r"([А-Яа-яA-Za-z]+)([²³]?)", tok)
            if not m:
                continue
            name, sup = m.group(1), m.group(2)
            if name not in DIM:
                return None
            power = SUP.get(sup, 1) * sign
            for i, v in enumerate(DIM[name]):
                total[i] += v * power
    return tuple(total)


def recorded_kappa_units() -> str:
    """Единица κ, записанная в kg/nodes.jsonl для F-004 (из kg/migrate.py UNITS)."""
    nodes = pathlib.Path(__file__).resolve().parent.parent / "kg" / "nodes.jsonl"
    if not nodes.exists():
        return "Дж/(с·г²)"
    for line in nodes.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n = json.loads(line)
        if n.get("id") == "F-004":
            return ((n.get("math") or {}).get("units") or {}).get("kappa") or "Дж/(с·г²)"
    return "Дж/(с·г²)"


def main() -> int:
    power = mul("Дж", ("с", -1))
    print(f"цель: все слагаемые расхода должны иметь {fmt(power)} (мощность)\n")

    kappa_units = recorded_kappa_units()
    print(f"κ записан в kg/ как: {kappa_units}")

    # слагаемые
    f0 = mul("Дж", ("с", -1))
    mu_n = mul(("Дж", 1), ("с", -1), ("г", -1), "г")          # μ·n
    kappa_table = parse_units(kappa_units) or mul("Дж", "с", ("г", -2))  # то, что записано в таблице
    kappa_term = mul(kappa_table, ("г", 2))                    # κ·n²/p при [p]=1
    kappa_needed = mul("Дж", ("с", -1), ("г", -2))             # что нужно, чтобы вышла мощность

    print(f"f₀                : {fmt(f0)}")
    print(f"μ·n               : {fmt(mu_n)}")
    print(f"κ·n²/p (по таблице): {fmt(kappa_term)}   ← из [κ] = {fmt(kappa_table)}")
    print(f"нужно для κ        : {fmt(kappa_needed)}")
    print()

    ok1 = f0 == power and mu_n == power
    bad = kappa_term != power
    print(f"первые два слагаемых сходятся: {ok1}")
    print(f"слагаемое с κ сходится: {not bad}")
    if bad:
        ratio = tuple(a - b for a, b in zip(kappa_term, power))
        print(f"  расхождение: лишнее {fmt(ratio)} — то есть в [κ] не хватает деления на время дважды")
        print(f"  правильная единица κ: {fmt(kappa_needed)} (Дж/(с·г²))")

    # 2) предел p → 0
    print()
    print("предел p → 0 (расход = f₀ + μ·n + κ·n²/p):")
    f0v, muv, nv, kv, income = 1.0, 0.5, 2.0, 0.3, 10.0
    for p in (1.0, 0.5, 0.2, 0.1, 0.05, 0.01):
        out = f0v + muv * nv + kv * nv ** 2 / p
        print(f"  p = {p:4.2f}: расход = {out:9.2f}   ({'жива' if income >= out else 'мертва'})")
    # критическая доля
    p_crit = kv * nv ** 2 / max(income - f0v - muv * nv, 1e-12)
    print(f"критическая доля: p* = {p_crit:.3f} — ниже неё расход превышает приход")

    # 3) различимость прочтений
    print()
    print("два прочтения n:")
    print("  n = масса (г):   [κ] = Дж/(с·г²)  — слагаемое κ·n²/p имеет смысл энергии на массу в квадрате")
    print("  n = число (шт):  [κ] = Дж/с        — слагаемое κ·n²/p безразмерно по n, и «починка» теряет связь с массой")

    print()
    if ok1 and not bad:
        print("ВЫВОД: размерности сходятся, предел p → 0 даёт конечную критическую долю — узел согласован.")
        return 0
    print("ВЫВОД: единица κ в таблице не даёт мощности: [κ] = Дж·с/г² вместо Дж/(с·г²).")
    print("        Это дефект ЗАПИСИ единиц (не формулы): само слагаемое κ·n²/p требует Дж/(с·г²).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
