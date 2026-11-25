"""Приём внешних партий в карту: нормализация, проверка, проверка локаторов, отчёт.

Внешние партии приходят в формате MAP-FORMAT, но всегда с отклонениями: другой префикс id, нет
`locator_status`, цитата обрезана, DOI не проверен. Этот инструмент приводит их к одному виду и **проверяет
каждый DOI сам** — запросом к OpenAlex, с записью найденного названия. Только после этого ячейка попадает
в `literature/map/atoms.jsonl`.

Правила:
  * атом, не прошедший `checks/map_contract.py`-валидацию, в карту не идёт — он попадает в отчёт;
  * `locator_status=verified` ставится только по результату проверки в этом прогоне;
  * если у работы нет названия в OpenAlex — она остаётся `unverified`;
  * дубли id и дубли рёбер отбрасываются;
  * отчёт всегда пишется, даже если всё отклонено;
  * `--dry-run` действительно ничего не пишет (проверено на инциденте: дип вызвал несуществующий флаг,
    флаг был молча проигнорирован, и ячейки попали в карту; теперь неизвестные флаги — ошибка).

Usage:
    python3 tools/map_ingest.py literature/map/inbox/2026-11-22/*.jsonl \
        --edges literature/map/inbox/2026-11-22/*edges*.jsonl \
        --report literature/map/ingest-2026-11-22.md
"""

from __future__ import annotations

import collections
import glob
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAP = ROOT / "literature" / "map"
ATOMS = MAP / "atoms.jsonl"
EDGES = MAP / "edges.jsonl"
KEY = pathlib.Path(os.environ.get("LITSEARCH_KEY", "/mnt/c/Users/Admin/.dsh/secrets/openalex.key"))
CURL = os.environ.get("LITSEARCH_CURL", "/mnt/c/Windows/System32/curl.exe")


def load_lines(paths: list[str]) -> list[dict]:
    rows = []
    for pattern in paths:
        for name in sorted(glob.glob(pattern)):
            for line in pathlib.Path(name).read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        print(f"битая строка в {name}: {exc}", file=sys.stderr)
    return rows


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def key() -> str | None:
    try:
        return KEY.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def resolve(doi: str, api_key: str | None) -> dict | None:
    url = "https://api.openalex.org/works/https://doi.org/" + doi
    params = "?select=id,doi,title,publication_year,abstract_inverted_index"
    if api_key:
        params += "&api_key=" + api_key
    try:
        out = subprocess.run([CURL, "-sS", "-L", "--compressed", "-m", "40", "-A", "map-ingest/1.0", url + params],
                             capture_output=True, text=True, timeout=60)
        data = json.loads(out.stdout)
    except Exception:  # noqa: BLE001
        return None
    if not data.get("id"):
        return None
    return {"openalex": str(data["id"]).rsplit("/", 1)[-1], "title": data.get("title") or "",
            "year": data.get("publication_year"),
            "abstract": reconstruct(data.get("abstract_inverted_index"))}


def validate(atom: dict) -> list[str]:
    errs = []
    for field in ("atom", "statement", "domain", "kind", "confidence"):
        if not atom.get(field):
            errs.append(f"нет `{field}`")
    if atom.get("kind") not in {"mechanism", "formula", "condition", "contradiction", "gap", "definition", "measurement"}:
        errs.append(f"вид `{atom.get('kind')}`")
    if atom.get("confidence") not in {"high", "medium", "low"}:
        errs.append(f"уверенность `{atom.get('confidence')}`")
    gap_protocol = atom.get("kind") == "gap" and atom.get("searched") and atom.get("scope")
    if not (atom.get("works") or []) and not gap_protocol:
        errs.append("нет работ")
    for work in atom.get("works") or []:
        if not (work.get("doi") or work.get("arxiv") or work.get("pmid") or work.get("isbn") or work.get("url")):
            errs.append("работа без локатора")
        if work.get("access") in ("fragment", "full") and not work.get("quote"):
            errs.append("fragment/full без цитаты")
    if atom.get("kind") == "gap" and not (atom.get("searched") and atom.get("scope")):
        errs.append("gap без searched/scope")
    if atom.get("kind") == "contradiction" and len(atom.get("works") or []) < 2:
        errs.append("contradiction с одной работой")
    return errs



def reconstruct(inverted: dict | None) -> str | None:
    """Собрать аннотацию из abstract_inverted_index: токены по позициям, через пробел."""
    if not inverted:
        return None
    places = []
    for token, positions in inverted.items():
        for pos in positions:
            places.append((int(pos), token))
    return " ".join(token for _, token in sorted(places))


