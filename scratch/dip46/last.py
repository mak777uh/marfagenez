import os, re
D = '/root/marfagenez/scratch/dip46/txt'
pat = re.compile(r'(R\s?2|R²|R\s?\^2)\s*[=:]')
for f in sorted(os.listdir(D)):
    t = open(os.path.join(D, f), encoding='utf-8', errors='replace').read().replace('\n', ' ')
    for s in re.split(r'(?<=[.!?])\s+', t):
        low = s.lower()
        if 'rate' in low and pat.search(s) and re.search(r'(slope|linear|regress|increas|decreas)', low):
            print(f, '|', s[:250])
            break
