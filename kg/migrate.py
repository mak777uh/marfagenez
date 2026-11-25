import hashlib
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
    # F-001: lambda и delta входят только произведением alpha = lambda*delta (1/с²);
    # по данным о смертности наблюдаемо только произведение, не множители.
    "F-001": {"H": "1", "T": "s", "mu": "1/s", "lambda": "1/с", "delta": "1/с", "mu0": "1/s",
              "alpha": "1/с²"},
    # F-004 размерно недоопределена, пока не объявлено, что такое n и p; каноническая
    # интерпретация (масса в г, доля безразмерна) дана в docs/UNITS-AUDIT.md §5.
    "F-004": {"приход": "Дж/с", "расход": "Дж/с", "f0": "Дж/с", "mu": "Дж/(с·г)",
              "n": "г", "kappa": "Дж·с/г²", "p": "1", "c_y": "Дж/г", "sigma": "1", "f": "г/с"},
    "F-002": {"D": "1", "h": "1", "delta": "1/с", "T": "с", "D_star": "1"},
    # F-005 / F-021: правило kappa. E и J_A — энергии и потоки (Дж, Дж/с), kappa — доля (1).
    # Сумма ветвей равна исходной величине, значит размерности совпадают по построению.
    "F-005": {"энергия": "Дж", "E": "Дж", "kappa": "1"},
    "F-021": {"J_A": "Дж/с", "J_M": "Дж/с", "kappa": "1"},
    # F-015 / F-028: sizer/adder/timer. s — размер (мкм), a — безразмерный коэффициент,
    # b — прибавка за цикл (мкм). Устойчивость требует |a| < 2 — это и есть безразмерность.
    "F-015": {"s_d": "мкм", "s_b": "мкм", "a": "1", "b": "мкм", "sigma": "мкм"},
    "F-028": {"s_d": "мкм", "s_b": "мкм", "a": "1", "b": "мкм", "CV_s": "1", "CV_h": "1"},
    # F-018: показатель нелинейности. eps и x безразмерны (нормированные отклонения), a — 1.
    "F-018": {"eps": "1", "x": "1", "a": "1", "k": "1"},
    # F-027: цена роста. A — площадь (м²), k_inc — м²/(с·концентрация), gamma — 1/с.
    "F-027": {"A": "м²", "t": "с", "k_inc": "м²/(с·концентрация)", "gamma": "1/с",
              "P": "1", "c": "1"},
    "F-003": {"D": "1", "lambda": "1/с", "mu0": "1/s", "delta": "1/s", "h": "1"},
    # F-007 / F-017: порог ошибок Эйгена. Все величины безразмерные: sigma — превосходство
    # (отношение приспособленностей), q — точность копирования на основание, nu — длина генома
    # в основаниях (счётная). L_max — это же nu, а не отдельная величина (docs/UNITS-AUDIT.md §6).
    "F-007": {"sigma": "1", "q": "1", "nu": "1", "L_max": "1"},
    "F-017": {"sigma": "1", "q": "1", "nu": "1", "mu_c": "1"},
    # F-006 / F-019: критерий Chao. Pi — время повреждения (с), lambda — темп (1/с);
    # произведение безразмерно, порог 1/6 тоже. Граница — линия lambda = (1/6)/Pi.
    "F-006": {"Pi": "с", "lambda": "1/с", "a": "1", "Pi_lambda": "1"},
    "F-019": {"Pi": "с", "lambda": "1/с", "a": "1", "Pi_lambda": "1"},
    # F-014: порог полосы — типичный максимум N гауссовых шумов; sigma_g в долях, N счёт.
    # 0,37 — не редкое событие: превышение ≈ 0,5–0,63 по построению (docs/UNITS-AUDIT.md §8).
    "F-014": {"delta_c": "1", "sigma_g": "1", "N": "1"},
    # F-020: Гомпертц/Макегам. Интенсивность смертности — 1/год; alpha — 1/год;
    # alpha·x безразмерно при x в годах; t_d = ln2/alpha — годы (docs/UNITS-AUDIT.md §9).
    "F-020": {"mu": "1/год", "R": "1/год", "mu0": "1/год", "alpha": "1/год", "x": "год",
              "t_d": "год"},
    "F-022": {"C": "множество вершин, шт", "indeg": "шт", "outdeg": "шт", "scc": "доля вершин, 1"},
    "F-023": {"S": "1", "v": "1", "c": "1", "y": "1", "w": "1"},
    "F-024": {"K": "множество состояний", "V": "множество состояний", "F": "отображение шага, 1",
              "alpha": "доля дохода, 1", "band": "доля дохода, 1"},
    "F-025": {"X": "1", "I_env": "bit", "I_ind": "bit", "I_col": "bit"},
    "F-029": {"r": "1/с", "x": "состояние, 1", "eps": "параметр несовершенства, 1",
              "a": "1/с", "b": "1/с", "c": "1/с",
              "Delta_r": "1/с — ширина по параметру, ~ eps^(2/3)",
              "Delta_x": "1 — сдвиг по состоянию, ~ eps^(1/3)"},
    # F-012: уравнение Прайса. w — приспособленность (безразмерная), z — признак в своих единицах,
    # поэтому ковариация делится на среднюю приспособленность и даёт единицы признака.
    "F-012": {"z": "единицы признака", "w": "1", "Delta_z": "единицы признака",
              "Cov": "единицы признака", "w_bar": "1"},
    # F-016: цена страховки. lambda — интенсивность (1/с), sigma^2 — её дисперсия (1/с^2);
    # sigma^2/lambda^2 безразмерно, поэтому логарифмы сравнимы.
    "F-016": {"lambda_s": "1/с", "lambda_bar": "1/с", "sigma2": "1/с²"},
    # F-011: эко-подпись — разность откликов, безразмерная (доли/индексы).
    "F-011": {"Delta_R": "1", "R_original": "1", "R_modified": "1"},
    # F-013: цепь рождения–смерти с шагом ±1. p и q — вероятности перехода за шаг (безразмерны),
    # поэтому rho = p/q безразмерно, а стационарное распределение pi(i) — вероятности.
    # Медиана m — индекс состояния (счётчик), а не величина с размерностью.
    "F-013": {"p": "1", "q": "1", "rho": "1", "pi": "1", "m": "шт"},
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
            "updated_at": "2026-11-21",
        })
        lm = re.search(r"^\*\*Линии\.\*\*\s*(.+)$", body, re.M)
        if lm:
            ids = [x.strip() for x in lm.group(1).split(",") if x.strip()]
            if ids:
                out[-1]["lines"] = sorted(set(ids))
                out[-1]["data"] = {"lines_provenance": {
                    "method": "declared in formula record",
                    "source": "docs/ELEPHANT-LITERATURE.md",
                    "checked_by": None}}
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




