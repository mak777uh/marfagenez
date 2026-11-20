"""parse_lines.py -- разметка 88 литературных записей по десяти линиям.

Источник истины — таблица §1 в docs/ELEPHANT-MAP.md, а не сами записи: там литература уже
разложена по частям слона. Парсер fail-closed: нераспознанная ячейка попадает в `unparsed`
с исходным значением, а не становится пустой линией по умолчанию.
"""
import json
import pathlib
import re

ROOT = pathlib.Path('/root/marfagenez')
SLUGS = {1: "granica", 2: "obmen", 3: "svoi-usloviya", 4: "organizaciya", 5: "proshloe",
         6: "smert", 7: "porog", 8: "vybor", 9: "individualnost", 10: "agentnost"}
ROW = re.compile(r'^\|\s*\*\*(\d+)\.\s*([^|*]+)\*\*\s*\|(.+)$')
LID = re.compile(r'L-(\d{3})')


def main():
    text = (ROOT / 'docs' / 'ELEPHANT-MAP.md').read_text(encoding='utf-8')
    mapping = {}
    unparsed = []
    rows = 0
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        num, name, rest = int(m.group(1)), m.group(2).strip(), m.group(3)
        slug = SLUGS.get(num)
        if not slug:
            unparsed.append({"part": num, "name": name, "why": "unknown part number"})
            continue
        rows += 1
        cols = [c.strip() for c in rest.split('|')]
        literature = cols[1] if len(cols) > 1 else ''
        ids = sorted(set('L-' + x for x in LID.findall(literature)))
        if not ids:
            unparsed.append({"part": num, "name": name, "value": literature[:80], "why": "no L-ids in literature cell"})
            continue
        for lid in ids:
            mapping.setdefault(lid, []).append(slug)
    nodes = [json.loads(l) for l in (ROOT / 'kg' / 'nodes.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    lit = {n['id'] for n in nodes if n['id'].startswith('L-')}
    parsed = sorted(set(mapping) & lit)
    missing = sorted(lit - set(mapping))
    unknown = sorted(set(mapping) - lit)
    for lid in missing:
        unparsed.append({"id": lid, "why": "not mentioned in ELEPHANT-MAP §1"})
    payload = {
        "version": 1,
        "generated_at": "2026-11-21",
        "source": "docs/ELEPHANT-MAP.md §1",
        "method": "parsed",
        "parser_version": "1",
        "rows": rows,
        "map": {k: sorted(set(v)) for k, v in sorted(mapping.items())},
        "unparsed": unparsed,
        "stats": {"literature_nodes": len(lit), "parsed": len(parsed), "missing": missing, "in_map_not_in_graph": unknown},
    }
    (ROOT / 'kg' / 'lines-map.json').write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    print("строк таблицы: %d · записей размечено: %d · без разметки: %d" % (rows, len(parsed), len(missing)))
    if missing:
        print("  без разметки:", ", ".join(missing[:12]), "..." if len(missing) > 12 else "")
    if unparsed:
        print("  unparsed:", unparsed[:3])
    print("88 = parsed + unparsed:", len(parsed), "+", len(missing), "=", len(parsed) + len(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
