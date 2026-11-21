#!/usr/bin/env python3
"""score.py -- protocol v1 for the frozen eval.

What it fixes relative to a single "recall" number:

* recall is split:  retrieval = cited AND existing gold / existing gold
                    existence = existing gold / all gold          (ledger of missing nodes)
  The target applies to retrieval only; missing nodes are backlog, not a metric failure.
* precision counts only the structured `cited:` block, and gold ancestors of provenance are whitelisted.
* numbers in the answer that do not appear in the payloads of the cited nodes are flagged.
* tokens are summed over map + expand + answer, against a PER-QUESTION budget.
* polarity rubrics: a `reject` item fires when its text appears in the answer (executable part),
  `assert` items need the judge -- the report says how many are pending.
* stagnation needs three rounds and a delta, not one noisy run.

A run record (one per question, per seed):
  {"id": "E-01", "seed": 1, "cited": ["C-001", "F-023..F-031"], "answer": "...",
   "map_tokens": 300, "expand_tokens": 900, "answer_tokens": 700,
   "files_opened": 0, "tools": ["kg.py atlas"]}
"""
import hashlib
import json
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
NUM = re.compile(r"\d+(?:\.\d+)?(?:/\d+)?")
RANGE = re.compile(r"^([A-Z]+-)(\d+)\.\.([A-Z]+-)?(\d+)$")


