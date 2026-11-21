#!/usr/bin/env python3
"""rho_surplus.py -- is the "window" defined against income or against the surplus?

`README` defines `rho = damage_rate * repair_cost / income` and asks a run that claims to measure life to
show `rho` inside a window. Review 2026-11-21 (§ params) pointed out the defect: `rho` unlike the surplus
hides death. A world with `income = 1.0`, `maintenance = 0.99` has `rho = 0.015` -- comfortably "inside" --
while nothing is left to keep the organism alive.

The honest quantity is

    rho_s = damage_rate * repair_cost / (income - maintenance)

with `income - maintenance <= 0` meaning "no window exists at all".

This script classifies every recorded run by both quantities and prints the runs that the old rule
would call "inside the window" while the surplus rule says "no window". It is a diagnostic: it reports,
it does not fail the gate.
"""
import glob
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WINDOW = 0.05   # the generous end of the "0.01 .. 0.05" window used in the docs


def params(run):
    p = run.get("parameters") or {}
    world = p.get("world") if isinstance(p.get("world"), dict) else p
    def g(*names, default=None):
        for n in names:
            if isinstance(world, dict) and n in world:
                return world[n]
            if n in p:
                return p[n]
        return default
    return (g("income"), g("maintenance_cost", "maintenance"), g("damage_rate"), g("repair_cost"))


def main():
    runs = []
    for path in sorted(glob.glob(str(ROOT / "results" / "*" / "run-*.json"))):
        try:
            d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        income, maintenance, dr, rc = params(d)
        try:
            income, maintenance, dr, rc = float(income), float(maintenance), float(dr), float(rc)
        except (TypeError, ValueError):
            continue
        row = {"exp": d.get("experiment_id") or pathlib.Path(path).parent.name,
               "run": d.get("run_id") or pathlib.Path(path).stem,
               "income": income, "maintenance": maintenance, "dr": dr, "rc": rc}
        row["rho"] = dr * rc / income if income > 0 else float("inf")
        surplus = income - maintenance
        row["surplus"] = surplus
        row["rho_s"] = dr * rc / surplus if surplus > 0 else float("inf")
        runs.append(row)

    print("записанных прогонов с параметрами: " + str(len(runs)))
    if not runs:
        return 0
    controls = [r for r in runs if r["income"] == 0]
    dead = [r for r in runs if r["surplus"] <= 0 and r["income"] > 0]
    false_window = [r for r in runs if r["rho"] <= WINDOW and r["surplus"] <= 0 and r["income"] > 0]
    print("контрольных плеч без дохода (income = 0, смерть и есть предмет): " + str(len(controls)))
    print("миров с доходом, но без избытка (income <= maintenance): " + str(len(dead)))
    print("случаев, где старое rho <= " + str(WINDOW) + ", а избытка нет: " + str(len(false_window)))
    for r in false_window[:8]:
        print("  %-28s rho=%.4f  income=%.2f  maintenance=%.2f  surplus=%.2f" % (
            r["exp"][:28], r["rho"], r["income"], r["maintenance"], r["surplus"]))
    in_window = [r for r in runs if 0 < r["rho_s"] <= WINDOW]
    print("в окне по rho_s: " + str(len(in_window)) + " из " + str(len(runs)))
    if false_window:
        print()
        print("  ДИАГНОЗ: rho против дохода пропускает смертельные миры как «в окне».")
        print("  Определение окна должно быть против избытка: rho_s = dr*rc/(income - maintenance).")
        print("  Подробности: docs/FINDING-325-rho-window.md")
    else:
        print("  ложных «в окне» миров в корпусе нет: правило ещё не ошиблось, но уже неправильное.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
