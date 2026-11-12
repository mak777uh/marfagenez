# -*- coding: utf-8 -*-
"""EXP-48: where does the sevenfold gap between arithmetic and measurement go?

EXP-36 measured the move cost at which `random` stops beating `stay` on a
uniform field with `--layout even`, `capacity 10`, `income 1`, `maintenance 0.1`,
`repair-cost 0.5`, `damage-rate 0.2`: the crossing sits at `move_cost = 0.1211`
for income 1.5, 2 and 3, and at 0.1445 for income 1.

Arithmetic says something else.  Two organisms share a cell, so each takes
`income/2`; a step costs `maintenance + damage_rate*repair_cost = 0.1 + 0.1 = 0.2`,
plus `move_cost` if it moves.  Net for a mover:

    income/2 - 0.2 - move_cost

For income 2 that is `1 - 0.2 - move_cost`, which is positive up to
`move_cost = 0.8`.  Measured: the crossing is at 0.1211, seven times lower.

Two candidate explanations, and they make different predictions:

  (a) the organism pays for a move it does not make.  `Policy::Random` stands
      still 1/3 of the time, so the average cost is
      `0.2 + move_cost*2/3`, and the crossing would be at
      `(1 - 0.2) / (2/3) = 1.2`.  That is higher, not lower — so this cannot
      explain a crossing that is too low.

  (b) the cell is not shared evenly.  The even layout puts organisms round
      robin, but after the first move they clump; a cell with k organisms pays
      `income/k` each.  The crossing is then set by the *worst* cell, not the
      average.

There is a third, cheaper possibility: the crossing is not a budget crossing at
all but the point where the population stops being able to replace itself, and
the replacement rate depends on how many cells are left rich.

This experiment measures the actual per-organism income at the crossing, so the
arithmetic can be written with the number that is true instead of the number
that is assumed.  The trace does not report income, but it does report energy,
so the income is recovered from the energy drop between frames.

Arithmetic before the run
-------------------------
At the crossing, `move_cost = 0.1211`, income 2, `p(move) = 2/3`:
expected drop per step = `0.2 + 0.1211*2/3 = 0.2807` if the organism earns
nothing, and `0.2807 - income_taken` if it earns.  Energy is measured to 4
decimals, so an income of 0.1 is 500x the resolution.  The arithmetic predicts
`income_taken = 0.5` (half a cell) -> net drop `-0.219` (energy rises), and
`income_taken = 0.05` (a fifth of a cell) -> net drop `+0.23`.
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
        '--energy', '5', '--field', 'uniform', '--layout', 'even',
        '--seed', '1', '--n', '120', '--income', '2', '--policy', 'random']


def run(extra):
    out = subprocess.run([TRACE] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    path = [l for l in out.splitlines() if 'written:' in l][0].split('written:', 1)[1].strip()
    return json.load(open(os.path.join(ROOT, path)))


def income_from_energy(trace, move_cost):
    """Recover the income an organism actually took, from its energy series.

    drop(k) = 0.2 + move_cost*[moved at step k+1] - income_taken(k+1), and the
    decision for step k+1 is in frame k+1 (EXP-44).  So for every pair of
    consecutive frames where the organism is alive in both:

        income_taken = 0.2 + move_cost*moved - drop
    """
    incomes = []
    frames = trace['frames']
    for a, b in zip(frames, frames[1:]):
        for sa, sb in zip(a['samples'], b['samples']):
            if not (sa['alive'] and sb['alive']):
                continue
            moved = 1.0 if sb['direction'] != 0 else 0.0
            drop = sa['energy'] - sb['energy']
            incomes.append(0.2 + move_cost * moved - drop)
    return incomes


exp = Experiment(
    experiment_id='where-the-sevenfold-gap-goes',
    question='At the crossing of EXP-36 (move_cost 0.1211, income 2) how much '
             'income does an organism actually take per step?',
    arithmetic={
        'step_cost': 'maintenance 0.1 + damage_rate 0.2 * repair_cost 0.5 = 0.2',
        'shared_cell': 'two organisms on a cell take income/2 = 1.0 each with '
                       'income 2, so a mover nets 1.0 - 0.2 - 0.1211 = +0.68',
        'if_income_were_zero': 'a mover would lose 0.2 + 0.1211*2/3 = 0.2807 per '
                               'step, so its energy would fall 56 units over 200 steps',
        'discriminator': 'energy rises or falls at the crossing; the recovered '
                         'income says by how much the assumed 1.0 is wrong',
    },
    arms={'at_crossing': 'move_cost 0.1211', 'below': 'move_cost 0.05',
          'above': 'move_cost 0.4'},
    seed=1,
    command=' '.join([TRACE] + BASE) + ' --move-cost 0.1211|0.05|0.4',
)

results = {}
for key, cost in [('at_crossing', 0.1211), ('below', 0.05), ('above', 0.4)]:
    t = run(['--move-cost', str(cost)])
    inc = income_from_energy(t, cost)
    alive_last = sum(1 for s in t['frames'][-1]['samples'] if s['alive'])
    results[key] = {
        'move_cost': cost,
        'mean_income_taken': round(sum(inc) / len(inc), 4) if inc else None,
        'min_income_taken': round(min(inc), 4) if inc else None,
        'max_income_taken': round(max(inc), 4) if inc else None,
        'alive_at_end': alive_last,
        'samples': len(inc),
    }
    exp.add_arm(key, f'move cost {cost}', results[key], trace_hash=t['hash'])

mean_inc = results['at_crossing']['mean_income_taken']

# --- controls -------------------------------------------------------------
# fires: the recovered income is not the assumed half-cell.
control_fires = mean_inc is not None and abs(mean_inc - 1.0) > 0.1
# silent: with no movement and no income the recovery must return exactly 0.
t0 = run(['--move-cost', '0', '--income', '0'])
inc0 = income_from_energy(t0, 0.0)
control_silent = inc0 and max(abs(x) for x in inc0) < 1e-9
# specific: the recovery separates the three arms, i.e. it is not a constant.
vals = {k: results[k]['mean_income_taken'] for k in results}
control_specific = len({round(v, 3) for v in vals.values() if v is not None}) >= 2

exp.control('fires', control_fires,
            f'mean income taken at the crossing {mean_inc} vs the assumed 1.0 '
            f'(half of income 2)')
exp.control('silent', bool(control_silent),
            f'no income, no movement: recovered income max |x| = '
            f'{max(abs(x) for x in inc0):.2e} over {len(inc0)} samples')
exp.control('specific', control_specific,
            f'mean income by move cost: {vals}')

exp.limitation('income is recovered from the energy drop, so it assumes the step '
               'cost is exactly 0.2 + move_cost*moved; EXP-39 supports that but '
               'it was measured without income')
exp.limitation('the trace does not report how many organisms share a cell, so '
               'the recovered income says "less than half a cell" without saying '
               'how the cell was split')
exp.limitation('one seed, one density (n=120 on 120 cells); the crossing of '
               'EXP-36 was measured with the same setup, so the comparison holds '
               'but nothing generalises')

if control_fires and control_silent and control_specific:
    exp.verdict('passed',
                f'at the crossing the organism takes {mean_inc} per step, not the '
                f'1.0 that a shared cell would give; the arithmetic that predicts '
                f'a crossing at 0.8 assumes an income the organism does not get')
else:
    exp.verdict('failed',
                f'controls fires={control_fires} silent={control_silent} '
                f'specific={control_specific}; mean income {mean_inc}')

print(json.dumps(results, indent=2))
print(exp.save())
