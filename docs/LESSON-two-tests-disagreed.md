# LESSON: two tests disagreed, and the wrong one was the one with a story

Date: 2026-11-12.

## What happened

`core/tests/threshold_brake.rs` had two tests about the same brake.

- `a_tight_brake_narrows_the_child` asserted `tight < law * 0.9` at limit 0.05.
  It failed: 1.653 vs 1.732, i.e. 0.954.
- `the_brake_is_gradual_not_a_cliff` swept the limit and measured 0.945 at the
  same limit.

The two tests disagreed about the same measurement. The failing one had a
sentence attached to it — "a brake at a small limit cuts most steps, so the
child cannot move far" — and the sentence was the reason it looked right. The
sweep had no sentence.

## The rule

**When two tests disagree, the disagreement is the finding.** Do not pick the
one that failed and relax its threshold to match the other. First ask which
one is measuring the thing it names.

Here the failing test's sentence was wrong in a specific way: the brake cuts
the *step*, but the noise is added every step and is not cut. Cutting the step
to `limit` leaves a lattice of width `2·limit = 0.1`, which is `0.058·law`; the
measured 0.945 is nowhere near that, so the brake is not cutting as the
sentence says either. Both the threshold and the story were wrong.

## What replaced it

Two-sided: the brake narrows the child (`< 0.98·law`) **and** does not collapse
it (`> 0.5·law`). A one-sided `less than` test can be passed by a brake that
does nothing at all, if the constant is loose enough.

## The same shape, same day

`core/tests/time_to_narrow.rs` asserted that a "corrected" estimate
`t* = (B − B/√3)/μ` was closer than the naive `B/μ`. Re-measured:

| push | B/μ | (B−law)/μ | measured |
|---|---|---|---|
| 0.020 | 150 | 63 | 110 |
| 0.050 | 60 | 25 | 32 |
| 0.100 | 30 | 13 | 12 |

The correction is worse at two of three rows. It had been fitted to three
numbers from one seed and then asserted as a law. Both formulas are now gone
from the test; what remains is the bound (`measured < B/μ`) and monotonicity
in the push — the two claims the data actually supports.

`LESSONS.md` lesson 8 is the same error: a parameter fitted to the data cannot
fail to match the data. Here the fitted thing was a formula instead of a
parameter, which made it look like a derivation.

## Check before asserting a formula

1. Does the formula have a derivation, or only a fit?
2. Was it fitted on the same rows the test asserts on?
3. Is the assertion one-sided in a way that a no-op could pass?
4. Does any other test measure the same quantity? If yes, compare the numbers
   before touching either.
