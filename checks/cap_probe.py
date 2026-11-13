import json, subprocess, sys, os, hashlib
sys.path.insert(0, '/root/marfagenez')

def run_raw(args, tag):
    cmd = ['/root/marfagenez/core/target/release/trace'] + args
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout, out.stderr

BASE = ['--policy','stay','--steps','6','--every','1','--seed','20250101',
        '--n','40','--cells','40','--regrow','0.8','--income','1.0',
        '--maintenance','0.6','--damage-rate','0.01','--field','uniform', '--rich', '2.0', '--poor', '0.2','--energy','10']

for cap in ['2.0', '1.0', '4.0']:
    out, err = run_raw(BASE + ['--capacity', cap], cap)
    # find written path
    line = [l for l in out.splitlines() if l.startswith('written:')]
    print(f"--- capacity={cap}  {line}")
    if err.strip():
        print('  STDERR:', err.strip()[:300])
    if line:
        p = line[0].split(':',1)[1].strip()
        d = json.load(open('/root/marfagenez/' + p))
        fl = d['frames'][-1]['field']
        al = sum(1 for s in d['frames'][-1]['samples'] if s['alive'])
        print(f"  hash={d['hash']} last-frame mean={sum(fl)/len(fl):.4f} alive={al}")
        # energy of first sample
        s0 = d['frames'][-1]['samples'][0]
        print(f"  sample0: cell={s0['cell']} energy={s0['energy']} taken={s0.get('taken')}")
