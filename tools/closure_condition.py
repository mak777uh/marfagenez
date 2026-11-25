"""`F-022`: замыкание как свойство графа — проверка условия и контрпример.

Узел говорит:
    условие замыкания (по L-061):  ∀ c: indeg(c) ≥ 1 и outdeg(c) ≥ 1
    усиление (наша гипотеза):      подграф сильно связен
    мера:                          доля вершин в наибольшей сильно связной компоненте

Вопрос раунда: эквивалентны ли эти два условия? Если нет — насколько первое слабее.

Проверяем:
1. Минимальный контрпример: две непересекающиеся 2-цикла. У каждой вершины indeg = outdeg = 1,
   но граф не сильно связен и распадается на ДВА замкнутых подмножества — ровно то, что запрещает
   определение замыкания (C-0004: «без разложения на два независимых замкнутых подмножества»).
2. Реальная карта: сколько вершин проходят условие степеней и сколько попадают в нетривиальные
   сильно связные компоненты.

Запуск: python3 tools/closure_condition.py
"""

from __future__ import annotations

import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def sccs(nodes, adj) -> list[list[str]]:
    """Тарьян: сильно связные компоненты."""
    index = {}
    low = {}
    on_stack = {}
    stack: list[str] = []
    out: list[list[str]] = []
    counter = [0]

    def strong(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in adj.get(v, ()):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif on_stack.get(w):
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                comp.append(w)
                if w == v:
                    break
            out.append(comp)

    for v in nodes:
        if v not in index:
            strong(v)
    return out


def main() -> int:
    # --- 1. контрпример
    cyc = {'a': ['b'], 'b': ['a'], 'c': ['d'], 'd': ['c']}
    print('КОНТРПРИМЕР: две непересекающиеся 2-цикла a↔b и c↔d')
    bad = []
    for v, outs in cyc.items():
        indeg = sum(1 for u in cyc if v in cyc[u])
        if len(outs) < 1 or indeg < 1:
            bad.append(v)
    comps = sccs(sorted(cyc), cyc)
    print(f'  вершин с indeg ≥ 1 и outdeg ≥ 1: {len(cyc) - len(bad)} из {len(cyc)}')
    print(f'  сильно связных компонент: {len(comps)} -> {comps}')
    print(f'  разложение на два замкнутых подмножества: {"да" if len(comps) > 1 else "нет"}')
    counterexample = len(bad) == 0 and len(comps) > 1
    print(f'  условие степеней выполнено, а замыкания НЕТ: {counterexample}')
    print()

    # --- 2. реальная карта
    atoms = [json.loads(l) for l in (ROOT / 'literature/map/atoms.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    edges = [json.loads(l) for l in (ROOT / 'literature/map/edges.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    nodes = [a['atom'] for a in atoms]
    adj = collections.defaultdict(list)
    indeg = collections.Counter()
    for e in edges:
        adj[e['from']].append(e['to'])
        adj[e['to']].append(e['from'])      # зависимость считаем неориентированной связью
        indeg[e['from']] += 1
        indeg[e['to']] += 1
    comps = sccs(nodes, adj)
    sizes = sorted((len(c) for c in comps), reverse=True)
    have_edges = sum(1 for n in nodes if indeg[n] >= 1)
    big = [c for c in comps if len(c) > 1]
    in_nontrivial = sum(len(c) for c in big)
    print('КАРТА (связи как неориентированные):')
    print(f'  вершин: {len(nodes)}; со степенью ≥ 1: {have_edges} ({have_edges / len(nodes) * 100:.0f} %)')
    print(f'  компонент: {len(comps)}; крупнейшая: {sizes[0]} ({sizes[0] / len(nodes) * 100:.0f} %)')
    print(f'  нетривиальных (размер > 1): {len(big)}; в них вершин: {in_nontrivial}')
    print(f'  «сильно связен» (одна компонента): {"да" if len(comps) == 1 else "нет"}')
    print()

    print('ВЫВОД:')
    if counterexample:
        print('  условие степеней НЕ эквивалентно сильной связности: оно необходимо, но не достаточно.')
        print('  Две независимые петли проходят его, хотя определение замыкания запрещает разложение на')
        print('  два независимых замкнутых подмножества (C-0004).')
    print(f'  В карте «со степенью ≥ 1» — {have_edges} вершин, но в общей компоненте только {sizes[0]}:')
    print('  то есть степенное условие засчитывает замыкание там, где его нет.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
