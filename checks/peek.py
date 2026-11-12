import json, sys
d = json.load(open('/root/marfagenez/results/stay/trace-stay-1794486690.json'))
print(type(d))
if isinstance(d, dict):
    for k in d:
        v = d[k]
        print(k, '=', (str(v)[:200] if not isinstance(v, list) else f'list[{len(v)}]'))
    for k in d:
        if isinstance(d[k], list) and d[k]:
            print('---', k, 'first:', json.dumps(d[k][0])[:400])
else:
    print(len(d), json.dumps(d[0])[:600])
