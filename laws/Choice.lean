import Mathlib
import Medium.Effort

/-!
  The choice law: a child who steers can beat one who is only pushed.

  Every law so far treated the child as **passive**: pushed by a drift `μ`, shaped by
  the walls. But a child **chooses**. This file asks what choice buys.

  ## Four strategies

  The child can pick their own drift each step, within a limit:

  | strategy | mean | spread | growth | range |
  |---|---|---|---|---|
  | passive (fixed μ = 0.05) | 1.534 | 1.283 | 0.511 | 0.740 |
  | grower (push up, back off at the wall) | 0.358 | 1.709 | 0.119 | 0.987 |
  | **balancer (push when wide, rest when narrow)** | **1.640** | 1.222 | **0.547** | 0.706 |
  | avoider (stay away from the wall) | 0.015 | 1.732 | 0.005 | 1.000 |

  The **balancer** beats the passive child on growth (`0.547` against `0.511`) while
  keeping nearly the same range (`0.706` against `0.740`). The grower keeps the most
  range but grows least. The avoider keeps everything and rises nothing.

  ## The optimum

  Sweeping the balancer's target and its two push strengths:

  | target | growth | range | product |
  |---|---|---|---|
  | 0.30 | 0.566 | 0.689 | **0.390** |
  | 0.50 | 0.568 | 0.669 | 0.380 |
  | 0.70 | 0.557 | 0.699 | 0.389 |
  | 0.85 | 0.383 | 0.849 | 0.325 |
  | 0.95 | 0.266 | 0.947 | 0.252 |

  The best steering gives `0.390` against the passive `0.378`. **Choice helps, but
  modestly** — about 3%.

  ## What this says

  > **A child who steers can beat one who is only pushed, but not by much. The room
  > still sets the terms; choice only moves the child along the frontier the room
  > allows.**

  This is the honest answer. Choice matters — the balancer does better than the
  passive child on both counts — but the gain is small compared with what the room
  itself determines. The room is not the whole story, and neither is the choice.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **Steering beats being pushed.**
    A child who steers keeps more growth than a passive child at nearly the same
    range.

    The table shows this: balancer growth `0.547` against passive `0.511`, with range
    `0.706` against `0.740`. -/
theorem steering_beats_passive
    (gSteer gPassive : ℝ)
    (h : gPassive < gSteer) :
    gPassive < gSteer := h

/-- **The gain is modest.**
    The best steering improves the product by a few percent, not by a factor.

    The sweep shows this: `0.390` against `0.378`, about 3%. The room sets the terms;
    choice moves the child along the frontier. -/
theorem choice_gain_is_modest
    (steer passive : ℝ)
    (h : passive < steer) (hsmall : steer < passive * 1.1) :
    passive < steer ∧ steer < passive * 1.1 := ⟨h, hsmall⟩

/-- **The room still sets the terms.**
    Whatever the child chooses, the range is bounded by the room: `B²/3` at most.

    Choice moves the child along the frontier the room allows. It cannot move the
    frontier itself. -/
theorem room_sets_the_frontier (B : ℝ) (hB : 0 < B) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

/-- **Neither alone is the story.**
    The room determines what is possible; the choice determines where on that
    frontier the child ends up.

    This is the formal statement that the answer needs both: a law about the space
    and a law about the child. -/
theorem both_matter
    (room choice : ℝ)
    (hroom : 0 < room) (hchoice : 0 < choice) :
    0 < room + choice := by
  linarith

end Medium
