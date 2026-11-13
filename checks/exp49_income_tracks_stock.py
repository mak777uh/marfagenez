# -*- coding: utf-8 -*-
"""EXP-49: is the income taken proportional to the cell's own stock?

EXP-48 recovered the income an organism actually takes from its energy series:
0.2974 per step at the crossing (income 2, capacity 10, 120 cells, 120
organisms), not the 1.0 that "two organisms share a cell" would give.

Where does 0.2974 come from?  Three candidates:

  (a) k organisms share a cell, each taking income/k.  0.2974 of income 2 is
      k = 6.7, which is a lot of organisms on one cell but not impossible if
      they clump.
  (b) the cell is poor.  A cell regrows toward its ceiling at `regrow` per step;
      if the organisms eat it faster than it regrows, the stock is low and
      `take` returns less than `income` because there is less than `income` to
      take.  The default `regrow` is 0.2 per step, so a cell that is eaten every
      step can only give 0.2 + whatever was left.
  (c) the income is capped by `income` but not by the stock, and the organism
      takes `min(stock, income)` — which is (b) seen from the code.

(b) and (c) make the same prediction: the income taken should track the cell's
stock, not the number of organisms on it.  To separate them from (a), lower the
number of organisms until crowding is gone (n = 30 on 120 cells, so most cells
hold one organism) and see whether the income taken rises to `income` or stays
near 0.3.

Arithmetic before the run
-------------------------
With n = 30 on 120 cells and `--layout even`, organisms occupy cells 0, 4, 8, ...
so no cell is shared.  A lone organism takes up to `income = 2`; the cell regrows
`regrow` per step.  If the organism takes everything, the cell is empty next step
and gives `regrow` = 0.2 only.  So even alone, the income alternates between
"whatever regrew" and "the cap", and the average cannot exceed
`regrow + (income - regrow)` ... which is just `income`.  The mean over a long
run should be `min(income, regrow + leftover)`.

If instead the income is set by crowding, n = 30 gives the full 2.0 and n = 120
gives 0.3.

The discriminator is therefore: does the recovered income at n = 30 exceed the
income at n = 120 by a factor near 6.7 (crowding), or stay near 0.3 (stock)?
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from checks.experiment import Experiment  # noqa: E402

TRACE = os.path.join(ROOT, 'core', 'target', 'release', 'trace')

BASE = ['--steps', '200', '--every', '1', '--cells', '120', '--capacity', '10',
        '--damage-rate', '0.2', '--maintenance', '0.1', '--repair-cost', '0.5',
        '--energy', '5', '--field', 'uniform', '--rich', '2.0', '--poor', '0.2', '--layout', 'even',
        '--seed', '1', '--income', '2', '--policy', 'random',
        '--move-cost', '0.1211']


def run(extra):
    out = subprocess.run([TRACE] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    path = [l for l in out.splitlines() if 'written:' in l][0].split('written:', 1)[1].strip()
    return json.load(open(os.path.join(ROOT, path)))


def income_from_energy(trace, move_cost):
    incomes = []
    frames = trace['frames']
    for a, b in zip(frames, frames[1:]):
        for sa, sb in zip(a['samples'], b['samples']):
            if not (sa['alive'] and sb['alive']):
                continue
            moved = 1.0 if sb['direction'] != 0 else 0.0
            incomes.append(0.2 + move_cost * moved - (sa['energy'] - sb['energy']))
    return incomes


def occupied(trace):
    """How many cells hold at least one organism, in the last frame."""
    cells = [s['cell'] for s in trace['frames'][-1]['samples'] if s['alive']]
    return len(set(cells)), len(cells)


exp = Experiment(
    experiment_id='income-tracks-stock-not-crowding',
    question='Is the income an organism takes set by how many share its cell '
             '(crowding) or by how much the cell has regrown (stock)?',
    arithmetic={
        'step_cost': '0.1 + 0.2*0.5 = 0.2',
        'crowding_prediction': 'n=120 on 120 cells, k=6.7 per cell -> income/k '
                               '= 0.30; n=30 on 120 cells, k=1 -> income 2.0, a '
                               'factor 6.7 higher',
        'stock_prediction': 'a cell eaten every step only holds what regrew '
                            '(0.2 per step by default), so the income is near '
                            '0.2-0.3 at both densities',
        'discriminator': 'the ratio of income at n=30 to income at n=120: near '
                         '6.7 means crowding, near 1 means stock',
    },
    arms={'n30': '30 organisms on 120 cells', 'n60': '60 on 120',
          'n120': '120 on 120'},
    seed=1,
    command=' '.join([TRACE] + BASE) + ' --n 30|60|120',
)

results = {}
for key, n in [('n30', 30), ('n60', 60), ('n120', 120)]:
    t = run(['--n', str(n)])
    inc = income_from_energy(t, 0.1211)
    used, alive = occupied(t)
    results[key] = {
        'n': n,
        'mean_income_taken': round(sum(inc) / len(inc), 4) if inc else None,
        'alive_at_end': alive,
        'cells_occupied': used,
        'mean_per_cell': round(alive / used, 2) if used else None,
        'samples': len(inc),
    }
    exp.add_arm(key, f'n={n}', results[key], trace_hash=t['hash'])

r30 = results['n30']['mean_income_taken']
r120 = results['n120']['mean_income_taken']
ratio = r30 / r120 if r120 else None

# --- controls -------------------------------------------------------------
# fires: the income is not the whole cell income in any arm.
control_fires = all(v['mean_income_taken'] < 1.0 for v in results.values())
# silent: at n=1 there is no crowding at all, and the income must still be low
# if the stock is the limit.
t1 = run(['--n', '1'])
inc1 = income_from_energy(t1, 0.1211)
mean1 = sum(inc1) / len(inc1) if inc1 else None
control_silent = mean1 is not None and mean1 < 1.0
# specific: the two predictions differ by a factor 6.7 and the measurement
# lands on one side of the midpoint (sqrt(6.7) = 2.6).
control_specific = ratio is not None and ratio < 2.6

exp.control('fires', control_fires,
            f'income taken by density: '
            f'{ {k: v["mean_income_taken"] for k, v in results.items()} }')
exp.control('silent', bool(control_silent),
            f'one organism alone on 120 cells takes {mean1} per step, so no '
            f'crowding is needed for the income to be low')
exp.control('specific', control_specific,
            f'income n=30 / n=120 = {ratio:.2f}, below the midpoint 2.6 between '
            f'crowding (6.7) and stock (1.0)')

exp.limitation('income is recovered from the energy drop, so it assumes the step '
               'cost is 0.2 + move_cost*moved; EXP-39 supports that')
exp.limitation('the trace does not report the cell stock, so "stock" is inferred '
               'from the absence of crowding, not read directly')
exp.limitation('one seed and one regrow (the default 0.2); a higher regrow would '
               'separate the two predictions more sharply and was not tried')

if control_fires and control_silent and control_specific:
    exp.verdict('passed',
                f'income n=30/n=120 = {ratio:.2f} (crowding predicts 6.7, stock '
                f'predicts 1.0); a lone organism takes {mean1} per step, so the '
                f'limit is the cell stock, not the number of organisms')
else:
    exp.verdict('failed',
                f'controls fires={control_fires} silent={control_silent} '
                f'specific={control_specific}; ratio {ratio}')

print(json.dumps(results, indent=2))
print(exp.save())
