"""EXP-24: where does k_max come from?

The question
------------
EXP-23 showed that capacity is set by seating: survivors = sum over cells of
min(occupancy, k_max).  That left k_max as a measured number.  This experiment
asks where k_max comes from.

What we claim
-------------
Let `M` be the level the cell regrows toward (the `rich` parameter, not the
final field level).  With k eaters on one cell, the cell level follows

    c_0 = M
    c_{n+1} = (c_n - min(k*income, c_n)) + (M - (c_n - min(k*income, c_n))) * regrow

and settles at c*.  The i-th eater takes t_i = min(income, c* - (i-1)*income).
Then

    k_max = max { k : t_i > maintenance for every i <= k }

and the field capacity is C = cells * k_max.

Three things that are easy to get wrong, and that this script gets right
-----------------------------------------------------------------------
1. The recursion starts at M = rich, not at the final field level.  The final
   level is an output of the recursion, not an input.
2. The comparison is strict.  The model kills on `energy <= 0`
   (core/src/organism.rs:177) and updates energy as
   `(energy + taken) - maintenance`, so an eater that takes exactly
   `maintenance` lands on 0.0 and dies.
3. The comparison carries a margin.  In f64 the subtraction `3.8 - 3.2` gives
   0.5999999999999999, so a bare `>` would pass an eater that takes exactly
   `maintenance` by accident.  The margin is what makes the test mean what the
   model does.

Why this is not a fit
---------------------
M, income, maintenance and regrow are all read from the model's own
parameters.  The prediction is computed before any run and then compared with
a run.  A fitted number could not fail; this one can, and did: the first two
versions of this script (final level as input; `>=` instead of `>`) predicted
[0, 40, 80, 120, 160] and [40, 80, 120, 160, 200] against a measured
[40, 80, 120, 160, 160].

What this does not prove
------------------------
* It does not prove the formula for fields that stay non-uniform.  The
  alternating field is used because its poor cells are pulled up to the rich
  level by regrow and stop being poor; the field is uniform at the end.
* It does not prove anything about moving organisms.  Every arm uses
  `--policy stay`.
* It does not prove the recursion is the *only* way to get k_max.  It shows
  that this recursion reproduces the measurement on five points.
* It does not prove the transient.  Only the settled state is compared.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from checks.experiment import Experiment  # noqa: E402

TRACE = os.path.join(ROOT, 'core', 'target', 'release', 'trace')
OUTDIR = os.path.join(ROOT, 'core', 'results', 'stay')

INCOME = 0.8
MAINT = 0.6
CELLS = 40
RICH = 4.0
POOR = 0.5
STEPS = 3000
EPS = 1e-9


def steady_field(level, regrow, k, steps=STEPS):
    """The cell level after `steps` steps of: k eaters take, then one regrow."""
    c = level
    for _ in range(steps):
        cc = c
        for _ in range(k):
            cc -= min(INCOME, cc)
        c = cc + (level - cc) * regrow
    return c


def kmax(regrow, level=RICH):
    """Largest k such that every one of the k eaters clears the maintenance."""
    best = 0
    for k in range(1, 40):
        c = steady_field(level, regrow, k)
        cc = c
        ok = True
        for _ in range(k):
            t = min(INCOME, cc)
            if t <= MAINT + EPS:
                ok = False
                break
            cc -= t
        if not ok:
            return best
        best = k
    return best


def run_trace(regrow, layout, n, seed=1, steps=STEPS):
    args = [TRACE, '--field', 'alternating', '--rich', str(RICH), '--poor', str(POOR),
            '--regrow', str(regrow), '--cells', str(CELLS), '--n', str(n),
            '--seed', str(seed), '--steps', str(steps), '--every', str(steps),
            '--policy', 'stay', '--layout', layout]
    subprocess.run(args, capture_output=True, text=True,
                   cwd=os.path.join(ROOT, 'core'))
    files = sorted([os.path.join(OUTDIR, f) for f in os.listdir(OUTDIR)],
                   key=os.path.getmtime)
    d = json.load(open(files[-1]))
    fr = d['frames'][-1]
    alive = sum(1 for s in fr['samples'] if s['alive'])
    return alive, fr['field'], d['hash']


def main():
    regrows = (0.2, 0.4, 0.6, 0.8, 0.95)
    arms = {'even_r%03d' % int(r * 100): 'alternating, even seating, regrow %.2f' % r
            for r in regrows}

    exp = Experiment(
        experiment_id='EXP-24',
        question='Where does k_max come from? Is it max{k : every eater takes > maintenance}?',
        arithmetic={
            'income': INCOME,
            'maintenance': MAINT,
            'cells': CELLS,
            'organisms_per_cell_at_start': 4,
            'recursion_start': RICH,
            'rich': RICH,
            'poor': POOR,
            'margin': EPS,
            'note': ('recursion starts at M=rich, comparison is strict, '
                     'prediction computed before any run'),
        },
        arms=arms,
        seed=1,
        command='python3 checks/exp24_kmax_floor.py',
        parameters={'steps': STEPS, 'cells': CELLS, 'n': 4 * CELLS},
    )

    rows = []
    for regrow in regrows:
        key = 'even_r%03d' % int(regrow * 100)
        alive, field, h = run_trace(regrow, 'even', 4 * CELLS)
        level = field[0]
        spread = max(field) - min(field)
        k = kmax(regrow)
        predicted = CELLS * k
        rows.append({'regrow': regrow, 'level': level, 'spread': spread,
                     'k_max': k, 'predicted': predicted, 'alive': alive,
                     'hash': h})
        exp.add_series(key, [float(STEPS)], [float(alive)])
        exp.add_arm(key, arms[key],
                    {'alive': alive, 'level': level, 'k_max': k,
                     'predicted': predicted, 'spread': spread},
                    trace_hash=h)

    print('%-8s %-9s %-8s %-6s %-10s %-8s' %
          ('regrow', 'level', 'spread', 'k_max', 'predicted', 'alive'))
    for r in rows:
        print('%-8.2f %-9.4f %-8.4f %-6d %-10d %-8d%s' %
              (r['regrow'], r['level'], r['spread'], r['k_max'],
               r['predicted'], r['alive'],
               '' if r['predicted'] == r['alive'] else '  MISS'))

    all_match = all(r['predicted'] == r['alive'] for r in rows)

    fires = rows[0]['alive'] < rows[-1]['alive']
    silent = all(r['spread'] < 1e-9 for r in rows)
    specific = len(set(r['predicted'] for r in rows)) > 1

    exp.control('fires', fires,
                'regrow 0.20 gives %d survivors, regrow 0.95 gives %d'
                % (rows[0]['alive'], rows[-1]['alive']))
    exp.control('silent', silent,
                'final field spread is under 1e-9 in every arm')
    exp.control('specific', specific,
                'predicted capacities are %s'
                % sorted(set(r['predicted'] for r in rows)))

    exp.limitation(
        'Uniform-at-the-end fields only, Policy::Stay only, one seed, cells=40, '
        'n=160.  The alternating field starts non-uniform; it is uniform at the '
        'end only because regrow pulls every cell toward rich.  Nothing here '
        'covers moving organisms or fields that stay non-uniform, and nothing '
        'here covers the transient.')

    if all_match and fires and silent and specific:
        exp.verdict('passed',
                    'k_max = max{k : every eater takes > maintenance} reproduces '
                    'all five arms: %s' % [r['alive'] for r in rows])
    elif not all_match:
        exp.verdict('failed', 'predicted %s, measured %s'
                    % ([r['predicted'] for r in rows],
                       [r['alive'] for r in rows]))
    else:
        exp.verdict('failed', 'a control did not pass')

    path = exp.save()
    print('saved:', path)
    print('verdict:', json.dumps(exp.result['verdict'], ensure_ascii=False))
    return 0 if all_match else 1


if __name__ == '__main__':
    sys.exit(main())
