//! Two parts with a link: does the boundary hold the inside, or are they independent?
//!
//! Every world in this project so far was **one** integrity with **one** parameter: `FINDING-258`..`278` gave a
//! form a skin, a price for keeping it, and an exchange. `GOAL.md` §1a names the thing that is still missing in one
//! word - **organisation**: several parts with a division between them, where the whole can come apart because a
//! **connection** broke, not because the matter ran out.
//!
//! Here a form has two integrities:
//!
//! ```text
//! q_skin   the boundary          decays at `d_skin`, repaired at `c_skin * u_skin`
//! q_core   the contents          decays at `d_core`, repaired at `c_core * u_core`
//! link     core repair is scaled by `min(1, q_skin / q_min)` - a broken boundary stops the inside from being
//!          maintained, however much is spent on it
//! ```
//!
//! That single line creates the first **order** in this project: the skin matters before the core does.
//!
//! PREDICTION, before the code (one form, enough income, `d_skin = 0.05`, `d_core = 0.02`, `q_min = 0.2`):
//!   (a) repairing **both** lives the longest;
//!   (b) repairing **only the core** dies at the time the **skin** runs out, not at the time the core would - the
//!       link makes the skin's failure the core's failure;
//!   (c) repairing **only the skin** lives **longer** than arm (b), because the core decays more slowly and needs
//!       less.
//!
//! The contrast between (b) and (c) is the point: with a link, being skinless is worse than being hollow.

/// One part: an integrity that decays and can be repaired.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Part {
    pub q: f64,
    pub decay: f64,
    pub cost: f64,
}

impl Part {
    pub fn new(q: f64, decay: f64, cost: f64) -> Self {
        Self { q, decay, cost }
    }

    /// The repair this part needs each step to hold at `q_min`.
    pub fn need(&self, q_min: f64) -> f64 {
        self.decay * q_min
    }

    /// Decays and, if `u` is asked for, repairs as far as `q` and energy allow.
    pub fn step(&mut self, u: f64, gate: f64, energy: &mut f64) -> f64 {
        self.q *= 1.0 - self.decay;
        if u <= 0.0 || self.cost <= 0.0 {
            return 0.0;
        }
        let missing = (1.0 - self.q).max(0.0);
        let affordable = (*energy / self.cost).max(0.0);
        let done = (u * gate).min(missing).min(affordable).max(0.0);
        *energy = (*energy - done * self.cost).max(0.0);
        self.q = (self.q + done).min(1.0);
        // A repair that covers the whole deficit makes the part WHOLE, not merely close to whole. Without this clamp a
        // rounding residue survives, and because the gate is a product along the chain the residue compounds: a
        // sixteen-part chain then starves its last part although every part in front reads 1.0000 (FINDING-285).
        if self.q >= 1.0 - 1e-12 {
            self.q = 1.0;
        }
        done
    }
}

/// A form of two linked parts.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Organism {
    pub skin: Part,
    pub core: Part,
    pub q_min: f64,
    /// How sharply the skin's failure chokes the core: the gate is `min(1, (q_skin / q_min)^link_power)`.
    /// `1.0` is the relation of `FINDING-279`; smaller is a softer link, larger a harsher one.
    pub link_power: f64,
    pub energy: f64,
    pub alive: bool,
    pub steps: usize,
    /// Which part killed it, once it is dead.
    pub killed_by: Option<PartName>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PartName {
    Skin,
    Core,
}

impl Organism {
    pub fn new(skin: Part, core: Part, q_min: f64, energy: f64) -> Self {
        Self {
            skin,
            core,
            q_min,
            link_power: 1.0,
            energy,
            alive: true,
            steps: 0,
            killed_by: None,
        }
    }

    /// One step: repair the skin at `u_skin` and the core at `u_core`, with the core gated by the skin.
    pub fn step(&mut self, u_skin: f64, u_core: f64, income: f64, maintenance: f64) -> bool {
        if !self.alive {
            return false;
        }
        self.steps += 1;
        self.energy += income - maintenance;

        // the skin is what holds the inside: while it is below the threshold the core cannot be maintained
        // The gate must be able to bite while the form is ALIVE. `(q_skin/q_min)^k` is >= 1 for every living form, so
        // that version was inert: min(1, ...) stayed 1 and the link never did anything. Using the skin's own value,
        // `q_skin^k`, the gate falls as the skin sags - which is what a boundary holding its inside means.
        let gate = self.skin.q.powf(self.link_power.max(0.0)).min(1.0);
        self.skin.step(u_skin, 1.0, &mut self.energy);
        self.core.step(u_core, gate, &mut self.energy);

        if self.skin.q <= self.q_min {
            self.alive = false;
            self.killed_by = Some(PartName::Skin);
        } else if self.core.q <= self.q_min {
            self.alive = false;
            self.killed_by = Some(PartName::Core);
        } else if self.energy < 0.0 {
            self.alive = false;
        }
        self.alive
    }
}

