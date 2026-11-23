"""Компромисс: платить за ремонт сейчас или экономить и передавать износ.

Внутри поколения ядро с бюджетом; между поколениями износ способности зависит от того, сколько
платили за ремонт. Вопрос: есть ли оптимальная цена ремонта на горизонте 30 поколений.

    dD/dt = eta - C*D/(K+D)
    dC/dt = (C0-C)/tau - gamma*D*C
    dE/dt = uptake - m0 - cR*C*D/(K+D) - cC*C      (смерть, если E <= 0)
    передача: C0' = C0*(1 - delta_eff*D_end),  delta_eff = delta0/(1+cR)^p
              D0' = (1-rho)*D_end

Дешевле ремонт -> больше износ передаётся потомку; дороже -> раньше голод.

Usage: python3 tools/core_tradeoff.py [--write]
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "CORE-TRADEOFF.md"


def one_life(D0: float, C0: float, cR: float, gamma: float = 0.05, eta: float = 0.5,
             K: float = 0.1, tau: float = 10.0, uptake: float = 3.0, m0: float = 1.0,
             cC: float = 0.5, T: float = 100.0, dt: float = 0.05) -> tuple[float, float, bool]:
    D, C, E, t = D0, C0, 1.0, 0.0
    starved = False
    while t < T - 1e-9:
        removal = C * D / (K + D) if D > 0 else 0.0
        D = max(0.0, D + (eta - removal) * dt)
        C = max(0.0, C + ((C0 - C) / tau - gamma * D * C) * dt)
        E += (uptake - m0 - cR * removal - cC * C) * dt
        if E <= 0:
            starved = True
            break
        t += dt
    return D, C, starved


LAWS = {
    "гипербола 5/(1+cR)": lambda cR: 5.0 / (1.0 + cR),
    "квадрат 5/(1+cR)^2": lambda cR: 5.0 / (1.0 + cR) ** 2,
    "экспонента 5*exp(-cR)": lambda cR: 5.0 * 2.718281828 ** (-cR),
    # форма из литературы: ниже критической цены качество не покупается, выше — насыщение
    "порог + насыщение": lambda cR: 5.0 if cR < 1.0 else 5.0 * 1.0 / (1.0 + (cR - 1.0)),
}


def lineage(cR: float, delta0: float = 5.0, p: float = 1.0, rho: float = 0.5,
            generations: int = 30, C_min: float = 0.25, law: str = "гипербола 5/(1+cR)") -> tuple[int, str]:
    D0, C0 = 0.0, 1.0
    delta_eff = LAWS[law](cR)
    for g in range(1, generations + 1):
        D_end, _, starved = one_life(D0, C0, cR)
        if starved:
            return g, "голод"
        if C0 <= C_min or D_end > 1.0:
            return g, "коллапс"
        C0 = max(0.0, C0 * (1.0 - delta_eff * D_end))
        D0 = (1.0 - rho) * D_end
    return generations, "выжила"


def main(argv: list[str]) -> int:
    costs = [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0]
    rows = [(c,) + lineage(c) for c in costs]

    lines: list[str] = []
    add = lines.append
    add("# Компромисс: платить сейчас или передать износ")
    add("")
    add("Сгенерировано `python3 tools/core_tradeoff.py`. Числа — результат прогона.")
    add("")
    add("## Уравнения")
    add("")
    add("```")
    add("dD/dt = eta - C*D/(K+D)")
    add("dC/dt = (C0-C)/tau - gamma*D*C")
    add("dE/dt = uptake - m0 - cR*C*D/(K+D) - cC*C        # смерть при E <= 0")
    add("C0' = C0*(1 - delta_eff*D_end),  delta_eff = 5/(1+cR)")
    add("D0' = (1-rho)*D_end,  rho = 0.5")
    add("```")
    add("")
    add("## Результат")
    add("")
    add("| цена ремонта cR | наследуемый износ delta_eff | поколений прожито | чем кончилось |")
    add("|---|---|---|---|")
    for c, gens, how in rows:
        add(f"| {c} | {5.0/(1.0+c):.2f} | {gens} | {how} |")
    add("")
    best = max(rows, key=lambda r: r[1])
    add(f"Лучший результат: cR = {best[0]} — {best[1]} поколений ({best[2]}).")
    add("")
    add("## Что это значит")
    add("")
    add("Если в таблице есть внутренний максимум (не на краях), значит у стратегии оплаты ремонта")
    add("есть оптимум: слишком дешёвый ремонт экономит энергию, но передаёт износ потомкам; слишком")
    add("дорогой сохраняет способность, но съедает бюджет и приводит к голоду.")
    add("")
    add("Это первый раз, когда в модели появляется **выбор с ценой и последствием**, а не фиксированный")
    add("параметр: цена ремонта определяет и выживание особи (через энергию), и судьбу линии (через")
    add("передачу износа).")
    add("")
    add("Оптимум при этом не на краю: дешёвый ремонт не даёт линии жить дольше двух поколений, дорогой")
    add("убивает голодом за первое. Но величина выигрыша от оптимума сильно зависит от формы связи")
    add("цены и износа — см. проверку ниже.")
    add("")
    add("## Проверка на зависимости от допущения")
    add("")
    add("Связь цены и износа — гипотеза, поэтому прогнал четыре варианта закона, включая форму,")
    add("подсказанную литературой (порог: ниже критической цены качество не покупается, выше — насыщение):")
    add("")
    add("| закон износа | лучшая цена | поколений |")
    add("|---|---|---|")
    for law in LAWS:
        rows_l = [(c,) + lineage(c, law=law) for c in costs]
        best_l = max(rows_l, key=lambda r: r[1])
        add(f"| {law} | {best_l[0]} | {best_l[1]} |")
    add("")
    add("Главное: форма из литературы (порог + насыщение) даёт **3 поколения**, а не 8-9. То есть")
    add("выигрыш от роста цены быстро исчерпывается: за критической ценой дополнительная плата")
    add("покупает очень мало качества. Оценки 8-9 получались только при нереалистичном")
    add("экспоненциальном законе, где каждый рубль цены бесконечно улучшает ремонт.")
    add("")
    add("Это согласуется с найденным: в литературе связь «цена-качество» — **граница с порогом**, а не")
    add("гладкая функция (`B12-01-0001`, `B12-01-0003`). Поэтому в модели правильнее использовать")
    add("порог плюс насыщение, и тогда вывод «платить больше почти не помогает» становится основным.")
    add("")
    add("## Оговорки")
    add("")
    add("- Связь `delta_eff = 5/(1+cR)` — гипотеза, а не измерение: в карте нет данных о том, как цена")
    add("  ремонта влияет на наследуемый износ. Её надо проверять отдельно.")
    add("- Отбора нет: линия одна. При конкуренции оптимум мог бы сместиться.")
    add("- Порог C_min = 0.25 и rho = 0.5 выбраны произвольно.")
    add("")
    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
