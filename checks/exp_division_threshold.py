"""EXP-DIVISION-THRESHOLD: цена разделения через поток.

## Вопрос

`FINDING-290` и `FINDING-292` измерили руками: разделение живо, когда часть производит избыток, и цена его —
**равновесие**, а не константа. Здесь те же плечи записаны по контракту `AGENTS.md` §1–§6.

## Арифметика (§1), до прогона

```
приход  = yield · q_a · d_a
расход  = 1.5·need_a + q_b·d_b
при q_a = 0.300, q_b = 0.200, d = 0.05:  расход = 0.015 + 0.010 = 0.025
порог:  yield ≥ 0.025 / (0.300 · 0.05) = 1.667
```

Значит `yield = 1.0` и `1.5` ниже порога (гибнут), `2.0` и `3.0` выше (живут).

## Контроли (§2)

- `fires` — плечо A (`yield = 1.0`) **обязано** погибнуть: контроль видит смерть там, где она есть.
- `silent` — плечо D (`yield = 3.0`) **обязано** выжить весь горизонт: контроль молчит на здоровом.
- `specific` — плечо E (`yield = 1.5`, но `stock_max` в сто раз больше) **тоже гибнет**: значит дело в балансе, а не
  в размере буфера. Соседний дефект (буфер) вердикт не двигает.
"""

from __future__ import annotations

import json
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

HORIZON = 200_000


def run_arms() -> list[dict]:
    out = subprocess.run(
        ["cargo", "run", "--release", "--quiet", "--example", "organ_division_arms"],
        cwd=ROOT / "core",
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if out.returncode != 0:
        raise SystemExit(f"example failed: {out.stderr[-2000:]}")
    arms = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            arms.append(json.loads(line))
    if len(arms) != 5:
        raise SystemExit(f"expected five arms, got {len(arms)}")
    return arms


def main() -> int:
    exp = Experiment(
        experiment_id="EXP-DIVISION-THRESHOLD",
        question="живёт ли разделение через поток, когда часть производит избыток, и где именно его порог?",
        arithmetic={
            "inflow": "yield * q_a * d_a",
            "outflow": "1.5 * need_a + q_b * d_b",
            "q_a_settled": 0.300,
            "q_b_settled": 0.200,
            "d": 0.05,
            "predicted_threshold_yield": 0.025 / (0.300 * 0.05),
            "horizon": HORIZON,
        },
        arms={
            "A": "yield=1.0",
            "B": "yield=1.5",
            "C": "yield=2.0",
            "D": "yield=3.0",
            "E": "yield=1.5, stock_max=100000",
        },
        seed=20261119,
        command="python3 checks/exp_division_threshold.py",
    )

    arms = run_arms()
    by_key = {a["arm"]: a for a in arms}
    for a in arms:
        exp.add_arm(
            a["arm"],
            a["label"],
            {
                "alive": a["alive"],
                "steps": a["steps"],
                "q_a": a["q_a"],
                "q_b": a["q_b"],
            },
            trace_hash=a["hash"],
        )

    # §5: two arms coincide BY CONSTRUCTION, and that coincidence is itself a result
    #   C и D - выше порога починка упирается в свой предел (`1.5 * need`), поэтому лишний избыток не меняет ничего;
    #   B и E - потолок запаса не связывает: дело в балансе, а не в буфере.
    exp.expect_coincident("C", "D")
    exp.expect_coincident("B", "E")

    # §2 controls
    exp.control(
        "fires",
        not by_key["A"]["alive"],
        f"A (yield=1.0) dies at step {by_key['A']['steps']} - below the balance",
    )
    exp.control(
        "silent",
        by_key["D"]["alive"],
        f"D (yield=3.0) lives the whole horizon of {HORIZON}",
    )
    exp.control(
        "specific",
        not by_key["E"]["alive"],
        f"E (yield=1.5 with a 100x stock) still dies at step {by_key['E']['steps']} - the buffer is not the cause",
    )

    # §6
    exp.limitation("две части, один набор распадов (d = 0.05) и одна цена починки")
    exp.limitation("yield задан извне, а не выработан формой")
    exp.limitation("горизонт 200 000 шагов: смерть после него неотличима от бессмертия")
    exp.limitation("порог измерен бисекцией в FINDING-292, здесь проверены только пять точек")

    # §4
    below = not by_key["A"]["alive"] and not by_key["B"]["alive"]
    above = by_key["C"]["alive"] and by_key["D"]["alive"]
    if below and above:
        exp.verdict(
            "passed",
            "ниже предсказанного порога 1.667 обе части гибнут, выше - обе живут; "
            "C и D совпали потому, что выше порога починка упирается в предел, а B и E - потому что потолок запаса "
            "не связывает: причина в балансе, не в буфере",
        )
    elif above:
        exp.verdict("failed", "выше порога живут, но и ниже порога выжило плечо, которого там быть не должно")
    else:
        exp.verdict("failed", "выше порога не выжило ни одно плечо - баланс не подтвердился")

    path = exp.save()
    print(f"записано: {path}")
    print(f"АРИФМЕТИКА: порог yield = {0.025 / (0.300 * 0.05):.4f}")
    for a in arms:
        print(f"  {a['arm']}: {a['label']:<28} живой={a['alive']!s:<5} шагов={a['steps']:<7} hash={a['hash'][:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
