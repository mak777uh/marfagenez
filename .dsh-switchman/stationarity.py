"""PROTOCOL-0 п.2 — гейт стационарности на публичных трассах.

Для каждой независимой серии (>=100 кадров, уникальный хэш):
  - окна длины L in {50, 100}
  - в окне: mean и std по шагам (по полю целиком и по сумме)
  - окно стационарно, если |mean(1-я половина) - mean(2-я половина)| < 2*std/sqrt(L/2)
  - окно absorbing, если поле не меняется между кадрами (или damage==0 и energy на потолке)
"""
import json, glob, math, collections

ROOT = '/root/marfagenez/results'
files = sorted(glob.glob(ROOT + '/**/trace-*.json', recursive=True))

def load(f):
    d = json.load(open(f))
    if not (isinstance(d, dict) and isinstance(d.get('frames'), list)):
        return None
    return d

# независимые: уникальный хэш и >=100 кадров
by_hash = collections.defaultdict(list)
for f in files:
    d = load(f)
    if d and d.get('hash'):
        by_hash[d['hash']].append(f)

series = []
for h, fs in by_hash.items():
    d = load(fs[0])
    if len(d['frames']) >= 100:
        series.append((fs[0], d))

print("независимых серий >=100 кадров:", len(series))
print()

def field_sum(frame):
    return sum(frame.get('field') or [])

for path, d in series:
    frames = d['frames']
    steps = [fr.get('step') for fr in frames]
    sums = [field_sum(fr) for fr in frames]
    print("=" * 62)
    print(f"{path.replace(ROOT+'/','')}")
    print(f"  policy={d.get('policy')} seed={d.get('seed')} кадров={len(frames)} "
          f"шаги {steps[0]}…{steps[-1]}")
    # absorbing check: identical consecutive field vectors
    identical = sum(1 for a, b in zip(frames, frames[1:]) if a.get('field') == b.get('field'))
    print(f"  подряд идущих одинаковых полей: {identical}/{len(frames)-1}")

    for L in (50, 100):
        if len(sums) < L:
            continue
        nwin = len(sums) // L
        stat = 0
        for w in range(nwin):
            seg = sums[w*L:(w+1)*L]
            half = L // 2
            m1 = sum(seg[:half]) / half
            m2 = sum(seg[half:]) / half
            var = sum((x - (m1+m2)/2) ** 2 for x in seg) / (L - 1)
            sd = math.sqrt(var)
            se = sd / math.sqrt(half)
            is_stat = abs(m1 - m2) < 2 * se if se > 0 else (abs(m1-m2) == 0)
            if is_stat:
                stat += 1
        print(f"  L={L}: окон {nwin}, стационарных {stat}")
    print()
