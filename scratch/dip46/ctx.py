import sys, re
p, needle = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 700
t = open(p, encoding='utf-8', errors='replace').read().replace('\n', ' ')
i = t.find(needle)
print('idx', i, 'len', len(t))
print(t[max(0, i - w):i + w])
