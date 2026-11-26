//! A compartment: energy, a paid boundary, and a repair that is itself a state.
//!
//! `GOAL.md` §1a and the notes behind `I-018`/`I-019` name the hole this module fills: in every
//! world so far repair was a **rate** the organism simply had. Repair capacity that can itself
//! be worn down by the load it repairs is what turns "two ways to die" from a slogan into a
//! mechanism:
//!
//! ```text
//! capacity    c' = (C0 - c)/tau - gamma * D * c     relaxed toward C0, suppressed by the damage load
//! boundary    q' = -decay * q + repair              repair is capped by capacity AND paid for
//! death       c <= c_min                            collapse: the repair system itself failed
//!            q <= q_min, energy-bound               starvation: the border could not be paid for
//!            q <= q_min, capacity-bound              fell apart: repair too weak by construction
//! ```
//!
//! PREDICTION, before the code (`C0=1, Cmin=0.2, tau=20, D=1`, `I-018`/`I-019` numbers):
//!   (a) the stationary capacity is `C* = C0/(1 + tau*gamma*D)` exactly;
//!   (b) the collapse floor is crossed at `gamma* = (C0 - Cmin)/(tau*D*Cmin) = 0.2`: below it the
//!       compartment lives for every repair price, above it no price saves it;
//!   (c) at `gamma = 0` a repair cheaper than `surplus/(decay*q_min) = 25` holds forever and
//!       a dear one (`cR = 30`, cost `1.5/step` at the floor) starves: the SAME grid holds both
//!       ways to die, and they are different cells.
//!
//! Nothing here touches `Life`, `organ` or `skin`: it is a small world of its own, measured on
//! its own, and every number measured before keeps its bits.

/// How the compartment is built. All rates are per step.
#[derive(Debug, Clone, Copy)]
pub struct CompartmentRules {
    /// Capacity the repair system relaxes toward when unloaded.
    pub c0: f64,
    /// Relaxation time of capacity.
    pub tau: f64,
    /// Suppression of capacity by the damage load (`I-018`).
    pub gamma: f64,
    /// Standing damage load (kept constant here; `Life` couples it to state).
    pub damage_load: f64,
    /// Below this the repair system has collapsed.
    pub c_min: f64,
    /// Fraction of boundary integrity lost each step.
    pub q_decay: f64,
    /// Below this the boundary has fallen apart.
    pub q_min: f64,
    /// Energy per unit of integrity repaired (`cR`).
    pub repair_cost: f64,
    /// Max repair per step per unit of capacity.
    pub repair_scale: f64,
    /// Energy taken in each step.
    pub income: f64,
    /// Energy paid to exist, before any repair.
    pub maintenance: f64,
}

/// The stationary capacity of `I-018`: `C0 / (1 + tau*gamma*D)`.
pub fn stationary_capacity(c0: f64, tau: f64, gamma: f64, damage: f64) -> f64 {
    let denom = 1.0 + tau * gamma * damage;
    if denom <= 0.0 {
        return c0;
    }
    c0 / denom
}

/// The collapse threshold of `I-018`: `gamma* = (C0 - Cmin)/(tau*D*Cmin)`.
pub fn collapse_gamma(c0: f64, c_min: f64, tau: f64, damage: f64) -> f64 {
    if tau <= 0.0 || damage <= 0.0 || c_min <= 0.0 {
        return f64::INFINITY;
    }
    (c0 - c_min) / (tau * damage * c_min)
}

/// The affordable repair price of `I-019`: with surplus `s` per step, holding the border at
/// integrity `q` costs `cR * decay * q`, so the binding price is `s / (decay * q)`.
pub fn affordable_repair(surplus: f64, q_decay: f64, q: f64) -> f64 {
    if q_decay <= 0.0 || q <= 0.0 {
        return f64::INFINITY;
    }
    surplus / (q_decay * q)
}

/// How the compartment died. Two of the three are the two ways to die of `I-019`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DeathMode {
    /// Repair capacity collapsed under its own load (`I-018`).
    Collapse,
    /// The boundary could not be paid for: energy was the binding constraint.
    Starved,
    /// The boundary fell apart with capacity to spare: repair too weak by construction.
    FellApart,
}

/// A compartment: one boundary, one budget, one repair system that can be worn down.
#[derive(Debug, Clone)]
pub struct Compartment {
    pub energy: f64,
    pub q: f64,
    pub c: f64,
    pub steps: usize,
    /// How often the repair cap (capacity) was the binding constraint.
    pub cap_bound: usize,
    /// How often affordability (energy) was the binding constraint.
    pub energy_bound: usize,
    pub death: Option<DeathMode>,
}

impl Compartment {
    pub fn born(rules: &CompartmentRules, energy0: f64) -> Self {
        Self {
            energy: energy0,
            q: 1.0,
            c: rules.c0,
            steps: 0,
            cap_bound: 0,
            energy_bound: 0,
            death: None,
        }
    }

    pub fn alive(&self) -> bool {
        self.death.is_none()
    }

