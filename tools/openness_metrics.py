"""`F-030`: метрики открытости — можно ли их считать на наших же данных.

Узел предлагает три метрики:
    изменение (novelty): расстояние Левенштейна между поколениями
    разнообразие:        энтропия Шеннона по типам
    сложность:           колмогоровская (аппроксимация сжатием)

Проверяем не «правильные ли это метрики», а **операциональны ли они**: считаются ли они на карте, которую мы
ведём, и что они дают в числах. Если метрика не считается — её нельзя использовать, и это надо записать.

Запуск: python3 tools/openness_metrics.py
"""

from __future__ import annotations

import collections
import json
import math
import pathlib
import subprocess
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def shannon(counts: collections.Counter) -> float:
    total = sum(counts.values())
    if not total:
        return 0.0
    h = 0.0
    for n in counts.values():
        p = n / total
        h -= p * math.log2(p)
    return h


def main() -> int:
    atoms = [json.loads(l) for l in (ROOT / 'literature/map/atoms.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]

    # 1) разнообразие: энтропия по типам (kind) и по доменам
    kinds = collections.Counter(a.get('kind') for a in atoms)
    domains = collections.Counter(a.get('domain') for a in atoms)
    print(f'ячеек: {len(atoms)}')
    print(f'энтропия по kind   : {shannon(kinds):.3f} бит ({len(kinds)} типов)')
    print(f'энтропия по domain : {shannon(domains):.3f} бит ({len(domains)} доменов)')
    print(f'  максимум при {len(kinds)} типах: {math.log2(len(kinds)):.3f} бит; '
          f'при {len(domains)} доменах: {math.log2(len(domains)):.3f} бит')

    # 2) сложность: сжатие как приближение колмогоровской
    raw = (ROOT / 'literature/map/atoms.jsonl').read_bytes()
    comp = zlib.compress(raw, 9)
    print()
    print(f'сложность (сжатие): {len(raw)} байт -> {len(comp)} байт, '
          f'отношение {len(comp) / len(raw):.3f}')
    per_cell = len(comp) / len(atoms)
    print(f'  на ячейку: {per_cell:.0f} сжатых байт')

    # 3) новизна: сколько ячеек добавлялось за коммит (по истории git)
    try:
        log = subprocess.run(['git', 'log', '--format=%H|%ad', '--date=short', '--reverse',
                              '--', 'literature/map/atoms.jsonl'],
                             cwd=ROOT, capture_output=True, text=True, timeout=120).stdout
        commits = [l.split('|') for l in log.splitlines() if '|' in l]
    except Exception:
        commits = []
    deltas = []
    prev = 0
    for sha, date in commits[-40:]:
        try:
            body = subprocess.run(['git', 'show', f'{sha}:literature/map/atoms.jsonl'],
                                  cwd=ROOT, capture_output=True, text=True, timeout=120).stdout
            n = len([l for l in body.splitlines() if l.strip()])
        except Exception:
            continue
        if prev:
            deltas.append((date, n - prev))
        prev = n
    if deltas:
        pos = [d for _, d in deltas if d > 0]
        print()
        print(f'новизна по истории: {len(deltas)} шагов, из них с приростом {len(pos)}')
        if pos:
            print(f'  средний прирост за коммит с приростом: {sum(pos) / len(pos):.1f} ячеек')
            print(f'  максимальный: {max(pos)}; последние шаги: {deltas[-5:]}')
    else:
        print()
        print('новизна по истории: не удалось восстановить (нет доступа к git log)')
        return 1

    missing = []
    if len(kinds) < 2:
        missing.append('энтропия по kind вырождена')
    if len(domains) < 2:
        missing.append('энтропия по domain вырождена')
    if not deltas:
        missing.append('новизна по истории не считается')
    print()
    if missing:
        print('НЕОПЕРАЦИОНАЛЬНО:', '; '.join(missing))
        return 1
    print('ВЫВОД: все три метрики считаются на наших данных; Левенштейн заменён приростом по истории')
    print('        (расстояние между поколениями карты не определено — поколений нет).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
