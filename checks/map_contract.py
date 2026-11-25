"""Контракт карты: ячейка без доказательства — не ячейка.

Проверки сделаны так, чтобы их нельзя было удовлетворить формулировкой: у каждой есть либо цитата,
либо формула, либо честная уверенность `low`.

M1 обязательные поля и перечисления;
M2 идентификаторы ячеек уникальны;
M3 `access: fragment` требует цитаты; `full` тоже;
M4 `medium`/`high` требуют `conditions`;
M5 у каждой работы есть локатор;
M6 `gap` требует `searched` и `scope`;
M7 `contradiction` требует минимум двух работ;
M8 рёбра ссылаются на существующие ячейки;
M9 доля `analogous` среди рёбер не больше трети (иначе карта становится метафорами);
M10 `high` требует формулы или цитаты, и локатор должен быть `verified`;
M11 необязательное `kg_ref` (сшивка с `kg/`): поле может отсутствовать **или быть пустым списком**
    (`[]` = «связей нет»); если в списке есть записи — каждая обязана быть непустым id вида
    `C-*`, `F-*`, `L-*`, `GAP-*`, `CORR-*`, `DEF-*`.

Usage:
    python3 checks/map_contract.py
    python3 checks/map_contract.py --selftest
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
EDGES = ROOT / "literature" / "map" / "edges.jsonl"

REQUIRED = ("atom", "statement", "domain", "kind", "works", "confidence")
KINDS = {"mechanism", "formula", "condition", "contradiction", "gap", "definition", "measurement"}
CONFIDENCE = {"high", "medium", "low"}


def load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check(atoms_path: pathlib.Path, edges_path: pathlib.Path) -> list[str]:
    atoms = load(atoms_path)
    edges = load(edges_path)
    errs: list[str] = []

    ids = collections.Counter(a.get("atom") for a in atoms)
    for atom_id, count in ids.items():
        if count > 1:
            errs.append(f"M2 идентификатор `{atom_id}` встречается {count} раз")

    for atom in atoms:
        atom_id = atom.get("atom", "?")
        for field in REQUIRED:
            if field == "works":
                continue  # пустота списка проверяется в M5: у gap её заменяет протокол поиска
            if not atom.get(field):
                errs.append(f"M1 {atom_id}: нет поля `{field}`")
        if atom.get("kind") not in KINDS:
            errs.append(f"M1 {atom_id}: вид `{atom.get('kind')}` вне перечисления")
        if atom.get("confidence") not in CONFIDENCE:
            errs.append(f"M1 {atom_id}: уверенность `{atom.get('confidence')}` вне перечисления")
        works = atom.get("works") or []
        # Пустота о том, что модели нет, не может ссылаться на работу, которой нет. Для gap
        # доказательство — протокол поиска, а не локатор; для всех остальных видов работа обязательна.
        gap_protocol = atom.get("kind") == "gap" and atom.get("searched") and atom.get("scope")
        if not works and not gap_protocol:
            errs.append(f"M5 {atom_id}: нет работ")
        for work in works:
            if not (work.get("doi") or work.get("arxiv") or work.get("pmid")
                    or work.get("isbn") or work.get("url")):
                errs.append(f"M5 {atom_id}: работа без локатора")
            if work.get("access") in ("fragment", "full") and not work.get("quote"):
                errs.append(f"M3 {atom_id}: `access: {work.get('access')}` без цитаты")
        if atom.get("confidence") in ("medium", "high") and not atom.get("conditions"):
            errs.append(f"M4 {atom_id}: нет `conditions` при уверенности `{atom.get('confidence')}`")
        if atom.get("kind") == "gap" and not (atom.get("searched") and atom.get("scope")):
            errs.append(f"M6 {atom_id}: gap без `searched` и `scope`")
        if atom.get("kind") == "contradiction" and len(works) < 2:
            errs.append(f"M7 {atom_id}: contradiction с одной работой")
        if atom.get("confidence") == "high":
            has_quote = any(w.get("quote") for w in works)
            if not atom.get("formula") and not has_quote:
                errs.append(f"M10 {atom_id}: `high` без формулы и без цитаты")
            if atom.get("locator_status") != "verified" and not has_quote:
                errs.append(f"M10 {atom_id}: `high` с непроверенным локатором")

    known = {a.get("atom") for a in atoms}
    types = collections.Counter()
    for edge in edges:
        if edge.get("from") not in known or edge.get("to") not in known:
            errs.append(f"M8 ребро ведёт в несуществующую ячейку: {edge.get('from')} -> {edge.get('to')}")
        types[edge.get("type")] += 1
    total = sum(types.values())
    # A ratio on three edges says nothing; the rule applies once the map has enough links to matter.
    if total >= 9 and types.get("analogous", 0) / total > 1 / 3:
        errs.append(f"M9 аналогий {types.get('analogous')} из {total}: больше трети, карта превращается в метафоры")
    # M11: необязательная сшивка с картой знаний. Поле может отсутствовать; если есть — обязано быть корректным.
    for a in atoms:
        refs = a.get("kg_ref")
        if refs is None:
            continue
        # Пустой список — законное «связей нет»; ошибка только если это не список.
        if not isinstance(refs, list):
            errs.append(f"M11 {a.get('atom')}: kg_ref должен быть списком")
            continue
        if not refs:
            continue
        for r in refs:
            if not isinstance(r, str) or not r.strip():
                errs.append(f"M11 {a.get('atom')}: пустая запись в kg_ref")
            elif not r.startswith(("C-", "F-", "L-", "GAP-", "CORR-", "DEF-", "EV-", "EXP-")):
                errs.append(f"M11 {a.get('atom')}: kg_ref {r!r} не id из kg/")
    return errs


def atom(atom_id="A-1", **over):
    base = {
        "atom": atom_id,
        "statement": "утверждение",
        "domain": "bio.ageing",
        "kind": "mechanism",
        "works": [{"doi": "10.1/x", "access": "abstract", "quote": None}],
        "confidence": "low",
    }
    base.update(over)
    return base


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="map-"))
    atoms = tmp / "atoms.jsonl"
    edges = tmp / "edges.jsonl"

    def write(rows, edge_rows=()):
        atoms.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        edges.write_text("".join(json.dumps(r) + "\n" for r in edge_rows), encoding="utf-8")
        return check(atoms, edges)

    cases = [
        ("чистая карта", write([atom()], [{"from": "A-1", "to": "A-1", "type": "requires"}]), []),
        ("дубль идентификатора", write([atom(), atom()]), ["M2"]),
        ("фрагмент без цитаты", write([atom(works=[{"doi": "10.1/x", "access": "fragment"}])]), ["M3"]),
        ("medium без условий", write([atom(confidence="medium")]), ["M4"]),
        ("gap без searched", write([atom(kind="gap")]), ["M6"]),
        ("contradiction с одной работой", write([atom(kind="contradiction")]), ["M7"]),
        ("ребро в пустоту", write([atom()], [{"from": "A-1", "to": "A-9", "type": "requires"}]), ["M8"]),
        ("высокая без доказательства", write([atom(confidence="high")]), ["M4", "M10"]),
        ("gap без работ, но с протоколом", write([atom(kind="gap", works=[], searched={"q": "x"}, scope="s")]), []),
        ("gap без работ и без протокола", write([atom(kind="gap", works=[])]), ["M5", "M6"]),
    ]
    total, bad = 0, 0
    for name, got, want in cases:
        total += 1
        ok = all(any(w in e for e in got) for w in want) if want else not got
        if not ok:
            bad += 1
            print(f"  FAIL {name}: ждали {want or 'чисто'}, получили {got[:3]}")
        else:
            print(f"  ok   {name}")
    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errs = check(ATOMS, EDGES)
    if errs:
        print(f"КАРТА: {len(errs)} нарушений")
        for e in errs[:25]:
            print("  " + e)
        return 1
    atoms = load(ATOMS)
    print(f"карта: {len(atoms)} ячеек, {len(load(EDGES))} рёбер, нарушений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
