/-
  Medium/DeathLaw.lean

  When does an organism die?

  The organisms in this model do not sit on one cell and eat it down. With
  `sighted` and a non-zero read budget they move to a cell they have not eaten
  and take a full `income` there. A mover's cycle is therefore:

    1. take:    energy <- min(energy + income, E_max)
    2. maintain: energy <- energy - maintenance
    3. repair:   energy <- energy - damage_rate * repair_cost

  Step 1 is truncated at the cap, so an organism at the cap gains nothing from
  the take and loses `maintenance + damage_rate * repair_cost` per step. The
  next take refills it to the cap again. The cycle nets

      income - maintenance - damage_rate * repair_cost

  per step, and the organism survives exactly when that is positive.

  Measured (checks/exp68_bisect_the_death_threshold.py): with income = 1.2,
  damage_rate = 0.02, repair_cost = 1.5, the population collapses at
  maintenance = 1.170068, and income - damage_rate * repair_cost = 1.17.

  **The sitter takes the same amount as the mover.** An earlier version of this
  file said a sedentary organism's threshold was `c* - damage*repair` = 1.67,
  because it eats its own cell down to `c* = 1.7`. That subtracted a LEVEL from
  a COST — litres from litres per step. The amount a sitter takes is
  `min(income, c*)`, and with income = 1.2 and c* = 1.7 that is 1.2, exactly a
  mover's take. EXP-69 measured a `stay` population collapsing at 1.170635, the
  same place as a mover, and EXP-70 showed the 0.000635 is the observation
  window (see `windowOffset` below), not a difference between the policies.

  The two regimes separate only when the cell cannot supply a full income at
  its own fixed point, `c* < income`, which at these settings is `t > 3.2`.

  What this file does NOT prove: that an organism always finds a full cell. At
  higher crowding the take per step is less than `income`, the net is smaller,
  and the threshold moves down. The law below is the threshold in the regime
  where a mover can always find a full cell.
-/

import Mathlib

namespace Medium

/-- The per-step net of an organism that always takes a full `income`.

    `income` is what a full cell gives, `maintenance` is what staying alive
    costs, and `damage_rate * repair_cost` is what clearing one step's damage
    costs. -/
def netPerStep (income maintenance damageRate repairCost : ℝ) : ℝ :=
  income - maintenance - damageRate * repairCost

/-- The maintenance at which the net per step is exactly zero. -/
def deathThreshold (income damageRate repairCost : ℝ) : ℝ :=
  income - damageRate * repairCost

/-- **The threshold is the zero of the net.** This is what the bisection
    measured: the population collapses where the net changes sign. -/
theorem net_zero_iff_maintenance_eq_threshold
    (income maintenance damageRate repairCost : ℝ) :
    netPerStep income maintenance damageRate repairCost = 0 ↔
      maintenance = deathThreshold income damageRate repairCost := by
  unfold netPerStep deathThreshold
  constructor
  · intro h
    linarith
  · intro h
    subst h
    ring

/-- **Below the threshold the net is positive**, so the organism gains energy
    each step until it reaches the cap. -/
theorem net_pos_of_maintenance_lt_threshold
    (income maintenance damageRate repairCost : ℝ)
    (h : maintenance < deathThreshold income damageRate repairCost) :
    0 < netPerStep income maintenance damageRate repairCost := by
  unfold netPerStep deathThreshold at *
  linarith

/-- **Above the threshold the net is negative**, so the organism loses energy
    every step and death is certain. -/
theorem net_neg_of_threshold_lt_maintenance
    (income maintenance damageRate repairCost : ℝ)
    (h : deathThreshold income damageRate repairCost < maintenance) :
    netPerStep income maintenance damageRate repairCost < 0 := by
  unfold netPerStep deathThreshold at *
  linarith

/-- The steady energy of an organism held at the cap.

    At the cap the take is truncated, so the organism loses
    `maintenance + damage_rate * repair_cost` per step and the next take refills
    it. The energy it is seen at is therefore `E_max` minus that loss. -/
def steadyEnergyAtCap (eMax maintenance damageRate repairCost : ℝ) : ℝ :=
  eMax - (maintenance + damageRate * repairCost)

/-- **The measured energy is the cap minus the cost.** EXP-67 measured
    9.2700, 9.1700, 9.0700, 8.9700 at maintenance 0.7, 0.8, 0.9, 1.0 with
    E_max = 10; this says why. -/
theorem steadyEnergyAtCap_eq
    (eMax maintenance damageRate repairCost : ℝ) :
    steadyEnergyAtCap eMax maintenance damageRate repairCost =
      eMax - maintenance - damageRate * repairCost := by
  unfold steadyEnergyAtCap
  ring

/-- **The threshold is the maintenance at which the steady energy at the cap
    would be exactly the cap minus the income.**

    This is the bridge between the two measurements: the energy the field
    settles at and the maintenance at which the population collapses are the
    same statement. -/
theorem threshold_iff_steady_energy_eq
    (eMax income maintenance damageRate repairCost : ℝ) :
    maintenance = deathThreshold income damageRate repairCost ↔
      steadyEnergyAtCap eMax maintenance damageRate repairCost =
        eMax - income := by
  unfold deathThreshold steadyEnergyAtCap
  constructor
  · intro h
    subst h
    ring
  · intro h
    linarith
/-- **Steps to death from the cap when the net is negative.**

    With a deficit `d = maintenance + damage*repair - income` per step starting
    from `E_max`, the organism is dead after `E_max / d` steps. For
    maintenance = 1.2, E_max = 10, income = 1.2, damage = 0.02, repair = 1.5
    this is 333.33 steps. -/
