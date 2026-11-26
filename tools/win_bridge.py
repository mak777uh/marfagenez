"""Мост для внешнего агента, у которого есть только Windows и GitHub (без WSL).

Агент кладёт файлы в `C:\\111\\graph-bridge\\outbox\\`, я забираю их проходом `--serve`:
валидирую, применяю, пишу ответ в `ack\\`. Никакого git из его стороны — история не ветвится.

Форматы (одна партия = один файл):

    <имя>.atoms.jsonl    по строке на ячейку карты:
        {"atom": "WIN-001", "statement": "...", "kind": "measurement",
         "domain": "...", "works": [{"doi": "...", "locator": "...", "quote": "..."}],
         "kg_ref": ["L-001"], "notes": "..."}

    <имя>.edges.jsonl    по строке на связь (обязательна для каждой новой ячейки):
        {"from": "WIN-001", "to": "DIP24-0005", "type": "refines", "note": "..."}

    <имя>.questions.jsonl  вопросы к данным (как у probe):
        {"question": "...", "atoms": ["..."], "kind": "numbers", "numbers": ["..."],
         "recalc": "...", "verifiable": "..."}

Запуск:
    python3 tools/win_bridge.py --state      обновить STATE.md для агента
    python3 tools/win_bridge.py --serve      забрать партии и ответить
    python3 tools/win_bridge.py --watch 30   то же в цикле
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BRIDGE = pathlib.Path('/mnt/c/111/graph-bridge')
PROCESSED = BRIDGE / 'processed'
LIVE = ROOT / 'literature/map/atoms.jsonl'
EDGES = ROOT / 'literature/map/edges.jsonl'


def counts() -> tuple[int, int]:
    a = len([l for l in LIVE.read_text(encoding='utf-8').splitlines() if l.strip()])
    e = len([l for l in EDGES.read_text(encoding='utf-8').splitlines() if l.strip()])
    return a, e


def write_state() -> int:
    """Снимок состояния для агента: он не имеет доступа к WSL и должен знать контекст."""
    BRIDGE.joinpath('outbox').mkdir(parents=True, exist_ok=True)
    BRIDGE.joinpath('ack').mkdir(parents=True, exist_ok=True)
    cells, edges = counts()

    def run(*cmd: str) -> str:
        r = subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, timeout=600)
        out = ((r.stdout or '') + (r.stderr or '')).strip().splitlines()
        return out[-1] if out else ''

    contract = run('python3', 'checks/map_contract.py')
    orphans = run('python3', 'tools/map_orphans.py', '--strict')
    coverage = run('python3', 'checks/stitch_coverage_floor.py')
    audit = run('python3', 'tools/map_duplicates.py', '--strict')

    doi_gaps = ROOT / 'docs' / 'L-DOI-GAPS.json'
    queue = []
    if doi_gaps.exists():
        data = json.loads(doi_gaps.read_text(encoding='utf-8'))
        queue = [(r['node'], r['doi'], r['text']) for r in data['nodes'][:15]]

    heads = subprocess.run(['git', 'log', '--oneline', '-1'], cwd=ROOT, capture_output=True, text=True).stdout.strip()

    lines = [
        '# Состояние графа для внешнего агента',
        '',
        f'**Обновлено:** {time.strftime("%Y-%m-%d %H:%M")}. **Коммит:** `{heads}`.',
        '',
        '## Числа',
        '',
        f'| величина | значение |', '|---|---|',
        f'| ячеек карты | **{cells}** |',
        f'| рёбер | **{edges}** |',
        f'| контракт | {contract[:90]} |',
        f'| сироты | {orphans[:90]} |',
        f'| покрытие | {coverage[:90]} |',
        f'| дубли | {audit[:90]} |',
        '',
        '## Что можно делать (только через этот каталог)',
        '',
        '1. `outbox\\<имя>.atoms.jsonl` — новые ячейки карты (3–5 за партию, лучше один источник).',
        '2. `outbox\\<имя>.edges.jsonl` — связи новых ячеек с существующими (обязательно).',
        '3. `outbox\\<имя>.questions.jsonl` — вопросы к числам в уже существующих ячейках.',
        '',
        'Ответ появится в `ack\\<имя>.json` в течение ~30 секунд. Причины отказа — там же.',
        '',
        '## Требования к ячейке (иначе отказ)',
        '',
        '- `atom` — уникальный идентификатор, начинается с `WIN-`;',
        '- `statement` — что измерено или доказано, с числами и единицами;',
        '- `works[0].doi`, `.locator` (раздел/таблица/уравнение), `.quote` (дословная подстрока) — все три;',
        '- `kg_ref` — на какой узел `kg/` это ложится (например `L-001`);',
        '- связь в `edges` для каждой новой ячейки (правило: ячейка без связи не принимается);',
        '- **никаких** пересказов без локатора и никаких чисел «по памяти».',
        '',
        '## Что делать нельзя',
        '',
        '- править `literature/map/atoms.jsonl`, `edges.jsonl`, `kg/`, `results/` — только новые файлы в `outbox`;',
        '- пушить в GitHub-ветку `master` и переписывать историю;',
        '- ставить связь типа `analogous` без обоснования в `note`;',
        '- выдавать своё восстановление за цитату источника (помечать «наша реконструкция»).',
        '',
        '## Очередь: источники, которых в карте нет',
        '',
        '| узел | DOI | о чём |', '|---|---|---|',
    ]
    for node, doi, text in queue:
        lines.append(f'| `{node}` | `{doi}` | {text[:80]} |')
    lines += ['', 'Полный список — 40 DOI, выдаётся по запросу в `ack`.', '']

    # копия плана и правил — чтобы агент читал их без WSL
    for src, dst in (('docs/AUTONOMOUS-PLAN.md', 'PLAN.md'),
                     ('docs/PROBE-INSTRUCTION.md', 'QUESTIONS-HOWTO.md'),
                     ('docs/UNITS-CONVENTIONS.md', 'UNITS.md')):
        s = ROOT / src
        if s.exists():
            shutil.copyfile(s, BRIDGE / dst)
    BRIDGE.joinpath('STATE.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'STATE.md обновлён: {cells} ячеек, {edges} рёбер')
    return 0


def validate_atoms(path: pathlib.Path, known: set[str]) -> tuple[list[dict], list[str]]:
    good, bad = [], []
    for i, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            a = json.loads(line)
        except Exception as exc:
            bad.append(f'{path.name}:{i}: не JSON ({exc})')
            continue
        problems = []
        atom = str(a.get('atom') or '')
        if not atom.startswith('WIN-'):
            problems.append('atom должен начинаться с WIN-')
        if atom in known:
            problems.append('такой atom уже есть в карте')
        if len(str(a.get('statement') or '')) < 40:
            problems.append('statement короче 40 символов')
        w = (a.get('works') or [{}])[0]
        for field in ('doi', 'locator', 'quote'):
            if not w.get(field):
                problems.append(f'works[0].{field} обязателен')
        if not a.get('kg_ref'):
            problems.append('kg_ref обязателен')
            if a.get("confidence") is None:
                problems.append("confidence обязателен (число 0..1)")
            if not a.get("kind"):
                problems.append("kind обязателен (measurement/claim/definition/gap)")
        if problems:
            bad.append(f'{path.name}:{i}: ' + '; '.join(problems))
        else:
            good.append(a)
    return good, bad


def serve() -> int:
    write_state()
    outbox = BRIDGE / 'outbox'
    ack = BRIDGE / 'ack'
    for d in (outbox, ack):
        d.mkdir(parents=True, exist_ok=True)

    known = {json.loads(l)['atom'] for l in LIVE.read_text(encoding='utf-8').splitlines() if l.strip()}
    done = 0
    for path in sorted(outbox.glob('*.jsonl')):
        stem = path.name.split('.')[0]
        result = {'file': path.name, 'accepted': 0, 'rejected': 0, 'reasons': []}
        if '.atoms' in path.name:
            good, bad = validate_atoms(path, known)
            result['rejected'] = len(bad)
            result['reasons'] = bad[:10]
            if good:
                tmp = ROOT / 'scratch' / f'win-{stem}.atoms.jsonl'
                tmp.parent.mkdir(exist_ok=True)
                tmp.write_text('\n'.join(json.dumps(g, ensure_ascii=False) for g in good) + '\n', encoding='utf-8')
                e = outbox / f'{stem}.edges.jsonl'
                cmd = ['python3', 'tools/map_ingest.py', str(tmp), '--report', f'/tmp/win-{stem}.md']
                if e.exists():
                    cmd += ['--edges', str(e)]
                r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
                tail = [ln for ln in ((r.stdout or '') + (r.stderr or '')).splitlines() if 'принято' in ln]
                result['accepted'] = len(good) if r.returncode == 0 else 0
                result['ingest'] = tail[0] if tail else f'rc={r.returncode}'
                if r.returncode == 0:
                    for g in good:
                        known.add(g['atom'])
        elif '.edges' in path.name:
            result['note'] = 'связи применены вместе с atoms того же имени (если atoms были в этой партии)'
        elif '.kg' in path.name:
            r = subprocess.run(['python3', 'tools/kg_inbox.py', '--serve', str(path)],
                               cwd=ROOT, capture_output=True, text=True)
            out = ((r.stdout or '') + (r.stderr or '')).strip().splitlines()
            head = out[0] if out else ''
            result['note'] = f'kg-инбокс: {head}'
            import re as _re
            m = _re.search(r'принято (\d+), отклонено (\d+)', head)
            if m:
                result['accepted'] = int(m.group(1))
                result['rejected'] = int(m.group(2))
            bm = _re.search(r'(\{.*\})', head)
            if bm:
                try:
                    result['by_kind'] = json.loads(bm.group(1))
                except Exception:
                    pass
            result['reasons'] = [l.strip()[:160] for l in out[1:] if l.strip()][:8]
        elif '.questions' in path.name:
            target = ROOT / 'literature/map/inbox' / f'win-{stem}.jsonl'
            shutil.copyfile(path, target)
            result['note'] = f'вопросы положены в {target.relative_to(ROOT)}'
            result['accepted'] = len([l for l in path.read_text(encoding='utf-8').splitlines() if l.strip()])
        if 'note' not in result:
            result['note'] = 'тип файла не распознан: нужен .atoms.jsonl / .edges.jsonl / .questions.jsonl / .kg.jsonl'
            ack.joinpath(f'{stem}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                                                    encoding='utf-8')
            print(f'{path.name}: НЕ РАСПОЗНАН, файл оставлен')
            continue
        ack.joinpath(f'{stem}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                                                encoding='utf-8')
        PROCESSED.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(path, PROCESSED / path.name)
        except Exception:
            pass
        path.unlink(missing_ok=True)
        (outbox / f'{stem}.edges.jsonl').unlink(missing_ok=True)
        print(f'{path.name}: принято {result["accepted"]}, отклонено {result["rejected"]}')
        done += 1
    if not done:
        print('outbox пуст')
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description='мост для агента с доступом только к Windows')
    ap.add_argument('--serve', action='store_true')
    ap.add_argument('--state', action='store_true')
    ap.add_argument('--watch', type=int, default=0, metavar='СЕК')
    args = ap.parse_args(argv)
    if args.state:
        return write_state()
    if not args.watch:
        return serve()
    print(f'мост в режиме наблюдения: проход каждые {args.watch} с')
    while True:
        try:
            serve()
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f'проход упал: {exc}')
        time.sleep(args.watch)


if __name__ == '__main__':
    raise SystemExit(main(__import__('sys').argv[1:]))