def lines_map():
    """Parsed classification: L-NNN -> parts of the elephant (docs/ELEPHANT-MAP.md §1)."""
    path = ROOT / "kg" / "lines-map.json"
    if not path.exists():
        return {}, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("map") or {}, data


PAPERS = ROOT / "papers"


LEVEL_FULL = "full_text_examined"
LEVEL_FRAGMENT = "fragment_read"
LEVEL_ABSTRACT = "abstract_read"
LEVEL_SECONDARY = "secondary_only"

# A record that says "полный текст не читал" contains the words "полный текст" too. Negation wins,
# otherwise the two PoC cases from the second review (L-001, L-066) upgrade themselves.
NEGATIVE_MARKERS = ("не читал", "не открыл", "не дост", "не удалось", "не проверял", "не видел")


def literature_level(level_line: str) -> str:
    """Turn the human line «Проверено: …» into one of the five levels, negation first."""
    s = (level_line or "").lower()
    negative = any(marker in s for marker in NEGATIVE_MARKERS)
    if negative:
        return LEVEL_ABSTRACT if "аннотац" in s else LEVEL_SECONDARY
    if "фрагмент" in s:
        return LEVEL_FRAGMENT
    if "полный текст" in s:
        return LEVEL_FULL
    if "аннотац" in s:
        return LEVEL_ABSTRACT
    return LEVEL_SECONDARY


