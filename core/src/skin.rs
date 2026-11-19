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

        if u > 0.0 && (self.energy > 0.0 || rules.repair_cost <= 0.0) {
            let missing = (1.0 - self.q).max(0.0);
            let affordable = if rules.repair_cost > 0.0 {
                self.energy / rules.repair_cost
            } else {
                f64::INFINITY
            };
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

/// A population of forms whose repair intensity is **inherited and mutated**.
///
/// `FINDING-258` gave one form a skin and a price for keeping it. The question that makes it a step towards
/// the elephant is whether the intensity of self-maintenance is **chosen by the medium** rather than written
/// by us: a form that repairs more lives longer but grows slower, and which of the two matters is decided by
/// the price.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SkinPopRules {
    pub skin: SkinRules,
    /// Relative spread of the child's repair intensity. Multiplicative, so a lineage that pays nothing can
    /// never produce a descendant that pays something: zero is absorbing.
    pub u_noise: f64,
    /// Absolute spread of the child's repair intensity, added on top. This is what lets maintenance appear
    /// from a population that has none.
    pub u_shift: f64,
    /// Energy needed before a form may divide.
    pub birth_price: f64,
    pub max_population: usize,
}

/// One form in the population.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SkinForm {
    pub q: f64,
    pub energy: f64,
    /// The inherited repair intensity: how much integrity this lineage tries to add each step.
    pub u: f64,
}

/// The population and the record of what it did.
#[derive(Debug, Clone, PartialEq)]
pub struct SkinPop {
    pub rules: SkinPopRules,
    pub forms: Vec<SkinForm>,
    pub births: u64,
    pub deaths: u64,
    pub steps: usize,
}

impl SkinPop {
    pub fn new(rules: SkinPopRules, q0: f64, energy: f64, u0: f64) -> Option<Self> {
        let f = SkinForm { q: q0, energy, u: u0 };
        Some(Self {
            rules,
            forms: vec![f],
            births: 0,
            deaths: 0,
            steps: 0,
        })
    }

    /// Mean inherited repair intensity, or `NaN` when nothing is alive.
    pub fn mean_u(&self) -> f64 {
        if self.forms.is_empty() {
            return f64::NAN;
        }
        self.forms.iter().map(|f| f.u).sum::<f64>() / self.forms.len() as f64
    }

    /// Share of forms that repair at least what the skin needs to hold.
    pub fn maintainers(&self) -> f64 {
        if self.forms.is_empty() {
            return f64::NAN;
        }
        let u_min = self.rules.skin.u_min();
        self.forms.iter().filter(|f| f.u >= u_min).count() as f64 / self.forms.len() as f64
    }

    pub fn step(&mut self, rng: &mut crate::Rng) {
        self.steps += 1;
        let skin = self.rules.skin;

        for f in self.forms.iter_mut() {
            f.energy += skin.income - skin.maintenance;
            f.q *= 1.0 - skin.decay;
            if f.u > 0.0 && (f.energy > 0.0 || skin.repair_cost <= 0.0) {
                let missing = (1.0 - f.q).max(0.0);
                // a free skin is affordable without limit; only a paid one divides by its price
                let affordable = if skin.repair_cost > 0.0 {
                    f.energy / skin.repair_cost
                } else {
                    f64::INFINITY
                };
                let done = f.u.min(missing).min(affordable).max(0.0);
                f.energy = (f.energy - done * skin.repair_cost).max(0.0);
                f.q = (f.q + done).min(1.0);
            }
        }

        let before = self.forms.len();
        self.forms.retain(|f| f.q > skin.q_min && f.energy >= 0.0);
        self.deaths += (before - self.forms.len()) as u64;

        let mut parents: Vec<usize> = Vec::new();
        for (i, f) in self.forms.iter().enumerate() {
            if f.energy >= self.rules.birth_price {
                parents.push(i);
            }
        }
        let room = self.rules.max_population.saturating_sub(self.forms.len());
        for i in parents.into_iter().take(room) {
            let parent = self.forms[i];
            // the inherited intensity is perturbed multiplicatively and stays non-negative
            let noise = 1.0 + (rng.uniform() - 0.5) * 2.0 * self.rules.u_noise;
            let shift = (rng.uniform() - 0.5) * 2.0 * self.rules.u_shift;
            let child = SkinForm {
                q: parent.q,
                energy: self.rules.birth_price,
                u: (parent.u * noise + shift).max(0.0),
            };
            self.forms[i].energy -= self.rules.birth_price;
            self.forms.push(child);
            self.births += 1;
        }
    }
}

