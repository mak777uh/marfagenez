"""Integer bounds that do not lose one at exact multiples.

`int(x // y)` looks like "how many times y fits into x", but for floats it is
not: `1.0 // 0.1` is `9.0`, `0.3 // 0.1` is `2.0`, `0.6 // 0.1` is `5.0`.
The floor is applied to a quotient that is already a hair below the integer
because `0.1` is not representable, so an exact multiple reports one less.

Every `k_max` law in this repo is "how many organisms fit", so an off-by-one
there is not cosmetic: it changes the boundary the experiment is measuring.
This module gives the two operations those laws actually need.

Why `1e-9` and not `math.isclose`: the tolerance has to be absolute and tiny,
because the quantities are energies of order 1-100 and the error we are
absorbing is a few ulps of a quotient of that size.
"""

#: Absorbs the float error of a quotient that should be an exact integer.
#: For energies of order 1e2 the error is ~1e-14, so 1e-9 is six orders of
#: magnitude of headroom and still far below any real difference in the model.
EPS = 1e-9


def how_many_fit(total, cost):
    """How many times `cost` fits into `total`, floored, without the off-by-one.

    >>> how_many_fit(1.0, 0.1)
    10
    >>> how_many_fit(0.3, 0.1)
    3
    >>> how_many_fit(0.6, 0.1)
    6
    >>> how_many_fit(0.25, 0.1)
    2
    """
    if cost <= 0:
        raise ValueError(f"cost must be positive, got {cost!r}")
    q = total / cost
    # `+ EPS` only matters when q is within EPS of an integer from below.
    # `int()` truncates toward zero, which equals floor for the q >= 0 this
    # model always has; the explicit floor keeps it right if it ever does not.
    n = int(q + EPS)
    if n > q + EPS:
        n -= 1
    return n


def k_max(total, cost):
    """The capacity law: the cell holds `1 + how_many_fit` organisms.

    One organism eats `cost` from `total`; the rest fit in the remainder.
    """
    return 1 + how_many_fit(total, cost)
