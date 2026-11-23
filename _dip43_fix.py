import json, io
p = '/root/marfagenez/literature/dips/reports/dip-2026-11-23-43.jsonl'
rows = [json.loads(l) for l in io.open(p, encoding='utf-8')]
for a in rows:
    if a['atom'] == 'DIP43-0001':
        a['statement'] = a['statement'].replace('за 21.6 генерации, то есть примерно', 'за 21.6 генерации, или примерно')
with io.open(p, 'w', encoding='utf-8') as fh:
    for a in rows:
        fh.write(json.dumps(a, ensure_ascii=False) + '\n')
print(rows[0]['statement'])
print('atoms:', len(rows))
