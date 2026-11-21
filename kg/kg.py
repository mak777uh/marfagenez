#!/usr/bin/env python3
"""kg.py — agent-friendly knowledge graph for this repository.

Generated store: kg/nodes.jsonl (one node per line; REBUILT from the corpora by kg/migrate.py).
Source of truth: kg/claims.jsonl + docs/ELEPHANT-LITERATURE.md + results/*/run-*.json. Never hand-edit
nodes.jsonl: the next migrate overwrites it.
Generated:       kg/meta.json (the map), kg/graph.json, kg/INDEX.md.

Node kinds: claim | formula | experiment | dataset | definition | question
Edges:      supports | refutes | qualifies | extends | replicates | supersedes | same_as | predicted_by

Commands
  build                 validate, then rebuild meta.json, graph.json, INDEX.md
  map                   one-line summary: counts, communities, frontier
  atlas [K1]            zoomable map: L0 the whole corpus, L1 one line
  math                  all formulas on one screen: units, checks, links
  frontier              what is missing: holes by kind, with ids
  connectivity          are our own claims one island or several (Q-05)
  preflight <тема>      the three questions before an experiment, as a stamp
  check                 validate against the invariants (code, not opinion)
  find <text>           search nodes
  show <id>             one node
  expand <id> [k]       neighbourhood
  trace <id>            evidence of a node
  chain <id>            claim -> formula -> experiment -> data
  formula <id>          signature: latex, units, what checks it
  contradictions        explicit refutes, plus refuted nodes
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

KG = Path(__file__).resolve().parent
ROOT = KG.parent
NODES = KG / "nodes.jsonl"
META = KG / "meta.json"
GRAPH = KG / "graph.json"
INDEX = KG / "INDEX.md"

KINDS = {"claim", "formula", "experiment", "dataset", "definition", "question", "correspondence", "gap", "evidence"}
EPISTEMIC = {"hypothesis", "established", "contested", "replicated", "refuted", "bounded"}
PROVENANCE = {"extracted", "verified_agent", "human_confirmed"}
MODES = {"formal", "literature", "experiment"}   # three kinds of research, not node kinds
EXPAND_THRESHOLD = 8   # degree at which one hop is already a full screen
EXPAND_CAP = 60        # nodes printed before the "+K ещё" marker
RELATIONS = {"supports", "refutes", "qualifies", "extends", "replicates", "supersedes", "same_as",
             "predicted_by", "analogous_to", "candidate_supports", "tested_in", "stated_in", "normalizes_to", "refuted_by"}
# relations that carry epistemic weight; mechanical ones do not, by construction (D-07)
EPISTEMIC_RELATIONS = {"supports", "refutes", "qualifies", "extends", "replicates", "supersedes", "same_as"}


def load():
    if not NODES.exists():
        raise SystemExit("kg/nodes.jsonl missing: run python3 kg/migrate.py")
    out = []
    for i, line in enumerate(NODES.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"nodes.jsonl line {i}: {exc}")
    return out



def resolve_refs(nodes):
    """Resolve every `evidence` reference to something real.

    Three acceptance routes, in order:
      1. a node id in the graph (`C-`, `F-`, `L-`, `X-`);
      2. a path that exists on disk (`docs/...`, `results/...`);
      3. an alias: `EXP-22` matches the run nodes whose text names it, `FINDING-317` matches the finding file.

    Returns (resolved_by_kind, unresolved) where unresolved is a list of (node_id, kind, ref).
    A reference that resolves to nothing is a hole in the graph, not a formatting detail -- it is reported,
    and `check --refs` turns the report into a failure.
    """
    by_id = {n["id"] for n in nodes}
    exp_aliases = {}
    for n in nodes:
        if n.get("kind") != "experiment":
            continue
        text = n.get("text") or ""
        head = text.split(" run ")[0].strip()
        if head:
            exp_aliases.setdefault(head, []).append(n["id"])
        src = (n.get("data") or {}).get("source") or ""
        stem = src.rsplit("/", 1)[-1].replace(".json", "")
        if stem:
            exp_aliases.setdefault(stem, []).append(n["id"])
    import glob as _glob
    resolved = {}
    unresolved = []
    for n in nodes:
        for ev in n.get("evidence") or []:
            ref = ev.get("ref") or ""
            kind = ev.get("kind") or "?"
            ok = False
            if ref in by_id or ref in exp_aliases:
                ok = True
            elif "/" in ref and (ROOT / ref).exists():
                ok = True
            elif ref.startswith("FINDING-"):
                num = ref.split("-")[1] if "-" in ref else ""
                # exact file or a dashed suffix; a bare prefix would make FINDING-14 resolve to FINDING-140
                ok = bool(_glob.glob(str(ROOT / "docs" / ("FINDING-" + num + ".md"))) or
                          _glob.glob(str(ROOT / "docs" / ("FINDING-" + num + "-*.md"))))
            if ok:
                resolved[kind] = resolved.get(kind, 0) + 1
            else:
                unresolved.append((n["id"], kind, ref))
    return resolved, unresolved

def invariants(nodes):
    problems = []
    ids = {n["id"] for n in nodes}
    if len(ids) != len(nodes):
        problems.append("duplicate ids")
    text_seen = {}
    for n in nodes:
        nid = n.get("id", "?")
        if n.get("kind") not in KINDS:
            problems.append(f"{nid}: kind {n.get('kind')!r}")
        if n.get("epistemic") not in EPISTEMIC:
            problems.append(f"{nid}: bad epistemic")
        if n.get("provenance") not in PROVENANCE:
            problems.append(f"{nid}: bad provenance")
        if not n.get("context"):
            problems.append(f"{nid}: empty context")
        if n.get("epistemic") == "established" and not n.get("evidence"):
            problems.append(f"{nid}: established without evidence")
        if n.get("epistemic") == "established" and n.get("provenance") == "extracted":
            problems.append(f"{nid}: established but only extracted")
        if n.get("kind") == "formula":
            math = n.get("math") or {}
            checked = (math.get("checked") or {}).get("kind", "none")
            if checked != "none" and not math.get("units"):
                problems.append(f"{nid}: checked formula without units")
        for r in n.get("relations", []):
            if r.get("type") not in RELATIONS:
                problems.append(f"{nid}: relation {r.get('type')!r}")
            if str(r.get("target", "")).startswith(("C-", "F-")) and r["target"] not in ids:
                problems.append(f"{nid}: dangling relation -> {r['target']}")
        key = n.get("text", "")[:80]
        if key:
            if key in text_seen and n.get("kind") == "claim":
                problems.append(f"{nid}: duplicate text with {text_seen[key]}")
            text_seen.setdefault(key, nid)
    refuted = {n["id"] for n in nodes if n.get("epistemic") == "refuted"}
    for n in nodes:
        for r in n.get("relations", []):
            if r.get("type") == "supports" and r.get("target") in refuted:
                problems.append(f"{n['id']}: supports a refuted node {r['target']}")
    return problems


def build(nodes):
    problems = invariants(nodes)
    if problems:
        print("INVARIANT VIOLATIONS:")
        for p in problems:
            print("  ", p)
        return 1
    kinds = Counter(n["kind"] for n in nodes)
    epistemic = Counter(n["epistemic"] for n in nodes)
    provenance = Counter(n["provenance"] for n in nodes)
    edges = [{"from": n["id"], "to": r["target"], "type": r["type"]}
             for n in nodes for r in n.get("relations", [])]
    refuted = {m["id"] for m in nodes if m["epistemic"] == "refuted"}
    refuted_referenced = sorted({r["target"] for n in nodes for r in n.get("relations", [])
                                 if r["type"] in ("supports", "extends", "qualifies")
                                 and r["target"] in refuted})
    frontier = {
        "without_evidence": sorted(n["id"] for n in nodes if not n.get("evidence")),
        "extracted_only": sorted(n["id"] for n in nodes if n.get("provenance") == "extracted"),
        "refuted_still_referenced": refuted_referenced,
        "contested": sorted(n["id"] for n in nodes if n.get("epistemic") == "contested"),
    }
    vocab = line_vocab() or []
    line_labels = {}
    if LINES.exists():
        for item in json.loads(LINES.read_text(encoding="utf-8")).get("lines", []):
            if isinstance(item, dict):
                line_labels[item.get("id")] = item.get("label", item.get("id"))
    line_counts = {}
    line_incidents = {}
    line_hubs = {}
    for n in nodes:
        for ln_id in n.get("lines") or []:
            line_counts[ln_id] = line_counts.get(ln_id, 0) + 1
            line_incidents[ln_id] = line_incidents.get(ln_id, 0) + 1
            if n["id"].startswith(("C-", "DEF-")):
                line_hubs.setdefault(ln_id, []).append(n["id"])
    lines_block = [{"id": lid, "label": line_labels.get(lid, lid),
                    "nodes": line_counts.get(lid, 0),
                    "hubs": sorted(line_hubs.get(lid, []))[:4]} for lid in vocab]
    communities = [
        {"id": "K1", "label": "цена и бюджет (legacy alias)", "hubs": ["C-001", "C-002"]},
        {"id": "K2", "label": "замыкание и выживание", "hubs": ["C-003", "C-006", "F-022", "F-024"]},
        {"id": "K3", "label": "порог и его форма", "hubs": ["C-005", "C-007", "F-003", "F-029"]},
        {"id": "K4", "label": "формулы", "hubs": sorted(n["id"] for n in nodes if n["kind"] == "formula")[:5]},
        {"id": "K5", "label": "прогоны", "hubs": sorted(n["id"] for n in nodes if n["kind"] == "experiment")[:5]},
    ]
    confirmed = load_confirmed()
    meta = {
        "schema": "kg/2",
        "human_confirmed": sorted(confirmed),
        "built_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                    .isoformat(timespec="seconds"),
        "counts": {"total": len(nodes), "by_kind": dict(kinds), "by_epistemic": dict(epistemic),
                   "by_provenance": dict(provenance), "edges": len(edges)},
        "invariants": [
            "every node has non-empty context",
            "established implies at least one evidence item",
            "established cannot have provenance=extracted",
            "a checked formula declares units for its symbols",
            "no dangling C-/F- references",
            "ids are unique",
            "claims do not repeat another claim's text",
            "a refuted node is never the target of supports",
        ],
        "communities": communities,
        "lines": lines_block,
        "lines_version": (json.loads(LINES.read_text(encoding="utf-8")).get("version") if LINES.exists() else None),
        "frontier": frontier,
        "verbs": ["atlas", "math", "map", "frontier", "connectivity", "preflight", "find", "show", "expand", "trace", "chain", "formula", "contradictions", "check"],
        "hashes": {"graph": hashlib.sha256(json.dumps(nodes, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]},
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    GRAPH.write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# kg/INDEX.md — карта графа (генерируется)", "",
             f"узлов: **{len(nodes)}**, рёбер: **{len(edges)}**", "",
             "| kind | сколько |", "|---|---|"]
    for k, v in sorted(kinds.items()):
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Фронтир", "",
              f"- без свидетельств: **{len(frontier['without_evidence'])}**",
              f"- только извлечено: **{len(frontier['extracted_only'])}**",
              f"- опровергнуто, но цитируется: **{len(refuted_referenced)}**",
              "", "## Глаголы", "",
              ", ".join(meta["verbs"]), ""]
    INDEX.write_text("\n".join(lines), encoding="utf-8")
    print(f"built: {len(nodes)} nodes, {len(edges)} edges")
    print("by kind:", dict(kinds))
    print("frontier:", {k: len(v) for k, v in frontier.items()})
    return 0


def warnings(nodes):
    """Known-open inconsistencies, reported instead of silently tolerated."""
    out = []
    for n in nodes:
        if n.get("epistemic") == "refuted":
            for r in n.get("relations") or []:
                if r.get("type") == "refutes":
                    out.append(n["id"] + ": refuted node still propagates refutes -> " + str(r.get("target")))
        for r in n.get("relations") or []:
            if r.get("type") == "same_as" and str(r.get("target", "")).startswith("L-"):
                out.append(n["id"] + ": same_as to literature " + r["target"] +
                           " -- bridge candidate, not identity (Q1/Q7/P1)")
    return out


def refs_report(nodes, strict):
    resolved, unresolved = resolve_refs(nodes)
    print("ссылки свидетельств: разрешено " + str(sum(resolved.values())) + ", не разрешено " + str(len(unresolved)))
    for kind, count in sorted(resolved.items()):
        print("  ok        " + kind + ": " + str(count))
    for nid, kind, ref in unresolved[:15]:
        print("  висит     " + nid + " -> " + kind + ":" + ref)
    if len(unresolved) > 15:
        print("  ... ещё " + str(len(unresolved) - 15))
    if strict and unresolved:
        print("FAIL: " + str(len(unresolved)) + " ссылок не разрешаются")
        return 1
    if unresolved:
        print("NOTE: ссылки выше -- дыры в графе; строгий режим: kg.py check --refs")
    return 0


# ---------------------------------------------------------------------------
# Карта с уровнями: atlas (L0) -> atlas <линия> (L1) -> expand (L2) -> show (L3)
# ---------------------------------------------------------------------------


def _edges(nodes):
    """(forward, backward) maps of typed relations, so a card can show both sides."""
    by_id = {n["id"] for n in nodes}
    fwd = {}
    back = {}
    for n in nodes:
        for r in n.get("relations") or []:
            t, tgt = r.get("type"), r.get("target")
            if tgt not in by_id:
                continue
            fwd.setdefault(n["id"], []).append((t, tgt))
            back.setdefault(tgt, []).append((t, n["id"]))
    return fwd, back


def _clip(text, width=64):
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def _units(formula):
    """(how many units declared, True if the formula declares any at all)."""
    math = formula.get("math") or {}
    units = math.get("units")
    if isinstance(units, dict) and units:
        return len(units), True
    if isinstance(units, list) and units:
        return len(units), True
    return 0, False


def atlas(nodes, cluster_id=None):
    """L0: the whole corpus on one screen. L1: one line with its hubs and holes."""
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    fwd, back = _edges(nodes)
    by_id = {n["id"]: n for n in nodes}

    if cluster_id:
        line = next((c for c in meta.get("lines", []) if c["id"] == cluster_id), None)
        legacy = False
        if line is None:
            line = next((c for c in meta.get("communities", []) if c["id"] == cluster_id), None)
            legacy = line is not None
        if not line:
            print("нет линии " + cluster_id + "; есть: " +
                  ", ".join(c["id"] for c in meta.get("lines", []) or meta.get("communities", [])))
            return 1
        print("ЛИНИЯ " + line["id"] + " · " + line["label"] + ("  (legacy alias)" if legacy else ""))
        if line.get("nodes") is not None:
            print("  узлов: " + str(line["nodes"]))
        for hub in line["hubs"]:
            n = by_id.get(hub)
            if not n:
                continue
            ev = len(n.get("evidence") or [])
            out_edges = fwd.get(hub, [])
            route = " -> ".join(t + ":" + tgt for t, tgt in out_edges) or "рёбер нет"
            print("  " + hub + " [" + n.get("epistemic", "?") + "/" + n.get("provenance", "?") + "] " + _clip(n.get("text"), 70))
            print("      очевидцев: " + str(ev) + " · " + route)
            for t, src in back.get(hub, [])[:3]:
                print("      <- " + t + ":" + src)
        print("  дальше: expand <id> — 1 шаг для хаба, 2 для листа; show <id> — карточка")
        return 0

    counts = meta.get("counts", {})
    kinds = counts.get("by_kind", {})
    epi = counts.get("by_epistemic", {})
    prov = counts.get("by_provenance", {})
    print("КАРТА L0  ·  " + str(counts.get("total", len(nodes))) + " узлов  ·  " + str(counts.get("edges", 0)) + " рёбер  ·  " + str(len(meta.get("lines", []))) + " линий")
    own = sum(1 for n in nodes if n.get("kind") == "claim" and n["id"].startswith("C-"))
    lit = sum(1 for n in nodes if n.get("kind") == "claim" and n["id"].startswith("L-"))
    print("своих утверждений " + str(own) + " · литературных " + str(lit) + " · формул " + str(kinds.get("formula", 0)) + " · прогонов " + str(kinds.get("experiment", 0)))
    print("статус: " + " · ".join(k + " " + str(v) for k, v in epi.items()))
    print("доверие: " + " · ".join(k + " " + str(v) for k, v in prov.items()) +
          " · подтверждено владельцем " + str(len(meta.get("human_confirmed") or [])))
    modes = {}
    for n in nodes:
        m = mode_of(n)
        if m:
            modes[m] = modes.get(m, 0) + 1
    with_lines = [n for n in nodes if isinstance(n.get("lines"), list) and n.get("lines")]
    if with_lines:
        incidences = sum(len(n["lines"]) for n in with_lines)
        print("линии: узлов " + str(len(with_lines)) + " · инцидентов " + str(incidences) +
              " (один узел может быть в нескольких)")
    print("виды исследования: " + " · ".join(m + " " + str(modes.get(m, 0))
                                             for m in ("formal", "literature", "experiment")))
    print()
    holes = meta.get("frontier", {})
    for ln in meta.get("lines", []):
        print("  " + ln["id"].ljust(15) + " " + ln["label"].ljust(26) + " узлов " + str(ln["nodes"]))
    print()
    print("дороги между линиями: " + str(counts.get("edges", 0)) + " рёбер на " + str(len(meta.get("lines", []))) + " линий")
    print("дыры: без свидетельств " + str(len(holes.get("without_evidence", []))) + " · только извлечено " + str(len(holes.get("extracted_only", []))) + " · опровергнуто, но используется " + str(len(holes.get("refuted_still_referenced", []))))
    print("куда смотреть: atlas <линия> · expand C-001 · math")
    print("legacy: K1–K5 — старые сообщества, доступны как алиасы")
    return 0


def math_map(nodes):
    """All formulas on one screen: units, what checks them, and what they touch."""
    fwd, back = _edges(nodes)
    forms = sorted((n for n in nodes if n.get("kind") == "formula"), key=lambda n: n["id"])
    print("МАТЕМАТИКА  ·  " + str(len(forms)) + " шт., все на одном экране")
    print("обозначения: единицы сколько_заполнено/сколько_символов · проверка · статус")
    for n in forms:
        have, declared = _units(n)
        checked = ((n.get("math") or {}).get("checked") or {}).get("kind", "none")
        links = [t + ":" + tgt for t, tgt in (fwd.get(n["id"], []) + back.get(n["id"], []))][:3]
        mark = ("ед " + str(have)) if declared else "ед  —"
        print("  " + n["id"] + "  " + mark.ljust(7) + "  " + checked.ljust(8) + " [" + n.get("epistemic", "?") + "]  " + _clip(n.get("text"), 58))
        if links:
            print("      связи: " + ", ".join(links))
    print()
    print("зум только по связям: formula F-001 -> show F-001 -> expand F-001")
    return 0


def frontier_view(nodes):
    """What is missing, with counts -- the question a research round actually asks."""
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    holes = meta.get("frontier", {})
    print("ФРОНТИР")
    for name, ids in holes.items():
        print("  " + name.ljust(24) + str(len(ids)))
        if ids:
            print("    " + ", ".join(ids[:8]) + (" ..." if len(ids) > 8 else ""))
    print("  без свидетельств: expand <id> -- свидетельство, show <id> -- что не доказано")
    return 0


def ref_targets(nodes, ref):
    """Where a reference actually lands in the graph. Same answer for `check` and for `expand`.

    A finding is its own evidence object (`EV-FINDING-NNN`); an experiment alias lands on the run
    nodes that name it; a file path lands on the node that owns that path in its own evidence.
    """
    ids = {n["id"] for n in nodes}
    out = set()
    if ref in ids:
        return {ref}
    if ref.startswith("FINDING-") and ("EV-" + ref) in ids:
        return {"EV-" + ref}
    if ref.startswith("EXP-"):
        for n in nodes:
            if n.get("kind") == "experiment" and ref in (n.get("text") or ""):
                out.add(n["id"])
        if ("EV-" + ref) in ids:
            out.add("EV-" + ref)
        return out
    if "/" in ref:
        for n in nodes:
            if n.get("kind") == "experiment" and any(str(e.get("ref", "")) == ref for e in (n.get("evidence") or [])):
                out.add(n["id"])
        return out
    return out


def adjacency(nodes):
    """The graph `expand` actually walks: relations plus evidence that names a node."""
    ids = {n["id"] for n in nodes}
    adj = {i: set() for i in ids}
    for n in nodes:
        for r in n.get("relations") or []:
            t = r.get("target")
            if t in ids:
                adj[n["id"]].add(t)
                adj[t].add(n["id"])
        for e in n.get("evidence") or []:
            ref = str(e.get("ref", ""))
            for target in ref_targets(nodes, ref):
                if target == n["id"]:
                    continue
                adj[n["id"]].add(target)
                adj[target].add(n["id"])
    return adj


def connectivity(nodes):
    """Are our own claims one island or several? This is the Q-05 criterion, measured.

    Counts components among claim nodes (`C-`), because that is the layer where a question is
    answered; a component split means `expand` cannot walk from one result to another.
    """
    adj = adjacency(nodes)
    claims = sorted(n["id"] for n in nodes if n["id"].startswith("C-"))
    seen, comps = set(), []
    for start in claims:
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in adj.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comps.append(sorted(c for c in comp if c.startswith("C-")))
    print("СВЯЗНОСТЬ СВОИХ УТВЕРЖДЕНИЙ: " + str(len(comps)) + " компонент(ы)")
    for i, comp in enumerate(comps, 1):
        print("  " + str(i) + ": " + ", ".join(comp))
    if len(comps) == 1:
        print("  цель Q-05 достигнута: любое утверждение достижимо из любого")
    else:
        print("  цель Q-05: одна компонента; сейчас не хватает " + str(len(comps) - 1) + " мост(ов)")
    return 0


def preflight(nodes, topic):
    """The three questions before an experiment, printed as a stamp.

    A miss is a result too: "not found" is printed, so a failed search cannot disappear.
    """
    words = [w for w in topic.lower().split() if len(w) > 2]
    hits = []
    for n in nodes:
        if hidden(n):
            continue
        text = (n.get("text") or "").lower()
        if words and all(w in text for w in words):
            hits.append(n["id"])
    print("ПРЕДПОЛЁТ: " + topic)
    print("  1) что уже знаем: " + (", ".join(sorted(hits)[:12]) if hits else "не найдено"))
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    holes = meta.get("frontier", {})
    print("  2) где дыра: без свидетельств " + str(len(holes.get("without_evidence", []))) +
          " · только извлечено " + str(len(holes.get("extracted_only", []))) +
          " · contested " + str(len(holes.get("contested", []))))
    eliminated = ROOT / "docs" / "ELIMINATED.md"
    tried = []
    if eliminated.exists():
        for line in eliminated.read_text(encoding="utf-8", errors="ignore").splitlines():
            low = line.lower()
            # all words, not any: "цена" alone matches every cost line in ELIMINATED and drowns the search
            if words and all(w in low for w in words):
                tried.append(line.strip()[:90])
    print("  3) что уже пробовали: " + (str(len(tried)) + " строк в ELIMINATED" if tried else "не найдено"))
    for line in tried[:3]:
        print("     " + line)
    try:
        commit = __import__("subprocess").check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    status = "MATCHES" if hits else "NO_MATCHES"
    stamp = {"topic": topic, "queries": words, "status": status, "hits": sorted(hits)[:12],
             "tried_lines": len(tried), "scope": "graph minus quarantined",
             "graph_hash": graph_hash(nodes)[:16], "commit": commit}
    print("  штамп: " + json.dumps(stamp, ensure_ascii=False))
    return 0


def graph_hash(nodes):
    """Canonical hash over node content, not over file bytes: stamps must be comparable across rounds."""
    body = []
    for n in sorted(nodes, key=lambda x: x["id"]):
        body.append("|".join([
            n["id"], n.get("kind", ""), n.get("epistemic", ""), n.get("provenance", ""),
            hashlib.sha256((n.get("text") or "").strip().encode("utf-8")).hexdigest()[:16],
        ]))
    return hashlib.sha256("\n".join(body).encode("utf-8")).hexdigest()


def hidden(node):
    """Three different reasons not to show a node, none of them a knowledge status:
    quarantine (triage), tombstone (lifecycle), and nothing else (D-09, U-08)."""
    data = node.get("data") or {}
    if data.get("triage_status") == "quarantined":
        return True
    return data.get("lifecycle") == "tombstone"


def extra_invariants(nodes):
    """Rules that were prose until the second round of review (D-04, D-06, D-07) plus research modes."""
    problems = []
    ids = {n["id"] for n in nodes}
    for cid in load_confirmed():
        if cid not in ids:
            problems.append("confirmed.jsonl: подтверждён несуществующий узел " + cid)
    vocab = line_vocab()
    if vocab:
        defined = {((n.get("data") or {}).get("defines")) for n in nodes if n.get("kind") == "definition"}
        missing = [l for l in vocab if l not in defined]
        if missing:
            problems.append("vocabulary v1 without definition nodes: " + ", ".join(missing))
    for n in nodes:
        for r in n.get("relations") or []:
            if r.get("type") == "same_as":
                tgt = str(r.get("target"))
                if not (n["id"].startswith("C-") and tgt.startswith("C-")):
                    problems.append(n["id"] + ": same_as is claim-to-claim only; got " + tgt +
                                    " (use analogous_to or correspondence)")
        if n.get("kind") == "evidence":
            ref = (n.get("data") or {}).get("ref")
            if not ref:
                problems.append(n["id"] + ": evidence without a ref")
            elif str(ref).startswith("FINDING-"):
                num = str(ref).split("-")[1]
                found = (ROOT / "docs" / ("FINDING-" + num + ".md")).exists() or bool(
                    list((ROOT / "docs").glob("FINDING-" + num + "-*.md")))
                if not found:
                    problems.append(n["id"] + ": finding file is missing")
        if n.get("kind") == "gap":
            data = n.get("data") or {}
            if data.get("left") not in ids or data.get("right") not in ids:
                problems.append(n["id"] + ": gap needs two existing ends (left, right)")
            if not data.get("required_test"):
                problems.append(n["id"] + ": gap without required_test is a wish, not a gap")
        if n.get("kind") == "correspondence":
            data = n.get("data") or {}
            if data.get("status") in ("complete", "exam_ready"):
                need = ["left", "right", "map", "kind", "shared_structure",
                        "kept_assumptions", "lost_assumptions", "evidence_left", "evidence_right", "falsification"]
                empty = [f for f in need if not data.get(f)]
                if empty:
                    problems.append(n["id"] + ": correspondence " + str(data.get("status")) +
                                    " without " + ", ".join(empty))
            left = (n.get("data") or {}).get("left")
            right = (n.get("data") or {}).get("right")
            if left not in ids or right not in ids:
                problems.append(n["id"] + ": correspondence needs both poles as existing nodes")
            for r in n.get("relations") or []:
                if r.get("type") in ("supports", "refutes"):
                    problems.append(n["id"] + ": correspondence must not " + str(r.get("type")) + " a claim")
        if n.get("lines"):
            lines = n.get("lines")
            vocab = line_vocab()
            if n.get("kind") != "claim":
                problems.append(n["id"] + ": lines belong to claims only (got " + str(n.get("kind")) + ")")
            if not isinstance(lines, list) or any(not isinstance(x, str) or not x.strip() for x in lines):
                problems.append(n["id"] + ": lines must be a non-empty list of non-empty strings")
            elif len(set(lines)) != len(lines):
                problems.append(n["id"] + ": duplicate line ids")
            elif vocab is not None:
                unknown = [x for x in lines if x not in vocab]
                if unknown:
                    problems.append(n["id"] + ": lines not in vocabulary v1: " + ", ".join(unknown))
        data = n.get("data") or {}
        if data.get("lifecycle") == "tombstone":
            if not data.get("tombstone_reason"):
                problems.append(n["id"] + ": tombstone without a reason")
            if n.get("kind") == "claim" and data.get("superseded_by") and data["superseded_by"] not in ids:
                problems.append(n["id"] + ": superseded_by points to a missing node")
        if n.get("mode") and n.get("mode") not in MODES:
            problems.append(n["id"] + ": mode not in " + str(sorted(MODES)))
        if n.get("kind") == "experiment" and n.get("domain") == "world" and n.get("epistemic") == "established":
            problems.append(n["id"] + ": a run cannot establish a world-claim (use a correspondence)")
    return problems


def mode_of(node):
    """Which kind of research produced this node. Derived, not stored twice."""
    if node.get("mode") in MODES:
        return node["mode"]
    kind, nid = node.get("kind"), node["id"]
    if kind == "experiment":
        return "experiment"
    if kind == "formula":
        return "formal"
    if nid.startswith("L-"):
        return "literature"
    return ""


LINES = ROOT / "kg" / "lines.json"


def line_vocab():
    """Closed vocabulary of the ten parts (owner decision, T-01). None while it is not frozen."""
    if not LINES.exists():
        return None
    data = json.loads(LINES.read_text(encoding="utf-8"))
    lines = data.get("lines") or []
    # vocabulary stores objects; the check compares ids
    return [l["id"] if isinstance(l, dict) else l for l in lines]

def admissions_path():
    return KG / "admissions.jsonl"


def admit(nodes, node_id, action, rationale, evidence, actor):
    """Append one admission event. The log is the history; the node keeps only the current state."""
    by_id = {n["id"]: n for n in nodes}
    if node_id not in by_id:
        print("нет узла " + node_id)
        return 1
    if not rationale or len(rationale) < 10:
        print("отказ: нужен rationale (не короче 10 символов)")
        return 1
    if not evidence:
        print("отказ: нужны evidence ids")
        return 1
    missing = [e for e in evidence if e not in by_id]
    if missing:
        print("отказ: свидетельства не найдены: " + ", ".join(missing))
        return 1
    path = admissions_path()
    prev = ""
    if path.exists():
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if lines:
            prev = json.loads(lines[-1]).get("event_hash", "")
        seq = len(lines) + 1
    else:
        seq = 1
    event = {
        "event_id": "ADM-" + f"{seq:04d}",
        "node_id": node_id,
        "action": action,
        "rationale": rationale,
        "evidence_ids": evidence,
        "actor": actor,
        "rules_version": "admit-v1",
        "graph_hash": graph_hash(nodes)[:16],
        "prev_hash": prev,
        "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"),
    }
    event["event_hash"] = hashlib.sha256(
        json.dumps(event, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    print("записано: " + event["event_id"] + " " + node_id + " " + action)
    return 0


def confirmed_path():
    return KG / "confirmed.jsonl"


def load_confirmed():
    path = confirmed_path()
    if not path.exists():
        return {}
    return {json.loads(l)["id"]: json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}


def confirm(nodes, node_id, note, actor):
    """Owner confirmation is the only way to human_confirmed. It is a queue, not a status rewrite."""
    by_id = {n["id"]: n for n in nodes}
    if node_id not in by_id:
        print("нет узла " + node_id)
        return 1
    done = load_confirmed()
    if node_id in done:
        print("уже подтверждён: " + node_id + " (" + done[node_id]["at"] + ")")
        return 0
    event = {"id": node_id, "by": actor, "at": __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).isoformat(timespec="seconds"), "note": note or ""}
    with confirmed_path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    print("подтверждено: " + node_id + " (" + str(len(done) + 1) + " всего)")
    return 0


def unconfirmed(nodes, limit=20):
    """Hubs first: a claim with the most edges is the cheapest thing to check by hand."""
    done = load_confirmed()
    fwd, back = _edges(nodes)
    degree = {nid: len(fwd.get(nid, [])) + len(back.get(nid, [])) for nid in fwd}
    cand = [n for n in nodes
            if n["id"] not in done and n.get("provenance") == "verified_agent"
            and n.get("kind") in ("claim", "formula", "definition", "correspondence")]
    cand.sort(key=lambda n: (-degree.get(n["id"], 0), n["id"]))
    if not cand:
        print("очередь пуста: все агентские узлы подтверждены")
        return 0
    print("очередь подтверждения: " + str(len(cand)) + " узлов, показаны " + str(min(limit, len(cand))))
    for n in cand[:limit]:
        print("  " + n["id"] + "  степень " + str(degree.get(n["id"], 0)) + "  " +
              _clip(n.get("text"), 70))
    print("  подтвердить: kg.py confirm <id> \"<заметка>\" [actor]")
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    nodes = load()
    by_id = {n["id"]: n for n in nodes}
    cmd = argv[1]

    if cmd == "build":
        return build(nodes)

    if cmd == "check":
        strict_refs = "--refs" in argv
        problems = invariants(nodes) + extra_invariants(nodes)
        print("OK" if not problems else "\n".join(problems))
        for w in warnings(nodes):
            print("NOTE: " + w)
        bad = refs_report(nodes, "--refs" in argv)
        if problems:
            return 1
        return 1 if bad else 0

    if cmd == "admit":
        if len(argv) < 6:
            print('usage: kg.py admit <id> <action> "<rationale>" <evidence,comma> [actor]')
            return 2
        return admit(nodes, argv[2], argv[3], argv[4], argv[5].split(","), argv[6] if len(argv) > 6 else "owner")

    if cmd == "confirm":
        if len(argv) < 3:
            print('usage: kg.py confirm <id> "<note>" [actor]')
            return 2
        return confirm(nodes, argv[2], argv[3] if len(argv) > 3 else "", argv[4] if len(argv) > 4 else "owner")

    if cmd == "unconfirmed":
        return unconfirmed(nodes, int(argv[2]) if len(argv) > 2 else 20)

    if cmd == "admissions":
        path = admissions_path()
        if not path.exists():
            print("журнал допуска пуст")
            return 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line)
                print(e["event_id"] + " " + e["at"] + " " + e["node_id"] + " " + e["action"] + " by " + e["actor"])
        return 0

    if cmd == "connectivity":
        return connectivity(nodes)

    if cmd == "preflight":
        if len(argv) < 3:
            print("usage: kg.py preflight <тема>")
            return 2
        return preflight(nodes, " ".join(argv[2:]))

    if cmd == "frontier":
        return frontier_view(nodes)

    if cmd == "atlas":
        return atlas(nodes, argv[2] if len(argv) > 2 else None)

    if cmd == "math":
        return math_map(nodes)

    if cmd == "map":
        if not META.exists():
            print("no meta.json: run build")
            return 1
        meta = json.loads(META.read_text(encoding="utf-8"))
        print(f"nodes: {meta['counts']['total']}  edges: {meta['counts']['edges']}")
        print("by kind:", meta["counts"]["by_kind"])
        print("by epistemic:", meta["counts"]["by_epistemic"])
        print("frontier:", {k: len(v) for k, v in meta["frontier"].items()})
        print("communities (legacy):", [c["label"] for c in meta["communities"]])
        print("lines:", [(l["id"], l["nodes"]) for l in meta.get("lines", [])])
        return 0

    if cmd == "find":
        needle = " ".join(argv[2:]).lower()
        hits = [n for n in nodes if needle in n.get("text", "").lower()]
        for n in hits[:20]:
            print(f"{n['id']} [{n['kind']}/{n['epistemic']}] {n['text'][:110]}")
        print(f"({len(hits)} hits)")
        return 0

    if cmd == "show":
        n = by_id.get(argv[2])
        if not n:
            print(f"{argv[2]}: not found")
            return 1
        print(json.dumps(n, ensure_ascii=False, indent=2))
        return 0

    if cmd == "expand":
        start = argv[2]
        # Adaptive depth: a hub with many neighbours already floods the view at one hop,
        # a leaf needs two hops to show anything. The rule is code, not habit.
        if len(argv) > 3:
            hops = int(argv[3])
        else:
            deg = 0
            for n in nodes:
                if hidden(n):
                    continue
                for r in n.get("relations", []):
                    if r.get("type") in EPISTEMIC_RELATIONS and (n["id"] == start or r["target"] == start):
                        deg += 1
            hops = 1 if deg >= EXPAND_THRESHOLD else 2
        seen = {start}
        frontier = {start}
        for _ in range(hops):
            nxt = set()
            for n in nodes:
                if hidden(n) and n["id"] not in (start,):
                    continue
                for r in n.get("relations", []):
                    if n["id"] in frontier:
                        nxt.add(r["target"])
                    if r["target"] in frontier:
                        nxt.add(n["id"])
                for e in n.get("evidence", []):
                    # the same resolver `check` uses: a finding is an object, an alias is a run,
                    # a path is the run that owns it. Otherwise validation and navigation disagree.
                    for target in ref_targets(nodes, str(e.get("ref", ""))):
                        if n["id"] in frontier:
                            nxt.add(target)
                        if target in frontier:
                            nxt.add(n["id"])
            frontier = nxt - seen
            seen |= nxt
        ids = sorted(seen)
        for i in ids[:EXPAND_CAP]:
            n = by_id.get(i)
            if n:
                print(f"{i} [{n['kind']}/{n['epistemic']}] {n['text'][:100]}")
        if len(ids) > EXPAND_CAP:
            print(f"... ещё {len(ids) - EXPAND_CAP}; сузить: expand {start} 1, либо show <id>")
        return 0

    if cmd == "trace":
        n = by_id.get(argv[2])
        if not n:
            print(f"{argv[2]}: not found")
            return 1
        print(f"{n['id']}: {n['text']}")
        for e in n.get("evidence", []):
            print(f"  evidence [{e['kind']}] {e['ref']} ({e.get('strength', '?')})")
        return 0

    if cmd == "chain":
        n = by_id.get(argv[2])
        if not n:
            print(f"{argv[2]}: not found")
            return 1
        print(f"claim  {n['id']}: {n['text']}")
        for e in n.get("evidence", []):
            print(f"-> {e['kind']:12} {e['ref']}")
            m = by_id.get(str(e["ref"]))
            if m:
                for e2 in m.get("evidence", []):
                    print(f"   -> {e2['kind']:10} {e2['ref']}")
        return 0

    if cmd == "formula":
        n = by_id.get(argv[2])
        if not n or n.get("kind") != "formula":
            print(f"{argv[2]}: not a formula node")
            return 1
        math = n.get("math", {})
        print(f"{n['id']}: {n['text']}")
        print("latex:", (math.get("latex") or "").splitlines()[:3])
        print("units:", math.get("units"))
        print("checked:", math.get("checked"))
        return 0

    if cmd == "contradictions":
        found = False
        for n in nodes:
            for r in n.get("relations", []):
                if r["type"] == "refutes":
                    found = True
                    print(f"REFUTES {n['id']} -> {r['target']}: {n['text'][:90]}")
        for n in nodes:
            if n["epistemic"] == "refuted":
                found = True
                print(f"REFUTED {n['id']}: {n['text'][:100]}")
        if not found:
            print("no contradictions recorded")
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
