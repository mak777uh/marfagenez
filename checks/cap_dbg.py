import math

def pmf(n, cells, k):
    p = 1.0 / cells
    if k == 0:
        return (1 - p) ** n
    if k == n:
        return p ** n
    lc = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    return math.exp(lc + k * math.log(p) + (n - k) * math.log1p(-p))

def jmax(M, r, t=1.0, maint=0.6):
    y = r * M
    return 0 if y < maint else int(math.floor((y - maint) / t)) + 1

def alive(n, cells, M, r):
    j = jmax(M, r)
    s, cum = 0.0, 0.0
    for k in range(0, min(n, j) + 1):
        pk = pmf(n, cells, k)
        cum += pk
        s += k * pk
    s += j * max(0.0, 1.0 - cum)
    return cells * s

# Measured (single seed 20250101, 300 steps, Policy::Stay):
#   cells=40, M=2, r=0.8 -> 37
#   cells=80, M=2, r=0.8 -> 76
#   cells=200, M=2, r=0.8 -> 183
# Hypothesis: capacity = n at which alive(n) = n, taking the LARGEST such n
# below the saturation point. alive(n) < n for all n >= 3 when j=2, so there
# is no such n. Therefore capacity is NOT a fixed point of alive.
# Alternative: capacity is where the *slope* of alive crosses 1.
for cells in (40, 80, 200):
    print(f"--- cells={cells} ---")
    prev = None
    for n in range(1, 40 * cells + 1):
        a = alive(n, cells, 2.0, 0.8)
        if prev is not None and a - prev < 1.0:
            print(f"  slope<1 first at n={n}: alive {prev:.2f} -> {a:.2f} (delta {a-prev:.3f})")
            break
        prev = a
