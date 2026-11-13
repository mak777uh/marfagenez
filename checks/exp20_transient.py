import json, subprocess, sys, math
sys.path.insert(0, '/root/marfagenez')

def run(c, steps=6, every=1, seed=20250101):
    cmd = ['/root/marfagenez/core/target/release/trace',
           '--policy', c.get('policy','stay'), '--steps', str(steps), '--every', str(every),
           '--seed', str(seed), '--n', str(c['n']), '--cells', str(c['cells']),
           '--capacity', str(c['M']), '--regrow', str(c['r']),
           '--income', str(c.get('income',1.0)), '--maintenance', str(c.get('maint',0.6)),
           '--damage-rate', str(c.get('dmg',0.01)), '--field', 'uniform', '--rich', '2.0', '--poor', '0.2', '--energy', '10']
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout

def load(path='/root/marfagenez/results/stay/trace-stay-1794486690.json'):
    return json.load(open(path))

CASES = [
    dict(name='M2 n40', cells=40, M=2.0, r=0.8, n=40),
    dict(name='M2 n80', cells=40, M=2.0, r=0.8, n=80),
    dict(name='M1 n40', cells=40, M=1.0, r=0.8, n=40),
]

print('=== per-step field statistics ===')
for c in CASES:
    run(c, steps=6, every=1)
    d = load()
    print(f"--- {c['name']}  hash={d['hash']}")
    for f in d['frames'][:6]:
        fl = f['field']
        alive = sum(1 for s in f['samples'] if s['alive'])
        print(f"  step {f['step']}: min={min(fl):.4f} max={max(fl):.4f} "
              f"mean={sum(fl)/len(fl):.4f} alive={alive}")

print()
print('=== arithmetic: one cell, k organisms, c=M=2, t=1, r=0.8 ===')
M, r, t = 2.0, 0.8, 1.0
for k in range(0, 6):
    c = M
    trace = []
    for _ in range(4):
        taken = min(c, k*t)
        c1 = c - taken
        c = c1 + (M - c1)*r
        trace.append(round(c, 4))
    print(f"  k={k}: start {M} -> {trace}")

print()
print('=== arithmetic: two organisms on one cell (sequential take) ===')
c = M
for step in range(1, 5):
    # first organism takes min(c,1), second takes min(c-first,1)
    a1 = min(c, 1.0); c -= a1
    a2 = min(c, 1.0); c -= a2
    c = c + (M - c)*r
    print(f"  step {step}: after two takes and regrow c={c:.4f}")
