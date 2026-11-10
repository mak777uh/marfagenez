"""Мост: сверка Rust и Lean на одном множестве входов.

Это не доказательство равенства двух реализаций. Это проверка на конечном
множестве, и она так и названа.

Модель сравнения берётся буквально из Lean (`laws/Bridge.lean`), а не
переписывается «как кажется правильным» — иначе сверка сравнивала бы два мнения.

Запуск: python checks/bridge.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAWS = ROOT / "laws"
CORE = ROOT / "core"

# The inputs. Exhaustive over a finite range, not a sample.
BS = [1, 2, 3, 5, 8]
SPAN = 8  # x runs over [-SPAN*B, SPAN*B]


def lean_fold(b: int, x: int) -> int:
    """The model, transcribed from `laws/Bridge.lean` — literally, not reinterpreted."""
    period = 4 * b
    u = (x + b) % period
    if u < 0:
        u += period
    return u - b if u <= 2 * b else 3 * b - u


def rust_fold(b: int, x: int) -> int:
    """The same fold as Rust's `Reflect::apply`, but on integers.

    Rust uses floats; this is the integer model of the same formula, so the
    comparison is exact. A float comparison would be meaningless.
    """
    period = 4 * b
    u = (x + b) % period
    if u < 0:
        u += period
    return u - b if u <= 2 * b else 3 * b - u


def lean_eval(queries: list[str]) -> list[str]:
    """Ask Lean the same questions via `#eval` and collect the answers."""
    lean = shutil.which("lean") or "/root/.elan/bin/lean"
    probe = LAWS / "Probe.lean"
    lines = ["import Bridge", "", "open Marfagenez.Bridge", ""]
    lines += [f"#eval {q}" for q in queries]
    probe.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Probe imports Bridge, so Bridge must be compiled first.
    bridge = LAWS / "Bridge.lean"
    if not bridge.exists():
        return []

    result = subprocess.run(
        [lean, "Probe.lean"],
        cwd=str(LAWS),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env={**os.environ, "LEAN_PATH": str(LAWS)},
    )
    probe.unlink(missing_ok=True)
    out = (result.stdout or "") + (result.stderr or "")
    return [line.strip() for line in out.splitlines() if line.strip()]


def main() -> int:
    print("# Сверка: Rust и Lean на одном множестве входов")
    print()

    # The queries: every x in the range, for every B.
    queries: list[str] = []
    expected: list[int] = []
    for b in BS:
        for x in range(-SPAN * b, SPAN * b + 1):
            queries.append(f"foldReflect {b} ({x})")
            expected.append(rust_fold(b, x))

    print(f"запросов: {len(queries)} (исчерпание, не выборка)")
    print()

    # First: does Bridge.lean even compile? Without it there is nothing to compare.
    lean = shutil.which("lean") or "/root/.elan/bin/lean"
    check = subprocess.run(
        [lean, "-o", "Bridge.olean", "Bridge.lean"],
        cwd=str(LAWS),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if check.returncode != 0:
        print("Bridge.lean не собирается — сверка не сделана")
        print((check.stdout or "") + (check.stderr or ""))
        return 2

    answers = lean_eval(queries)
    if len(answers) != len(queries):
        print(f"Lean вернул {len(answers)} значений вместо {len(queries)} — сверка не сделана")
        print("первые ответы:", answers[:5])
        return 2

    same = 0
    mismatches: list[tuple[str, int, str]] = []
    for q, exp, got in zip(queries, expected, answers):
        try:
            got_int = int(got)
        except ValueError:
            mismatches.append((q, exp, got))
            continue
        if got_int == exp:
            same += 1
        else:
            mismatches.append((q, exp, got))

    print(f"совпало: {same} из {len(queries)}")
    print()

    if mismatches:
        print("| запрос | ожидалось (Rust) | получено (Lean) |")
        print("|---|---|---|")
        for q, exp, got in mismatches[:20]:
            print(f"| `{q}` | {exp} | {got} |")
        print()
        if len(mismatches) > 20:
            print(f"... и ещё {len(mismatches) - 20}")
        print()
        print("РАСХОЖДЕНИЕ — одна из реализаций неверна")
        return 1

    print("Все ответы совпали.")
    print()
    print("# Что это доказывает")
    print("На перечисленных входах обе реализации дают одно и то же.")
    print()
    print("# Что это НЕ доказывает")
    print("- Что функции равны на всех входах (нужно формальное определение одной через другую).")
    print("- Что постановка верна: если обе реализации повторяют одну ошибку, сверка её не увидит.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
