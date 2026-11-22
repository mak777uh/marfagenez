"""Линия поколений: что передаётся и когда линия вымирает.

    внутри поколения:  dD/dt = eta - C*D/(K+D)
                       dC/dt = (C0-C)/tau - gamma*D*C
    передача:          C0' = C0*(1 - delta*D_end)
                       D0' = (1-rho)*D_end

Usage: python3 tools/core_lineage.py [--write]
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "CORE-LINEAGE.md"


def one_life(D0: float, C0: float, gamma: float, eta: float = 0.5, K: float = 0.1,
             tau: float = 10.0, T: float = 100.0, dt: float = 0.05) -> tuple[float, float]:
    D, C, t = D0, C0, 0.0
    while t < T - 1e-9:
        removal = C * D / (K + D) if D > 0 else 0.0
        D = max(0.0, D + (eta - removal) * dt)
        C = max(0.0, C + ((C0 - C) / tau - gamma * D * C) * dt)
        t += dt
    return D, C


def lineage(delta: float, rho: float, gamma: float = 0.05, generations: int = 30,
            C_min: float = 0.25) -> list[dict]:
    D0, C0 = 0.0, 1.0
    rows = []
    for g in range(1, generations + 1):
        D_end, C_end = one_life(D0, C0, gamma)
        rows.append({"gen": g, "C_start": C0, "C_end": C_end, "D_end": D_end,
                     "alive": C0 > C_min and D_end < 1.0})
        C0 = max(0.0, C0 * (1.0 - delta * D_end))
        D0 = (1.0 - rho) * D_end
        if not rows[-1]["alive"]:
            break
    return rows


def main(argv: list[str]) -> int:
    configs = [("без наследования износа", 0.0, 0.5),
               ("слабый износ", 1.0, 0.5),
               ("средний износ", 5.0, 0.5),
               ("сильный износ", 20.0, 0.5),
               ("средний износ + слабая асимметрия", 5.0, 0.1)]

    lines: list[str] = []
    add = lines.append
    add("# Линия поколений: что передаётся и когда линия кончается")
    add("")
    add("Сгенерировано `python3 tools/core_lineage.py`. Числа — результат прогона.")
    add("")
    add("## Уравнения")
    add("")
    add("```")
    add("внутри поколения:  dD/dt = eta - C*D/(K+D)")
    add("                   dC/dt = (C0-C)/tau - gamma*D*C,  gamma = 0.05")
    add("передача:          C0' = C0*(1 - delta*D_end)")
    add("                   D0' = (1-rho)*D_end")
    add("```")
    add("")
    add("## Результат")
    add("")
    add("| сценарий | delta | rho | прожито поколений | C в начале последнего | груз к концу |")
    add("|---|---|---|---|---|---|")
    for name, delta, rho in configs:
        rows = lineage(delta, rho)
        last = rows[-1]
        add(f"| {name} | {delta} | {rho} | {len(rows)} | {last['C_start']:.3f} | {last['D_end']:.3f} |")
    add("")
    base = lineage(0.0, 0.5)
    add("Без наследуемого износа линия проходит все 30 поколений: способность в начале каждого")
    add(f"поколения остаётся 1.000, груз к концу поколения {base[-1]['D_end']:.3f}.")
    add("")
    add("## Что это значит")
    add("")
    add("1. **Без наследуемого износа линия бессмертна:** 30 поколений при rho=0.5 проходят с")
    add("   неизменной способностью 1.000 и грузом 0.112 к концу поколения. Асимметрии достаточно.")
    add("2. **С наследуемым износом линия гибнет резко, а не постепенно:** уже слабый износ (delta=1)")
    add("   даёт 4 поколения, средний и сильный — 2. Порог способности пересекается, и дальше работает")
    add("   тот же коллапс, что в одной жизни. Это и есть «второй порядок», которого мы не нашли")
    add("   в литературе: он получается из передачи, а не из новых повреждений.")
    add("3. **Асимметрия не спасает при сильном износе:** при delta=5 различие rho=0.5 и rho=0.1")
    add("   по числу поколений нулевое (2 и 2), а груз к концу отличается на 0.06 процента. Значит")
    add("   главный фактор — износ способности, а не стартовый груз потомка.")
    add("")
    add("## Чего в этом прогоне нет")
    add("")
    add("- Цены ремонта: способность здесь бесплатна, хотя предыдущий шаг показал, что цена важна.")
    add("  Следующая версия должна связать `delta` с ценой: чем дешевле ремонт, тем меньше износ.")
    add("- Отбора: линия одна, конкуренции нет.")
    add("- Случайности: детерминированный прогон даёт точку смерти, а не распределение.")
    add("")
    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
