# FINDING: `%` on `ℝ` is zero, and the "fold" never folded anything

Date: 2026-11-12
Status: proved (`laws/Medium/FoldPeriodic.lean`), build green (18324 jobs)

## What was believed

`laws/Legacy/Convergence2.lean` carried a `sorry` on `fold_identifies`. The
claim was that the expression

```
fold B x = B - |((x + B) % (4B) + 4B) % (4B) - 2B|
```

folds `x` into the interval `[-B, B]`, i.e. it is a periodic wrap-around.

## What is true

`%` on a field is **not** a periodic remainder. It is
`Field.toEuclideanDomain` (priority 100, `Mathlib/Algebra/EuclideanDomain/Field.lean`),
whose remainder is

```
remainder a b = a - a * b / b
```

For `b ≠ 0` this is `a - a = 0`. So:

> **`a % b = 0` for every `a` and every `b ≠ 0` in any field.**

Proved as `mod_field_eq_zero` in `laws/Medium/FoldPeriodic.lean`.

Consequently the legacy fold is a **constant**:

```
fold B x = B - |0 - 2B| = B - 2B = -B      (for 0 < B)
```

Proved as `fold_collapse`. It did not fold, it did not depend on `x`, and it did
not depend on anything except the sign of `B`.

## Why this matters more than a single `sorry`

The `sorry` was hiding an **empty definition**. A theorem "proved" about it
would have been vacuously true and completely useless. This is the third
instance in this project of a statement that compiles but says nothing
(see `LESSONS.md`).

It is also a trap that is easy to fall into: `%` *looks* like `mod` from
Python/C, and on `ℤ` it does behave that way (`Int.emod`). On `ℝ` it does not.
The type checker will not warn you.

## What this does NOT prove

That wrapping into `[-B, B]` is impossible on `ℝ`. It is possible, but it needs
an explicit floor:

```
wrap B x = x - 4 * B * ⌊(x + B) / (4 * B)⌋
```

That is a different expression from the one in `Legacy`, and it is not what `%`
gives. If a future file needs wrapping, it must use the floor form and prove
`-B ≤ wrap B x ∧ wrap B x < B` explicitly.

## Reproduce

```bash
cd laws
lake build Medium.FoldPeriodic     # 0 errors
```

Theorems: `mod_field_eq_zero`, `real_mod_eq_zero`, `fold_collapse`.

## The `sorry` in `Legacy/Convergence2.lean:64`

It stays a `sorry`, but now with a reason: **the statement is false**. It is not
an unfinished proof, it is a refuted claim. The honest action would be to delete
the theorem, not to prove it. It is left in place with this note because the
legacy file is not imported by `Medium.lean` and deleting it would hide the
lesson.
