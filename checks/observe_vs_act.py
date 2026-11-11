"""Наблюдение vs воздействие: три условия на одинаковых начальных состояниях.

## Вопрос

Принцип проекта: «среда не измеряет». Но это смешивает три вещи:

  A. наблюдение
  B. оценивание
  C. обратное воздействие

## Эксперимент

Три условия, одинаковые seed и начальные состояния:

  A. контроль: никто не смотрит
  B. наблюдатель: читает и пишет в лог, но НЕ влияет
  C. управляющая связь: читает и меняет ширину комнаты

## Артефакты

Результат сохраняется в `results/observe-vs-act/<run_id>.json`.
Визуализатор читает его, не пересчитывая.

Запуск: python3 checks/observe_vs_act.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import result as R

B0 = 2.0
SIGMA = 0.3
N = 4000
STEPS = 3000
SEED = 20250101
GAIN = 1.2
WMIN, WMAX = 0.5, 4.0


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def run(condition: str, seed: int = SEED):
    rng = np.random.default_rng(seed)
    pop = rng.normal(0.0, 0.5, N)
    width = B0
    widths, spreads = [], []

    for _ in range(STEPS):
        if condition in ("B", "C"):
            s = float(pop.std())
            if condition == "C":
                width = float(np.clip(GAIN * s, WMIN, WMAX))

        widths.append(width)
        spreads.append(float(pop.std()))
        pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, N), width)

    return {
        "mean": float(pop.mean()),
        "spread": float(pop.std()),
        "widths": widths,
        "spreads": spreads,
    }


def main() -> int:
    res = R.new_result(
        experiment_id="observe-vs-act",
        seed=SEED,
        parameters={
            "B0": B0, "sigma": SIGMA, "N": N, "steps": STEPS,
            "gain": GAIN, "width_min": WMIN, "width_max": WMAX,
        },
        command="python3 checks/observe_vs_act.py",
    )

    labels = {
        "A": "никто не смотрит",
        "B": "наблюдатель пишет в лог",
        "C": "управляющая связь",
    }

    data = {}
    for cond in ("A", "B", "C"):
        d = run(cond)
        data[cond] = d
        R.add_condition(res, cond, labels[cond], {
            "mean": d["mean"],
            "spread": d["spread"],
            "width_min": float(min(d["widths"])),
            "width_max": float(max(d["widths"])),
        })
        # Downsample the series so the JSON stays small: every 10th step.
        R.add_series(res, cond,
                     [float(i) for i in range(0, STEPS, 10)],
                     [d["spreads"][i] for i in range(0, STEPS, 10)])

    sA, sB, sC = data["A"]["spread"], data["B"]["spread"], data["C"]["spread"]
    res["comparisons"] = {
        "B_vs_A": {"diff_pct": abs(sA - sB) / sA * 100},
        "C_vs_A": {"diff_pct": abs(sA - sC) / sA * 100},
    }

    R.add_limitation(res, "Одна модель, один набор параметров.")
    R.add_limitation(res, "Наблюдатель только читает; думающий наблюдатель — это уже воздействие.")
    R.add_limitation(res, "75% — для этой связи, не универсально.")

    path = R.save(res)

    print("# Наблюдение vs воздействие")
    print()
    print(f"B0 = {B0}, sigma = {SIGMA}, N = {N}, steps = {STEPS}")
    print()
    print("условие   mean      spread    ширина (мин/макс)")
    print("-" * 58)
    for cond in ("A", "B", "C"):
        d = data[cond]
        print(f"  {cond}       {d['mean']:+.4f}   {d['spread']:.4f}    "
              f"{min(d['widths']):.2f} / {max(d['widths']):.2f}")
    print()
    print(f"  B против A: {res['comparisons']['B_vs_A']['diff_pct']:.6f}%")
    print(f"  C против A: {res['comparisons']['C_vs_A']['diff_pct']:.2f}%")
    print()
    print(f"Результат сохранён: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
