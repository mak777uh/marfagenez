//! A skin: integrity that decays by itself and can be held only by paying for it.
//!
//! Every world in this project so far had, at most, a counter that kills: `damage` grows and at one it is
//! over. Nothing in the model could be held **better or worse** - a form could keep a size, but a stone keeps
//! its size too. `GOAL.md` §1a calls the missing thing a skin: a boundary that is a **state**, maintained
//! against decay.
//!
//! This module is that state, alone and small:
//!
//! ```text
//! each step   q <- q * (1 - decay)          integrity falls by itself
//! repair      q <- min(1, q + u)            and costs repair_cost * u
//! death       q <= q_min                    it fell apart
//! the decision  u, chosen from the organism's own state
//! ```
//!
//! Arithmetic before the code (`docs/DESIGN-skin.md`):
//!
//! * without repair the lifetime is `ln(q_min)/ln(1 - decay)` exactly;
//! * with a constant `u` the steady value is `q* = u / decay`, so holding needs `u >= decay * q_min`, and
//!   that costs `repair_cost * decay * q_min` a step - a **third term** in the maintenance boundary.
//!
//! Nothing here touches `Life`: it is a second small world in the same crate, and every number measured
//! before it existed keeps its bits.

/// What the medium and the body cost.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SkinRules {
    /// Fraction of the integrity lost each step.
    pub decay: f64,
    /// Below this the form has fallen apart.
    pub q_min: f64,
    /// Energy per unit of integrity repaired.
    pub repair_cost: f64,
    /// Energy taken from the medium each step.
    pub income: f64,
    /// Energy paid simply to stay in place.
    pub maintenance: f64,
}

impl SkinRules {
    /// The integrity a form holds if it repairs at `u` every step: `u / decay`.
    pub fn steady_integrity(&self, u: f64) -> f64 {
        if self.decay <= 0.0 {
            return 1.0;
        }
        (u / self.decay).min(1.0)
    }

    /// The repair intensity needed to hold at least `q_min`.
    pub fn u_min(&self) -> f64 {
        self.decay * self.q_min
    }

    /// What holding costs per step: the third term of the maintenance boundary.
    pub fn skin_cost(&self) -> f64 {
        self.repair_cost * self.u_min()
    }

    /// Lifetime without repair: `ln(q_min / q0) / ln(1 - decay)`, rounded down to a whole step.
    pub fn bare_lifetime(&self, q0: f64) -> usize {
        if self.decay <= 0.0 || self.decay >= 1.0 || q0 <= self.q_min {
            return 0;
        }
        let n = (self.q_min / q0).ln() / (1.0 - self.decay).ln();
        n.floor() as usize
    }
}

/// One form, its integrity and its energy.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Skin {
    pub q: f64,
    pub energy: f64,
    pub alive: bool,
    pub steps: usize,
    /// How much integrity has been repaired in total, for the record.
    pub repaired: f64,
}

impl Skin {
    pub fn new(q0: f64, energy: f64) -> Option<Self> {
        if !(q0.is_finite() && q0 > 0.0 && q0 <= 1.0) {
            return None;
        }
        if !(energy.is_finite() && energy >= 0.0) {
            return None;
        }
        Some(Self {
            q: q0,
            energy,
            alive: true,
            steps: 0,
            repaired: 0.0,
        })
    }

    /// One step, repairing at intensity `u` as far as the state allows.
    ///
    /// The repair is limited by three things: how much integrity is missing, how much energy there is, and
    /// the requested intensity itself. A form that cannot pay repairs less and therefore decays - that is the
    /// whole point of a skin, and it is why this cannot be a counter.
    pub fn step(&mut self, rules: &SkinRules, u: f64) -> bool {
        if !self.alive {
            return false;
        }
        self.steps += 1;
        self.energy += rules.income - rules.maintenance;

        // the decay happens first: the step is a fall that may be caught, not a catch that may fall
        self.q *= 1.0 - rules.decay;

        if u > 0.0 && self.energy > 0.0 && rules.repair_cost > 0.0 {
            let missing = (1.0 - self.q).max(0.0);
            let affordable = self.energy / rules.repair_cost;
            let done = u.min(missing).min(affordable).max(0.0);
            self.energy = (self.energy - done * rules.repair_cost).max(0.0);
            self.q = (self.q + done).min(1.0);
            self.repaired += done;
        }

        if self.q <= rules.q_min || self.energy < 0.0 {
            self.alive = false;
            self.q = self.q.max(0.0);
            self.energy = self.energy.max(0.0);
        }
        self.alive
    }
}

