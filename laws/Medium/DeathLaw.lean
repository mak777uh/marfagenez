/-
  Medium/DeathLaw.lean

  When does a moving organism die?

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

  This file states the law and proves the two things that make it a law rather
  than a curve fit: the threshold is exactly `income - damage*repair`, and below
  it the steady energy is exactly `E_max - (maintenance + damage*repair)`.

  What this file does NOT prove: that an organism always finds a full cell. At
  higher crowding the take per step is less than `income`, the net is smaller,
  and the threshold moves down. The law below is the threshold in the regime
  where a mover can always find a full cell.
-/

import Mathlib

namespace Medium

/-- The per-step net of a moving organism that always finds a full cell.

    `income` is what a full cell gives, `maintenance` is what staying alive
    costs, and `damage_rate * repair_cost` is what clearing one step's damage
    costs. -/
def netPerStep (income maintenance damageRate repairCost : ℝ) : ℝ :=
  income - maintenance - damageRate * repairCost

/-- The maintenance at which a mover's net per step is exactly zero. -/
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

/-- The steady energy of a mover held at the cap.

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

/-- **The two thresholds are not the same number, and the field shows the
    moving one.**

    A sedentary organism eats its own cell down to `c* = M - income*(1-r)/r`
    (see `Medium/Field.lean` and `Medium/Capacity.lean`). Its threshold is
    `c* - damage*repair`. The mover's threshold is `income - damage*repair`.
    With income = 1.2, M = 2.0, r = 0.8, damage = 0.02, repair = 1.5 these are
    1.17 and 1.67.

    The measured collapse at 1.170068 is the mover's. -/
theorem mover_threshold_below_sitter_threshold
    (income cStar damageRate repairCost : ℝ)
    (h : income < cStar) :
    deathThreshold income damageRate repairCost <
      deathThreshold cStar damageRate repairCost := by
  unfold deathThreshold
  linarith

end Medium
