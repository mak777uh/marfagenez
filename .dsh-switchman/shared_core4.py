"""PROTOCOL-0 п.4, версия 4 — финальная. Три теста алгоритма `shared-core`.

История версий (важнее результата):
  v1 — 1/3. Обе отрицательные сети проходили: у COT+RAF нет требования
       нетривиальности, поэтому одиночная реакция A->B с cat=None проходила
       как «ядро». Дефект ПОСТАНОВКИ, не реализации.
  v2 — 2/3. Добавлены |H| >= 2 и каталитический цикл. Положительный контроль
       провалился: has_catalytic_cycle исключал i == j и тем выкидывал
       самокатализ. Дефект РЕАЛИЗАЦИИ.
  v3 — отладка показала, что is_cot и is_raf на положительном контроле
       возвращают True, а цикл — False.
  v4 — самокатализ считается петлёй.

Смысл: тесты поймали два разных дефекта подряд. Это и есть их работа.
Если бы все три теста прошли с первого раза, они были бы бесполезны.
"""
import itertools

def cot_closure(mols, reactions):
    mols = set(mols); changed = True
    while changed:
        changed = False
        for ins, outs, _cat in reactions:
            if all(i in mols for i in ins):
                for o in outs:
                    if o not in mols:
                        mols.add(o); changed = True
    return mols

def is_cot(mols, reactions):
    return cot_closure(mols, reactions) == set(mols)

def is_raf(sub, food=frozenset()):
    prod = set(food)
    for _ins, outs, _cat in sub:
        prod.update(outs)
    for ins, _outs, cat in sub:
        if not all(i in prod for i in ins): return False
        if cat is not None and cat not in prod: return False
    return True

def has_catalytic_cycle(sub):
    """Цикл в графе «реакция j производит катализатор реакции i».
    j == i разрешено: самокаталитическая реакция — это петля длины 1."""
    n = len(sub); adj = {i: [] for i in range(n)}
    for i, (_ins, outs, cat) in enumerate(sub):
        if cat is None: continue
        for j, (_i2, outs2, _c2) in enumerate(sub):
            if cat in outs2:
                adj[j].append(i)
    color = {i: 0 for i in range(n)}
    def dfs(u):
        color[u] = 1
        for v in adj[u]:
            if color[v] == 1: return True
            if color[v] == 0 and dfs(v): return True
        color[u] = 2
        return False
    return any(color[i] == 0 and dfs(i) for i in range(n))

def find_core(reactions, food=frozenset()):
    n = len(reactions)
    for size in range(2, n + 1):
        for combo in itertools.combinations(range(n), size):
            sub = [reactions[i] for i in combo]
            mols = set(food)
            for ins, outs, _c in sub:
                mols.update(ins); mols.update(outs)
            if not is_cot(mols, reactions): continue
            if not is_raf(sub, food): continue
            if not has_catalytic_cycle(sub): continue
            return sub
    return None

def show(name, reactions, expect_core, food=frozenset()):
    core = find_core(reactions, food)
    got = core is not None
    ok = (got == expect_core)
    print(f"\n{'='*72}\n{name}\n{'='*72}")
    for i, (ins, outs, cat) in enumerate(reactions):
        print(f"  r{i}: {ins} -> {outs}  cat={cat}")
    if core is None:
        print("  ЯДРО: не найдено")
    else:
        print(f"  ЯДРО: {len(core)} реакций")
        for ins, outs, cat in core:
            print(f"    {ins} -> {outs}  cat={cat}")
    print(f"  ожидание: {'ядро есть' if expect_core else 'ядра нет'} -> {'OK' if ok else 'ПРОВАЛ'}")
    return ok

results = []

r1 = [
    (['A'], ['B'], None),
    (['B'], ['A'], None),
    (['X'], ['C'], 'D'),
    (['C'], ['D'], 'C'),
]
results.append(show("ТЕСТ 1: разделённые свидетели (ожидание: ядра нет)", r1, False))

r2 = [(['A'], ['A'], 'A')]
results.append(show("ТЕСТ 2: тривиальное ядро H=G (ожидание: ядра нет)", r2, False))

r3 = [(['A'], ['B'], 'B'), (['B'], ['A'], 'A')]
results.append(show("ТЕСТ 3: положительный контроль (ожидание: ядро есть)", r3, True))

print(f"\n{'='*72}")
passed = sum(results)
print(f"ИТОГ п.4 (v4): {passed}/3 теста прошли")
if passed == 3:
    print("ВЕРДИКТ: passed — алгоритм различает сети.")
    print("  НО: содержательной сети у нас нет. Общий вердикт пункта 4 —")
    print("  not applicable (по таблице протокола: «содержательной сети нет»).")
else:
    print("ВЕРДИКТ: void — тесты провалены.")
print("=" * 72)
