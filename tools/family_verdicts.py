"""Разбор семейств с расходящимися вердиктами: что это на самом деле.

Гипотеза, с которой начинали: расхождение = недетерминизм или разные версии кода.
Проверка показывает третье: часть прогонов **явно помечена как заменённая** более поздним
(«Superseded by run-…» в тексте вердикта). Тогда семья — не конфликт, а история исправления.

Запуск:
    python3 tools/family_verdicts.py           # сводка
    python3 tools/family_verdicts.py --write   # docs/FAMILY-VERDICTS.md
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"
OUT = ROOT / "docs" / "FAMILY-VERDICTS.md"

RUN_RE = re.compile(r"^X-(?P<exp>.+?)-run-(?P<ts>.+)$")
SUPERSEDE_RE = re.compile(r"(?:Superseded by|superseded by|заменён)\s+(run-[0-9T:\-]+)")
HASH_RE = re.compile(r"hashes?:\s*([0-9a-f]{6,})")


def load() -> list[dict]:
    out = []
    for line in NODES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n = json.loads(line)
            if n.get("kind") == "experiment":
                out.append(n)
    return out


def exp_of(n: dict) -> str:
    m = RUN_RE.match(n["id"])
    return m.group("exp") if m else n["id"]


def params_of(n: dict) -> str:
    raw = n.get("context", {}).get("parameters", "")
    try:
        return json.dumps(json.loads(raw), sort_keys=True)
    except (ValueError, TypeError):
        return raw


def verdict(n: dict) -> str:
    t = n.get("text", "")
    if t.endswith("passed"):
        return "passed"
    if t.endswith("failed"):
        return "failed"
    if t.endswith("void") or t.endswith("not applicable"):
        return "no-verdict"
    return "unknown"


def result_json(n: dict) -> dict:
    ref = ((n.get("evidence") or [{}])[0].get("ref") or "")
    p = ROOT / ref if ref else None
    if p and p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def reason_of(n: dict) -> str:
    v = result_json(n).get("verdict")
    if isinstance(v, dict):
        return str(v.get("reason", ""))
    return ""


def superseded_by(n: dict) -> str:
    m = SUPERSEDE_RE.search(reason_of(n))
    return m.group(1) if m else ""


def main(argv: list[str]) -> int:
    write = "--write" in argv
    nodes = load()
    groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for n in nodes:
        groups[(exp_of(n), params_of(n))].append(n)

    def is_conflict(runs: list[dict]) -> bool:
        kinds = {verdict(n) for n in runs}
        return "passed" in kinds and "failed" in kinds

    mixed = {k: v for k, v in groups.items() if is_conflict(v)}

    rows = []
    for (exp, _key), runs in sorted(mixed.items()):
        runs = sorted(runs, key=lambda n: n["id"])
        sup = {n["id"]: superseded_by(n) for n in runs}
        seeds = {str(result_json(n).get("seed", "нет")) for n in runs}
        commits = {result_json(n).get("model_commit") for n in runs}
        # объяснено, если каждый failed/unknown явно указывает, каким прогоном он заменён
        unexplained = [n for n in runs
                       if verdict(n) != "passed" and not sup.get(n["id"])]
        known = {c for c in commits if c and c != "unknown"}
        if len(known) > 1:
            cause = "разные версии кода"
        elif all(sup.get(n["id"]) for n in runs if verdict(n) == "failed"):
            cause = "замена прогона"
        elif len(known) == 1:
            cause = "не объяснено (один коммит)"
        else:
            cause = "не объяснено (коммиты неизвестны)"
        rows.append({
            "exp": exp,
            "runs": len(runs),
            "verdicts": collections.Counter(verdict(n) for n in runs),
            "seeds": seeds,
            "commits": commits,
            "supersede": sup,
            "unexplained": len(unexplained),
            "cause": cause,
        })

    explained = [r for r in rows if r["cause"] != "" and not r["cause"].startswith("не объяснено")]
    broken = [r for r in rows if r["cause"].startswith("не объяснено")]

    lines: list[str] = []
    a = lines.append
    a("# Семейства с расходящимися вердиктами: разбор (сгенерировано `tools/family_verdicts.py`)")
    a("")
    a("## Вопрос")
    a("")
    a("В черновике `docs/FAMILIES-DRAFT.md` нашлось 10 семейств, где одинаковые параметры дают разные")
    a("вердикты. Гипотезы были: недетерминизм или разные версии кода. Проверка исходных JSON даёт")
    a("третье объяснение.")
    a("")
    a("## Что оказалось")
    a("")
    a("Часть неудачных прогонов **сама себя объявляет заменённой**: в поле `verdict.reason` стоит")
    a("«Superseded by run-…», и там же объяснено, что было не так (например, скрипт подавал конечный")
    a("уровень поля в рекурсию вместо начального и использовал нестрогое сравнение). То есть это не")
    a("конфликт и не случайность, а **история исправления**, записанная в данных.")
    a("")
    a(f"- смешанных семейств: **{len(rows)}**")
    a(f"- объяснены (замена прогона или разные версии кода): **{len(explained)}**")
    a(f"- не объяснены (настоящий сигнал): **{len(broken)}**")
    a("")
    a("## Таблица")
    a("")
    a("| эксперимент | прогонов | вердикты | сиды | коммитов | причина |")
    a("|---|---|---|---|---|---|")
    for r in rows:
        verdicts = ", ".join(f"{v}×{c}" for v, c in sorted(r["verdicts"].items()))
        seeds = ", ".join(str(s) for s in sorted(r["seeds"], key=str))
        commits = ", ".join("unknown" if c == "unknown" else str(c) for c in r["commits"])
        known = {c for c in r["commits"] if c and c != "unknown"}
        a(f"| `{r['exp']}` | {r['runs']} | {verdicts} | {seeds} | {len(known)} | {r['cause']} |")
    a("")
    if broken:
        a("## Не объяснено — требует внимания")
        a("")
        for r in broken:
            a(f"- `{r['exp']}`: {r['runs']} прогонов, {dict(r['verdicts'])}, без ссылки на замену")
    else:
        a("## Не объяснено")
        a("")
        a("Ни одного: у каждого расхождения в данных есть ссылка на заменяющий прогон.")
    a("")
    a("## Что это значит для `kg/`")
    a("")
    a("1. Семейство не должно иметь один «агрегированный вердикт»: правильная запись — **последний")
    a("   прогон** и цепочка замен.")
    a("2. Неудачный прогон, у которого есть ссылка на замену, не считается опровержением: он")
    a("   документирует исправление.")
    a("3. Неудачный прогон **без** ссылки на замену — сигнал: либо опыт не воспроизводится, либо")
    a("   исправление не записано.")
    a("")
    a("## Ограничение")
    a("")
    a("`model_commit` у большинства прогонов `unknown`, поэтому «разные версии кода» нельзя ни")
    a("подтвердить, ни исключить по данным. Это отдельный дефект записи, а не вывод.")
    text = "\n".join(lines) + "\n"

    if write:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано: {OUT}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