def spec_hash(spec):
    body = {k: v for k, v in spec.items() if k != "frozen_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_registry():
    nodes = [json.loads(l) for l in (ROOT / "kg" / "nodes.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return {n["id"]: n for n in nodes}


def expand(ids, aliases):
    out = []
    for x in ids:
        m = RANGE.match(x)
        if m:
            pre, a, _pre2, b = m.groups()
            out += [pre + str(i).zfill(len(a)) for i in range(int(a), int(b) + 1)]
        elif x in aliases:
            out += aliases[x]
        else:
            out.append(x)
    return out


def norm(text):
    """Unicode minus, dashes and spacing must not hide a rejected formula."""
    text = (text or "").lower()
    for ch in ("\u2212", "\u2013", "\u2014", "\u2010"):
        text = text.replace(ch, "-")
    text = text.replace("*", "").replace("`", "")
    return " ".join(text.split())


def score_question(q, run, registry, aliases):
    gold = set(q.get("gold", []))
    absent = set(q.get("expected_absent", []))
    cited = set(expand(run.get("cited", []), aliases))
    exist = gold & set(registry)
    # `expected_absent` is a ledger of things that must NOT be cited as evidence: citing one is a
    # penalty, not an allowed extra (review 2026-11-21, §5).
    allow = gold | set(q.get("allow_extra", []))
    extra = cited - allow
    absent_cited = sorted(cited & absent)
    payload = " ".join((registry[n].get("text") or "") for n in cited & set(registry))
    rejects_hit = [r["text"] for r in q.get("rubric", [])
                   if r["polarity"] == "reject" and norm(r["text"]) in norm(run.get("answer"))]
    pending = sum(1 for r in q.get("rubric", []) if r["polarity"] == "assert")
    return {
        "id": q["id"],
        "seed": run.get("seed"),
        "recall_retrieval": (len(cited & exist) / len(exist)) if exist else None,
        "precision": (1 - len(extra) / len(cited)) if cited else 1.0,
        "extra": sorted(extra),
        "absent_cited": absent_cited,
        "rejects_hit": rejects_hit,
        "rubric_pending": pending,
        "ungrounded_numbers": sorted(set(NUM.findall(run.get("answer") or "")) - set(NUM.findall(payload))),
        "files_opened": run.get("files_opened", 0),
        "tokens_ok": (run.get("map_tokens", 0) + run.get("expand_tokens", 0) + run.get("answer_tokens", 0) <= 15000
                      and run.get("answer_tokens", 0) <= q["budget"]),
        "tools_missing": [t for t in q.get("expected_tools", []) if t not in (run.get("tools") or [])],
    }


def coverage(spec, runs):
    """Every question, every seed, exactly once. A partial run is INVALID, not a smaller exam."""
    seeds = int(spec["targets"].get("seeds", 3))
    wanted = {(q["id"], s) for q in spec["questions"] for s in range(1, seeds + 1)}
    seen = {}
    unknown = []
    for r in runs:
        key = (r.get("id"), r.get("seed"))
        if r.get("id") not in {q["id"] for q in spec["questions"]}:
            unknown.append(r.get("id"))
        seen[key] = seen.get(key, 0) + 1
    duplicates = sorted(k for k, v in seen.items() if v > 1)
    missing = sorted(wanted - set(seen))
    extra = sorted(set(seen) - wanted)
    return {
        "expected": len(wanted),
        "present": len(wanted & set(seen)),
        "missing": ["%s/seed%s" % (i, s) for i, s in missing],
        "duplicates": ["%s/seed%s" % (i, s) for i, s in duplicates],
        "unknown_ids": sorted(set(x for x in unknown if x)),
        "unexpected": ["%s/seed%s" % (i, s) for i, s in extra],
    }


def verdict_of(spec, report, cov):
    """PASS / FAIL / INVALID. Missing data is INVALID (never a silent pass)."""
    reasons = []
    if cov["missing"] or cov["duplicates"] or cov["unknown_ids"] or cov["unexpected"]:
        return "INVALID", ["покрытие неполное: " + str(len(cov["missing"])) + " нет, " +
                           str(len(cov["duplicates"])) + " дублей, " +
                           str(len(cov["unknown_ids"])) + " неизвестных id"]
    t = spec["targets"]
    if report["recall_retrieval_macro"] is None or report["recall_retrieval_macro"] < t["recall_retrieval"]:
        reasons.append("recall_retrieval ниже цели")
    if report["precision_macro"] is None or report["precision_macro"] < t["precision"]:
        reasons.append("precision ниже цели")
    if not report["tokens_ok"]:
        reasons.append("бюджет токенов превышен")
    if report["files_opened"] != t.get("files_opened", 0):
        reasons.append("открывались файлы")
    if report["rejects_total"]:
        reasons.append("сработал reject-пункт рубрики")
    if report["ungrounded_total"]:
        reasons.append("числа без заземления")
    if report["absent_cited_total"]:
        reasons.append("цитируется отсутствующий объект")
    # A failed target is FAIL even if the judge is absent: the answer is already known to be wrong.
    # The judge only decides the remaining case, where everything measurable passed.
    if reasons:
        return "FAIL", reasons
    if report["rubric_pending"]:
        return "INVALID", ["assert-пункты рубрики не оценены: нужен судья"]
    return "PASS", []


def round_report(spec, runs):
    assert spec_hash(spec) == spec["frozen_hash"], "спека изменена после заморозки -- abort"
    registry = load_registry()
    aliases = spec.get("alias_map", {})
    by_q = {q["id"]: q for q in spec["questions"]}
    per = [score_question(by_q[r["id"]], r, registry, aliases) for r in runs if r["id"] in by_q]
    A = [p for p in per if p["id"].startswith("E-") and p["recall_retrieval"] is not None]
    C = [p for p in per if p["id"].startswith("AG-")]
    B = [p for p in per if p["id"].startswith("N-")]
    cov = coverage(spec, runs)
    report = {
        "eval_hash": spec["frozen_hash"],
        "questions": len(per),
        "coverage": cov,
        "ruled_out_assert": "assert-пункты рубрики оценивает судья; без него вердикт INVALID",
        "recall_retrieval_macro": round(statistics.mean(p["recall_retrieval"] for p in A), 3) if A else None,
        "precision_macro": round(statistics.mean(p["precision"] for p in A), 3) if A else None,
        "rejects_total": sum(len(p["rejects_hit"]) for p in per),
        "ungrounded_total": sum(len(p["ungrounded_numbers"]) for p in per),
        "files_opened": sum(p["files_opened"] for p in per),
        "tokens_ok": all(p["tokens_ok"] for p in per),
        "agent_tools_missing": sum(len(p["tools_missing"]) for p in C),
        "negative_auto_pass": sum(1 for p in B if not p["rejects_hit"] and not p["ungrounded_numbers"]),
        "negative_total": len(B),
        "existence_ledger": sorted({n for q in spec["questions"] for n in q.get("expected_absent", [])}),
        "rubric_pending": sum(p["rubric_pending"] for p in per),
        "absent_cited_total": sum(len(p["absent_cited"]) for p in per),
    }
    report["verdict"], report["reasons"] = verdict_of(spec, report, cov)
    return report


def stagnation(history, delta=0.03):
    k = [r["recall_retrieval_macro"] or 0.0 for r in history]
    if len(k) < 3:
        return False
    return (k[-2] - k[-3]) < delta and (k[-1] - k[-2]) < delta


def main(argv):
    spec = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    if len(argv) < 2:
        print("usage: score.py <runs.json> [history.json] [--report-only]")
        return 2
    report_only = "--report-only" in argv
    args = [a for a in argv[1:] if a != "--report-only"]
    runs = json.loads(pathlib.Path(args[0]).read_text(encoding="utf-8"))
    report = round_report(spec, runs)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if len(args) > 1:
        hist = json.loads(pathlib.Path(args[1]).read_text(encoding="utf-8"))
        print("стагнация:", stagnation(hist + [report]))
    print("вердикт:", report["verdict"] + ((" — " + "; ".join(report["reasons"])) if report["reasons"] else ""))
    if report_only:
        return 0
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
