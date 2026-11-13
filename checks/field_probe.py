import json, subprocess
from collections import Counter

def run(cells=40, M=2.0, r=0.8, n=40, income=1.0, maint=0.6, dmg=0.01,
        steps=4, every=1, seed=20250101, policy='stay'):
    cmd = ['/root/marfagenez/core/target/release/trace',
           '--policy', policy, '--steps', str(steps), '--every', str(every),
           '--seed', str(seed), '--n', str(n), '--cells', str(cells),
           '--capacity', str(M), '--regrow', str(r),
           '--income', str(income), '--maintenance', str(maint),
           '--damage-rate', str(dmg), '--field', 'uniform', '--rich', '2.0', '--poor', '0.2', '--energy', '10']
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    p = [l for l in out.splitlines() if l.startswith('written:')][0].split(':',1)[1].strip()
    return json.load(open('/root/marfagenez/' + p))

d = run()
f1 = d['frames'][0]
fl = f1['field']
occ = Counter(s['cell'] for s in f1['samples'] if s['alive'])
taken = {}
for s in f1['samples']:
    if s['alive']:
        taken[s['cell']] = taken.get(s['cell'], 0.0) + s['taken']

print('cell  occ  sum_taken  field_after  regrow_pred  take_only_pred')
M, r = 2.0, 0.8
for c in sorted(occ)[:12]:
    k = occ[c]; tk = taken.get(c, 0.0); after = fl[c]
    # hypothesis A: take then regrow
    a = (M - tk) + (M - (M - tk))*r
    # hypothesis B: regrow then take
    b = M + (M - M)*r - tk
    print(f"{c:4d} {k:4d}  {tk:8.3f}  {after:10.4f}  {a:11.4f}  {b:13.4f}")
