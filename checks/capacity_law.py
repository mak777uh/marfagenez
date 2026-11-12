import math

def pmf(n, cells, k):
    """Binomial(n, 1/cells) pmf, in log space to avoid overflow."""
    p = 1.0 / cells
    if k == 0:
        return (1 - p) ** n
    if k == n:
        return p ** n
    logc = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    return math.exp(logc + k * math.log(p) + (n - k) * math.log1p(-p))

def jmax(M, r, t=1.0, maint=0.6):
    y = r * M
    return 0 if y < maint else int(math.floor((y - maint) / t)) + 1

def alive(n, cells, M, r):
    j = jmax(M, r)
    # E[min(K, j)] = sum_{k<j} k*P(k) + j*P(K>=j); truncate the tail safely.
    s = 0.0
    cum = 0.0
    for k in range(0, min(n, j) + 1):
        pk = pmf(n, cells, k)
        cum += pk
        s += k * pk
    s += j * max(0.0, 1.0 - cum)
    return cells * s

def capacity(cells, M, r):
    """Largest n such that alive(n) >= n."""
    best = 0
    for n in range(1, 40 * cells + 1):
        if alive(n, cells, M, r) >= n - 1e-9:
            best = n
    return best

print("cells  M    r    | j | capacity | cap/cells")
for cells in (10, 20, 40, 80, 120, 160, 200):
    for (M, r) in ((1.0, 0.8), (1.5, 0.8), (2.0, 0.8), (2.0, 0.5), (3.0, 0.6), (4.0, 0.8)):
        c = capacity(cells, M, r)
        print(f"{cells:5} {M:4.1f} {r:4.2f} | {jmax(M, r)} | {c:8} | {c/cells:.3f}")