/// Runs one form for at most `horizon` steps and returns it.
pub fn run(rules: SkinRules, q0: f64, energy: f64, u: f64, horizon: usize) -> Skin {
    let mut s = Skin::new(q0, energy).expect("valid start");
    for _ in 0..horizon {
        if !s.step(&rules, u) {
            break;
        }
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rules() -> SkinRules {
        SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 10.0,
            income: 1.0,
            maintenance: 0.6,
        }
    }

    #[test]
    fn the_arithmetic_matches_the_design() {
        let r = rules();
        assert!((r.u_min() - 0.01).abs() < 1e-12);
        assert!((r.skin_cost() - 0.1).abs() < 1e-12);
        // ln(0.2)/ln(0.95) = 31.4, so thirty-one whole steps are survived
        assert_eq!(r.bare_lifetime(1.0), 31);
        assert!((r.steady_integrity(0.02) - 0.4).abs() < 1e-12);
    }

    #[test]
    fn without_repair_the_form_dies_on_the_arithmetic_step() {
        let r = rules();
        let s = run(r, 1.0, 10.0, 0.0, 1000);
        assert!(!s.alive);
        assert_eq!(s.steps, r.bare_lifetime(1.0) + 1, "one step past the last whole one");
    }

    #[test]
    fn at_the_threshold_it_holds_forever() {
        let r = rules();
        let s = run(r, 1.0, 10.0, r.u_min(), 100_000);
        assert!(s.alive, "u = d*q_min should hold the integrity");
        assert!((s.q - r.steady_integrity(r.u_min())).abs() < 0.02, "q* = u/d");
    }

    #[test]
    fn below_the_threshold_the_lifetime_is_finite_and_grows() {
        let r = rules();
        let slow = run(r, 1.0, 10.0, 0.008, 100_000);
        let slower = run(r, 1.0, 10.0, 0.0095, 100_000);
        assert!(!slow.alive && !slower.alive);
        assert!(
            slower.steps > slow.steps,
            "a smaller gap should live longer: {} vs {}",
            slower.steps,
            slow.steps
        );
    }

    /// The lifetime below the threshold is logarithmic, not hyperbolic.
    ///
    /// `FINDING-258` predicted `1/(d*q_min - u)` and was wrong by a factor of five to twenty-three: the
    /// integrity moves from `q0` towards `q* = u/decay`, and death is where that path crosses `q_min`, so the
    /// time is In((q_min - q*) / (q0 - q*)) / In(1 - decay).
    #[test]
    fn below_the_threshold_the_lifetime_is_logarithmic() {
        let r = rules();
        for u in [0.005, 0.008, 0.009, 0.0095] {
            let star = u / r.decay;
            let predicted = ((r.q_min - star) / (1.0 - star)).ln() / (1.0 - r.decay).ln();
            let s = run(r, 1.0, 10.0, u, 100_000);
            assert!(!s.alive);
            assert!(
                (s.steps as f64 - predicted).abs() <= 1.5,
                "u = {u}: lived {} steps, the logarithmic law predicts {predicted:.1}",
                s.steps
            );
        }
    }

    #[test]
    fn the_skin_moves_the_maintenance_boundary() {
        let mut r = rules();
        // free surplus 0.37 against a skin cost of 0.1: affordable
        assert!(run(r, 1.0, 10.0, r.u_min(), 10_000).alive);
        // free surplus 0.02: maintenance is paid, the skin is not, and the world dies
        r.maintenance = 0.95;
        let s = run(r, 1.0, 10.0, r.u_min(), 10_000);
        assert!(!s.alive, "a form paying 0.95 cannot also keep its skin");
    }
}
