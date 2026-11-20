import json
import pathlib
import subprocess
from datetime import datetime, timezone

root = pathlib.Path('/root/marfagenez')
out_dir = root / 'results' / 'EXP-CLOSURE-MEASURE'
out_dir.mkdir(parents=True, exist_ok=True)

N = 4  # parts in the chain, each gated by the previous one


def measure(edges, n):
    """Fraction of nodes in the largest strongly connected component (F-022)."""
    adj = {i: [] for i in range(n)}
    for a, b in edges:
        adj[a].append(b)
    # Tarjan, iterative
    index = {}
    low = {}
    on_stack = set()
    stack = []
    counter = [0]
    comps = []

    def strongconnect(v0):
        work = [(v0, 0)]
        while work:
            v, pi = work.pop()
            if pi == 0:
                index[v] = low[v] = counter[0]
                counter[0] += 1
                stack.append(v)
                on_stack.add(v)
            recurse = False
            neigh = adj[v]
            while pi < len(neigh):
                w = neigh[pi]
                pi += 1
                if w not in index:
                    work.append((v, pi))
                    work.append((w, 0))
                    recurse = True
                    break
                elif w in on_stack:
                    low[v] = min(low[v], index[w])
            if recurse:
                continue
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                comps.append(comp)
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[v])

    for v in range(n):
        if v not in index:
            strongconnect(v)
    biggest = max((len(c) for c in comps), default=0)
    return biggest / n, comps


configs = {}
# A: a pure chain - each part depends on the previous one, nothing comes back
configs['chain'] = [(i, i + 1) for i in range(N - 1)]
# B: the last part pays for the first (mutual support) - the cycle closes
configs['cycle'] = [(i, i + 1) for i in range(N - 1)] + [(N - 1, 0)]
# C: only the first three support each other
configs['partial'] = [(0, 1), (1, 2), (2, 0), (2, 3)]

rows = []
for name, edges in configs.items():
    m, comps = measure(edges, N)
    rows.append({'config': name, 'edges': [[a, b] for a, b in edges], 'measure': round(m, 3),
                 'components': [sorted(c) for c in comps]})

fires = rows[0]['measure'] != rows[1]['measure']
silent = rows[0]['measure'] == round(1 / N, 3)     # a chain: only isolated nodes are in no cycle
specific = rows[1]['measure'] == 1.0 and rows[2]['measure'] == round(3 / N, 3)
verdict = 'passed' if (fires and silent and specific) else 'failed'

record = {
    'schema': 'experiment/1',
    'experiment_id': 'EXP-CLOSURE-MEASURE',
    'run_id': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S'),
    'model_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True).stdout.strip(),
    'seed': 0,
    'hash_version': '2-prev-cell',
    'parameters': {'parts': N, 'configs': list(configs)},
    'arithmetic': {
        'measure': 'share of nodes in the largest strongly connected component (F-022)',
        'chain': 'no cycle, so every component is a single node: measure = 1/4 = 0.25',
        'cycle': 'one cycle covers all four parts: measure = 4/4 = 1.0',
        'partial': 'a three-part cycle plus one dependent part: measure = 3/4 = 0.75',
    },
    'conditions': {'graph': 'hand-built from the part-support relation, not read from organ.rs'},
    'series': rows,
    'controls': {
        'fires': {'passed': bool(fires), 'evidence': 'the measure separates a chain from a cycle'},
        'silent': {'passed': bool(silent), 'evidence': 'a chain gives exactly 1/n'},
        'specific': {'passed': bool(specific), 'evidence': 'a closed cycle gives 1.0, a partial cycle gives 3/n'},
    },
    'verdict': {'kind': verdict,
                'reason': 'the closure measure behaves as the graph definition predicts: 0.25 for a chain, '
                          '0.75 for a partial cycle, 1.0 for a closed cycle'},
    'hashes': {'chain': '1/n', 'partial': '3/n', 'cycle': '1'},
    'limitations': ('The graphs are hand-built illustrations of the measure, not a reading of the model: the '
                    'real part-support relation in organ.rs is not extracted here. Weights are absent, so '
                    'the measure is structural only.'),
    'command': 'python3 checks/exp_closure.py',
    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}
path = out_dir / f"run-{record['run_id']}.json"
path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

for r in rows:
    print(f"{r['config']:>8} measure={r['measure']} components={r['components']}")
print('controls:', {k: v['passed'] for k, v in record['controls'].items()}, 'verdict:', verdict)
print('saved:', path.relative_to(root))
