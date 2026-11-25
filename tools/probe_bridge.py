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
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_BRIDGE = pathlib.Path("/mnt/c/111/probe-bridge")

KINDS = {"units", "numbers", "order", "gap-as-support", "no-locator"}
REQUEST_KINDS = {"cells", "orphans", "nodes", "standing", "audit"}
MAX_PER_FILE = 8


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
        for rel in (".coord/standing/S8-data-questions.md", "docs/PROBE-PLAN.md",
                    "docs/PROMPT-probe.md"):
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


def validate_submission(path: pathlib.Path, atoms: dict[str, dict]) -> tuple[list[dict], list[str]]:
    good, bad = [], []
    if path.suffix != ".jsonl":
        return good, [f"{path.name}: не .jsonl"]
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(lines) > MAX_PER_FILE:
        bad.append(f"{path.name}: {len(lines)} вопросов, потолок {MAX_PER_FILE}")
    for i, line in enumerate(lines, 1):
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

    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M")
    inbox = ROOT / "literature" / "map" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    for sub in sorted(out_dir.glob("*.jsonl")):
        good, bad = validate_submission(sub, atoms)
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
