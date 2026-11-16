"""Минимально детектируемый эффект (MDE): сколько плеч нужно, чтобы увидеть Δ.

## Зачем

`PROTOCOL-0` п. 3 требует рядом с `arithmetic` поле `mde`. Горизонт отвечает
на вопрос «успеет ли мир ответить»; `mde` — на другой: «увидим ли мы ответ,
если он есть». Прогон на 30 сидах при σ ≈ 0.2 различает только эффекты
≳ 10 %. Всё меньшее — `void`, а не `failed`: инструмент не увидел эффект,
мир не сказал «нет».

## Формула

    n = 2·(z_{α/2} + z_β)²·σ² / Δ²

σ — разброс изучаемой величины **между сидами** (не внутри прогона),
Δ — эффект в тех же единицах, α = 0.05 (двусторонний), мощность 0.8.

При σ = 0.2: 6280 плеч для 1 %, 252 для 5 %, 63 для 10 %.

## Запуск

    python3 checks/mde.py             # таблица 3 σ × 3 Δ
    python3 checks/mde.py --selftest  # таблица сверяется с зашитыми числами
    python3 checks/mde.py --sigma 0.2 --effect 0.05

`--selftest` — гейт: числа 393/16/4, 6280/252/63, 39245/1570/393 зашиты в
этом файле и обязаны совпасть с тем, что считает `checks/result.py:set_mde`.
Зашитые числа взяты из внешнего разбора (`docs/REVIEW-emergence-notes.md`
§3.1), поэтому расхождение — это либо ошибка кода, либо ошибка разбора,
и молчать о нём нельзя.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from result import arms_needed, set_mde  # noqa: E402

SIGMAS = (0.05, 0.20, 0.50)
EFFECTS = (0.01, 0.05, 0.10)

#: Rows are σ between seeds, columns are Δ (1 %, 5 %, 10 %).
EXPECTED = {
    (0.05, 0.01): 393,
    (0.05, 0.05): 16,
    (0.05, 0.10): 4,
    (0.20, 0.01): 6280,
    (0.20, 0.05): 252,
    (0.20, 0.10): 63,
    (0.50, 0.01): 39245,
    (0.50, 0.05): 1570,
    (0.50, 0.10): 393,
}


def table() -> None:
    print("σ между сидами | Δ = 1 % | Δ = 5 % | Δ = 10 %")
    print("---|---|---|---")
    for sigma in SIGMAS:
        cells = " | ".join(str(arms_needed(sigma, effect)) for effect in EFFECTS)
        print(f"{sigma:.2f} | {cells}")


def selftest() -> int:
    bad = 0
    print("таблица (σ × Δ):")
    for sigma in SIGMAS:
        for effect in EFFECTS:
            got = arms_needed(sigma, effect)
            want = EXPECTED[(sigma, effect)]
            ok = got == want
            bad += not ok
            print(
                f"  {'OK  ' if ok else 'FAIL'} σ={sigma:.2f} Δ={effect:.2f} "
                f"-> {got} (ожидалось {want})"
            )

    # `set_mde` must write the same number it computes, and the field must be
    # the part of the measurement that appears only when it is asked for.
    result: dict = {}
    set_mde(result, 0.20, 0.05)
    got = (result.get("mde") or {}).get("arms_needed")
    ok = got == 252
    bad += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} set_mde(σ=0.20, Δ=0.05) -> {got} (ожидалось 252)")

    # Scaling: four times the seed spread needs four times the arms.
    ok = arms_needed(0.40, 0.10) == 4 * arms_needed(0.20, 0.10)
    bad += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} 4·σ ⇒ 4·n (Δ = 10 %)")

    # A negative or zero effect is not a question; it must raise, not divide.
    try:
        arms_needed(0.2, 0.0)
        ok = False
    except ValueError:
        ok = True
    bad += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} Δ = 0 отвергается, а не делится на ноль")

    total = len(SIGMAS) * len(EFFECTS) + 3
    print()
    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MDE: arms needed to detect an effect")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--sigma", type=float)
    parser.add_argument("--effect", type=float)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.sigma is not None and args.effect is not None:
        print(arms_needed(args.sigma, args.effect))
        return 0
    table()
    return 0


if __name__ == "__main__":
    sys.exit(main())
