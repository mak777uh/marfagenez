import json, glob, collections, os

os.chdir("/root/marfagenez")
c = collections.Counter()
for f in glob.glob("results/**/run-*.json", recursive=True):
    if "_archive" in f:
        continue
    d = json.load(open(f))
    v = d.get("verdict")
    if isinstance(v, dict):
        v = v.get("kind")
    c[v] += 1
for k, n in c.most_common():
    print(n, k)
print("total", sum(c.values()))
