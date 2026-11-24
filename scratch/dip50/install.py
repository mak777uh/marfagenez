import json, shutil
src = '/mnt/c/Users/Admin/Documents/Qoder/2026-10-18/82ab86cd/dip-2026-11-23-50.md'
dst = '/root/marfagenez/literature/dips/reports/dip-2026-11-23-50.md'
shutil.copyfile(src, dst)
rows = [json.loads(l) for l in open('/root/marfagenez/literature/dips/reports/dip-2026-11-23-50.jsonl', encoding='utf-8')]
print('jsonl cells:', len(rows), 'atoms unique:', len(set(r['atom'] for r in rows)))
print('dois:', sorted(set(w['doi'] for r in rows for w in r['works'])))
print('quotes:', sum(len(r['works']) for r in rows))
print('md bytes:', len(open(dst, encoding='utf-8').read()))
print('domains:', set(r['domain'] for r in rows))
print('confidence:', set(r['confidence'] for r in rows), 'locator_status:', set(r['locator_status'] for r in rows))
print('kinds:', sorted(set(r['kind'] for r in rows)))
