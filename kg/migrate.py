#!/usr/bin/env python3
"""migrate.py — collect nodes for the knowledge graph.

Sources:
  kg/claims.jsonl                      hand-written claims (legacy, kept as input)
  docs/ELEPHANT-LITERATURE.md          formula records `### F-NNN · title`
  results/*/run-*.json                 experiment records

Output: kg/nodes.jsonl  (one node per line, append-only by nature: rebuilt deterministically)
"""
import glob
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
KG = ROOT / "kg"

UNITS = {
    "F-001": {"H": "1", "T": "s", "mu": "1/s", "lambda": "1", "delta": "1", "mu0": "1/s"},
    "F-003": {"D": "1", "lambda": "1", "mu0": "1/s", "delta": "1/s", "h": "1"},
    "F-022": {"C": "1", "indeg": "1", "outdeg": "1"},
    "F-023": {"S": "1", "v": "1", "c": "1", "y": "1", "w": "1"},
    "F-024": {"K": "1", "V": "1", "F": "1", "alpha": "1"},
    "F-025": {"X": "1", "I_env": "bit", "I_ind": "bit", "I_col": "bit"},
    "F-029": {"r": "1", "x": "1", "eps": "1", "Delta": "1"},
}
CHECKED = {
    "F-001": {"kind": "run", "ref": "FINDING-297"},
    "F-003": {"kind": "run", "ref": "FINDING-309"},
    "F-022": {"kind": "run", "ref": "EXP-CLOSURE-MEASURE"},
    "F-023": {"kind": "run", "ref": "EXP-PRICE-KINKS"},
    "F-024": {"kind": "none", "ref": ""},
    "F-025": {"kind": "none", "ref": ""},
    "F-029": {"kind": "none", "ref": ""},
}


def claims():
    out = []
    p = KG / "claims.jsonl"
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        node = json.loads(line)
        node.setdefault("kind", "claim")
        node.setdefault("context", {"scope": "unspecified"})
        out.append(node)
    return out


def formulas():
    path = ROOT / "docs" / "ELEPHANT-LITERATURE.md"
    text = path.read_text(encoding="utf-8")
    out = []
    pattern = re.compile(r"^### (F-\d{3}) · (.+?)$", re.M)
    marks = list(pattern.finditer(text))
    for i, m in enumerate(marks):
        fid, title = m.group(1), m.group(2).strip()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        latex = ""
        fm = re.search(r"```[a-z]*\n(.*?)```", body, re.S)
        if fm:
            latex = fm.group(1).strip()
        out.append({
            "id": fid,
            "kind": "formula",
            "text": title,
            "context": {"scope": "formula record from ELEPHANT-LITERATURE", "parameters": "see body", "conditions": "see body"},
            "epistemic": "established" if fid in CHECKED and CHECKED[fid]["kind"] != "none" else "hypothesis",
            "provenance": "verified_agent" if fid in CHECKED and CHECKED[fid]["kind"] != "none" else "extracted",
            "evidence": ([{"kind": CHECKED[fid]["kind"], "ref": CHECKED[fid]["ref"], "strength": "strong"}]
                         if fid in CHECKED and CHECKED[fid]["kind"] != "none" else []),
            "relations": [],
            "math": {"latex": latex, "structure": "", "units": UNITS.get(fid, {}),
                     "checked": CHECKED.get(fid, {"kind": "none", "ref": ""})},
            "created_at": "2026-11-20",
            "updated_at": "2026-11-20",
        })
    return out


def experiments():
    out = []
    for path in sorted(glob.glob(str(ROOT / "results" / "*" / "run-*.json"))):
        try:
            d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise SystemExit(f"битый файл прогона {run}: {exc}")
        exp = d.get("experiment_id") or pathlib.Path(path).parent.name
        run = d.get("run_id") or pathlib.Path(path).stem
        verdict = d.get("verdict") or {}
        kind = verdict.get("kind") if isinstance(verdict, dict) else str(verdict)
        out.append({
            "id": f"X-{exp}-{run}",
            "kind": "experiment",
            "text": f"{exp} run {run}: verdict {kind}",
            "context": {"scope": "recorded run", "parameters": json.dumps(d.get("parameters", {}), ensure_ascii=False)[:300],
                        "conditions": f"commit {d.get('model_commit', '?')[:12]}"},
            "epistemic": "established" if kind == "passed" else ("refuted" if kind == "failed" else "hypothesis"),
            "provenance": "verified_agent",
            "evidence": [{"kind": "experiment", "ref": pathlib.Path(path).relative_to(ROOT).as_posix(), "strength": "strong"}],
            "relations": [],
            "data": {"source": pathlib.Path(path).relative_to(ROOT).as_posix(), "license": "repo", "accessed_at": ""},
            "created_at": d.get("created_at", "2026-11-20"),
            "updated_at": "2026-11-20",
        })
    return out




def literature():
    """Literature records `### L-NNN · title` from the registry become claim nodes.

    Provenance: `verified_agent` only when the record says the FULL TEXT was read, otherwise `extracted`.
    Epistemic: always `hypothesis` -- a literature statement is not established for us until we reproduce it.
    """
    path = ROOT / "docs" / "ELEPHANT-LITERATURE.md"
    text = path.read_text(encoding="utf-8")
    out = []
    pattern = re.compile(r"^### (L-\d{3}) · (.+?)$", re.M)
    marks = list(pattern.finditer(text))
    for i, m in enumerate(marks):
        lid, title = m.group(1), m.group(2).strip()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        level = "вторые руки"
        lm = re.search(r"\*\*Проверено\.\*\*\s*(.+)", body)
        if lm:
            level = lm.group(1).strip().splitlines()[0][:80]
        statement = ""
        sm = re.search(r"\*\*Утверждение[^*]*\.\*\*\s*(.+)", body)
        if sm:
            statement = sm.group(1).strip()
        chosen = "verified_agent" if "полный текст" in level.lower() else "extracted"
        out.append({
            "id": lid,
            "kind": "claim",
            "text": (title + (" — " + statement if statement else ""))[:400],
            "context": {"scope": "literature record from ELEPHANT-LITERATURE", "parameters": "see registry", "conditions": level},
            "epistemic": "hypothesis",
            "provenance": chosen,
            "evidence": [{"kind": "literature", "ref": "docs/ELEPHANT-LITERATURE.md", "strength": "strong" if chosen == "verified_agent" else "weak"}],
            "relations": [],
            "data": {"source": "docs/ELEPHANT-LITERATURE.md", "license": "see source", "accessed_at": "2026-11-20"},
            "created_at": "2026-11-20",
            "updated_at": "2026-11-20",
        })
    return out


def definitions():
    """Ten line definitions (kind: definition) -- their own file, not a claim."""
    path = ROOT / "kg" / "definitions.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    nodes = claims() + formulas() + experiments() + literature() + definitions()
    seen = set()
    unique = []
    for n in nodes:
        if n["id"] in seen:
            raise SystemExit(f"повтор ID {n['id']} при сборке графа")
        seen.add(n["id"])
        unique.append(n)
    out = KG / "nodes.jsonl"
    out.write_text("\n".join(json.dumps(n, ensure_ascii=False) for n in unique) + "\n", encoding="utf-8")
    kinds = {}
    for n in unique:
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    print(f"nodes: {len(unique)} -> {out.relative_to(ROOT)}")
    print("by kind:", kinds)


if __name__ == "__main__":
    main()
