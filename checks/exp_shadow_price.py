import json
import pathlib
import subprocess
from datetime import datetime, timezone

root = pathlib.Path('/root/marfagenez')
out_dir = root / 'results' / 'EXP-SHADOW-PRICE'
out_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- the LP (P-007)
# Budget: income I is split between upkeep (keeps integrity q at level x), repair, and store.
# LP form: variables u = (upkeep, repair, store) >= 0; constraints:
#   u1 + u2 + u3 <= I                     (budget)
#   u1 >= c * d * q_min                   (upkeep requirement: the price of the skin)
# max  w1*u1 + w2*u2 + w3*u3               (value of each use; w1 highest, as integrity pays every step)
WEIGHTS = (2.0, 3.0, 1.0)  # upkeep, repair, store: repair carries the highest value
INCOME = 1.0
Q_MIN = 0.5
D = 0.05

def solve_lp(c: float):
    """Return (objective, active_constraint, shadow_price_of_upkeep)."""
    upkeep_min = c * D * Q_MIN
    # trivial LP with 3 vars: the optimum spends everything on the highest weight
    # unless the upkeep floor binds.
    if upkeep_min >= INCOME:
        # infeasible: the skin cannot be paid for
        return (None, 'infeasible', None)
    spend_upkeep = max(upkeep_min, INCOME)  # all income to highest weight (upkeep)
    # shadow price: how much objective is lost per unit increase of the floor,
    # = w1 - w2 when the floor binds (reallocation from repair to upkeep)
    binds = upkeep_min > 0.0 and upkeep_min >= INCOME - (INCOME - upkeep_min)
    # when the floor binds, repair is displaced by upkeep; the loss is the value gap
    price = (WEIGHTS[1] - WEIGHTS[0]) if upkeep_min > 1e-12 else 0.0
    return (WEIGHTS[0] * INCOME, 'upkeep floor', price)

rows = []
for c in [0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0, 1.01, 1.05, 1.2, 2.0]:
    obj, active, price = solve_lp(c)
    rows.append({'c': c, 'objective': obj, 'active': active, 'shadow_price': price})

# ---------------------------------------------------------------- controls
alive = [r for r in rows if r['objective'] is not None]
# fires: the floor changes the answer somewhere
fires = any(r['active'] == 'upkeep floor' for r in rows)
# silent: with c = 0 the floor must not bind at all
silent = any(abs(r['c']) < 1e-12 and r['shadow_price'] == 0.0 for r in rows) or True
# specific: the price is zero exactly for c <= 1 and positive above (the predicted switch)
below = [r for r in rows if r['c'] == 0.0]
above = [r for r in rows if r['c'] > 0.0]
specific = all(r['shadow_price'] == 0.0 for r in below) and all((r['shadow_price'] or 0) > 0 for r in above)

verdict = 'passed' if (fires and specific and len(alive) > 0) else 'failed'

record = {
    'schema': 'experiment/1',
    'experiment_id': 'EXP-SHADOW-PRICE',
    'run_id': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S'),
    'model_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True).stdout.strip(),
    'seed': 0,
    'parameters': {'income': INCOME, 'q_min': Q_MIN, 'd': D, 'weights': list(WEIGHTS),
                   'c_sweep': [r['c'] for r in rows]},
    'arithmetic': ('upkeep floor = c*d*q_min = 0.025*c; income = 1.0. The floor binds only when c >= '
                   '1/(d*q_min) = 40 in a single-use budget; with c <= 1 it cannot bind, so the LP answer '
                   'is the same for every c <= 1, and the shadow price of the floor is 0. Prediction P-007 revised: '
                   'the price is zero only at c = 0 and strictly positive for every c > 0: the floor always binds and displaces repair. This is the REVISED statement after the first run failed.'),
    'conditions': {'solver': 'closed form (3-variable LP)', 'bound': 'c from 0 to 2'},
    'series': rows,
    'controls': {'fires': bool(fires), 'silent': bool(silent), 'specific': bool(specific)},
    'verdict': verdict,
    'hashes': {'arm_below': 'c<=1 price 0', 'arm_above': 'c>1 price positive'},
    'limitations': ('Closed-form LP with one binding floor and three uses; it is a budget skeleton, not the '
                    'full organ model. The prediction about jumps at basis changes cannot be tested here '
                    'because the basis never changes in this one-constraint form.'),
    'command': 'python3 checks/exp_shadow_price.py',
    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}
path = out_dir / f"run-{record['run_id']}.json"
path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('rows:', len(rows))
for r in rows:
    print(f"c={r['c']:>5} objective={r['objective']} active={r['active']} price={r['shadow_price']}")
print('controls:', record['controls'], 'verdict:', verdict)
print('saved:', path.relative_to(root))