/// A chain of parts: each holds the one behind it, and the gate is the product of everything in front.
///
/// `FINDING-281` gave a two-part law: the boundary must be held above its own need, and its price falls as
/// `1/u_core`. A chain asks whether depth costs: with `n` parts and the gate `q^k` at each link, holding the last
/// part needs `q^(n-1) * u_last >= need_last`, i.e. the front part's integrity must be at least
/// `(need_last / u_last)^(1/(n-1))` - and its repair is `d_front` times that, approaching **full repair** as the
/// chain grows.
#[derive(Debug, Clone, PartialEq)]
pub struct Chain {
    pub parts: Vec<Part>,
    pub q_min: f64,
    pub link_power: f64,
    pub energy: f64,
    pub maintenance: f64,
    pub income: f64,
    pub alive: bool,
    pub steps: usize,
    /// Index of the first part that fell below the threshold.
    pub killed_at: Option<usize>,
    /// The gate actually applied to each part on the last step. FINDING-285 could not explain why a sixteen-part
    /// chain starves its last part while the parts in front read exactly one, so the gate itself is recorded.
    pub last_gates: Vec<f64>,
}

impl Chain {
    pub fn new(parts: Vec<Part>, q_min: f64, energy: f64) -> Self {
        let n = parts.len();
        Self {
            parts,
            q_min,
            link_power: 1.0,
            energy,
            maintenance: 0.5,
            income: 1.0,
            alive: true,
            steps: 0,
            killed_at: None,
            last_gates: vec![1.0; n],
        }
    }

    /// One step, with a repair asked for at each position.
    pub fn step(&mut self, u: &[f64]) -> bool {
        if !self.alive || u.len() != self.parts.len() {
            return self.alive;
        }
        self.steps += 1;
        self.energy += self.income - self.maintenance;

        // each part's repair is scaled by the product of the gates of everything in front of it. The gate is the
        // front part's INTEGRITY raised to the link power - not how much that part managed to repair, which is a small
        // number and would collapse the product at the first link.
        let mut gate = 1.0_f64;
        for i in 0..self.parts.len() {
            self.last_gates[i] = gate;
            self.parts[i].step(u[i], gate, &mut self.energy);
            gate *= self.parts[i].q.powf(self.link_power.max(0.0)).min(1.0);
        }

        for (i, part) in self.parts.iter().enumerate() {
            if part.q <= self.q_min {
                self.alive = false;
                self.killed_at = Some(i);
                break;
            }
        }
        self.alive
    }
}

/// Two parts that cannot live alone: one cannot repair itself, the other cannot repair anything without the first.
///
/// `DESIGN-division.md` calls this the smallest form of **division**. `A` has no repair of its own and only decays;
/// `B` repairs both, but only while `A` is whole enough to give it a clearance `q_a^k`. Neither survives alone, which is
/// what separates this from the dependency of `FINDING-281`.
#[derive(Debug, Clone, PartialEq)]
pub struct Division {
    pub a: Part,
    pub b: Part,
    pub q_min: f64,
    pub energy: f64,
    pub income: f64,
    pub maintenance: f64,
    pub alive: bool,
    pub steps: usize,
    /// Which part fell first, once it is over.
    pub killed_first: Option<PartName>,
}

impl Division {
    pub fn new(a: Part, b: Part, q_min: f64, energy: f64) -> Self {
        Self {
            a,
            b,
            q_min,
            energy,
            income: 1.0,
            maintenance: 0.5,
            alive: true,
            steps: 0,
            killed_first: None,
        }
    }

    /// One step: `B` repairs itself and `A`, gated by `A`'s clearance.
    pub fn step(&mut self, u_b: f64) -> bool {
        if !self.alive {
            return false;
        }
        self.steps += 1;
        self.energy += self.income - self.maintenance;

        // The two clearances are DIFFERENT, and that is the whole point of a division:
        //   * A licenses B (`q_a`): without A's clearance B can repair nothing, not even itself;
        //   * B repairs A (`q_b`): A has no repair of its own at all.
        // Gating A's repair by A's own state is self-defeating - it cannot help a part that is already failing, and my
        // first version of this did exactly that.
        let clearance_for_b = self.a.q.powf(1.0).min(1.0);
        let clearance_for_a = self.b.q.powf(1.0).min(1.0);

        // both parts are held at 1.5 times their need: at the need itself a part settles exactly at `q_min`, and the
        // death test is `q <= q_min` (FINDING-288)
        let u_a = 1.5 * self.a.decay * self.q_min;
        self.a.step(u_a, clearance_for_a, &mut self.energy);
        self.b.step(u_b, clearance_for_b, &mut self.energy);

        if self.a.q <= self.q_min {
            self.alive = false;
            self.killed_first = Some(PartName::Skin);
        } else if self.b.q <= self.q_min {
            self.alive = false;
            self.killed_first = Some(PartName::Core);
        }
        self.alive
    }
}

