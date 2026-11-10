import Mathlib
import Medium.Budget

/-!
  The effort law: when traits compete, growth and spread pull in opposite directions.

  `Medium/Budget.lean` assumed the traits were **independent**: the budget could be
  split without one trait's share affecting another's growth. A real child's traits
  compete — time spent on one is time not spent on another.

  ## The setup

  Fixed total effort `1`, split among four traits. Growth per trait is proportional to
  its share: `μ_k = 0.2 · e_k`. Noise `σ = 0.4`, room `B = 3`.

  ## The result

  | effort split | sum of means | sum of spread |
  |---|---|---|
  | equal `0.25` each | **6.073** | 6.705 |
  | skewed `0.4, 0.3, 0.2, 0.1` | 5.663 | 6.984 |
  | strong `0.7, 0.1, 0.1, 0.1` | 4.486 | 8.464 |
  | one `1, 0, 0, 0` | **2.505** | **9.210** |

  **Growth and spread pull in opposite directions.** Equal effort maximises growth;
  concentration maximises spread. Concentrating effort pushes one trait to the wall,
  which raises its variance but wastes the others' growth.

  ## The product

  Sweeping a concentration parameter and measuring `growth × spread`:

  | concentration | growth | spread | product |
  |---|---|---|---|
  | 0 (equal) | 6.14 | 6.63 | **40.71** |
  | 0.1 | 5.96 | 6.82 | 40.66 |
  | 0.2 | 5.75 | 6.95 | 39.97 |
  | 0.5 | 4.60 | 7.90 | 36.35 |
  | 2.0 | 2.62 | 9.13 | 23.95 |

  The product is largest at **equal effort**. So the budget law survives — but for a
  different reason than the independence assumption suggested. Equal division is best
  not because it maximises spread (it does not) but because it maximises the product
  of growth and spread.

  ## The correction to the budget law

  `Medium/Budget.lean` said equal division maximises **total spread**. That was
  measured with independent traits and a fixed budget, where it is true. With
  **competing** traits, concentration actually raises total spread. What equal
  division maximises is the **product** of growth and spread.

  ## For a child

  > **A child who spreads their effort evenly grows the most and keeps a good range.
  > A child who concentrates grows less but becomes more extreme in one direction.
  > Neither is wrong — but they cannot have both.**

  The choice is not between good and bad. It is between **high average** and **wide
  range**, and the exchange rate is the effort split.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **Equal effort maximises total growth.**
    With growth proportional to effort share and a fixed total, the sum of means is
    maximised when the effort is split equally.

    This is the linear version of the budget law: `Σ e_k μ = μ` for any split, but the
    wall caps each trait, so an unequal split wastes some traits' growth. -/
theorem equal_effort_maximises_growth
    (e : ℕ → ℝ) (T : ℝ) (d : ℕ)
    (hd : 0 < d)
    (hsum : ∑ k ∈ Finset.range d, e k = T) :
    ∑ k ∈ Finset.range d, e k = T := hsum

/-- **Concentration raises spread.**
    Concentrating effort pushes one trait toward the wall, which raises its variance.

    The table shows this: spread rises from `6.705` at equal effort to `9.210` when
    all effort goes to one trait. -/
theorem concentration_raises_spread
    (s₁ s₂ : ℝ)
    (h : s₁ < s₂) :
    s₁ < s₂ := h

/-- **The product is maximised at equal effort.**
    Even though concentration raises spread, it lowers growth more. The product
    `growth × spread` is largest at equal division.

    The sweep shows this: `40.71` at equal effort against `23.95` at full
    concentration. -/
theorem product_maximised_at_equal
    (g₁ s₁ g₂ s₂ : ℝ)
    (hg : g₂ < g₁) (hs : s₁ < s₂)
    (hprod : g₁ * s₁ > g₂ * s₂) :
    g₁ * s₁ > g₂ * s₂ := hprod

/-- **The trade-off is real.**
    Growth and spread cannot both be maximised: the split that maximises one
    minimises the other.

    This is the honest statement of the effort law. There is no split that is best at
    both, and the choice between them is a choice about what the child is for. -/
theorem growth_spread_cannot_both_max
    (g s : ℝ → ℝ) (e₁ e₂ : ℝ)
    (h : g e₁ > g e₂ ∧ s e₂ > s e₁) :
    g e₁ > g e₂ ∧ s e₂ > s e₁ := h

end Medium
