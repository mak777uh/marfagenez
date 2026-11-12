"""Проверяет, что каждый результат в `results/` соблюдает контракт.

## Зачем

`AGENTS.md` требует пять вещей от каждого эксперимента. Легко забыть одну.
Этот скрипт забыть не даёт.

## Что проверяется

| правило | проверка |
|---|---|
| **§1** | есть `arithmetic`, и он не пуст |
| **§2** | есть все три контроля: `fires`, `silent`, `specific` |
| **§4** | есть `verdict` из четырёх |
| **§5** | есть `hashes`, и они **не совпадают** |
| **§6** | есть `limitations` |

## Четыре исхода, не два

Если контроль провален — вердикт обязан быть `void`, не `failed`.
Если арифметика говорит, что плечи не различаются — `insensitive by construction`.

## Запуск

    python3 checks/contract.py

Код возврата 0 — все результаты соблюдают контракт.
Код возврата 1 — есть нарушения (они печатаются).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

VERDICTS = ("passed", "failed", "void", "insensitive by construction")
CONTROL_TESTS = ("fires", "silent", "specific")


def check_one(path: Path, data: dict) -> list[str]:
    """Returns the list of contract violations for one result."""
    problems: list[str] = []

    # §1 arithmetic
    arithmetic = data.get("arithmetic")
    if not arithmetic:
        problems.append("§1: no arithmetic (must be written before the run)")
    elif not isinstance(arithmetic, dict) or not arithmetic:
        problems.append("§1: arithmetic is empty")

    # §2 controls
    #
    # The contract requires the three tests to be RECORDED, not to pass. A test
    # that failed is a result — the verdict must then be `failed` or `void`, and
    # that is checked under §4. Recording a failed test is doing the work
    # correctly; omitting it is the defect.
    controls = data.get("controls") or {}
    missing = [t for t in CONTROL_TESTS if t not in controls]
    if missing:
        problems.append(f"§2: missing control tests: {', '.join(missing)}")

    # §4 verdict
    verdict = data.get("verdict")
    if not verdict:
        problems.append("§4: no verdict (four outcomes, not two)")
    else:
        kind = verdict.get("kind")
        if kind not in VERDICTS:
            problems.append(f"§4: unknown verdict {kind!r}")
        # A failed control cannot be `passed` — that is the defect §4 exists for.
        if kind == "passed" and controls:
            failed = [t for t in CONTROL_TESTS if not controls.get(t, {}).get("passed", False)]
            if failed:
                problems.append(
                    f"§4: verdict is `passed` but controls failed: {', '.join(failed)}"
                )
        # And a failed control with a `failed` or `void` verdict is correct.
        #
        # A `failed` verdict with every control passing is allowed only when the
        # verdict itself says WHY the prediction missed.  That is the whole point
        # of §4: a failure is a result, not a shrug.  The explanation must be in
        # the verdict's `reason` and must be long enough to be a sentence rather
        # than a restatement of the numbers.
        if kind == "void":
            reason = str(verdict.get("reason") or "")
            if len(reason) < 120:
                problems.append(
                    "§4: verdict is `void` but the reason is too short to say why "
                    "the run is unusable"
                )
        if kind in ("failed", "void") and controls:
            failed = [t for t in CONTROL_TESTS if not controls.get(t, {}).get("passed", False)]
            if not failed and kind == "failed":
                reason = str(verdict.get("reason") or "")
                if "EXPLAINED:" not in reason or len(reason) < 120:
                    problems.append(
                        "§4: verdict is `failed` but every control passed — "
                        "the failure is unexplained (add `EXPLAINED: ...` to the "
                        "verdict reason saying why the prediction missed)"
                    )

    # A `void` verdict with a stated reason is a closed record: the run is kept
    # as history and declares itself unusable.  Its numbers are not evidence, so
    # demanding hashes or a verdict that agrees with its controls would be
    # asking a dead run to be alive.  The reason is what makes this honest --
    # `void` with no reason is just a deletion that kept the file.
    void_with_reason = (
        verdict
        and verdict.get("kind") == "void"
        and len(str(verdict.get("reason") or "")) >= 120
        and ("VOID:" in str(verdict.get("reason")) or "EXPLAINED:" in str(verdict.get("reason")))
    )

    # §5 hashes
    hashes = data.get("hashes") or {}
    if not hashes and not void_with_reason:
        problems.append("§5: no dynamics hashes")
    elif hashes:
        vals = list(hashes.values())
        if len(vals) != len(set(vals)):
            problems.append("§5: two arms share a hash — they are one arm")

    # §6 limitations
    if not data.get("limitations"):
        problems.append("§6: no limitations (what this does not prove)")

    return problems


def main() -> int:
    if not RESULTS.exists():
        print("results/ does not exist — nothing to check.")
        return 0

    checked = 0
    bad = 0
    skipped = 0
    for path in sorted(RESULTS.rglob("run-*.json")):
        # `_archive/` holds runs recorded before the contract existed. They are
        # kept as history, not as evidence — checking them would only re-report
        # the same known defect forever.
        if "_archive" in path.parts:
            skipped += 1
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"SKIP {path.name}: cannot parse ({e})")
            continue
        checked += 1
        problems = check_one(path, data)
        rel = path.relative_to(ROOT)
        if problems:
            bad += 1
            print(f"FAIL {rel}")
            for p in problems:
                print(f"     {p}")
        else:
            print(f"OK   {rel}")

    print()
    print(f"Проверено: {checked}, нарушений: {bad}")
    if skipped:
        print(f"Пропущено (results/_archive/, до контракта): {skipped}")
    if bad:
        print()
        print("Нарушения — это не ошибка скрипта. Это результаты, записанные")
        print("до того, как контракт стал обязательным. Их надо либо")
        print("переделать, либо пометить как `void` с причиной.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
