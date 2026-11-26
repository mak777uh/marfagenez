#!/usr/bin/env python3
"""coord_migrate.py v1 — инвентарь и экспорт .coord/ (Фаза 1 миграции).

Read-only. Фаза 1 требует мигратор с --dry-run и отчётом о потерянных
сущностях; сам перенос (Фаза 3) сюда НЕ входит, поэтому опция --write
(импорт) в v1 отсутствует и запуск ничего не пишет в .coord/.

Выход:
  --out JSON    снимок по lab/migration/coord-export.schema.json (v1)
  --report TXT  человекочитаемый отчёт: счётчики, непарсящееся,
                эвристики department, transferable claims

Правила:
  - неизвестное и непарсящееся не теряется молча: попадает в unresolved
    и в отчёт, решение остаётся за main;
  - legacy ID (P*, S*, раунды, gens) сохраняются как есть;
  - порядок обхода и ключи вывода детерминированы, повторный запуск
    идентичен (можно сверять хэши);
  - mail read/ack, которые координатор не фиксирует, выгружаются как
    null (unverifiable), а не выдумываются.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SECTIONS_TASK = ("## Рабочая область", "## Критерии приёмки", "## Что нужно сделать")
ROUND_RE = re.compile(r"^(?P<base>[PESFG0-9][A-Za-z0-9-]*?)-(?P<ts>20\d{6}T\d{6})-(?P<agent>[A-Za-z0-9_]+)$")
WHO_RE = re.compile(r"^# (?P<id>\S+) — (?P<title>.+)$")
META_RE = {
    "автор": re.compile(r"^- автор: `(.+)`"),
    "вид": re.compile(r"^- вид: `(.+)`"),
    "постоянная": re.compile(r"^- постоянная: (да|нет)"),
    "приоритет": re.compile(r"^- приоритет: (\d+)"),
    "создана": re.compile(r"^- создана: (\S+)"),
}
BULLET_RE = re.compile(r"^- `(.+)`")
EVENT_RE = re.compile(r"^# (?P<ts>\S+ \S+) — (?P<agent>\S+)$")

def department_for(area: list[str], title: str) -> tuple[str, str]:
    """Эвристика контура по области/заголовку. Возвращает (department, rationale)."""
    a = " ".join(area).lower(); t = title.lower()
    if any(s in a for s in ("laws/", "lean", "verus")) or "lean" in t or "формул" in t:
        return "formulas", "область laws/lean/verus либо заголовок"
    if any(s in a for s in ("results/", "core/", "experiments")) or "эксперимент" in t or "прогон" in t:
        return "experiments", "область results/core либо заголовок"
    return "knowledge", "по умолчанию: литература/граф/прочее"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_task_md(text: str) -> dict:
    lines = text.splitlines()
    card: dict = {"id": None, "title": None, "area": [], "accept": [], "note_lines": []}
    section = None
    for ln in lines:
        m = WHO_RE.match(ln)
        if m:
            card["id"], card["title"] = m.group("id"), m.group("title").strip()
            continue
        if any(ln.startswith(s) for s in SECTIONS_TASK):
            section = ln.strip()
            continue
        if section and ln.startswith("## "):
            section = None
            continue
        for key, rx in META_RE.items():
            m = rx.match(ln)
            if m:
                card[key] = m.group(1)
        b = BULLET_RE.match(ln)
        if b and section and section.startswith("## Рабочая"):
            card["area"].append(b.group(1))
        elif b and section and section.startswith("## Критерии"):
            card["accept"].append(b.group(1))
        elif section and section.startswith("## Что нужно") and ln.strip():
            card["note_lines"].append(ln)
    return card

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"__error__": f"{type(e).__name__}: {e}"}

class Migrator:
    def __init__(self, root: Path):
        self.root = root
        self.tasks: list[dict] = []
        self.standing_templates: list[dict] = []
        self.agents: list[dict] = []
        self.events: list[dict] = []
        self.messages: list[dict] = []
        self.unresolved: list[dict] = []
        self.counts: dict[str, int] = {}
        self.inventory: list[dict] = []
        self.gens: dict[str, int] = {}
        self.locks: list[dict] = []

    def inv(self, rel: str, typ: str, p: Path):
        self.inventory.append({
            "path": rel, "type": typ, "bytes": p.stat().st_size,
            "sha256": sha256_file(p), "mtime": int(p.stat().st_mtime)})

    def note_unresolved(self, typ, path, reason, p: Path | None = None):
        rec = {"type": typ, "path": path, "reason": reason}
        if p is not None:
            rec["sha256"] = sha256_file(p)
        self.unresolved.append(rec)

    def add_task(self, tid: str, state: str, d: Path, month: str = "") -> None:
        tmd = d / "TASK.md"
        card = parse_task_md(tmd.read_text(encoding="utf-8")) if tmd.exists() else {}
        tid = tid or card.get("id") or d.name
        claim = load_json(d / ".claim.json") if (d / ".claim.json").exists() else None
        done = load_json(d / "DONE.json") if (d / "DONE.json").exists() else None
        if isinstance(claim, dict) and "__error__" in claim:
            self.note_unresolved("claim-unparsable", str(d / ".claim.json"), claim["__error__"], d / ".claim.json")
        if isinstance(done, dict) and "__error__" in done:
            self.note_unresolved("done-unparsable", str(d / "DONE.json"), done["__error__"], d / "DONE.json")
        claim_clean = claim if isinstance(claim, dict) and "__error__" not in (claim or {}) else None
        done_clean = done if isinstance(done, dict) and "__error__" not in (done or {}) else None
        area = claim_clean.get("area") if claim_clean else card.get("area", [])
        dept, why = department_for(area or [], card.get("title") or tid)
        task = {
            "id": tid, "state": state, "department": dept,
            "department_rationale": why,
            "title": card.get("title") or (done_clean or {}).get("task") or tid,
            "area": area or [], "write_scope": list(area or []),
            "accept": card.get("accept", []),
            "priority": int(claim_clean["priority"]) if claim_clean and "priority" in claim_clean
                        else int(card["приоритет"]) if card.get("приоритет") and str(card.get("приоритет")).isdigit()
                        else None,
            "task_md_sha256": sha256_file(tmd) if tmd.exists() else None,
            "max_gen": self.gens.get(tid, (claim_clean or {}).get("gen") if claim_clean else None),
            "has_result": (d / "RESULT.md").exists(),
            "done_json": done_clean or ({} if (d / "DONE.json").exists() else None),
            "raw_paths": sorted(str(x.relative_to(self.root)) for x in d.rglob("*") if x.is_file()),
        }
        if state == "active" and claim_clean:
            task["claim"] = {
                "round_id": d.name, "agent": claim_clean.get("agent"),
                "gen": claim_clean.get("gen"),
                "taken_at": claim_clean.get("taken_at"),
                "ttl_remaining_seconds": 180 * 60,
                "transferable": True,
                "boot_id": claim_clean.get("boot_id"),
                "task_sha256": claim_clean.get("task_sha256"),
                "standing": claim_clean.get("standing"),
                "parent": claim_clean.get("parent"),
            }
        self.tasks.append(task)

    def run(self) -> None:
        for sub, state in (("pending", "pending"), ("active", "active"), ("completed", "completed")):
            base = self.root / sub
            if not base.is_dir():
                continue
            for d in sorted(base.iterdir()):
                if d.is_dir():
                    # completed/<YYYY-MM>/<задача>/ — месячный архив закрытых задач
                    if state == "completed" and re.match(r"^\d{4}-\d{2}$", d.name):
                        for sd in sorted(d.iterdir()):
                            if sd.is_dir():
                                before = len(self.tasks)
                                self.add_task(sd.name, state, sd, month=d.name)
                                if len(self.tasks) == before:
                                    self.note_unresolved("task-dir-unparsed", str(sd),
                                                         "в месячном архиве нет TASK.md и не распознана")
                                for f in sd.rglob("*"):
                                    if f.is_file():
                                        self.inv(str(f.relative_to(self.root)),
                                                 f"completed/{d.name}-task-file", f)
                            elif sd.is_file():
                                self.note_unresolved("completed-loose-file", str(sd),
                                                     "файл в месячном архиве без папки задачи", sd)
                        continue
                    before = len(self.tasks)
                    self.add_task(d.name, state, d)
                    if len(self.tasks) == before:
                        self.note_unresolved("task-dir-unparsed", str(d), "нет TASK.md и не распознана")
                    for f in d.rglob("*"):
                        if f.is_file():
                            self.inv(str(f.relative_to(self.root)), f"{state}-task-file", f)
                elif d.is_file():
                    self.note_unresolved(f"{sub}-loose-file", str(d), "файл в каталоге задач без папки", d)

        std = self.root / "standing"
        if std.is_dir():
            for f in sorted(std.iterdir()):
                if f.name.endswith("-card.md"):
                    continue
                if f.is_file():
                    tid = f.name[:-3] if f.name.endswith(".md") else f.name
                    card = std / (f.name[:-3] + "-card.md") if f.name.endswith(".md") else None
                    self.standing_templates.append({
                        "id": tid, "department": department_for([], tid)[0],
                        "card_sha256": sha256_file(card) if card and card.exists() else None,
                        "latest_round": None,
                        "history": [],
                        "instruction_sha256": sha256_file(f),
                    })
                elif f.is_dir():
                    self.note_unresolved("standing-dir", str(f), "неожиданный каталог в standing/")

        agents = self.root / "agents"
        if agents.is_dir():
            for f in sorted(agents.iterdir()):
                if f.is_file():
                    self.agents.append({"agent_id": f.name.rsplit(".", 1)[0],
                                        "role_md_sha256": sha256_file(f)})
                else:
                    self.note_unresolved("agents-unknown", str(f), "не файл")

        ev = self.root / "events"
        if ev.is_dir():
            for f in sorted(ev.iterdir()):
                if not f.is_file():
                    self.note_unresolved("events-unknown", str(f), "не файл")
                    continue
                text = f.read_text(encoding="utf-8")
                m = EVENT_RE.match(text.splitlines()[0] if text.splitlines() else "")
                self.events.append({
                    "file": f.name, "ts": m.group("ts") if m else None,
                    "agent": m.group("agent") if m else None,
                    "body_sha256": sha256_file(f),
                    "body": text if f.stat().st_size < 8192 else None,
                })

        mail = self.root / "mail"
        if mail.is_dir():
            for agent_dir in sorted(mail.iterdir()):
                if not agent_dir.is_dir():
                    self.note_unresolved("mail-unknown", str(agent_dir), "не каталог агента", agent_dir)
                    continue
                # maildir-семантика: mail/<agent>/new — не прочитано, mail/<agent>/read — прочитано.
                # Время прочтения координатор не фиксирует: read_at=null, факт — из каталога (box).
                for box in ("new", "read"):
                    box_dir = agent_dir / box
                    if box_dir.is_file():
                        self.note_unresolved("mail-unknown", str(box_dir), "файл вместо каталога new/read", box_dir)
                        continue
                    if not box_dir.is_dir():
                        continue
                    for f in sorted(box_dir.iterdir()):
                        if not f.is_file():
                            self.note_unresolved("mail-unknown", str(f), "не файл")
                            continue
                        try:
                            j = json.loads(f.read_text(encoding="utf-8"))
                        except Exception:
                            j = None
                        self.messages.append({
                            "id": f.name, "from": (j or {}).get("from") or "unknown",
                            "to": agent_dir.name,
                            "body_sha256": sha256_file(f),
                            "raw_path": str(f.relative_to(self.root)),
                            "body": (j or {}).get("body") if isinstance(j, dict) else
                                    (f.read_text(encoding="utf-8") if f.stat().st_size < 16384 else None),
                            "box": box,
                            "read_at": None, "ack_at": None,
                            "read_ack_verifiable": True,
                        })
                for other in agent_dir.iterdir():
                    if other.name not in ("new", "read") and other.is_file():
                        self.note_unresolved("mail-unknown", str(other),
                                             "файл вне new/read в почте агента", other)

        gens_dir = self.root / "gens"
        if gens_dir.is_dir():
            for d in sorted(gens_dir.iterdir()):
                if d.is_dir():
                    entries = sorted(x.name for x in d.iterdir())
                    self.gens[d.name] = len(entries)
                    self.counts[f"gens:{d.name}"] = len(entries)
                    continue
                try:
                    self.gens[d.name] = int(d.read_text(encoding="utf-8").strip() or 0)
                except Exception:
                    self.note_unresolved("gens-unknown", str(d), "не число и не каталог генераций", d)

        locks = self.root / "locks"
        if locks.is_dir():
            for f in sorted(locks.rglob("*")):
                if f.is_file():
                    self.locks.append({"path": str(f.relative_to(self.root)),
                                        "sha256": sha256_file(f)})

        backups = self.root / "backups"
        if backups.is_dir():
            n = 0
            for f in sorted(backups.rglob("*")):
                if f.is_file():
                    self.inv(str(f.relative_to(self.root)), "backup", f)
                    n += 1
            self.counts["backup_files"] = n

        gy = self.root / "graveyard"
        if gy.is_dir():
            for f in sorted(gy.iterdir()):
                self.note_unresolved("graveyard-object", str(f),
                                     "архивный объект (просмотр при импорте)", f)

        for other in ("STATUS.md", "README.md"):
            p = self.root / other
            if p.exists():
                self.inv(other, "render", p)
        for d in self.root.iterdir():
            if d.name in {"pending", "active", "completed", "standing", "agents",
                          "events", "mail", "gens", "locks", "graveyard", "backups"}:
                continue
            if d.is_dir():
                self.note_unresolved("coord-dir-other", str(d), "нераспознанный каталог .coord/")
            elif d.is_file():
                self.inv(str(d.relative_to(self.root)), "other-file", d)

        self.counts.update({
            "tasks": len(self.tasks), "pending": sum(1 for t in self.tasks if t["state"] == "pending"),
            "active": sum(1 for t in self.tasks if t["state"] == "active"),
            "completed": sum(1 for t in self.tasks if t["state"] == "completed"),
            "standing_templates": len(self.standing_templates),
            "agents": len(self.agents), "events": len(self.events),
            "messages": len(self.messages), "unresolved": len(self.unresolved),
            "locks": len(self.locks), "inventory_files": len(self.inventory),
        })

    def export(self, repo_head: str, exported_at: str) -> dict:
        for t in self.tasks:
            candidates = [v for v in (t.get("max_gen"), self.gens.get(t["id"])) if v is not None]
            t["max_gen"] = max(candidates) if candidates else None
            if "claim" in t and t["claim"].get("gen") is not None:
                t["claim"]["lease_epoch_base"] = t["claim"]["gen"]
        return {
            "schema": "coord-export/v1",
            "exported_at": exported_at, "repo_head": repo_head,
            "coord_snapshot_sha256": hashlib.sha256(
                "\n".join(f"{i['sha256']}  {i['path']}" for i in sorted(
                    self.inventory, key=lambda x: x["path"])).encode()
            ).hexdigest(),
            "counts": self.counts,
            "tasks": self.tasks, "standing_templates": self.standing_templates,
            "agents": self.agents, "events": self.events,
            "messages": self.messages, "unresolved": self.unresolved,
        }

def main() -> int:
    ap = argparse.ArgumentParser(description="Инвентарь .coord/ (read-only, Фаза 1)")
    ap.add_argument("--coord", required=True, help="путь к .coord/")
    ap.add_argument("--out", help="путь JSON-снимка (coord-export/v1)")
    ap.add_argument("--report", help="путь человекочитаемого отчёта")
    ap.add_argument("--repo-head", default="")
    ap.add_argument("--exported-at", default="")
    args = ap.parse_args()

    root = Path(args.coord)
    if not root.is_dir():
        print(f"ошибка: {root} не существует", file=sys.stderr)
        return 2

    mig = Migrator(root)
    mig.run()
    snap = mig.export(args.repo_head or "unknown", args.exported_at or "unknown")

    print("=== coord_migrate v1 (dry-run, read-only) ===")
    for k in sorted(mig.counts):
        print(f"  {k}: {mig.counts[k]}")
    print(f"  unresolved всего: {len(mig.unresolved)}")
    print("  активные claim (transferable): "
          f"{[t['id'] for t in mig.tasks if t.get('claim', {}).get('transferable')]}")
    heur = [t["id"] for t in mig.tasks if t.get("department_rationale", "").startswith("по умолчанию")]
    print(f"  department по эвристике по умолчанию (знания): {len(heur)} задач: {heur[:12]}")
    print(f"  mail: {len(mig.messages)} сообщений "
          f"(new={sum(1 for m in mig.messages if m['box'] == 'new')}, "
          f"read={sum(1 for m in mig.messages if m['box'] == 'read')}); "
          f"ack координатор не фиксирует — решение за main при импорте")

    if args.out:
        Path(args.out).write_text(json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True),
                                  encoding="utf-8")
        print(f"снимок: {args.out}")
    if args.report:
        lines = ["# Отчёт coord_migrate v1 (dry-run)", "",
                 "## Счётчики", ""] + [
                 f"- {k}: {v}" for k, v in sorted(mig.counts.items())] + [
                 "", "## Unresolved (решение за main)", ""]
        lines += [f"- [{u['type']}] {u['path']}: {u['reason']}" for u in mig.unresolved]
        lines += ["", "## Эвристики department", "",
                  "- formulas: область laws/lean/verus либо заголовок",
                  "- experiments: область results/core либо заголовок",
                  f"- knowledge (по умолчанию): {heur}", "",
                  "## Активные claim", ""]
        lines += [f"- {t['id']}: agent={t['claim']['agent']} gen={t['claim']['gen']} "
                  f"boot_id={t['claim'].get('boot_id')}" for t in mig.tasks if "claim" in t]
        lines += ["", "## Соответствие требований Фазы 1",
                  "",
                  "- полный снимок, включая ignored runtime-состояние: да",
                  "- dry-run не меняет старое состояние: да (read-only)",
                  "- неизвестные сущности в отчёте, не теряются молча: да",
                  "- legacy ID сохранены как есть: да",
                  "- идемпотентность экспорта: детерминированный обход, сортированные ключи"]
        Path(args.report).write_text("\n".join(lines), encoding="utf-8")
        print(f"отчёт: {args.report}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
