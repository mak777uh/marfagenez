import json
d = json.load(open('/root/marfagenez/results/EXP-22/run-2026-11-12T12-44-33.json'))
print('verdict:', json.dumps(d.get('verdict'), ensure_ascii=False))
for k, v in d.get('controls', {}).items():
    print(k, v.get('passed'), '|', v.get('evidence', '')[:140])
print('arms:')
for a in d.get('conditions', []):
    print(' ', a.get('key'), a.get('metrics'))