def artifact_integrity(rel: str) -> dict | None:
    """Size and sha256 of the local copy: the declaration now costs a file, not only its name."""
    path = ROOT / rel
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data:
        return None
    return {"artifact": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def literature_artifact(body: str) -> str | None:
    """The local copy is what turns `verified_agent` into a fact instead of a self-report.

    `docs/ELEPHANT-LITERATURE.md` says how deeply a record was read; `papers/` says whether the
    text is actually here. Before this guard the label alone promoted a node to `verified_agent`
    with `strength: strong`, and four records did it while two of them said the opposite in the
    same line ("полный текст не читал", "не открылся") -- FINDING-336.
    """
    ids = re.findall(r"arXiv:(\d{4}\.\d{4,5})", body)
    ids += [d.replace("/", "_") for d in re.findall(r"(10\.\d{4,9}/[^\s)\];,]+)", body)]
    if not ids or not PAPERS.exists():
        return None
    for path in sorted(PAPERS.iterdir()):
        if not path.is_file():
            continue
        for ident in ids:
            if ident in path.name:
                return path.relative_to(ROOT).as_posix()
    return None


LIT_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.S)


def literature_block(body: str) -> dict | None:
    """The machine record of a section: one fenced json block, written by tools/lit_migrate.py.

    The prose stays the human record; the block is what the machine is allowed to trust, and
    `checks/literature_contract.py` recounts it independently.
    """
    found = LIT_BLOCK_RE.findall(body)
    if len(found) != 1:
        return None
    try:
        return json.loads(found[0])
    except json.JSONDecodeError:
        return None


def literature_integrity(block: dict | None) -> dict | None:
    """Recount bytes and sha256 from the file; a block that lies about them is not evidence."""
    if not block:
        return None
    acc = block.get("access") or {}
    rel = acc.get("artifact")
    if not rel:
        return None
    path = ROOT / rel
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data:
        return None
    digest = hashlib.sha256(data).hexdigest()
    if acc.get("sha256") and acc.get("sha256") != digest:
        return None
    if acc.get("bytes") and acc.get("bytes") != len(data):
        return None
    return {"artifact": rel, "bytes": len(data), "sha256": digest}


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
        block = literature_block(body)
        if block:
            level_kind = (block.get("access") or {}).get("level") or literature_level(level)
            integrity = literature_integrity(block)
        else:
            # no machine block yet: fall back to the prose, but never above `extracted`
            level_kind = literature_level(level)
            artifact = literature_artifact(body) if level_kind in (LEVEL_FULL, LEVEL_FRAGMENT) else None
            integrity = artifact_integrity(artifact) if artifact else None
        if level_kind == LEVEL_FULL and integrity:
            chosen, strength = "verified_agent", "strong"
        elif level_kind == LEVEL_FRAGMENT and integrity:
            chosen, strength = "extracted", "moderate"
        else:
            chosen, strength = "extracted", "weak"
        lmap, meta = lines_map()
        lines = lmap.get(lid, [])
        prov = {"method": meta.get("method", "parsed"), "parser_version": meta.get("parser_version", "1"),
                "source": meta.get("source", ""), "checked_by": None} if lines else None
        node = {
            "id": lid,
            "kind": "claim",
            "text": (title + (" — " + statement if statement else ""))[:400],
            "context": {"scope": "literature record from ELEPHANT-LITERATURE", "parameters": "see registry", "conditions": level},
            "epistemic": "hypothesis",
            "provenance": chosen,
            "evidence": [{"kind": "literature", "ref": "docs/ELEPHANT-LITERATURE.md", "strength": strength}]
            + ([{"kind": "artifact", "ref": (integrity or {}).get("artifact"),
                "strength": strength,
                "sha256": (integrity or {}).get("sha256")}] if integrity else []),
            "relations": [],
            "data": {"source": "docs/ELEPHANT-LITERATURE.md", "license": "see source",
                     "accessed_at": "2026-11-20", "registry_level": level[:80],
                     "level_kind": level_kind, "artifact": (integrity or {}).get("artifact"),
                     "artifact_bytes": (integrity or {}).get("bytes"),
                     "artifact_sha256": (integrity or {}).get("sha256"),
                     "locator": (block or {}).get("locator")},
            "created_at": "2026-11-20",
            "updated_at": "2026-11-21",
        }
        ov = literature_overrides().get(lid)
        if ov:
            node["data"].update({k: v for k, v in ov.items() if k != "note"})
            node["data"]["override_note"] = ov.get("note", "")
            if ov.get("internal_review"):
                node["data"]["not_an_external_source"] = True
        if lines:
            node["lines"] = sorted(set(lines))
            node["data"]["lines_provenance"] = prov
        out.append(node)
    return out


