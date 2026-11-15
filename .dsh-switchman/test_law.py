import json

rows = json.load(open(".dsh-switchman/sweep_capacity.json"))
cost = 0.13
income = 2.0

ok = bad = 0
for r in rows:
    if r["protocol"] != "proportional":
        continue
    n = r["n"]
    pred = n if income / n > cost else 0
    if r["alive"] == pred:
        ok += 1
    else:
        bad += 1
        print("PROP MISS M=%s r=%s n=%d alive=%d pred=%d taken=%s"
              % (r["M"], r["r"], n, r["alive"], pred, r["taken"][:4]))
print("\nprop law (alive == n if income/n > cost else 0): matches %d/%d" % (ok, ok + bad))
