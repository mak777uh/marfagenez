"""Карта: приём атомарных ячеек, агрегация и масштабирование.

Владелец спросил, удобно ли агенту «видеть всю карту и изучать её в разных масштабах». Честный ответ:
в контексте — нет, пять тысяч ячеек туда не влезут. Поэтому карта живёт на диске, а агент смотрит её
через уровни:

  L0  сводка: области, сколько ячеек, формулы, противоречия, пустоты        (~ одна страница)
  L1  область: подытог по подобластям и тегам                               (~ несколько строк на область)
  L2  выборка: ячейки по фильтру (область, вид, уверенность, тег)           (~ десятки строк)
  L3  окрестность: ячейка и её связи на глубину N                           (~ десяток строк)
  L4  источник: работа и её цитата

Каждый уровень — отдельная команда, потому что «увидеть всё» и «увидеть нужное» — разные задачи.

Usage:
    python3 tools/map.py add <файл.jsonl> [--edges <файл.jsonl>]
    python3 tools/map.py stats
    python3 tools/map.py digest [--domain bio.protocell]
    python3 tools/map.py zoom --atom A-0001 --depth 2
    python3 tools/map.py zoom --domain bio.ageing --kind formula --limit 20
    python3 tools/map.py coverage
"""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAP = ROOT / "literature" / "map"
ATOMS = MAP / "atoms.jsonl"
EDGES = MAP / "edges.jsonl"
COVERAGE = MAP / "coverage.json"

REQUIRED = ("atom", "statement", "domain", "kind", "works", "confidence")
KINDS = {"mechanism", "formula", "condition", "contradiction", "gap", "definition", "measurement"}
CONFIDENCE = {"high", "medium", "low"}


