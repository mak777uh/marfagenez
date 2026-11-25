"""Инбокс предложений для `kg/` — «дубовый формат» из спеки внешнего агента (Часть VII).

Три типа строк, всё остальное — отказ:

    {"kind":"node","tmp":"n1","type":"literature","text":"...","quote":"...",
     "source":{"doi":"...","url":"...","level":"abstract_read"},
     "lines":["vybor"],"context":{"scope":"..."},"notes":"..."}

    {"kind":"edge","from":"n1","to":"F-016","type":"extends","note":"..."}

    {"kind":"check","id":"F-006","quote":"...","source":{"url":"...","level":"fragment_read"},
     "verdict":"supported","note":"..."}

Инбокс **не правит** `kg/`: принятые строки лежат в `docs/KG-INBOX.jsonl` (предложения) и
`docs/KG-CHECKS.jsonl` (проверки). Идентификаторы назначает коллектор (я), не автор.

Запуск:
    python3 tools/kg_inbox.py --serve <файл>...   принять партии и ответить
    python3 tools/kg_inbox.py --state             что ждёт очереди (фронтир)
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
NODES = ROOT / 'kg' / 'nodes.jsonl'
LINES = ROOT / 'kg' / 'lines.json'
INBOX = ROOT / 'docs' / 'KG-INBOX.jsonl'
CHECKS = ROOT / 'docs' / 'KG-CHECKS.jsonl'

EDGE_TYPES = {'qualifies', 'tested_in', 'stated_in', 'extends', 'analogous_to', 'normalizes_to',
              'refutes', 'refuted_by', 'supports', 'derived_from', 'bridges', 'maps_to'}
SOURCE_LEVELS = {'metadata_only', 'abstract_read', 'fragment_read', 'full_text_examined', 'secondary_only'}
NODE_TYPES = {'literature', 'claim', 'formula', 'definition', 'gap', 'correspondence'}
VERDICTS = {'supported', 'contradicted', 'not_found'}
MAX_LINES = 50


def load_nodes() -> dict[str, dict]:
    out = {}
    for line in NODES.read_text(encoding='utf-8').splitlines():
        if line.strip():
            n = json.loads(line)
            out[n['id']] = n
    return out


def load_lines() -> set[str]:
    data = json.loads(LINES.read_text(encoding='utf-8'))
    return {x['id'] for x in data['lines']}


def norm(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text)).strip().lower()


def preflight(path: pathlib.Path, nodes: dict[str, dict], lines: set[str]) -> tuple[list[dict], list[str]]:
    """Пять проверок спеки + кап 50 строк. Возвращает (принятые, причины отказа)."""
    good, bad = [], []
    raw = [l for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
    if len(raw) > MAX_LINES:
        return [], [f'{path.name}: строк {len(raw)}, потолок {MAX_LINES}']

    texts = {norm(n.get('text')) for n in nodes.values()}
    tmp_seen = set()
    for i, line in enumerate(raw, 1):
        try:
            row = json.loads(line)
        except Exception as exc:
            bad.append(f'{path.name}:{i}: не JSON ({exc})')
            continue
        kind = row.get('kind')
        problems = []

        if kind == 'node':
            tmp = row.get('tmp') or ''
            if not tmp:
                problems.append('нет tmp (внутреннее имя строки)')
            if row.get('type') not in NODE_TYPES:
                problems.append(f"type не из списка: {sorted(NODE_TYPES)}")
            if len(str(row.get('text') or '')) < 20:
                problems.append('text короче 20 символов')
            if len(str(row.get('quote') or '')) < 10:
                problems.append('quote короче 10 символов (нужна дословная цитата)')
            src = row.get('source') or {}
            if src.get('level') not in SOURCE_LEVELS:
                problems.append(f"source.level не из списка: {sorted(SOURCE_LEVELS)}")
            if not (src.get('doi') or src.get('url')):
                problems.append('source: нужен doi или url')
            row_lines = row.get('lines') or []
            if not row_lines:
                problems.append('lines пустой: нужна линия слона')
            elif set(row_lines) - lines:
                problems.append(f"lines вне набора: {sorted(set(row_lines) - lines)}")
            if norm(row.get('text')) in texts:
                problems.append('такой текст уже есть в kg (дубль)')
            if not problems:
                tmp_seen.add(tmp)
                texts.add(norm(row.get('text')))
                good.append(row)

        elif kind == 'edge':
            if row.get('type') not in EDGE_TYPES:
                problems.append(f"type не из 12 существующих: {sorted(EDGE_TYPES)}")
            for side in ('from', 'to'):
                val = str(row.get(side) or '')
                if not val:
                    problems.append(f'нет {side}')
                elif val not in nodes and val not in tmp_seen and not re.fullmatch(r'n\d+', val):
                    problems.append(f'{side}={val}: нет такого узла и нет tmp в этом файле')
            if len(str(row.get('note') or '')) < 10:
                problems.append('note: нужно одно предложение «почему»')
            if not problems:
                good.append(row)

        elif kind == 'check':
            node_id = str(row.get('id') or '')
            if node_id not in nodes:
                problems.append(f'id={node_id}: узла нет в kg')
            if row.get('verdict') not in VERDICTS:
                problems.append(f"verdict не из списка: {sorted(VERDICTS)}")
            if len(str(row.get('quote') or '')) < 10:
                problems.append('quote обязательна (дословная подстрока источника)')
            src = row.get('source') or {}
            if src.get('level') not in SOURCE_LEVELS:
                problems.append('source.level не из списка')
            if node_id in nodes and row.get('verdict') == 'supported' \
                    and nodes[node_id].get('epistemic') == 'refuted':
                problems.append('нельзя поддерживать опровергнутый узел (инвариант графа)')
            if not problems:
                good.append(row)
        else:
            problems.append(f"kind={kind!r}: допустимы node / edge / check")

        if problems:
            bad.append(f'{path.name}:{i}: ' + '; '.join(problems))
    return good, bad


def append(path: pathlib.Path, rows: list[dict], extra: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().isoformat(timespec='seconds')
    with path.open('a', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps({**r, **extra, 'received_at': stamp}, ensure_ascii=False) + '\n')
    return len(rows)


def serve(files: list[pathlib.Path]) -> int:
    nodes, lines = load_nodes(), load_lines()
    summary = {}
    for path in files:
        if not path.exists():
            print(f'нет файла: {path}')
            continue
        good, bad = preflight(path, nodes, lines)
        nodes_rows = [r for r in good if r['kind'] == 'node']
        edge_rows = [r for r in good if r['kind'] == 'edge']
        check_rows = [r for r in good if r['kind'] == 'check']
        if nodes_rows or edge_rows:
            append(INBOX, nodes_rows + edge_rows, {'file': path.name})
        if check_rows:
            append(CHECKS, check_rows, {'file': path.name})
        ack = {
            'file': path.name,
            'accepted': len(good),
            'rejected': len(bad),
            'by_kind': {'node': len(nodes_rows), 'edge': len(edge_rows), 'check': len(check_rows)},
            'reasons': bad[:12],
            'note': ('принятое лежит в docs/KG-INBOX.jsonl (предложения) и docs/KG-CHECKS.jsonl (проверки). '
                     'Идентификаторы назначаю я при слиянии: tmp остаётся именем строки.'),
        }
        out = pathlib.Path('/mnt/c/111/graph-bridge/ack') / f'{path.name.split(".")[0]}-kg.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        summary[path.name] = ack
        print(f'{path.name}: принято {len(good)}, отклонено {len(bad)} ' +
              json.dumps(ack['by_kind'], ensure_ascii=False))
        for r in bad[:6]:
            print('   ', r[:140])
    return 0


def state() -> int:
    nodes = load_nodes()
    extracted = [n for n in nodes.values()
                 if n.get('provenance') == 'extracted' and n.get('epistemic') != 'refuted']
    no_evidence = [n for n in nodes.values() if not (n.get('evidence') or [])]
    goals = collections.Counter(n.get('kind') for n in extracted)
    print(f'узлов: {len(nodes)}; «только извлечено»: {len(extracted)}; без свидетельств: {len(no_evidence)}')
    print('по видам (извлечённые):', dict(goals))
    print()
    print('цикл A — первые 20 целей (нужна цитата и вердикт):')
    for n in extracted[:20]:
        print(f"  {n['id']:8} {str(n.get('text'))[:70]}")
    print()
    print('цикл C — узлы, у которых нет ни одного ребра в источниках:')
    linked = set()
    for f in ('claims.jsonl', 'definitions.jsonl', 'bridges.jsonl', 'candidates.jsonl'):
        p = ROOT / 'kg' / f
        if p.exists():
            for line in p.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    for rel in (json.loads(line).get('relations') or []):
                        linked.add(str(rel.get('target')))
    lonely = [n for n in nodes.values() if n['id'] not in linked and n.get('kind') in ('claim', 'formula')]
    print(f'  кандидатов: {len(lonely)}')
    for n in lonely[:10]:
        print(f"  {n['id']:8} {str(n.get('text'))[:70]}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description='инбокс предложений для kg/ (3 типа строк)')
    ap.add_argument('--serve', nargs='*', default=[])
    ap.add_argument('--state', action='store_true')
    args = ap.parse_args(argv)
    if args.state:
        return state()
    files = [pathlib.Path(f) for f in args.serve]
    if not files:
        print('укажи файлы: --serve <файл>.kg.jsonl')
        return 2
    return serve(files)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
