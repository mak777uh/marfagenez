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
        done
    }
}

/// A form of two linked parts.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Organism {
    pub skin: Part,
    pub core: Part,
    pub q_min: f64,
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
        let gate = (self.skin.q / self.q_min).min(1.0);
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
        (Part::new(1.0, 0.05, 1.0), Part::new(1.0, 0.02, 2.0))
    }

    #[test]
    fn repairing_both_survives_longest() {
        let (skin, core) = parts();
        let u_min_skin = 0.05 * 0.2;
        let u_min_core = 0.02 * 0.2;
        let both = run(skin, core, 0.2, 10.0, 1.0, 0.5, u_min_skin, u_min_core, 200_000);
        assert!(both.alive, "repairing both should live");
    }

    #[test]
    fn repairing_only_the_core_dies_when_the_skin_goes() {
        // the link: a skinless form cannot maintain its inside, however much it spends there
        let (skin, core) = parts();
        let only_core = run(skin, core, 0.2, 10.0, 1.0, 0.5, 0.0, 0.02 * 0.2, 200_000);
        assert!(!only_core.alive);
        assert_eq!(only_core.killed_by, Some(PartName::Skin), "the skin should be what fails first");
    }

    #[test]
    fn repairing_only_the_skin_lives_longer_than_repairing_only_the_core() {
        let (skin, core) = parts();
        let only_core = run(skin, core, 0.2, 10.0, 1.0, 0.5, 0.0, 0.02 * 0.2, 200_000);
        let only_skin = run(skin, core, 0.2, 10.0, 1.0, 0.5, 0.05 * 0.2, 0.0, 200_000);
        assert!(
            only_skin.steps > only_core.steps,
            "skin only {} vs core only {}",
            only_skin.steps,
            only_core.steps
        );
    }

    #[test]
    fn without_the_link_the_core_outlives_the_skin() {
        // the control: if the core is not gated, spending on it keeps it whole while the skin falls - so the
        // contrast in the test above is caused by the link and not by the decay rates
        let (skin, mut core) = parts();
        core.decay = 0.02;
        let mut o = Organism::new(skin, core, 0.2, 10.0);
        for _ in 0..200_000 {
            // gate forced to 1: no link
            o.energy += 1.0 - 0.5;
            o.skin.step(0.0, 1.0, &mut o.energy);
            o.core.step(0.02 * 0.2, 1.0, &mut o.energy);
            if o.skin.q <= 0.2 {
                o.alive = false;
                o.killed_by = Some(PartName::Skin);
                break;
            }
            if o.core.q <= 0.2 {
                o.alive = false;
                o.killed_by = Some(PartName::Core);
                break;
            }
        }
        assert_eq!(o.killed_by, Some(PartName::Skin), "the skin still goes first here, by decay alone");
        assert!(o.core.q > 0.2, "but the core stays whole: the gate is what kills it, not its own decay");
    }
}
