"""Шаблон эксперимента по контракту `AGENTS.md`.

## Зачем

Каждый эксперимент обязан пройти пять проверок, и **порядок важен**:

1. **Арифметика ДО прогона** (§1). Что делает разницу: доход, расход,
   отношение, точка окупаемости. Если всё поле выше порога в обоих плечах —
   эксперимент нечувствителен по построению и **не запускается**.

2. **Контроль проходит три теста** (§2): срабатывает там, где эффект
   известен; молчит там, где его нет; специфичен — отделяет механизм от
   любого другого, дающего то же направление.

3. **Хэш каждого плеча** (§5). Два плеча с одинаковым хэшем — одно плечо.

4. **Вердикт из четырёх** (§4): `passed`, `failed`, `void`,
   `insensitive by construction`.

5. **«Что это не доказывает»** (§6).

## Почему класс, а не функция

Потому что порядок — часть контракта. Класс не даёт вызвать `verdict()`
до того, как записана арифметика, и не даёт сохранить результат без
вердикта.

## Использование

```python
from checks.experiment import Experiment

exp = Experiment(
    experiment_id="frozen-ceiling",
    question="9.37 — это потолок или равновесие?",
    arithmetic={
        "formula": "capacity - maintenance - damage_rate * repair_cost",
        "capacity": 10.0,
        "maintenance": 0.6,
        "damage_rate": 0.02,
        "repair_cost": 1.5,
        "predicted_ceiling": 9.37,
    },
    arms={"A": "capacity=100", "B": "capacity=10", "C": "damage=0.10"},
    seed=20250101,
    command="python3 checks/exp05_frozen.py",
)

exp.add_arm("A", "capacity=100", {"energy": 99.37}, trace_hash="a1b2c3d4")
exp.control("fires", True, "A: energy 99.37 > 9.37")
exp.verdict("passed", "все три плеча на предсказанных потолках")
exp.save()
```
"""

from __future__ import annotations

from typing import Any

from . import result as R


class ExperimentError(RuntimeError):
    """Raised when an experiment breaks the contract."""


class Experiment:
    """One experiment, checked against the contract as it is built."""

    def __init__(
        self,
        experiment_id: str,
        question: str,
        arithmetic: dict[str, Any],
        arms: dict[str, str],
        seed: int,
        command: str,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        if not arithmetic:
            raise ExperimentError(
                "arithmetic is required before the run (AGENTS.md §1)"
            )
        if not arms:
            raise ExperimentError("at least one arm is required")

        self.question = question
        self.arm_labels = dict(arms)
        self._arithmetic_done = True
        self._result = R.new_result(
            experiment_id=experiment_id,
            seed=seed,
            parameters=parameters or {},
            command=command,
        )
        R.set_arithmetic(self._result, arithmetic)

    # -- arms ---------------------------------------------------------------

    def add_arm(
        self,
        key: str,
        label: str,
        metrics: dict[str, Any],
        trace_hash: str | None = None,
    ) -> None:
        """Records one arm's metrics and its dynamics hash (§5)."""
        R.add_condition(self._result, key, label, metrics, trace_hash=trace_hash)

    def add_series(
        self, key: str, steps: list[float], values: list[float]
    ) -> None:
        R.add_series(self._result, key, steps, values)

    # -- controls -----------------------------------------------------------

    def control(self, test: str, passed: bool, evidence: str) -> None:
        """Records one of the three control tests (§2)."""
        R.add_control(self._result, test, passed, evidence)

    def controls_passed(self) -> bool:
        """True when all three control tests were recorded and all passed."""
        c = self._result["controls"]
        return all(c.get(t, {}).get("passed", False) for t in R.CONTROL_TESTS)

    def controls_recorded(self) -> bool:
        """True when all three control tests were recorded, pass or fail."""
        c = self._result["controls"]
        return all(t in c for t in R.CONTROL_TESTS)

    # -- hashes -------------------------------------------------------------

    def hashes(self) -> dict[str, str]:
        return dict(self._result["hashes"])

    def hashes_are_distinct(self) -> bool:
        """Two arms with the same hash are one arm (§5)."""
        h = list(self._result["hashes"].values())
        return len(h) == len(set(h))

    # -- limitations and verdict -------------------------------------------

    def limitation(self, text: str) -> None:
        """Records what the result does NOT show (§6)."""
        R.add_limitation(self._result, text)

    def verdict(self, kind: str, reason: str) -> None:
        """Sets the verdict (§4).

        Refuses `passed` when a control failed or the hashes coincide: those are
        `void`, and calling them `passed` is the failure this contract exists to
        prevent.
        """
        if kind == "passed":
            if not self.controls_recorded():
                raise ExperimentError(
                    "cannot pass: not all three control tests are recorded (§2)"
                )
            if not self.controls_passed():
                raise ExperimentError(
                    "cannot pass: a control test failed — the verdict is `void` (§2, §4)"
                )
            if not self.hashes_are_distinct():
                raise ExperimentError(
                    "cannot pass: two arms share a hash, so they are one arm (§5)"
                )
        R.set_verdict(self._result, kind, reason)

    # -- save ---------------------------------------------------------------

    def save(self) -> Any:
        """Saves the result. Refuses an incomplete one."""
        if self._result["verdict"] is None:
            raise ExperimentError("cannot save without a verdict (§4)")
        if not self._result["limitations"]:
            raise ExperimentError(
                "cannot save without a limitation (§6: what this does not prove)"
            )
        return R.save(self._result)

    @property
    def result(self) -> dict[str, Any]:
        return self._result
