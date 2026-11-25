"""Мост для агента `probe`: обмен файлами вместо исполнения команд.

Почему так. Схема «очередь shell-скриптов на C:\\, которые исполняются как root в репозитории» технически
работает, но снимает все ограничения проекта: скрипт из Windows-каталога может сделать `git push`, изменить
`kg/nodes.jsonl`, удалить файлы. Тогда дисциплина «публикует только main» перестаёт существовать.

Здесь мост **декларативный**: агент просит данные и присылает вопросы, а исполняет всё `main`.
Никакого shell из очереди.

Как пользоваться (main запускает):

    python3 tools/probe_bridge.py --serve          # один проход: запросы -> data/, outbox/ -> inbox/
    python3 tools/probe_bridge.py --status         # что лежит в очередях

Протокол на стороне агента (в каталоге моста, по умолчанию /mnt/c/111/probe-bridge):

    request/<NNNN>.json   {"kind": "cells", "args": {"ids": ["DIP24-0005", "DIP24-0011"]}}
    outbox/<имя>.jsonl    строки-вопросы: question, atoms, kind, numbers, verifiable

Мост создаёт:

    data/<NNNN>.md        готовый срез: полные тексты ячеек/узлов
    ack/<имя>.json        что принято, что отклонено и почему
    literature/map/inbox/probe-<дата>-<NNNN>.jsonl   принятые вопросы (уже в репозитории)

Запуск: python3 tools/probe_bridge.py --serve [--bridge /mnt/c/111/probe-bridge]
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_BRIDGE = pathlib.Path("/mnt/c/111/probe-bridge")

KINDS = {"units", "numbers", "order", "gap-as-support", "no-locator"}
REQUEST_KINDS = {"cells", "orphans", "nodes", "standing", "audit"}
MAX_PER_FILE = 24


def load_atoms() -> dict[str, dict]:
    p = ROOT / "literature" / "map" / "atoms.jsonl"
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            a = json.loads(line)
            out[a["atom"]] = a
    return out


def load_nodes() -> dict[str, dict]:
    p = ROOT / "kg" / "nodes.jsonl"
    out = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n = json.loads(line)
            out[n["id"]] = n
    return out


def load_edges() -> list[dict]:
    p = ROOT / "literature" / "map" / "edges.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def atom_block(a: dict) -> str:
    works = a.get("works") or []
    lines = [f"### {a['atom']}  [{a.get('domain')}/{a.get('kind')}]",
             f"**утверждение:** {a.get('statement')}"]
    if a.get("formula"):
        lines.append(f"**формула:** {a['formula']}")
    if a.get("notes"):
        lines.append(f"**заметки:** {a['notes']}")
    for w in works:
        lines.append(f"- DOI: {w.get('doi')} | локатор: {w.get('locator')} | доступ: {w.get('access')}")
        if w.get("quote"):
            lines.append(f"- цитата: {w['quote']}")
    return "\n".join(lines)


def node_block(n: dict) -> str:
    units = (n.get("math") or {}).get("units")
    latex = (n.get("math") or {}).get("latex") or ""
    lines = [f"### {n['id']}  [{n.get('kind')}]", f"**текст:** {n.get('text')}"]
    if latex:
        lines.append(f"**формула:** {latex}")
    if units:
        lines.append(f"**единицы:** {json.dumps(units, ensure_ascii=False)}")
    return "\n".join(lines)


def answer_request(req: dict, atoms: dict[str, dict], nodes: dict[str, dict],
                   edges: list[dict]) -> str:
    kind = req.get("kind")
    args = req.get("args") or {}
    head = f"# Срез по запросу: {kind}\n"
    if kind == "cells":
        ids = args.get("ids") or []
        parts = [atom_block(atoms[i]) for i in ids if i in atoms]
        missing = [i for i in ids if i not in atoms]
        body = "\n\n".join(parts) or "(ничего не найдено)"
        tail = f"\n\n_нет ячеек: {', '.join(missing)}_" if missing else ""
        return head + "\n" + body + tail
    if kind == "nodes":
        ids = args.get("ids") or []
        parts = [node_block(nodes[i]) for i in ids if i in nodes]
        missing = [i for i in ids if i not in nodes]
        body = "\n\n".join(parts) or "(ничего не найдено)"
        tail = f"\n\n_нет узлов: {', '.join(missing)}_" if missing else ""
        return head + "\n" + body + tail
    if kind == "orphans":
        deg = collections.Counter()
        for e in edges:
            deg[e["from"]] += 1
            deg[e["to"]] += 1
        group = args.get("group")
        ids = [i for i in atoms if deg[i] == 0 and (not group or i.startswith(group))]
        lines = [f"сирот: {len(ids)}" + (f" в группе {group}" if group else "")]
        lines += [f"- {i}" for i in sorted(ids)]
        return head + "\n" + "\n".join(lines)
    if kind == "standing":
        out = []
        for rel in (".coord/standing/S8-data-questions.md", "docs/PROBE-INSTRUCTION.md",
                    "docs/PROBE-PLAN.md", "docs/PROMPT-probe.md", "docs/PROBE-BRIDGE.md"):
            p = ROOT / rel
            if p.exists():
                out.append(f"## {rel}\n\n" + p.read_text(encoding="utf-8"))
        return head + "\n" + "\n\n".join(out)
    if kind == "audit":
        p = ROOT / "docs" / "STITCH-AUDIT.md"
        if not p.exists():
            return head + "\n(таблицы ещё нет)"
        text = p.read_text(encoding="utf-8")
        ids = args.get("ids") or []
        kept = [ln for ln in text.splitlines() if any(i in ln for i in ids)] if ids else text.splitlines()
        return head + "\n" + "\n".join(kept)
    return head + f"\nнеизвестный вид запроса: {kind}"


def norm_num(text: str) -> set[str]:
    """Числа из текста в нормализованном виде, включая научную запись с надстрочными цифрами."""
    import re as _re
    SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
           "⁻": "-", "⁺": "+"}
    out: set[str] = set()
    text = text or ""
    # сначала научная запись: 1,0·10⁻³ и 8×10⁻⁴
    for m in _re.finditer(r"(\d+(?:[.,]\d+)?)\s*[·×x]\s*10\s*(?:\^\s*([-+]?\d+)|([⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+))", text):
        mant = float(m.group(1).replace(",", "."))
        if m.group(2) is not None:
            exp = int(m.group(2))
        else:
            exp = int("".join(SUP.get(c, "") for c in (m.group(3) or "")) or 0)
        val = mant * 10 ** exp
        out.add(f"{val:g}")
        out.add(f"{mant:g}e{exp}")
        out.add(m.group(0).replace(" ", ""))      # как записано в тексте: 1.67×10^-1
    # остальные числа
    for m in _re.finditer(r"\d+(?:[.,]\d+)?", text):
        raw = m.group(0).replace(",", ".")
        out.add(raw)
        try:
            out.add(f"{float(raw):g}")
        except ValueError:
            pass
    return out


def numbers_present(q: dict, atoms: dict[str, dict]) -> str | None:
    """Каждое число вопроса должно встречаться в тексте своих ячеек (иначе оно придумано)."""
    text = " ".join(
        " ".join(str((atoms[a].get(k) or "")) for k in ("statement", "formula", "notes"))
        + " " + " ".join(str(w.get("quote") or "") for w in (atoms[a].get("works") or []))
        for a in q.get("atoms") or [] if a in atoms)
    pool = norm_num(text)
    for n in q.get("numbers") or []:
        key = str(n).replace(",", ".").replace(" ", "")
        try:
            key = f"{float(key):g}"
        except ValueError:
            pass
        if key not in pool:
            return f"число {n!r} не встречается в тексте ячеек {q.get('atoms')}"
    return None


def q_hash(q: dict) -> str:
    """Отпечаток ТЕКСТА вопроса: один и тот же вопрос не повторяем, разные — принимаем."""
    norm = re.sub(r"\s+", " ", str(q.get("question") or "").strip().lower())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def validate_submission(path: pathlib.Path, atoms: dict[str, dict],
                        seen: set[tuple[str, tuple[str, ...], str]] | None = None) -> tuple[list[dict], list[str]]:
    good, bad = [], []
    seen = seen if seen is not None else set()
    if path.suffix != ".jsonl":
        return good, [f"{path.name}: не .jsonl"]
    raw = path.read_text(encoding="utf-8")
    # сначала пробуем весь файл как JSON: массив объектов или один объект
    items: list[tuple[int, str]] = []
    try:
        whole = json.loads(raw)
        if isinstance(whole, list):
            items = [(i, json.dumps(x, ensure_ascii=False)) for i, x in enumerate(whole, 1)]
        elif isinstance(whole, dict):
            items = [(1, json.dumps(whole, ensure_ascii=False))]
    except json.JSONDecodeError:
        pass
    if not items:
        # иначе — построчно, но собираем многострочные объекты по балансу скобок
        buf, depth, start = [], 0, 0
        for no, line in enumerate(raw.splitlines(), 1):
            if not line.strip() and not buf:
                continue
            buf.append(line)
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                items.append((start or no, "\n".join(buf)))
                buf, depth, start = [], 0, 0
        if buf:
            items.append((start or 1, "\n".join(buf)))
    if len(items) > MAX_PER_FILE:
        bad.append(f"{path.name}: {len(items)} вопросов, потолок {MAX_PER_FILE}")
    for i, line in items:
        try:
            q = json.loads(line)
        except json.JSONDecodeError as exc:
            bad.append(f"{path.name}:{i}: не JSON ({exc.msg})")
            continue
        problem = None
        if len(str(q.get("question") or "")) < 20:
            problem = "вопрос короче 20 символов"
        elif q.get("kind") not in KINDS:
            problem = f"kind {q.get('kind')!r} не из {sorted(KINDS)}"
        elif not q.get("atoms") or not all(a in atoms for a in q["atoms"]):
            problem = f"atoms не найдены в карте: {q.get('atoms')}"
        elif not isinstance(q.get("numbers"), list) or len(q["numbers"]) < 2:
            problem = "нужно ≥2 числа (numbers)"
        elif not q.get("verifiable"):
            problem = "нет поля verifiable: как проверить ответ"
        elif q.get("kind") in ("units", "order") and not q.get("recalc"):
            problem = "для units/order обязателен recalc — пересчёт"
        if not problem:
            problem = numbers_present(q, atoms)
        if not problem:
            sig = (str(q.get("kind")), tuple(sorted(q.get("atoms") or [])), q_hash(q))
            if sig in seen:
                problem = "этот же вопрос уже принимался (совпал текст)"
            else:
                seen.add(sig)
        if problem:
            bad.append(f"{path.name}:{i}: {problem}")
        else:
            good.append(q)
    return good, bad


def serve(bridge: pathlib.Path) -> int:
    atoms, nodes = load_atoms(), load_nodes()
    edges = load_edges()
    req_dir, data_dir = bridge / "request", bridge / "data"
    out_dir, ack_dir = bridge / "outbox", bridge / "ack"
    for d in (req_dir, data_dir, out_dir, ack_dir):
        d.mkdir(parents=True, exist_ok=True)

    done = 0
    for req_path in sorted(req_dir.glob("*.json")) + sorted(req_dir.glob("*.req")):
        try:
            req = json.loads(req_path.read_text(encoding="utf-8"))
        except Exception as exc:
            (ack_dir / f"{req_path.stem}.error").write_text(f"не разобрать запрос: {exc}", encoding="utf-8")
            req_path.rename(req_dir / (req_path.name + ".bad"))
            continue
        if req.get("kind") not in REQUEST_KINDS:
            (ack_dir / f"{req_path.stem}.error").write_text(
                f"вид запроса {req.get('kind')!r} не разрешён: {sorted(REQUEST_KINDS)}", encoding="utf-8")
            req_path.rename(req_dir / (req_path.name + ".bad"))
            continue
        (data_dir / f"{req_path.stem}.md").write_text(answer_request(req, atoms, nodes, edges),
                                                      encoding="utf-8")
        req_path.rename(bridge / "done" / req_path.name)
        done += 1
        print(f"запрос {req_path.stem}: готово -> data/{req_path.stem}.md")

    state = bridge / "state" / "probe-seen.json"
    seen: set[tuple[str, tuple[str, ...]]] = set()
    if state.exists():
        try:
            raw = json.loads(state.read_text(encoding="utf-8"))
            seen = set()
            for item in raw:
                if len(item) == 3:
                    seen.add((item[0], tuple(item[1]), item[2]))
                elif len(item) == 2:
                    seen.add((item[0], tuple(item[1]), "old"))
        except Exception:
            seen = set()

    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M")
    inbox = ROOT / "literature" / "map" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    triage_rows = []
    for sub in sorted(out_dir.glob("*.jsonl")):
        good, bad = validate_submission(sub, atoms, seen)
        for q in good:
            triage_rows.append(q)
        ack = {"file": sub.name, "accepted": len(good), "rejected": len(bad), "reasons": bad}
        if good:
            out_file = inbox / f"probe-{stamp}-{sub.stem}.jsonl"
            out_file.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in good) + "\n",
                                encoding="utf-8")
            ack["written_to"] = str(out_file.relative_to(ROOT))
            print(f"принято {len(good)} из {len(good) + len(bad)} -> {ack['written_to']}")
        else:
            print(f"{sub.name}: принято 0 из {len(bad)}")
        (ack_dir / f"{sub.stem}.json").write_text(json.dumps(ack, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
        sub.rename(bridge / "done" / sub.name)

    state.write_text(json.dumps(sorted([[k, list(v), h] for k, v, h in seen]), ensure_ascii=False),
                     encoding="utf-8")
    if triage_rows:
        triage = ROOT / "docs" / "PROBE-TRIAGE.md"
        by_kind = collections.Counter(q.get("kind") for q in triage_rows)
        lines = ["# Очередь вопросов `probe` на проверку", "",
                 f"Обновлено: {dt.datetime.now():%Y-%m-%d %H:%M}. Принято мостом: {len(triage_rows)}.", "",
                 "| вид | сколько |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in sorted(by_kind.items())]
        lines += ["", "## Вопросы", ""]
        for q in triage_rows:
            lines.append(f"- **[{q.get('kind')}]** {q.get('question')}")
            lines.append(f"  - ячейки: {', '.join(q.get('atoms') or [])}; числа: {', '.join(map(str, q.get('numbers') or []))}")
        triage.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"триаж записан: docs/PROBE-TRIAGE.md ({len(triage_rows)} вопросов)")

    if not done and not any(out_dir.glob("*.jsonl")):
        print("очередь пуста: ни запросов, ни посылок")
    return 0


def status(bridge: pathlib.Path) -> int:
    for name in ("queue", "request", "outbox", "data", "done", "ack"):
        d = bridge / name
        n = len(list(d.glob("*"))) if d.exists() else 0
        print(f"{name:8} {n:3} файлов")
    rnd = bridge / "state" / "round"
    if rnd.exists():
        print("round:", rnd.read_text(encoding="utf-8").strip())
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="обмен файлами с агентом probe")
    ap.add_argument("--bridge", default=str(DEFAULT_BRIDGE))
    ap.add_argument("--serve", action="store_true", help="один проход: запросы и посылки")
    ap.add_argument("--status", action="store_true", help="состояние каталогов моста")
    args = ap.parse_args(argv)
    bridge = pathlib.Path(args.bridge)
    if not bridge.exists():
        print(f"нет каталога моста: {bridge}")
        return 1
    if args.status:
        return status(bridge)
    return serve(bridge)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