def load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(rows: list[dict], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n" for r in rows), encoding="utf-8")


def nid(statement: str) -> str:
    return "A-" + hashlib.sha256(statement.strip().lower().encode("utf-8")).hexdigest()[:6]


def validate(atom: dict) -> list[str]:
    errs = []
    for field in REQUIRED:
        if not atom.get(field):
            errs.append(f"нет поля `{field}`")
    if atom.get("kind") not in KINDS:
        errs.append(f"вид `{atom.get('kind')}` вне перечисления")
    if atom.get("confidence") not in CONFIDENCE:
        errs.append(f"уверенность `{atom.get('confidence')}` вне перечисления")
    works = atom.get("works") or []
    if not works:
        errs.append("нет ни одной работы")
    for work in works:
        if not (work.get("doi") or work.get("arxiv") or work.get("pmid") or work.get("isbn") or work.get("url")):
            errs.append("работа без локатора")
        if work.get("access") == "fragment" and not work.get("quote"):
            errs.append("access=fragment без цитаты")
    if atom.get("confidence") in ("high", "medium") and not atom.get("conditions"):
        errs.append("нет `conditions` при уверенности medium/high")
    if atom.get("kind") == "gap" and not (atom.get("searched") and atom.get("scope")):
        errs.append("gap без `searched`/`scope`")
    if atom.get("kind") == "contradiction" and len(works) < 2:
        errs.append("contradiction с одной работой: это пробел, а не противоречие")
    return errs


def add(atoms_path: str, edges_path: str | None) -> int:
    incoming = load(pathlib.Path(atoms_path))
    existing = load(ATOMS)
    known = {a["atom"] for a in existing}
    added = 0
    for atom in incoming:
        errs = validate(atom)
        if errs:
            print(f"ОТКЛОНЕНО {atom.get('atom')}: " + "; ".join(errs))
            continue
        atom.setdefault("atom", nid(atom["statement"]))
        if atom["atom"] in known:
            continue
        if not atom.get("locator_status"):
            atom["locator_status"] = "unknown"
        existing.append(atom)
        known.add(atom["atom"])
        added += 1
    dump(existing, ATOMS)
    if edges_path:
        new_edges = load(pathlib.Path(edges_path))
        have = load(EDGES)
        seen = {(e.get("from"), e.get("to"), e.get("type")) for e in have}
        for edge in new_edges:
            key = (edge.get("from"), edge.get("to"), edge.get("type"))
            if key in seen:
                continue
            have.append(edge)
            seen.add(key)
        dump(have, EDGES)
    print(f"ячеек добавлено: {added}; всего {len(existing)}")
    return 0


def stats() -> int:
    atoms = load(ATOMS)
    edges = load(EDGES)
    print(f"ячеек: {len(atoms)}; рёбер: {len(edges)}")
    print("по областям: " + ", ".join(f"{k}={v}" for k, v in sorted(collections.Counter(a["domain"] for a in atoms).items())))
    print("по видам: " + ", ".join(f"{k}={v}" for k, v in sorted(collections.Counter(a["kind"] for a in atoms).items())))
    print("по уверенности: " + ", ".join(f"{k}={v}" for k, v in sorted(collections.Counter(a["confidence"] for a in atoms).items())))
    print("по локаторам: " + ", ".join(f"{k}={v}" for k, v in sorted(collections.Counter(a.get("locator_status", "unknown") for a in atoms).items())))
    return 0


def digest(domain: str | None) -> int:
    atoms = load(ATOMS)
    edges = load(EDGES)
    if domain:
        atoms = [a for a in atoms if a["domain"] == domain]
        if not atoms:
            print(f"области `{domain}` нет в карте")
            return 0
    by_domain = collections.defaultdict(list)
    for atom in atoms:
        by_domain[atom["domain"]].append(atom)
    print(f"# Карта: {len(atoms)} ячеек в {len(by_domain)} областях\n")
    for name in sorted(by_domain):
        rows = by_domain[name]
        kinds = collections.Counter(r["kind"] for r in rows)
        conf = collections.Counter(r["confidence"] for r in rows)
        gaps = [r for r in rows if r["kind"] == "gap"]
        contr = [r for r in rows if r["kind"] == "contradiction"]
        print(f"## {name}")
        print(f"ячеек {len(rows)}; " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
        print("уверенность: " + ", ".join(f"{k}={v}" for k, v in sorted(conf.items())))
        if gaps:
            print(f"пустот: {len(gaps)} — " + "; ".join(g["statement"][:90] for g in gaps[:3]))
        if contr:
            print(f"противоречий: {len(contr)} — " + "; ".join(c["statement"][:90] for c in contr[:3]))
        print()
    return 0


def zoom(atom: str | None, domain: str | None, kind: str | None, limit: int, depth: int) -> int:
    atoms = load(ATOMS)
    index = {a["atom"]: a for a in atoms}
    edges = load(EDGES)
    if atom:
        if atom not in index:
            print(f"нет ячейки {atom}")
            return 1
        seen = {atom}
        frontier = [atom]
        for _ in range(max(1, depth)):
            nxt = []
            for current in frontier:
                for edge in edges:
                    if edge.get("from") == current and edge.get("to") not in seen:
                        nxt.append(edge["to"])
                    if edge.get("to") == current and edge.get("from") not in seen:
                        nxt.append(edge["from"])
            seen.update(nxt)
            frontier = nxt
        for key in sorted(seen):
            row = index[key]
            mark = "*" if key == atom else " "
            print(f"{mark} {key} [{row['domain']}/{row['kind']}/{row['confidence']}] {row['statement'][:110]}")
            if row.get("formula"):
                print(f"    формула: {row['formula'][:100]}")
        return 0
    rows = atoms
    if domain:
        rows = [r for r in rows if r["domain"] == domain]
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    rows = rows[:limit]
    for row in rows:
        print(f"{row['atom']} [{row['domain']}/{row['kind']}/{row['confidence']}] {row['statement'][:110]}")
    print(f"показано {len(rows)}")
    return 0


def coverage() -> int:
    atoms = load(ATOMS)
    works = collections.Counter()
    for atom in atoms:
        for work in atom.get("works") or []:
            works[work.get("doi") or work.get("arxiv") or work.get("pmid") or work.get("url") or "?"] += 1
    report = {
        "atoms": len(atoms),
        "domains": len({a["domain"] for a in atoms}),
        "works": len(works),
        "high_without_formula_or_quote": sum(
            1 for a in atoms if a["confidence"] == "high"
            and not a.get("formula")
            and not any(w.get("quote") for w in a.get("works") or [])
        ),
    }
    COVERAGE.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 2
    verb = argv[0]
    rest = argv[1:]
    if verb == "add":
        return add(rest[0], rest[rest.index("--edges") + 1] if "--edges" in rest else None)
    if verb == "stats":
        return stats()
    if verb == "digest":
        return digest(rest[rest.index("--domain") + 1] if "--domain" in rest else None)
    if verb == "zoom":
        return zoom(
            rest[rest.index("--atom") + 1] if "--atom" in rest else None,
            rest[rest.index("--domain") + 1] if "--domain" in rest else None,
            rest[rest.index("--kind") + 1] if "--kind" in rest else None,
            int(rest[rest.index("--limit") + 1]) if "--limit" in rest else 20,
            int(rest[rest.index("--depth") + 1]) if "--depth" in rest else 1,
        )
    if verb == "coverage":
        return coverage()
    print(f"неизвестный глагол {verb}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
