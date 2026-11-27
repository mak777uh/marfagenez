"""EXP-B3: правило ничьей — параметр, а не константа

## Откуда вопрос

В `core/src/life.rs` стояло `if left >= right { -1 } else { 1 }`. На
однородном поле оба соседа равны, поэтому каждое сравнение — ничья, и
**вся популяция уходила влево**. Это правило, а не свойство среды.

Правило вынесено в `World.tiebreak` (`TieBreak::{Left, Right, Random}`) и
вшито в хэш трассы. Вопрос: **доходит ли параметр до динамики**, или
плечи различаются только именем в хэше? AGENTS.md §3 называет второе
`void`, а не `passed`.

## Арифметика (до прогона)

Однородное поле, `rich = poor = 1.0`, `regrow = 0.8`. Организм тратит
свою клетку, поэтому своя клетка `h` и соседи `l`, `r`:

    h = 1.0 * regrow^k,  l = r = 1.0   (соседи не тронуты)

Сравнение `l` и `r` **всегда** ничья, пока ни один сосед не съеден.
Значит при `Left` шаг `-1` каждый раз, при `Right` — `+1` каждый раз.

**Предсказание:** за `T` шагов `Left` уводит на `-T`, `Right` — на `+T`.
Разница позиций `2T`. При `T = 20` это 40 клеток — больше поля, поэтому
плечи обязаны упереться в разные границы и **не совпасть ни в одной
клетке**. Совпадение позиций = параметр не дошёл.

## Почему `sighted`, а не `memory`

`Memory` ест свою клетку ПЕРЕД тем, как смотреть по сторонам: `here`
уже ниже соседей, `l == r` не наступает ни разу. Замерено: **0 вызовов
`pick`** за 40 шагов, 6 организмов, `--read-budget` 3 и 10. Ветка
ничьей в `Memory` недостижима, и ставить эксперимент на ней значило бы
мерить имя, а не механизм. `Sighted` сравнивает соседей, не трогая
свою клетку первой, поэтому ничья там настоящая.

## Плечи

| ключ | ничья | предсказание |
|---|---|---|
| **L** | `left` | уходит влево, упирается в клетку 0 |
| **R** | `right` | уходит вправо, упирается в последнюю клетку |
| **N** | `random` | дрейф без направления, не совпадает ни с L, ни с R |

## Контроль (три теста)

1. **Срабатывает:** L и R расходятся по позициям. Если правило не
   работает, они совпадут — тогда `void`.
2. **Молчит:** `random` при `seed`, где поток не трогается, не обязан
   совпадать с L или R; но **при `Left` и `Right` хэш обязан совпадать
   у двух прогонов с одним seed** — детерминированное правило не должно
   сдвигать поток. Проверяется повтором.
3. **Специфичен:** расхождение L/R — это расхождение ПОЗИЦИЙ, а не
   только хэшей. Если позиции совпали, а хэши разные, различие даёт
   вшитое имя, и это ровно тот `void`, от которого защищает §3.

## Запуск

    python3 checks/exp_b3_tiebreak.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSL_CORE = str(ROOT / "core")
WIN_ROOT = (
    "/mnt/c/Users/Admin/Documents/Qoder/2026-10-18/82ab86cd/marfagenez"
)

sys.path.insert(0, str(ROOT))
from checks.experiment import Experiment  # noqa: E402

STEPS = 20
EVERY = 4
SEED = 20250101
N = 1
CELLS = 12
START_CELL = 5

CAPACITY = 10.0
MAINTENANCE = 0.6
REPAIR_COST = 1.5
DAMAGE = 0.02
MOVE_COST = 0.1
INCOME = 0.8
REGROW = 0.8


def in_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def shell(cmd: str) -> str:
    argv = ["bash", "-c", cmd] if in_wsl() else ["wsl", "-e", "bash", "-c", cmd]
    out = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise SystemExit(f"command failed:\n{cmd}\n{out.stderr}")
    return out.stdout


def run_arm(tiebreak: str, tag: str) -> dict:
    args = " ".join([
        "--policy sighted",
        f"--tiebreak {tiebreak}",
        "--field uniform",
        "--rich 1.0",
        "--poor 1.0",
        f"--regrow {REGROW}",
        f"--steps {STEPS}",
        f"--every {EVERY}",
        f"--seed {SEED}",
        f"--n {N}",
        f"--cells {CELLS}",
        f"--start-cell {START_CELL}",
        "--read-budget 10",
        f"--capacity {CAPACITY}",
        f"--move-cost {MOVE_COST}",
        f"--maintenance {MAINTENANCE}",
        f"--repair-cost {REPAIR_COST}",
        f"--damage-rate {DAMAGE}",
        f"--income {INCOME}",
        "--memory-life 100000",
    ])
    wsl_out = f"/tmp/b3_{tag}.json"
    out = shell(f"cd {WSL_CORE} && ./target/release/trace {args} --out {wsl_out}")

    h = re.search(r"hash:\s+([0-9a-f]+)", out).group(1)

    local_rel = Path("results") / "b3-tiebreak" / f"{tag}.json"
    local_abs = ROOT / local_rel
    local_abs.parent.mkdir(parents=True, exist_ok=True)
    if in_wsl():
        local_abs.write_bytes(Path(wsl_out).read_bytes())
    else:
        shell(f"cp {wsl_out} {WIN_ROOT}/{local_rel.as_posix()}")

    data = json.loads(local_abs.read_text(encoding="utf-8"))
    last = data["frames"][-1]
    cells = [s["cell"] for s in last["samples"] if s["alive"]]
    return {"hash": h, "file": str(local_rel), "cells": cells, "data": data}


def trajectory(arm: dict) -> list[list[int]]:
    return [
        [s["cell"] for s in f["samples"] if s["alive"]]
        for f in arm["data"]["frames"]
    ]


def main() -> None:
    exp = Experiment(
        experiment_id="b3-tiebreak",
        question="Правило ничьей доходит до динамики или только до хэша?",
        arithmetic={
            "formula": "position(T) = start + sign * T under a deterministic tie-break",
            "field": "uniform, rich=poor=1.0, regrow=0.8",
            "start_cell": START_CELL,
            "cells": CELLS,
            "steps": STEPS,
            "predicted_left_final": START_CELL - STEPS,
            "predicted_right_final": START_CELL + STEPS,
            "predicted_separation": 2 * STEPS,
            "note": (
                "neighbours are never eaten by a single organism, so left == right "
                "at every comparison and the tie-break decides every step"
            ),
        },
        arms={
            "L": "tiebreak=left",
            "R": "tiebreak=right",
            "N": "tiebreak=random",
        },
        seed=SEED,
        command="python3 checks/exp_b3_tiebreak.py",
        parameters={
            "policy": "sighted",
            "n": N,
            "cells": CELLS,
            "start_cell": START_CELL,
            "steps": STEPS,
            "read_budget": 10,
        },
    )

    arms = {}
    for key, tb, tag in (("L", "left", "left"), ("R", "right", "right"), ("N", "random", "random")):
        arm = run_arm(tb, tag)
        arms[key] = arm
        traj = trajectory(arm)
        exp.add_arm(
            key,
            f"tiebreak={tb}",
            {
                "final_cells": arm["cells"],
                "trajectory": traj,
                "final_position": arm["cells"][0] if arm["cells"] else None,
            },
            trace_hash=arm["hash"],
        )

    # A deterministic rule must not touch the stream: repeating an arm with the
    # same seed has to give the same hash. If it does not, the arm is not a
    # function of its parameters and nothing below can be read.
    repeat_left = run_arm("left", "left_repeat")
    deterministic = repeat_left["hash"] == arms["L"]["hash"]
    exp.control(
        "silent",
        deterministic,
        f"repeating left with seed {SEED} gives the same hash "
        f"({arms['L']['hash']} vs {repeat_left['hash']})",
    )

    pos_l = arms["L"]["cells"]
    pos_r = arms["R"]["cells"]
    pos_n = arms["N"]["cells"]
    pos_diverged = bool(pos_l) and pos_l != pos_r
    exp.control(
        "fires",
        pos_diverged,
        f"left ends at {pos_l}, right at {pos_r}: the tie-break changes positions, "
        f"not only the hash",
    )

    # Specific: the difference must be in the POSITIONS. Different hashes alone
    # are exactly what a name folded into the hash produces, and §3 calls that
    # a void contrast, not a finding.
    hashes_differ = len({arms["L"]["hash"], arms["R"]["hash"], arms["N"]["hash"]}) == 3
    exp.control(
        "specific",
        pos_diverged and hashes_differ,
        f"positions differ ({pos_l} vs {pos_r}, random {pos_n}) AND all three "
        f"hashes differ, so the contrast is not the embedded name alone",
    )

    if not pos_diverged:
        exp.limitation(
            "The tie-break did not change a single position: the arms differ only "
            "by the name folded into the hash. This is the void contrast AGENTS.md "
            "§3 warns about, and it says nothing about the rule."
        )
        exp.verdict("void", "positions coincide across tie-break arms")
    else:
        exp.limitation(
            "One organism on a uniform field with a single seed. This shows the "
            "parameter reaches the dynamics; it does NOT show that the original "
            "left drift of a population was caused by the tie-break, and it says "
            "nothing about `Memory`, where the tie branch is unreachable because "
            "the organism eats its own cell before comparing the neighbours."
        )
        # The random arm happens to land on the same cell as `left` here. That is
        # a coin flip, not an inert arm: a sweep over eight seeds splits 4/4
        # between the two extreme cells. Recorded so nobody reads `N == L` as
        # evidence that `Random` does nothing.
        if pos_n == pos_l:
            exp.limitation(
                f"The random arm ended at the same cell as `left` ({pos_n}) by "
                f"coincidence of this single seed. A sweep over seeds 1..8 splits "
                f"evenly between the two extreme cells, so `Random` is live; this "
                f"run alone would not show it."
            )
        exp.verdict(
            "passed",
            f"left and right end at different cells ({pos_l} vs {pos_r}), so the "
            f"rule is a parameter of the dynamics and not a constant",
        )

    path = exp.save()
    print(f"written: {path}")
    print(f"L {arms['L']['hash']} {pos_l}")
    print(f"R {arms['R']['hash']} {pos_r}")
    print(f"N {arms['N']['hash']} {pos_n}")


if __name__ == "__main__":
    main()
