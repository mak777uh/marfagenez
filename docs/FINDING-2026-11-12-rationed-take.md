# FINDING 2026-11-12 — the rationed take is 0.65, not 0.75

## What was wrong

`Medium/Capacity.lean` claimed, in a comment and in two theorems:

    at M = 2, r = 0.8, t = 0.9 the level is 1.55
    the second organism takes 1.55 - 0.9 = 0.75
    0.75 > 0.6 = maintenance, so it lives

The arithmetic is wrong. `1.55 - 0.9 = 0.65`, not `0.75`.

Checked over the rationals in Lean:

    #eval (2 + 2 * (9/10 : ℚ) - 2 * (9/10) / (4/5))        = 31/20
    #eval (2 + 2 * (9/10 : ℚ) - 2 * (9/10) / (4/5)) - 9/10 = 13/20

So `cStar(2) = 1.55` and the second take is `0.65`.

## Why it took 60 patches to find

The theorem was

    theorem rationed_second_lives :
        cStar 2 (4 / 5) 2 (9 / 10) - 1 * (9 / 10) = 3 / 4 := ...

`3/4 = 0.75` is **false**. Every tactic that was tried — `norm_num`, `rw; norm_num`,
`linarith`, `calc`, `Eq.trans (congrArg ...)` — failed, and each failed with a
different error message that looked like a tactic problem:

    unsolved goals ⊢ False
    linarith failed to find a contradiction

Sixty patches were spent on the tactics. The theorem itself was false.

## The lesson

`PROTOCOL.md` §"check the simple before the complex" already says this, and it was
not followed. The order should have been:

1. Evaluate the two sides numerically (`#eval` over `ℚ`, or sympy).
2. Only then look at the tactics.

One `#eval` would have ended this in one step instead of sixty. A Lean error that
says `⊢ False` after `norm_num` is not a tactic problem — it is the arithmetic
saying the goal is not true.

## What is now in the file

    theorem measured_levels :
        cStar 2 (4/5) 2 (4/5) = 8/5 ∧
        cStar 2 (4/5) 1 (4/5) = 9/5 ∧
        cStar 2 (4/5) 2 (9/10) = 31/20

    theorem rationed_second_lives :
        cStar 2 (4/5) 2 (9/10) - 1 * (9/10) = 13/20

    theorem rationed_take_above_maintenance : (13/20 : ℝ) > 6/10

All three compile. `lake build` completes: 18320 jobs, 0 errors.

## The conclusion that does not change

The second organism at `t = 0.9` still lives: `0.65 > 0.6`. The qualitative claim
(rationing does not kill at `t = 0.9`) survives; only the number was wrong. This is
the dangerous kind of error — the story was right and the number was wrong, so the
story kept being told with the wrong number attached.
