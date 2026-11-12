import json, subprocess

def run(M, r=0.8, n=1, cells=40, income=1.0, steps=3, every=1, policy='stay',
        rich=None, poor=None):
    rich = M if rich is None else rich
    poor = M if poor is None else poor
    cmd = ['/root/marfagenez/core/target/release/trace',
           '--policy', policy, '--steps', str(steps), '--every', str(every),
           '--seed', '20250101', '--n', str(n), '--cells', str(cells),
           '--capacity', '10', '--regrow', str(r),
           '--income', str(income), '--maintenance', '0.6',
           '--damage-rate', '0.01', '--field', 'uniform',
           '--rich', str(rich), '--poor', str(poor), '--energy', '10']
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    p = [l for l in out.splitlines() if l.startswith('written:')][0].split(':',1)[1].strip()
    return json.load(open('/root/marfagenez/' + p))

print('n=1, r=0.8, income=1.0, feed=false (take then regrow)')
print(' M   step1    pred=(M-t)+(M-(M-t))*r   taken')
for M in [1.0, 1.5, 2.0, 4.0]:
    d = run(M)
    f = d['frames'][0]
    s = f['samples'][0]
    val = f['field'][s['cell']]
    tk = min(M, 1.0)
    pred = (M - tk) + (M - (M - tk))*0.8
    ok = 'OK' if abs(val - pred) < 1e-9 else 'MISMATCH'
    print(f"{M:4.1f} {val:8.4f} {pred:24.4f} {s['taken']:8.3f}  {ok}")

print()
print('n=2 on same cell (n=2, cells=40 -> likely different cells; use cells=1)')
print(' M   step1    pred k=2')
for M in [1.0, 2.0]:
    d = run(M, n=2, cells=1, steps=2)
    f = d['frames'][-1]
    val = f['field'][0]
    tk = min(M, 1.0) + min(max(M - min(M,1.0),0), 1.0)
    pred = (M - tk) + (M - (M - tk))*0.8
    print(f"{M:4.1f} {val:8.4f} {pred:12.4f}  alive={sum(1 for s in f['samples'] if s['alive'])}")

print()
print('n=2, cells=1, steady state over steps (M=2, r=0.8)')
d = run(2.0, n=2, cells=1, steps=6, every=1)
for f in d['frames']:
    print(f"  step {f['step']}: field={f['field'][0]:.4f} alive={sum(1 for s in f['samples'] if s['alive'])}")