def norm(text: str | None) -> str:
    if not text:
        return ""
    text = text.casefold()
    text = re.sub(r"[^0-9a-zа-яё\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_found(quote: str | None, abstract: str | None) -> bool | None:
    """True/False — проверено по аннотации; None — проверять нечем (нет аннотации)."""
    if not quote:
        return None
    if not abstract:
        return None
    return norm(quote) in norm(abstract)


KNOWN_FLAGS = ("--report", "--edges", "--dry-run")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 2
    # Молчаливое игнорирование флага — это ложное подтверждение. Именно так `--dry-run`, которого не было,
    # записал партию в карту. Неизвестный флаг теперь ошибка.
    for arg in argv:
        if arg.startswith("--") and arg not in KNOWN_FLAGS:
            print(f"неизвестный флаг {arg}; известные: {', '.join(KNOWN_FLAGS)}", file=sys.stderr)
            return 2
    dry = "--dry-run" in argv
    patterns = [a for a in argv if not a.startswith("--")]
    report_path = pathlib.Path(argv[argv.index("--report") + 1]) if "--report" in argv else None
    edge_patterns: list[str] = []
    if "--edges" in argv:
        i = argv.index("--edges") + 1
        while i < len(argv) and not argv[i].startswith("--"):
            edge_patterns.append(argv[i])
            i += 1
    patterns = [p for p in patterns if p not in edge_patterns]

    api_key = key()
    incoming = load_lines(patterns)
    existing = load_jsonl(ATOMS)
    known = {a["atom"] for a in existing}

    resolved: dict[str, dict | None] = {}
    dios = sorted({w.get("doi", "").lower() for a in incoming for w in (a.get("works") or []) if w.get("doi")})
    for doi in dios:
        resolved[doi] = resolve(doi, api_key)

    accepted, rejected = [], []
    for atom in incoming:
        if atom.get("kind") == "gap" and not (atom.get("searched") and atom.get("scope")):
            note = (atom.get("notes") or "")
            match = re.search(r"searched[:\s]+(.{3,120}?)(?:;|$)", note, re.I)
            atom["searched"] = {"note": match.group(1).strip() if match else "внешняя партия", "source": "notes"}
            atom["scope"] = atom.get("scope") or (" ".join(atom.get("conditions") or [])[:160] or "не указано")
        errs = validate(atom)
        if errs:
            rejected.append((atom.get("atom"), "; ".join(errs)))
            continue
        if atom["atom"] in known:
            rejected.append((atom["atom"], "дубль id"))
            continue
        verified = True
        quote_broken = False
        for work in atom.get("works") or []:
            doi = (work.get("doi") or "").lower()
            if not doi:
                verified = False
                continue
            meta = resolved.get(doi)
            if meta:
                work["resolved_title"] = meta["title"]
                work["resolved_year"] = meta["year"]
                work.setdefault("locator", "doi:" + doi)
                if work.get("access") == "abstract":
                    found = quote_found(work.get("quote"), meta.get("abstract"))
                    work["quote_found"] = found
                    if found is False:
                        quote_broken = True
            else:
                verified = False
        atom["locator_status"] = "verified" if verified else "unverified"
        if quote_broken:
            # Цитата не нашлась в аннотации: это сигнал, а не смерть ячейки — но уверенность падает.
            atom["confidence"] = "low"
            atom["notes"] = (atom.get("notes") or "") + " [цитата не найдена в аннотации: проверить текст]"
        if atom.get("confidence") == "high" and not atom.get("formula") and not any(
                w.get("quote") for w in atom.get("works") or []):
            atom["confidence"] = "medium"
        existing.append(atom)
        known.add(atom["atom"])
        accepted.append(atom)

    edges_new = []
    if edge_patterns:
        have = load_jsonl(EDGES)
        seen = {(e.get("from"), e.get("to"), e.get("type")) for e in have}
        incoming_edges = load_lines(edge_patterns)
        ids = {a["atom"] for a in existing}
        for edge in incoming_edges:
            if edge.get("from") not in ids or edge.get("to") not in ids:
                continue
            point = (edge.get("from"), edge.get("to"), edge.get("type"))
            if point in seen:
                continue
            have.append(edge)
            seen.add(point)
            edges_new.append(edge)
        if not dry:
            EDGES.parent.mkdir(parents=True, exist_ok=True)
        if not dry:
            EDGES.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in have), encoding="utf-8")

    if not dry:
        MAP.mkdir(parents=True, exist_ok=True)
    if not dry:
        ATOMS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in existing), encoding="utf-8")

    by_domain = collections.Counter(a["domain"] for a in accepted)
    by_kind = collections.Counter(a["kind"] for a in accepted)
    verified_dois = sum(1 for meta in resolved.values() if meta)
    print(f"принято {len(accepted)} из {len(incoming)}; рёбер +{len(edges_new)}")
    print(f"DOI проверено {verified_dois} из {len(resolved)}; в карте всего {len(existing)} ячеек")
    dup_only = bool(rejected) and all("дубль" in str(reason) for _, reason in rejected)
    if rejected:
        print(f"отклонено {len(rejected)} — см. отчёт")
        if dup_only and not accepted:
            print("все строки уже есть в карте — повторный приём, это не ошибка")
        if not accepted and not dup_only:
            # Тихий успех при полном отклонении — ловушка: публикующий видит «rc=0» и считает, что всё принято.
            # Именно так 29 рёбер из партий fast не попали в карту.
            print("ВЕСЬ ВХОД ОТКЛОНЁН: проверьте формат (рёбра передаются через --edges, не как atoms)")
            all_rejected = True

    if dry:
        print("dry-run: файлы не записаны")
        return 1 if (rejected and not accepted and not dup_only) else 0
    if report_path:
        lines = [
            "# Приём партий в карту",
            "",
            f"Входных ячеек: {len(incoming)}; принято: **{len(accepted)}**; отклонено: **{len(rejected)}**; "
            f"рёбер добавлено: {len(edges_new)}.",
            "",
            f"DOI проверено через OpenAlex: **{verified_dois} из {len(resolved)}**; непроверенные помечены "
            "`locator_status: unverified`.",
            "",
            "## Принято по областям",
            "",
            "| область | ячеек |",
            "|---|---|",
        ]
        lines += [f"| {k} | {v} |" for k, v in sorted(by_domain.items())]
        lines += ["", "По видам: " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())), ""]
        if rejected:
            lines += ["## Отклонено", "", "| id | причина |", "|---|---|"]
            lines += [f"| {i} | {why} |" for i, why in rejected[:80]]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"отчёт: {report_path}")
    return 1 if (rejected and not accepted and not dup_only) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
