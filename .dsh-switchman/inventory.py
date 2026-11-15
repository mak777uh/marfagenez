"""PROTOCOL-0 п.1 — инвентаризация трасс. Отвечает: сколько НЕЗАВИСИМЫХ серий.

Классы:
  independent      — уникальный хэш, уникальный (policy, seed), >= 100 кадров
  duplicate        — совпадающий хэш с другой трассой
  final-frame-only — одна запись состояния
  too-short        — < 100 кадров
"""
import json, glob, hashlib, collections, sys

ROOT = '/root/marfagenez/results'
files = sorted(glob.glob(ROOT + '/**/trace-*.json', recursive=True))

rows = []
for f in files:
    try:
        d = json.load(open(f))
    except Exception as e:
        rows.append(dict(path=f, cls='unreadable', n=0, hash=None, policy=None, seed=None))
        continue
    if isinstance(d, dict) and isinstance(d.get('frames'), list):
        n = len(d['frames'])
        h = d.get('hash')
        pol = d.get('policy')
        seed = d.get('seed')
    elif isinstance(d, list):
        n = len(d)
        h, pol, seed = None, None, None
    else:
        n = 1
        h, pol, seed = None, None, None
    rows.append(dict(path=f, cls=None, n=n, hash=h, policy=pol, seed=seed))

# classify by hash duplicates
by_hash = collections.defaultdict(list)
for r in rows:
    if r['hash']:
        by_hash[r['hash']].append(r)

dup_hashes = {h for h, rs in by_hash.items() if len(rs) > 1}

for r in rows:
    if r['cls']:
        continue
    if r['hash'] in dup_hashes:
        r['cls'] = 'duplicate'
    elif r['n'] >= 100:
        r['cls'] = 'independent'
    elif r['n'] == 1:
        r['cls'] = 'final-frame-only'
    else:
        r['cls'] = 'too-short'

cnt = collections.Counter(r['cls'] for r in rows)
print("=" * 60)
print("ВСЕГО ФАЙЛОВ:", len(rows))
for k in ('independent', 'duplicate', 'too-short', 'final-frame-only', 'unreadable'):
    print(f"  {k:18s} {cnt.get(k, 0)}")
print()

print("=" * 60)
print("НЕЗАВИСИМЫЕ СЕРИИ (>=100 кадров, уникальный хэш):")
ind = [r for r in rows if r['cls'] == 'independent']
for r in sorted(ind, key=lambda x: -x['n']):
    print(f"  {r['n']:4d} кадров  policy={r['policy']:<10} seed={r['seed']}  {r['path'].replace(ROOT+'/','')}")
print()
print("уникальных (policy, seed) среди независимых:",
      len({(r['policy'], r['seed']) for r in ind}))
print()

print("=" * 60)
print("ДУБЛИКАТЫ (один хэш — несколько путей):")
for h, rs in sorted(by_hash.items(), key=lambda kv: -len(kv[1])):
    if len(rs) > 1:
        print(f"  хэш {h[:16]}… × {len(rs)}")
        for r in rs:
            print(f"      {r['path'].replace(ROOT+'/','')}")
print()

print("=" * 60)
print("ВЕРДИКТ ПРОТОКОЛА-0 п.1:")
n_ind = len(ind)
n_seeds = len({(r['policy'], r['seed']) for r in ind})
n_long = len([r for r in ind if r['n'] >= 300])
if n_long >= 20:
    print(f"  passed — {n_long} независимых серий >=300 шагов")
elif n_ind >= 20:
    print(f"  passed (слабо) — {n_ind} независимых >=100, но >=300 всего {n_long}")
elif n_ind > 0:
    print(f"  FAILED — независимых серий >=100 всего {n_ind} (нужно >=20), "
          f"из них >=300 шагов: {n_long}")
    print(f"  независимых (policy, seed): {n_seeds}")
else:
    print("  NOT APPLICABLE — независимых серий нет")