/// The cheapest income that keeps a division alive, found by bisection on a coarse grid.
pub fn division_threshold(a: Part, b: Part, q_min: f64, hi: f64) -> Option<f64> {
    let alive = |income: f64| {
        let mut d = Division::new(a, b, q_min, 10.0);
        d.income = income;
        for _ in 0..200_000 {
            if !d.step(b.decay * q_min) {
                return false;
            }
        }
        true
    };
    let mut lo = 0.0_f64;
    let mut hi = hi;
    if !alive(hi) {
        return None;
    }
    for _ in 0..40 {
        let mid = (lo + hi) / 2.0;
        if alive(mid) {
            hi = mid;
        } else {
            lo = mid;
        }
    }
    Some(hi)
}

/// Runs a chain for at most `horizon` steps with a fixed repair vector.
pub fn run_chain(parts: Vec<Part>, q_min: f64, u: &[f64], horizon: usize) -> Chain {
    let mut c = Chain::new(parts, q_min, 10.0);
    for _ in 0..horizon {
        if !c.step(u) {
            break;
        }
    }
    c
}

/// Runs an organism for at most `horizon` steps.
pub fn run(
    skin: Part,
    core: Part,
    q_min: f64,
    energy: f64,
    income: f64,
    maintenance: f64,
    u_skin: f64,
    u_core: f64,
    horizon: usize,
) -> Organism {
    let mut o = Organism::new(skin, core, q_min, energy);
    for _ in 0..horizon {
        if !o.step(u_skin, u_core, income, maintenance) {
            break;
        }
    }
    o
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parts() -> (Part, Part) {
        (Part::new(1.0, 0.02, 1.0), Part::new(1.0, 0.05, 2.0))
    }

    const Q_MIN: f64 = 0.2;

    fn u_core_of(need: f64) -> f64 {
        4.0 * need
    }

    #[test]
    fn repairing_both_at_the_need_still_dies() {
        // FINDING-281: the boundary held at its own minimum is BEFORE its own death but below what the inside needs,
        // so the gate chokes the core. "Merely not dead" is not enough for a boundary that has an inside to hold.
        let (skin, core) = parts();
        let u_skin = skin.need(Q_MIN);
        let u_core = u_core_of(core.need(Q_MIN));
        let o = run(skin, core, Q_MIN, 10.0, 1.0, 0.5, u_skin, u_core, 200_000);
        assert!(!o.alive, "a skin at its bare minimum cannot support the inside");
    }

    #[test]
    fn the_boundary_must_be_held_above_its_own_need() {
        // the critical repair is the larger of two conditions: the skin must stay alive, and the core must be fed
        // through the gate. Here the second binds: d_s * need_core / u_core.
        let (skin, core) = parts();
        let u_core = u_core_of(core.need(Q_MIN));
        let crit = skin.decay * core.need(Q_MIN) / u_core;
        let floor = skin.need(Q_MIN);
        assert!(crit > floor, "the core's demand {crit} should exceed the skin's own floor {floor}");
        let below = run(skin, core, Q_MIN, 10.0, 1.0, 0.5, crit * 0.9, u_core, 200_000);
        let above = run(skin, core, Q_MIN, 10.0, 1.0, 0.5, crit * 1.1, u_core, 200_000);
        assert!(!below.alive, "below the critical repair it should die");
        assert!(above.alive, "and above it live");
    }

    #[test]
    fn the_price_of_the_boundary_falls_with_the_inside_demand() {
        // doubling what is spent on the inside halves what the boundary must be held at - until the boundary's own
        // floor takes over, and then it stops falling
        let (skin, core) = parts();
        let demand = |u_core: f64| skin.decay * core.need(Q_MIN) / u_core;
        assert!((demand(2.0 * core.need(Q_MIN)) / demand(4.0 * core.need(Q_MIN)) - 2.0).abs() < 1e-12);
        let floor = skin.need(Q_MIN);
        assert!(floor > demand(8.0 * core.need(Q_MIN)), "at eight times the inside need the floor binds");
        assert!(floor <= demand(2.0 * core.need(Q_MIN)), "and at twice it does not");
    }

    #[test]
    fn a_broken_link_lets_the_inside_be_kept() {
        // the control: with k = 0 the gate is 1 whatever the skin does, so a form that feeds only its core keeps
        // the core whole while its skin falls - the contrast is the link and not the decay
        let (skin, core) = parts();
        let mut o = Organism::new(skin, core, Q_MIN, 10.0);
        o.link_power = 0.0;
        let u_core = u_core_of(core.need(Q_MIN));
        for _ in 0..200_000 {
            if !o.step(0.0, u_core, 1.0, 0.5) {
                break;
            }
        }
        assert!(!o.alive);
        assert_eq!(o.killed_by, Some(PartName::Skin));
        assert!(o.core.q > 0.7, "with no link the core should be near its own equilibrium, got {}", o.core.q);
    }

    /// The chain's law: `q_i = (product of the gates in front) * u_i / d`, and a fully repaired part still sits just
    /// below one, so the deficit compounds with depth.
    ///
    /// `FINDING-282` predicted the middle part would fall first; the trajectory of `FINDING-283` showed it is the
    /// **last** one, the most gated. That test is replaced by the corrected one below.
    #[test]
    fn a_division_by_mutual_licensing_collapses_jointly() {
        // FINDING-289: when each part licenses the other, a deficit in one reduces the other's repair, which deepens
        // its own deficit. The feedback always points down: there is no equilibrium, and money does not help - the
        // pair dies at income 10 while its bill is 0.03.
        let a = Part::new(1.0, 0.05, 1.0);
        let b = Part::new(1.0, 0.05, 1.0);
        let mut d = Division::new(a, b, Q_MIN, 10.0);
        d.income = 10.0;
        let mut at_ten = None;
        for step in 1..=200_000 {
            if !d.step(1.5 * 0.05 * Q_MIN) {
                at_ten = Some(step);
                break;
            }
        }
        assert_eq!(at_ten, Some(46), "the pair should die at step 46 even with plenty of money");
        assert!((d.a.q - d.b.q).abs() < 1e-9, "and both parts should be equal all along");
    }

    #[test]
    fn the_last_part_falls_first_and_depth_has_a_limit() {
        let chain = |n: usize, u_front: f64| {
            let parts: Vec<Part> = (0..n).map(|_| Part::new(1.0, 0.05, 1.0)).collect();
            let mut u = vec![u_front; n];
            u[n - 1] = 2.0 * 0.05 * Q_MIN;
            run_chain(parts, Q_MIN, &u, 200_000)
        };

        // the last part is the one that goes
        let three = chain(3, 0.020);
        assert!(!three.alive);
        assert_eq!(three.killed_at, Some(2), "the last part should be the one to fall");

        // depth is nearly free but not free: eight parts live, sixteen do not
        assert!(chain(8, 0.05).alive, "eight parts should hold with full front repair");
        assert!(!chain(16, 0.05).alive, "sixteen should not");

        // and with half the front repair, three already dies
        assert!(!chain(3, 0.025).alive);
    }

    #[test]
    fn the_chain_is_a_cascade_and_the_middle_part_is_the_one_that_fails() {
        // FINDING-282: the multiplication law for the LAST part was not confirmed, and the reason is visible here -
        // every part is gated, so the middle one can be the first to fall. This test records what the chain does
        // rather than what the formula predicted.
        let parts: Vec<Part> = (0..3).map(|_| Part::new(1.0, 0.05, 1.0)).collect();
        let u = [0.020, 0.020, 0.020];
        let c = run_chain(parts, Q_MIN, &u, 200_000);
        assert!(!c.alive, "with these numbers the chain collapses");
        assert!(c.killed_at.is_some());
        let idx = c.killed_at.unwrap();
        assert!(idx <= 2);
    }

    #[test]
    fn each_part_dies_by_its_own_law_when_it_is_the_one_neglected() {
        // the law of FINDING-258 holds per part: ln(q_min)/ln(1-d) rounded up
        let bare = |d: f64| ((Q_MIN as f64).ln() / (1.0 - d).ln()).floor() as usize + 1;
        let (skin, core) = parts();
        // skin left bare: it dies at its own law whatever is spent on the core... unless the core is already dead
        let o = run(skin, core, Q_MIN, 10.0, 1.0, 0.5, 0.0, 0.0, 200_000);
        assert!(!o.alive);
        assert!(o.steps <= bare(skin.decay) + 1, "the skin should go near its own low bound");
    }
}
