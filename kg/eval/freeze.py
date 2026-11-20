#!/usr/bin/env python3
"""freeze.py -- turn the editable spec into the frozen, extensional eval.

Why a freeze step: a pattern such as "all runs before the code change" is a moving
target -- the corpus grows, the gold set silently grows with it, and recall drifts
without any version change. The frozen spec lists concrete ids resolved TODAY; new
ids require a new dated spec.

Outputs
  kg/eval/questions.json   the frozen spec (with frozen_hash over itself minus that field)
  kg/eval/manifest.json    per-entry resolution: node | absent | alias, with counts

Fails loudly when a gold id is neither in the graph nor declared `expected_absent`.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
NODES = ROOT / "kg" / "nodes.jsonl"


def load_nodes():
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_id = {n["id"]: n for n in nodes}
    alias = {}
    for n in nodes:
        if n.get("kind") != "experiment":
            continue
        head = (n.get("text") or "").split(" run ")[0].strip()
        if head:
            alias.setdefault(head, []).append(n["id"])
    return by_id, alias


def canon(name, by_id, alias):
    """Alias -> canonical node ids. An id that is a node stays itself."""
    if name in alias:
        return alias[name]
    return [name] if name in by_id else []


def spec_hash(spec):
    body = {k: v for k, v in spec.items() if k != "frozen_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    src = json.loads((HERE / "questions.src.json").read_text(encoding="utf-8"))
    by_id, alias = load_nodes()
    manifest = {"resolved": {}, "absent": [], "unknown": []}
    seen_absent = []
    for q in src["questions"]:
        gold, resolved = [], []
        for name in q.get("gold", []):
            hits = canon(name, by_id, alias)
            if hits:
                resolved.extend(hits)
            else:
                manifest["unknown"].append({"q": q["id"], "entry": name})
        q["gold"] = sorted(set(resolved))
        for name in q.get("expected_absent", []):
            if canon(name, by_id, alias):
                manifest["unknown"].append({"q": q["id"], "entry": name, "why": "declared absent but exists"})
            else:
                seen_absent.append(name)
    manifest["absent"] = sorted(set(seen_absent))
    if manifest["unknown"]:
        print("НЕ РАЗРЕШЕНО (исправь spec):")
        for row in manifest["unknown"]:
            print("  ", row)
        return 1
    spec = dict(src)
    # alias_map is part of the frozen body: it is resolved TODAY, so the hash must cover it.
    spec["alias_map"] = {k: sorted(v) for k, v in alias.items() if len(v) <= 40}
    spec["frozen_hash"] = spec_hash(spec)
    (HERE / "questions.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest["frozen_hash"] = spec["frozen_hash"]
    manifest["questions"] = len(spec["questions"])
    manifest["absent"] = sorted(set(seen_absent))
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(q["budget"] for q in spec["questions"])
    print("заморожено: " + str(len(spec["questions"])) + " вопросов, hash " + spec["frozen_hash"][:16])
    print("вопросов с gold: " + str(sum(1 for q in spec["questions"] if q["gold"])) +
          " · absent-записей: " + str(len(manifest["absent"])))
    print("сумма бюджетов: " + str(total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