noncomputable def stepsToDeath (eMax income maintenance damageRate repairCost : ℝ) : ℝ :=
  eMax / (maintenance + damageRate * repairCost - income)

/-- The deficit is positive exactly when the maintenance is above the
    threshold, so `stepsToDeath` is positive exactly in the dying regime. -/
theorem stepsToDeath_pos_iff
    (eMax income maintenance damageRate repairCost : ℝ)
    (hE : 0 < eMax) :
    0 < stepsToDeath eMax income maintenance damageRate repairCost ↔
      deathThreshold income damageRate repairCost < maintenance := by
  unfold stepsToDeath deathThreshold
  rw [div_pos_iff]
  constructor
  · rintro (h | h)
    · linarith
    · linarith
  · intro h
    left
    exact ⟨hE, by linarith⟩

/-- **What a sitter takes is not the level it sits on.**

    A sedentary organism eats its own cell down to `c* = M - income*(1-r)/r`.
    The amount it takes per step is `min(income, c*)`, not `c*`. This is the
    definition that fixes the units error: a level is compared against
    `income`, and a cost is subtracted from the take. -/
def sitterTake (income cStar : ℝ) : ℝ := min income cStar

/-- **When the cell can supply a full income, a sitter takes exactly what a
    mover takes.** With income = 1.2 and c* = 1.7 this is 1.2, so the sitter's
    threshold is the mover's threshold, 1.17. -/
theorem sitter_take_eq_income_of_income_le_cStar
    (income cStar : ℝ) (h : income ≤ cStar) :
    sitterTake income cStar = income := by
  unfold sitterTake
  exact min_eq_left h

/-- **The sitter's threshold is the mover's threshold when the cell is rich
    enough.** This is the statement EXP-69 measured: `stay` collapsed at
    1.170635 and `sighted` at 1.170068, both the mover's 1.17. -/
theorem sitter_threshold_eq_mover_threshold
    (income cStar damageRate repairCost : ℝ) (h : income ≤ cStar) :
    deathThreshold (sitterTake income cStar) damageRate repairCost =
      deathThreshold income damageRate repairCost := by
  rw [sitter_take_eq_income_of_income_le_cStar income cStar h]

/-- **When the cell is too poor to supply a full income, the sitter's threshold
    is lower than the mover's.** This is the regime the earlier version of this
    file mistook for the ordinary one: it holds only when `c* < income`, which
    at M = 2.0, r = 0.8, income = 1.2 means `t > 3.2`. -/
theorem sitter_threshold_lt_mover_threshold_of_cStar_lt_income
    (income cStar damageRate repairCost : ℝ) (h : cStar < income) :
    deathThreshold (sitterTake income cStar) damageRate repairCost <
      deathThreshold income damageRate repairCost := by
  unfold deathThreshold sitterTake
  rw [min_eq_right (le_of_lt h)]
  linarith

/-- **The observation window adds `E_0 / steps` to the measured threshold.**

    Every organism starts at energy `E_0` and loses `deficit` per step. It is
    alive when the trace is read at step `steps` exactly when
    `steps * deficit < E_0`, that is when `deficit < E_0 / steps`. So the
    maintenance at which the last organism is seen alive is the true threshold
    plus `E_0 / steps`.

    This is a property of the apparatus, not of the medium, which is why
    EXP-69 measured the SAME 0.000635 offset at three different values of
    `damage*repair`. EXP-70 confirmed it: `offset * steps` was 4.9902, 5.0586
    and 4.9609 at 8000, 16000 and 32000 steps, against `E_0 = 5.0`. -/
noncomputable def windowOffset (e0 steps : ℝ) : ℝ := e0 / steps

/-- **The offset halves when the run doubles.** This is the shape EXP-70 saw:
    0.000624, 0.000316, 0.000155 at 8000, 16000, 32000 steps. -/
theorem windowOffset_halves (e0 steps : ℝ) (h : steps ≠ 0) :
    windowOffset e0 (2 * steps) = windowOffset e0 steps / 2 := by
  unfold windowOffset
  field_simp

/-- **The offset times the step count is the starting energy**, independent of
    the step count. This is the quantity EXP-70 found constant at 5.0. -/
theorem windowOffset_mul_steps (e0 steps : ℝ) (h : steps ≠ 0) :
    windowOffset e0 steps * steps = e0 := by
  unfold windowOffset
  field_simp

/-- **The measured threshold is the true threshold plus the window offset.**
    A measurement that does not subtract this offset reports a threshold that
    drifts with the length of the run. -/
noncomputable def measuredThreshold (income damageRate repairCost e0 steps : ℝ) : ℝ :=
  deathThreshold income damageRate repairCost + windowOffset e0 steps

/-- **The measured threshold tends to the true threshold as the run grows.**
    For any tolerance there is a run long enough that the measurement is within
    it. This is what makes the offset a window and not a law. -/
theorem measuredThreshold_tends_to_threshold
    (income damageRate repairCost e0 : ℝ) (he : 0 < e0) :
    ∀ ε : ℝ, 0 < ε → ∃ steps : ℝ, 0 < steps ∧
      |measuredThreshold income damageRate repairCost e0 steps -
        deathThreshold income damageRate repairCost| < ε := by
  intro ε hε
  refine ⟨2 * e0 / ε, div_pos (by linarith) hε, ?_⟩
  unfold measuredThreshold windowOffset
  have hsteps : 2 * e0 / ε ≠ 0 := ne_of_gt (div_pos (by linarith) hε)
  rw [add_sub_cancel_left, abs_of_pos (div_pos he (div_pos (by linarith) hε))]
  rw [div_lt_iff₀ (div_pos (by linarith) hε)]
  field_simp
  linarith

end Medium