def apply_lit_refs(nodes):
    """Сшивка с литературной картой: `kg/lit-refs.json` (узел kg/ -> ячейки `literature/map/`).

    Вынесено в функцию, потому что тот же второй проход делает `kg/regress.py`; иначе сверка
    «корпус -> nodes.jsonl» видит расхождение по `data`, которого нет в корпусе.
    Поле необязательное: если файла нет, ничего не меняется.
    """
    path = ROOT / "kg" / "lit-refs.json"
    if not path.exists():
        return nodes
    lit = json.loads(path.read_text(encoding="utf-8")).get("map", {})
    for node in nodes:
        refs = lit.get(node["id"])
        if refs:
            node.setdefault("data", {})["lit_ref"] = sorted(set(refs))
    return nodes


def literature_overrides():
    path = ROOT / "kg" / "literature-overrides.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("overrides") or {}


def definitions():
    """Ten line definitions (kind: definition) -- their own file, not a claim."""
    path = ROOT / "kg" / "definitions.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]



def bridges():
    """Gaps and correspondences: separate objects, not claims."""
    path = ROOT / "kg" / "bridges.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def evidence_nodes(base):
    """Evidence stops being a string: a finding or an experiment alias becomes an addressable object.

    Only refs that are not node ids and belong to the two families the graph must be able to walk
    (`FINDING-*`, `EXP-*`) become nodes. Bulk document paths stay references: 420 distinct paths
    would bury the graph in duplicates of one registry file (review 2026-11-21, §4.1).
    """
    ids = {n["id"] for n in base}
    owners = {}
    for n in base:
        for e in n.get("evidence") or []:
            ref = str(e.get("ref", ""))
            if ref in ids or not (ref.startswith("FINDING-") or ref.startswith("EXP-")):
                continue
            owners.setdefault(ref, []).append(n["id"])
    out = []
    for ref, who in sorted(owners.items()):
        is_finding = ref.startswith("FINDING-")
        out.append({
            "id": "EV-" + ref,
            "kind": "evidence",
            "text": ("находка " + ref) if is_finding else ("серия прогонов " + ref),
            "context": {"scope": "evidence object", "parameters": ref, "conditions": "см. источник"},
            "epistemic": "hypothesis",
            "provenance": "verified_agent",
            "evidence": [],
            "relations": [],
            "data": {
                "ref": ref,
                "form": "finding" if is_finding else "experiment_alias",
                "used_by": sorted(set(who)),
                "locator": ("docs/" + ref + ".md") if is_finding else "results/*",
            },
            "created_at": "2026-11-21",
            "updated_at": "2026-11-21",
        })
    return out


def main():
    base = claims() + formulas() + experiments() + literature() + definitions() + bridges()
    base = apply_lit_refs(base)
    nodes = base + evidence_nodes(base)
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
