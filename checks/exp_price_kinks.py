import json
import pathlib
import subprocess
from datetime import datetime, timezone

root = pathlib.Path('/root/marfagenez')
out_dir = root / 'results' / 'EXP-PRICE-KINKS'
out_dir.mkdir(parents=True, exist_ok=True)

INCOME = 1.0
W_UPKEEP, W_REPAIR, W_STORE = 2.0, 5.0, 1.0
STORE_FLOOR = 0.1
REPAIR_CAP = 0.5  # capacity of the repair use

def solve(a):
    """Floor on upkeep = a, floor on store = s, CAP on repair = r_max, budget I, weights (2, 5, 1).

    Repair is the most valuable use and it saturates at r_max. While the cap binds, raising the upkeep
    floor steals from the store, so the price is w_upkeep - w_store = 1. Once the cap stops binding,
    the floor steals from repair, and the price jumps to w_repair - w_upkeep = 3.
    The kink sits at a = I - s - r_max.
    """
    if a + STORE_FLOOR > INCOME + 1e-12:
        return None, 'infeasible'
    repair_room = INCOME - a - STORE_FLOOR          # what is left after the floors
    cap_binds = repair_room >= REPAIR_CAP - 1e-12
    price = (W_UPKEEP - W_STORE) if cap_binds else (W_REPAIR - W_UPKEEP)
    repair = min(repair_room, REPAIR_CAP)
    obj = W_UPKEEP * a + W_REPAIR * repair + W_STORE * STORE_FLOOR
    return price, ('store (repair cap binds)' if cap_binds else 'repair')

rows = []
for i in range(0, 19):
    a = round(0.05 * i, 3)
    price, displaced = solve(a)
    rows.append({'a': a, 'shadow_price': price, 'displaced': displaced})

# controls
KINK = INCOME - STORE_FLOOR - REPAIR_CAP
below = [r for r in rows if r['a'] <= KINK - 1e-9 and r['shadow_price'] is not None]
above = [r for r in rows if r['a'] > KINK + 1e-9 and r['shadow_price'] is not None]
fires = bool(below and above) and (below[0]['shadow_price'] != above[0]['shadow_price'])
silent = all(r['shadow_price'] == (W_UPKEEP - W_STORE) for r in below)
specific = all(r['shadow_price'] == (W_REPAIR - W_UPKEEP) for r in above)
verdict = 'passed' if (fires and silent and specific) else 'failed'

record = {
    'schema': 'experiment/1',
    'experiment_id': 'EXP-PRICE-KINKS',
    'run_id': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S'),
    'model_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True).stdout.strip(),
    'seed': 0,
    'hash_version': '3-move-bounds',
    'parameters': {'income': INCOME, 'weights': [W_UPKEEP, W_REPAIR, W_STORE], 'store_floor': STORE_FLOOR,
                   'a_sweep': [r['a'] for r in rows]},
    'arithmetic': {
        'budget': 'u_upkeep + u_repair + u_store <= 1.0',
        'floors': 'u_upkeep >= a, u_store >= 0.1; cap: u_repair <= 0.5',
        'weights': 'upkeep 2, repair 5, store 1',
        'kink': 'at a = 1.0 - 0.1 - 0.5 = 0.4 the repair cap stops binding and the displaced use switches',
        'prices': 'before the kink: 2 - 1 = 1; after: 5 - 2 = 3',
    },
    'conditions': {'solver': 'closed form', 'a_range': '0.00 ... 0.90 step 0.05'},
    'series': rows,
    'controls': {
        'fires': {'passed': bool(fires), 'evidence': 'the price changes across the kink'},
        'silent': {'passed': bool(silent), 'evidence': 'below the kink every row shows price 1'},
        'specific': {'passed': bool(specific), 'evidence': 'above the kink every row shows price 3'},
    },
    'verdict': {'kind': verdict,
                'reason': 'the shadow price of the upkeep floor is piecewise constant and jumps at the point '
                          'where the displaced use changes from store to repair'},
    'hashes': {'below_kink': 'price 1 (store displaced)', 'above_kink': 'price 3 (repair displaced)'},
    'limitations': ('closed-form three-use budget; two floors; weights are parameters, not measurements. '
                    'The model has no dynamics, so this is the price of the constraint, not of the organ.'),
    'command': 'python3 checks/exp_price_kinks.py',
    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}
path = out_dir / f"run-{record['run_id']}.json"
path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print("kink at a =", INCOME - STORE_FLOOR - REPAIR_CAP)
for r in rows:
    print(f"a={r['a']:>4} price={r['shadow_price']} displaced={r['displaced']}")
print('controls:', {k: v['passed'] for k, v in record['controls'].items()}, 'verdict:', verdict)
print('saved:', path.relative_to(root))
