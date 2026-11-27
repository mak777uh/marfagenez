#!/usr/bin/env python3
"""Fail-closed selftest do_kg (аудит 28.11.2026, P0).

Извлекает do_kg() из run.sh и прогоняет его в песочнице с фейковыми
kg/kg.py, kg/regress.py, checks/kg_edges.py, checks/bridge_price_derivative.py,
каждый из которых выходит с заданным кодом. Провал любой команды обязан
сделать do_kg красным и напечатать KG_SECTION_RED с номером виновника.
Раньше `local rrc=$?` читал статус OR-list (всегда 0), rc kg/regress.py не
сохранялся вовсе, bad=1 не доходил до return: раздел печатал FAIL и
оставался зелёным (гейт c896).
"""
import pathlib
import re
import subprocess
import sys
import tempfile

RUN_SH = pathlib.Path(__file__).resolve().parents[1] / "run.sh"

FAKE = {
    "kg/kg.py": "import sys; sys.exit({kg})",
    "kg/regress.py": "import sys; sys.exit({regress})",
    "checks/kg_edges.py": "import sys; sys.exit({edges})",
    "checks/bridge_price_derivative.py": "import sys; sys.exit({price})",
    # stub: извлечённый do_kg зовёт selftest; в песочнице он всегда зелёный,
    # чтобы rc do_kg определялся именно проверяемыми командами.
    "checks/gate_kg_fail_closed.py": "import sys; sys.exit(0)",
}


def extract_do_kg(src: str) -> str:
    m = re.search(r"^do_kg\(\) \{.*?^\}", src, re.M | re.S)
    assert m, "do_kg() не найден в run.sh"
    return m.group(0)


def run_case(src: str, rcs: dict):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        for rel, tpl in FAKE.items():
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(tpl.format(**rcs), encoding="utf-8")
        script = "section() { :; }\n" + extract_do_kg(src) + "\ndo_kg\n"
        p = subprocess.run(["bash", "-c", script], cwd=root,
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr


def main() -> int:
    src = RUN_SH.read_text(encoding="utf-8")
    cases = [
        (dict(kg=0, regress=0, edges=0, price=0), 0, None),
        (dict(kg=0, regress=1, edges=0, price=0), 1, "regress=1"),
        (dict(kg=0, regress=0, edges=3, price=0), 1, "KG_FAIL kg_edges.py"),
        (dict(kg=0, regress=0, edges=0, price=2), 1, "KG_FAIL bridge_price_derivative.py"),
        (dict(kg=1, regress=0, edges=0, price=0), 1, "check=1"),
    ]
    fails = 0
    for rcs, want_rc, marker in cases:
        rc, out = run_case(src, rcs)
        ok = rc == want_rc and (marker is None or marker in out)
        print(f"  case {rcs}: rc={rc} want={want_rc} {'OK' if ok else 'FAIL'}")
        if not ok:
            fails += 1
            print("    tail:", out[-300:])
    if fails:
        print(f"GATE_KG_SELFTEST_FAIL: {fails}/5 кейсов провалено")
        return 1
    print("GATE_KG_SELFTEST_OK: 5/5 кейсов")
    return 0


if __name__ == "__main__":
    sys.exit(main())
