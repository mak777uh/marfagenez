import sys, re, html, os
p = sys.argv[1]
raw = open(p, encoding='utf-8', errors='replace').read()
raw = re.sub(r'(?is)<script.*?</script>', ' ', raw)
raw = re.sub(r'(?is)<style.*?</style>', ' ', raw)
raw = re.sub(r'(?i)</(p|div|h[1-6]|li|tr|table|section)>', '\n', raw)
raw = re.sub(r'<[^>]+>', ' ', raw)
raw = html.unescape(raw)
raw = re.sub(r'[ \t]+', ' ', raw)
raw = re.sub(r'\n\s*\n+', '\n', raw)
out = p + '.txt'
open(out, 'w', encoding='utf-8').write(raw)
print('saved', out, len(raw))