    /// One step. Deaths are attributed by mechanism, not by convenience: capacity collapse,
    /// unaffordable repair, or repair too weak by construction.
    pub fn step(&mut self, r: &CompartmentRules) {
        if !self.alive() {
            return;
        }
        // repair capacity: relaxed toward C0, suppressed by the damage load
        self.c += (r.c0 - self.c) / r.tau - r.gamma * r.damage_load * self.c;
        if self.c < 0.0 {
            self.c = 0.0;
        }
        // the budget
        self.energy += r.income - r.maintenance;
        // the boundary decays by itself
        self.q *= 1.0 - r.q_decay;
        // repair: what is missing, what capacity allows, what energy pays for
        let missing = (1.0 - self.q).max(0.0);
        let cap = r.repair_scale * self.c;
        let affordable = if r.repair_cost > 0.0 {
            (self.energy / r.repair_cost).max(0.0)
        } else {
            f64::INFINITY
        };
        if missing > 0.0 {
            if cap < missing && cap <= affordable {
                self.cap_bound += 1;
            }
            if affordable < missing && affordable < cap {
                self.energy_bound += 1;
            }
        }
        let done = missing.min(cap).min(affordable).max(0.0);
        self.energy -= done * r.repair_cost;
        if self.energy < 0.0 {
            self.energy = 0.0;
        }
        self.q = (self.q + done).min(1.0);
        if self.q >= 1.0 - 1e-12 {
            self.q = 1.0;
        }
        self.steps += 1;
        // deaths, in order of mechanism
        if self.c <= r.c_min {
            self.death = Some(DeathMode::Collapse);
        } else if self.q <= r.q_min {
            if self.energy_bound > self.cap_bound {
                self.death = Some(DeathMode::Starved);
            } else {
                self.death = Some(DeathMode::FellApart);
            }
        }
    }

    /// Run for `n` steps or until death.
    pub fn run(&mut self, r: &CompartmentRules, n: usize) {
        for _ in 0..n {
            if !self.alive() {
                return;
            }
            self.step(r);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rules(gamma: f64, repair_cost: f64) -> CompartmentRules {
        CompartmentRules {
            c0: 1.0,
            tau: 20.0,
            gamma,
            damage_load: 1.0,
            c_min: 0.2,
            q_decay: 0.05,
            q_min: 0.2,
            repair_cost,
            repair_scale: 1.0,
            income: 0.3,
            maintenance: 0.05,
        }
    }

    /// (a) the stationary capacity is the closed form of I-018.
    #[test]
    fn stationary_capacity_matches_theory() {
        let r = rules(0.05, 1.0);
        let mut w = Compartment::born(&r, 1.0);
        // capacity alone: freeze the boundary and the budget noise
        w.q = 1.0;
        for _ in 0..400 {
            let c = w.c;
            w.c += (r.c0 - c) / r.tau - r.gamma * r.damage_load * c;
        }
        let theory = stationary_capacity(r.c0, r.tau, r.gamma, r.damage_load);
        assert!(
            (w.c - theory).abs() < 1e-9,
            "capacity {} vs theory {}",
            w.c,
            theory
        );
    }

    /// (b) below the collapse threshold every price lives; above it none does.
    #[test]
    fn collapse_threshold_is_sharp() {
        let g_star = collapse_gamma(1.0, 0.2, 20.0, 1.0);
        assert!((g_star - 0.2).abs() < 1e-12, "gamma* = {}", g_star);
        let r = rules(0.15, 8.0);
        let mut w = Compartment::born(&r, 1.0);
        w.run(&r, 4000);
        assert!(w.alive(), "gamma=0.15 must live, died {:?}", w.death);
        let r = rules(0.3, 0.25);
        let mut w = Compartment::born(&r, 1.0);
        w.run(&r, 4000);
        assert_eq!(w.death, Some(DeathMode::Collapse), "gamma=0.3 must collapse");
    }

    /// (c) at gamma = 0 a cheap repair holds and a dear one starves: two ways to die, one grid.
    #[test]
    fn two_ways_to_die() {
        let r = rules(0.0, 1.0);
        let mut w = Compartment::born(&r, 1.0);
        w.run(&r, 4000);
        assert!(w.alive(), "gamma=0, cR=1 must live, died {:?}", w.death);
        let r = rules(0.0, 30.0);
        let mut w = Compartment::born(&r, 1.0);
        w.run(&r, 4000);
        assert_eq!(w.death, Some(DeathMode::Starved), "gamma=0, cR=30 must starve");
    }

    /// repair too weak by construction: the border falls with capacity and budget to spare.
    #[test]
    fn fell_apart_when_repair_scale_is_zero() {
        let mut r = rules(0.0, 1.0);
        r.repair_scale = 0.0;
        let mut w = Compartment::born(&r, 1.0);
        w.run(&r, 4000);
        assert_eq!(w.death, Some(DeathMode::FellApart));
    }

    /// the affordable price of I-019 matches the starvation edge: a repair is unaffordable
    /// exactly when even q_min cannot be held, i.e. cR > surplus/(decay * q_min) = 25 here.
    #[test]
    fn affordable_repair_bounds_the_starvation_edge() {
        // surplus 0.25, decay 0.05, q_min 0.2: binding price at the floor is 25.0
        let p = affordable_repair(0.25, 0.05, 0.2);
        assert!((p - 25.0).abs() < 1e-9, "p={}", p);
        let r = rules(0.0, 20.0);
        let mut w = Compartment::born(&r, 1.0);
        w.run(&r, 8000);
        assert!(w.alive(), "cR=20 must live (q* = 0.25), died {:?}", w.death);
        let r = rules(0.0, 30.0);
        let mut w = Compartment::born(&r, 1.0);
        w.run(&r, 8000);
        assert_eq!(w.death, Some(DeathMode::Starved), "cR=30 must starve, died {:?}", w.death);
    }
}
