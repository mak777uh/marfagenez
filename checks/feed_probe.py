import json, subprocess

def run(M, r=0.8, n=1, cells=40, income=1.0, steps=4, every=1, policy='stay', feed=False):
    cmd = ['/root/marfagenez/core/target/release/trace',
           '--policy', policy, '--steps', str(steps), '--every', str(every),
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

print('=== feed = true (regrow then take) ===')
print('Prediction: regrow first does nothing (c=M already at max), then take.')
print('So step 1 field = M - k*t, and it stays there (regrow adds r*(M-c) each step).')
print()
print(' M   n  step1   step2   step3   step4   pred_step1=M-t')
for M in [1.0, 2.0, 4.0]:
    d = run(M, n=1, steps=4, every=1, feed=True)
    vals = [f['field'][d['frames'][0]['samples'][0]['cell']] for f in d['frames']]
    print(f"{M:4.1f}   1 " + " ".join(f"{v:7.4f}" for v in vals) + f"   {M-1.0:7.4f}")

print()
print('=== feed = true, n=2 cells=1, M=2 ===')
d = run(2.0, n=2, cells=1, steps=5, every=1, feed=True)
for f in d['frames']:
    print(f"  step {f['step']}: field={f['field'][0]:.4f} alive={sum(1 for s in f['samples'] if s['alive'])}")

print()
print('=== feed = false, n=2 cells=1, M=2 (control) ===')
d = run(2.0, n=2, cells=1, steps=5, every=1, feed=False)
for f in d['frames']:
    print(f"  step {f['step']}: field={f['field'][0]:.4f} alive={sum(1 for s in f['samples'] if s['alive'])}")