/// Runs a population and returns it after `steps`.
pub fn run_pop(rules: SkinPopRules, q0: f64, energy: f64, u0: f64, steps: usize, seed: u64) -> SkinPop {
    let mut pop = SkinPop::new(rules, q0, energy, u0).expect("valid start");
    let mut rng = crate::Rng::new(seed);
    for _ in 0..steps {
        pop.step(&mut rng);
    }
    pop
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

    fn pop_rules(surplus: f64, u_shift: f64) -> SkinPopRules {
        SkinPopRules {
            skin: SkinRules {
                decay: 0.05,
                q_min: 0.2,
                repair_cost: 10.0,
                income: 1.0,
                maintenance: 1.0 - surplus,
            },
            u_noise: 0.3,
            u_shift,
            birth_price: 1.5,
            max_population: 300,
        }
    }

    #[test]
    fn maintenance_cannot_appear_from_zero_without_an_additive_shift() {
        // FINDING-259: `u' = u * noise` leaves zero at zero, so a population that pays nothing dies out even
        // where the medium could afford to keep it.
        let pop = run_pop(pop_rules(0.30, 0.0), 1.0, 10.0, 0.0, 3000, 7);
        assert!(pop.forms.is_empty(), "multiplicative mutation must leave zero absorbing");
    }

    #[test]
    fn with_an_additive_shift_the_medium_picks_maintenance_near_its_price() {
        let rules = pop_rules(0.30, 0.003);
        let u_min = rules.skin.u_min();
        let pop = run_pop(rules, 1.0, 10.0, 0.0, 3000, 7);
        assert!(!pop.forms.is_empty(), "the population should survive");
        let mean = pop.mean_u();
        assert!(
            mean >= u_min * 0.9 && mean <= u_min * 3.0,
            "the mean intensity {mean} should sit near the threshold {u_min}"
        );
        assert!(
            pop.maintainers() > 0.9,
            "almost every form should maintain, got {}",
            pop.maintainers()
        );
    }

    #[test]
    fn a_free_skin_is_still_needed() {
        // FINDING-260: the guard `repair_cost > 0.0` once made free repair impossible, so every form died at
        // the arithmetic step. With that fixed, a free skin keeps everyone alive - and the intensity is still
        // held at the need `d*q_min`, because a free price does not remove the need.
        let rules = pop_rules(0.30, 0.003);
        let free = SkinPopRules {
            skin: SkinRules { repair_cost: 0.0, ..rules.skin },
            ..rules
        };
        let u_min = free.skin.u_min();
        let pop = run_pop(free, 1.0, 10.0, 0.0, 3000, 7);
        assert!(!pop.forms.is_empty(), "a free skin should keep the population alive");
        assert!(
            pop.mean_u() >= u_min * 0.9,
            "even for free, the intensity should stay at the need {u_min}, got {}",
            pop.mean_u()
        );
    }

    #[test]
    fn the_world_freezes_once_maintainers_fill_it() {
        // FINDING-260: maintainers do not die of their skin, and income does not depend on how many forms there
        // are, so once they reach the ceiling nothing turns over and a longer horizon measures nothing.
        let rules = SkinPopRules {
            max_population: 5000,
            birth_price: 1.2,
            ..pop_rules(0.30, 0.003)
        };
        let short = run_pop(rules, 1.0, 10.0, 0.0, 3000, 7);
        let long = run_pop(rules, 1.0, 10.0, 0.0, 30_000, 7);
        assert_eq!(short.births, long.births, "the world should have stopped turning over");
        assert_eq!(short.forms.len(), long.forms.len());
    }

    #[test]
    fn a_medium_below_the_skin_price_kills_everyone() {
        // surplus 0.05 against a skin cost of 0.10: no intensity both pays the skin and breeds
        let pop = run_pop(pop_rules(0.05, 0.003), 1.0, 10.0, 0.0, 3000, 7);
        assert!(pop.forms.is_empty(), "a medium that cannot pay the skin should have nobody left");
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
