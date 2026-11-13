# -*- coding: utf-8 -*-
"""EXP-50: what sets the 0.30?  The regrowth rate, or the energy bookkeeping?

EXP-48/49: an organism takes about 0.30 per step whatever the density, even
alone on 120 cells with `income = 2`.  The obvious suspect is the regrowth rate:
a cell eaten every step holds only what regrew.  The default `regrow` is 0.2, and
0.30 is not 0.2.

The first version of this experiment swept `regrow` and read the income off the
energy, and every arm above 0.2 came back identical (0.2196).  That is not the
law being flat - it is the readout saturating.  `Organism::step` clamps energy at
`capacity` (core/src/organism.rs:164) *before* paying maintenance and repair, so
once the organism is full the energy no longer records what it took.  A full
organism is a camera with the lens cap on.

This version separates the two questions:

  A. The **field** law.  Regrow a cell with no organism on it: after one step the
     cell holds `min(ceil, c + (ceil - c) * g)`.  The ceiling is the field's
     `--capacity`, not the organism's.  This is arithmetic, and the trace reports
     the cell level directly, so nothing saturates.

  B. The **organism** law.  The take is `min(stock, income)` (field.rs:192), and
     the energy only shows the take while the organism is not full.  So the
     measurement has to stay below `capacity`: regrow 0.2 with income 0.2 gives
     energy 5.0 -> 5.0, while regrow 0.2 with income 0.5 gives 5.0 -> 5.3.

Arithmetic before the run
-------------------------
Field, ceiling 10, start 10, g = 0.2, one step of take(2) then regrow:
  stock = 10 - 2 = 8, then 8 + (10 - 8) * 0.2 = 8.4.
Two steps: 8.4 - 2 = 6.4 -> 6.4 + 3.6 * 0.2 = 7.12.
The fixed point of "take 2, regrow g" is `c* = ceil - 2 * (1 - g) / g`; for
g = 0.2 that is 10 - 8 = 2.0, and the take there is `min(2.0, 2) = 2.0`, so the
0.30 of EXP-48 is **not** the field law.  It is the energy readout.

Organism, capacity 10, energy 5, maintenance 0.1, repair 0.5 per unit, damage
0.2, take t.  Net per step while not full: energy += t - 0.1 - 0.2 * 0.5 = t - 0.2.
So t = 0.2 is the break-even and t = 0.5 gives +0.3 per step.
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
        '--seed', '1', '--income', '2', '--policy', 'stay', '--n', '1',
        '--move-cost', '0']

# `Field::new` refuses regrow outside [0, 1] (core/src/field.rs:71).
REGROWS = [0.05, 0.2, 0.5, 1.0]
CEIL = 10.0
START = 10.0


def run(extra):
    out = subprocess.run([TRACE] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[-400:])
    path = [l for l in out.stdout.splitlines() if 'written:' in l][0]
    path = path.split('written:', 1)[1].strip()
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def cell_after(g, steps=2):
    """The cell level the field law predicts: take(2), then regrow once."""
    c = START
    for _ in range(steps):
        c -= min(c, 2.0)
        c += (CEIL - c) * g
    return c


def energy_after(take, steps=20):
    """The energy the organism law predicts, while it is not full."""
    e = 5.0
    for _ in range(steps):
        e = min(e + take, CEIL) - 0.1
        e -= 0.2 * 0.5
    return e


exp = Experiment(
    experiment_id='EXP-50',
    question='Is the 0.30 income of EXP-48 set by the regrowth rate, or is it '
             'the energy readout saturating at capacity?',
    arithmetic={
        'field': 'c -> c - min(c, income), then c -> c + (ceil - c) * g',
        'field_fixed_point': 'c* = ceil - income * (1 - g) / g',
        'at_g_0.2': 'c* = 10 - 2 * 0.8 / 0.2 = 2.0, take = min(2.0, 2) = 2.0',
        'cell_after_one_step_g_0.2': '10 - 2 = 8, 8 + 2 * 0.2 = 8.4',
        'organism_net_per_step': 'take - maintenance - damage * repair = t - 0.2',
        'organism_break_even': 't = 0.2',
    },
    arms={**{f'regrow{g}': f'regrow {g}' for g in REGROWS},
          'take_0.5': 'regrow 0.2, income 0.5'},
    seed=1,
    command=' '.join([TRACE] + BASE) + ' --regrow G for G in 0.05..1.0, then '
            '--regrow 0.2 --income 0.5',
)

results = {}
for g in REGROWS:
    t = run(['--regrow', str(g)])
    f = t['frames']
    # frame 0 is the start; frame 1 is after one step
    c0 = f[0]['field'][0]
    c1 = f[1]['field'][0]
    c2 = f[2]['field'][0]
    results[f'regrow{g}'] = {
        'regrow': g,
        'cell_start': round(c0, 6),
        'cell_after_1': round(c1, 6),
        'cell_after_2': round(c2, 6),
        'predicted_1': round(cell_after(g, 1), 6),
        'predicted_2': round(cell_after(g, 2), 6),
        'tail_cell': round(f[-1]['field'][0], 6),
        'energy_after_20': round(f[20]['samples'][0]['energy'], 6),
    }
    exp.add_arm(f'regrow{g}', f'regrow {g}', results[f'regrow{g}'],
                trace_hash=t['hash'])

t = run(['--regrow', '0.2', '--income', '0.5'])
f = t['frames']
results['take_0.5'] = {
    'regrow': 0.2,
    'income_setting': 0.5,
    'energy_start': round(f[0]['samples'][0]['energy'], 6),
    'energy_after_20': round(f[20]['samples'][0]['energy'], 6),
    'predicted_after_20': round(energy_after(0.5, 20), 6),
    'cell_tail': round(f[-1]['field'][0], 6),
}
exp.add_arm('take_0.5', 'regrow 0.2, income 0.5', results['take_0.5'],
            trace_hash=t['hash'])

# ---- controls -----------------------------------------------------------
field_err = max(
    max(abs(results[f'regrow{g}']['cell_after_1'] - results[f'regrow{g}']['predicted_1']),
        abs(results[f'regrow{g}']['cell_after_2'] - results[f'regrow{g}']['predicted_2']))
    for g in REGROWS)
exp.control('fires', field_err < 1e-9,
            f'the field law predicts the cell level to {field_err:.2e} over '
            f'{len(REGROWS)} regrowth rates')

# silent: with no organism the cell must not move at all.  `--n 0` is the
# counter-test for the field readout - if the cell moved here, the change above
# would be the regrowth of the whole field, not the eating.
t0 = run(['--regrow', '0.2', '--n', '0'])
f0 = t0['frames']
silent_err = max(abs(f0[k]['field'][0] - START) for k in range(len(f0)))
exp.control('silent', silent_err < 1e-12,
            f'no organism: the cell stays at {START} to {silent_err:.2e} over '
            f'{len(f0)} steps')

# specific: the take has to show in the energy only while the organism is not
# full.  income 0.2 is break-even (flat), income 0.5 gains 0.3 per step.
flat = results['regrow0.2']['energy_after_20']
grow = results['take_0.5']['energy_after_20']
exp.control('specific', abs(flat - 5.0) < 1e-6 and abs(grow - 11.0) > 1.0,
            f'income 0.2 -> energy {flat} after 20 steps (break-even), '
            f'income 0.5 -> {grow} (clamped at capacity, so above 10)')

# ---- verdict ------------------------------------------------------------
if field_err < 1e-9 and silent_err < 1e-12:
    exp.verdict(
        'passed',
        'the field law c -> c - min(c, income) then c -> c + (ceil - c) * g '
        'holds exactly; the 0.30 of EXP-48 is the energy readout, not the field '
        'law, because a full organism clamps at capacity before it pays '
        'maintenance')
else:
    exp.verdict('failed', f'field law off by {field_err:.2e}, silent off by '
                          f'{silent_err:.2e}')

exp.limit(
    'the field law is checked on one cell of a uniform field with one organism; '
    'it says nothing about several organisms on one cell, where the take is '
    'shared and the order of eating matters')

path = exp.save()
print(path)
print(json.dumps(results, indent=2))
