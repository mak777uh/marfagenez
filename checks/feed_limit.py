import json, subprocess

def run(M, r=0.8, n=1, cells=40, income=1.0, steps=200, every=50, feed=True):
    cmd = ['/root/marfagenez/core/target/release/trace',
           '--policy', 'stay', '--steps', str(steps), '--every', str(every),
           '--seed', '20250101', '--n', str(n), '--cells', str(cells),
           '--capacity', '10', '--regrow', str(r),
           '--income', str(income), '--maintenance', '0.6',
           '--damage-rate', '0.01', '--field', 'uniform',
           '--rich', str(M), '--poor', str(M), '--energy', '10']
    if feed:
        cmd.append('--feed')
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    p = [l for l in out.splitlines() if l.startswith('written:')][0].split(':',1)[1].strip()
    return json.load(open('/root/marfagenez/' + p))

print('feed=true, n=1, long run. Prediction: c -> M - t/r')
print(' M    r    final     M - t/r')
for M, r in [(2.0,0.8),(4.0,0.8),(2.0,0.5),(2.0,0.9)]:
    d = run(M, r=r, steps=400, every=100)
    f = d['frames'][-1]
    cell = f['samples'][0]['cell']
    val = f['field'][cell]
    pred = M - 1.0/r
    print(f"{M:4.1f} {r:4.1f} {val:9.5f} {pred:11.5f}")

print()
print('feed=false, n=1, long run. Prediction: c -> M - t/r + t  (equilibrium)')
print(' M    r    final     M + t - t/r')
for M, r in [(2.0,0.8),(4.0,0.8),(2.0,0.5),(2.0,0.9)]:
    d = run(M, r=r, steps=400, every=100, feed=False)
    f = d['frames'][-1]
    cell = f['samples'][0]['cell']
    val = f['field'][cell]
    pred = M + 1.0 - 1.0/r
    print(f"{M:4.1f} {r:4.1f} {val:9.5f} {pred:11.5f}")
