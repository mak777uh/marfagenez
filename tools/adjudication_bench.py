"""Заготовка теста: хватает ли слабой модели интеллекта для адъюдикации вопросов `probe`.

Собирает контрольный набор из УЖЕ разобранных вопросов (вопрос + текст ячейки + мой вердикт),
чтобы любую модель можно было прогнать и сравнить с моими решениями.

Запуск:
    python3 tools/adjudication_bench.py --build       # собрать cases.json
    python3 tools/adjudication_bench.py --score       # сверить answers.json с вердиктами
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
BR = pathlib.Path('/mnt/c/111/probe-bridge')
OUT = ROOT / 'scratch' / 'bench'
OUT.mkdir(parents=True, exist_ok=True)


def load_cells() -> dict[str, dict]:
    cells = {}
    for line in (ROOT / 'literature/map/atoms.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            a = json.loads(line)
            cells[a['atom']] = a
    return cells


def load_questions() -> dict[tuple[str, str], dict]:
    """(round, atom) -> вопрос."""
    out = {}
    for f in sorted(glob.glob(str(ROOT / 'literature/map/inbox/probe-*.jsonl'))):
        m = re.search(r'round(\d+)', f)
        rnd = m.group(1) if m else '0'
        for line in pathlib.Path(f).read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            q = json.loads(line)
            atoms = q.get('atoms') or []
            if len(atoms) == 1:
                out[('*', atoms[0])] = q
            for atom in atoms:
                out.setdefault((rnd, atom), q)
    return out


def load_verdicts() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(BR / 'ack' / '*verdict*.json'))):
        try:
            d = json.loads(pathlib.Path(f).read_text(encoding='utf-8'))
        except Exception:
            continue
        rnd = re.search(r'round([\d\-]+)', pathlib.Path(f).name)
        for v in d.get('verdicts', []):
            atom = str(v.get('atom', '')).split('/')[0].strip()
            score = v.get('score')
            if not atom or score is None:
                continue
            rows.append({'atom': atom, 'score': float(score),
                         'round': (rnd.group(1) if rnd else '')})
    return rows


def build(n_defect=8, n_partial=4, n_clear=4) -> None:
    cells = load_cells()
    questions = load_questions()
    verdicts = load_verdicts()
    cases, seen = [], set()
    for want, label in ((1.0, 'defect'), (0.5, 'partial'), (0.0, 'clear')):
        limit = {1.0: n_defect, 0.5: n_partial, 0.0: n_clear}[want]
        got = 0
        for v in verdicts:
            if got >= limit:
                break
            if v['score'] != want or v['atom'] in seen:
                continue
            q = questions.get(('*', v['atom']))
            if not q:
                continue
            cell = cells.get(v['atom'])
            if not cell:
                continue
            seen.add(v['atom'])
            cases.append({
                'id': f'{label}-{got + 1}',
                'atom': v['atom'],
                'truth_label': label,
                'truth_score': want,
                'question': q['question'],
                'statement': str(cell.get('statement'))[:700],
                'formula': str(cell.get('formula'))[:300],
                'notes': str(cell.get('notes'))[:500],
            })
            got += 1
    (OUT / 'cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'собрано случаев: {len(cases)} -> {OUT / "cases.json"}')
    for c in cases:
        print(f"  {c['id']:10} {c['atom']:14} ({c['truth_label']}, {c['truth_score']})")


def score() -> int:
    cases = {c['id']: c for c in json.loads((OUT / 'cases.json').read_text(encoding='utf-8'))}
    answers = json.loads((OUT / 'answers.json').read_text(encoding='utf-8'))
    ok_label = 0
    err = []
    for aid, ans in answers.items():
        c = cases.get(aid)
        if not c:
            continue
        got = str(ans.get('verdict', '')).strip().lower()
        truth = c['truth_label']
        if got == truth:
            ok_label += 1
        else:
            err.append((aid, c['atom'], truth, got, c['truth_score'], ans.get('score')))
    n = len(answers)
    print(f'совпало меток: {ok_label} из {n} ({100 * ok_label / max(n, 1):.0f}%)')
    for e in err:
        print(f'  ошибка: {e[0]} {e[1]}: мой {e[2]} ({e[4]}), модель {e[3]} ({e[5]})')
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--score', action='store_true')
    a = ap.parse_args()
    if a.score:
        raise SystemExit(score())
    build()
