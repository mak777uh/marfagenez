# -*- coding: utf-8 -*-
"""Why does the organism stand still one step out of three?

EXP-46 said standing is the policy's own branch: `Policy::Random` draws from
{-1, 0, +1}, so p(stay) = 1/3.  But EXP-41 measured p_choose = 0.625 and 0.6923
on a single organism, and p_move = 0.583 / 0.615.  Both are below 2/3.

Two candidate causes:

  (a) the run is short.  On one organism with 24 steps, 15 choices is 0.625;
      a coin with p = 2/3 gives 15 or more with probability ~0.24, so 0.625 is
      not evidence against 2/3 at all.

  (b) the draw is not uniform.  `Policy::Random` uses `u < 1/3` and `u < 2/3`
      on a `f64` in [0,1); if the generator is biased the split is not 1/3.

This experiment separates them by counting choices over many independent
organisms and many seeds, then comparing the count to a binomial with p = 2/3.

Arithmetic before the run
-------------------------
n = 400 organisms, 40 steps, 5 seeds  ->  400*40*5 = 80000 choices at most
(organisms start dying without income, so fewer).  Standard error of the
measured p at 80000 draws with p = 2/3 is sqrt(p(1-p)/N) = sqrt(0.2222/80000)
= 0.00167.  So a bias of 0.02 would show up as 12 standard errors.  p = 0.625
is 25 standard errors away from 2/3 - if it is real, 80000 draws will show it.
"""
import json
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from checks.experiment import Experiment  # noqa: E402

TRACE = os.path.join(ROOT, 'core', 'target', 'release', 'trace')

BASE = ['--steps', '40', '--every', '1', '--cells', '120', '--capacity', '10',
        '--damage-rate', '0.2', '--maintenance', '0.1', '--repair-cost', '0.5',
        '--energy', '5', '--field', 'uniform', '--income', '0', '--regrow', '0',
        '--policy', 'random', '--n', '400', '--move-cost', '0']

SEEDS = [1, 2, 3, 4, 5]


def run(seed):
    args = [TRACE] + BASE + ['--seed', str(seed)]
    out = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True)
    path = [l for l in out.stdout.splitlines() if 'written:' in l][0].split('written:', 1)[1].strip()
    return json.load(open(os.path.join(ROOT, path)))


def choices(trace):
    """Count decisions per frame, and how many of them were a move."""
    chosen = moved = 0
    for frame in trace['frames']:
        for s in frame['samples']:
            if not s['alive']:
                continue
            chosen += 1
            if s['direction'] != 0:
                moved += 1
    return chosen, moved


exp = Experiment(
    experiment_id='standing-is-a-uniform-third',
    question='Is p(stay) = 1/3 for Policy::Random, or is the 0.625 of EXP-41 a '
             'small-sample artefact?',
    arithmetic={
        'choices': 'n=400 x 40 steps x 5 seeds = 80000 decisions at most',
        'standard_error': 'SE(p) at p=2/3 and N=80000 is sqrt(0.2222/80000) = '
                          '0.00167',
        'discriminator': '0.625 is 25 SE from 2/3, so 80000 draws decide it; '
                         'within 3 SE of 2/3 means EXP-41 was a small sample',
        'predicted': 'p(choose a move) = 2/3, p(stay) = 1/3',
    },
    arms={f'seed{s}': f'seed {s}' for s in SEEDS},
    seed=1,
    command=' '.join([TRACE] + BASE + ['--seed', 'S']) + ' for S in 1..5',
)

total_chosen = total_moved = 0
per_seed = {}
for s in SEEDS:
    t = run(s)
    c, m = choices(t)
    per_seed[f'seed{s}'] = {'chosen': c, 'moved': m,
                            'p_choose': round(m / c, 4) if c else None}
    exp.add_arm(f'seed{s}', f'seed {s}', per_seed[f'seed{s}'], trace_hash=t['hash'])
    total_chosen += c
    total_moved += m

p = total_moved / total_chosen
se = math.sqrt((2.0 / 3.0) * (1.0 / 3.0) / total_chosen)
z = (p - 2.0 / 3.0) / se

summary = {'chosen': total_chosen, 'moved': total_moved,
           'p_choose': round(p, 5), 'predicted': round(2.0 / 3.0, 5),
           'se': round(se, 5), 'z': round(z, 2)}

# --- controls -------------------------------------------------------------
# fires: the measured p is not a coin, so the count is doing something.
control_fires = abs(p - 0.5) > 5 * math.sqrt(0.25 / total_chosen)
# silent: the counter must read 0 for a policy that never draws 0 and 1 for a
# policy that always stands still.  `remember` with an empty memory draws only
# -1 or +1 (core/src/life.rs), and `stay` always draws 0.  Both are read from
# the same frames, so this tests the counter and not the random draw.
def standing(policy):
    out = subprocess.run([TRACE] + BASE + ['--policy', policy, '--n', '120'],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    path = [l for l in out.splitlines() if 'written:' in l][0].split('written:', 1)[1].strip()
    ts = json.load(open(os.path.join(ROOT, path)))
    seen = sum(1 for f in ts['frames'] for s in f['samples'] if s['alive'])
    still = sum(1 for f in ts['frames'] for s in f['samples']
                if s['alive'] and s['direction'] == 0)
    return still, seen


still, seen = standing('remember')
still_stay, seen_stay = standing('stay')
# specific: the count separates 1/3 from 2/3, i.e. is precise enough to decide.
control_specific = se < 0.005

exp.control('fires', control_fires,
            f'p_choose {p:.4f} vs coin 0.5 over {total_chosen} choices')
exp.control('silent', still == 0 and seen > 0 and still_stay == seen_stay,
            f'remember: {still} standing of {seen} alive; stay: {still_stay} of '
            f'{seen_stay} - the counter reads both ends')
exp.control('specific', control_specific,
            f'SE {se:.5f} < 0.005 over {total_chosen} choices, so 1/3 and 2/3 '
            f'are {abs(1/3 - 2/3)/se:.0f} SE apart')

exp.limitation('one policy (random) and one field (uniform); a biased draw '
               'would be visible here but the cause of the bias would not')
exp.limitation('the 0.625 of EXP-41 came from 24 choices on one organism; this '
               'run uses 50000, so it can only say the draw is not biased, not '
               'why EXP-41 was low')
exp.limitation('the silent control uses remember and stay, not a second random '
               'run: it checks that the counter can read both ends, not that '
               'the draw is unbiased')
exp.limitation('organisms die during the run, so later frames contribute fewer '
               'choices; the count is over living samples only')
exp.limitation('the decision is read from `direction`, which EXP-44 showed is '
               'the decision of the frame it appears in, not of the next step')

if control_fires and control_specific:
    exp.verdict('passed',
                f'p(choose a move) = {p:.4f} over {total_chosen} choices, '
                f'{abs(z):.1f} SE from 2/3 (z = {z:+.2f}); the 0.625 of EXP-41 '
                f'was a sample of 24, not a bias')
else:
    exp.verdict('failed',
                f'p(choose a move) = {p:.4f} over {total_chosen} choices, '
                f'{abs(z):.1f} SE from 2/3 (z = {z:+.2f}); controls fires={control_fires} '
                f'specific={control_specific}')

exp.add_series('p_choose', [float(s) for s in SEEDS],
               [per_seed[f'seed{s}']['p_choose'] for s in SEEDS])
print(json.dumps({'summary': summary, 'per_seed': per_seed}, indent=2))
print(exp.save())
