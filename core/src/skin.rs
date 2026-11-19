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
    /// When set, a form asks the medium for **what it needs** - maintenance, the price of its own repair, and
    /// this much extra for breeding - instead of for the fixed `income`. `FINDING-265` found that the fixed
    /// figure is a ceiling of my own making: a richer pool could never give a form more than that.
    ///
    /// **This mode rewards asking for more**: a form with a higher intensity asks for a bigger ration, so the
    /// intensity inflates (`FINDING-266`). Use it only to show that effect.
    pub demand_growth: Option<f64>,
    /// The pool pays for repair **directly**: a form receives `maintenance + margin` as energy, and its repair is
    /// drawn from the stock at `repair_cost * u`, in the same proportion. A form can no longer turn an inflated
    /// need into extra energy - but it can still spend the commons for its own survival.
    pub repair_from_pool: bool,
    /// A form's own decay lands in its **own pocket** and repairs it for free, before any energy is spent.
    /// Repair is then self-funding while `q * decay >= u`, i.e. while `q >= q_min` - a form at the threshold can
    /// pay for its own maintenance out of what it lost.
    pub local_recycle: bool,
    /// How much of the decay falls into the form's own pocket, when `local_recycle` is set. `1.0` is a fully local
    /// cycle (`FINDING-271`), `0.0` is the communal one (`FINDING-270`). The mixture is what decides whether a form
    /// still needs the medium it shares.
    pub local_share: f64,
    /// Ceiling on the pocket. `None` means the pocket is bottomless, which `FINDING-274` named as the possible
    /// source of its whole advantage: a pocket is matter the common ceiling cannot hold, so an endless pocket would
    /// beat a capped medium for reasons that have nothing to do with locality.
    pub pocket_max: Option<f64>,
}

/// One form in the population.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SkinForm {
    pub q: f64,
    pub energy: f64,
    /// The inherited repair intensity: how much integrity this lineage tries to add each step.
    pub u: f64,
    /// Steps lived. A population that dies in two steps cannot be selected on anything.
    pub age: usize,
    /// Matter this form's own decay has returned, and which only it can use for repair.
    ///
    /// With the pocket the cycle is **local** instead of communal: `FINDING-270` showed that on a communal cycle
    /// dying donates your body to the competitors, so keeping yourself whole is the only way a line keeps its
    /// matter. Here the question is the opposite one: what happens when the return goes to the line.
    pub pocket: f64,
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
        let f = SkinForm { q: q0, energy, u: u0, age: 0, pocket: 0.0 };
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
                age: 0,
                pocket: 0.0,
            };
            self.forms[i].energy -= self.rules.birth_price;
            self.forms.push(child);
            self.births += 1;
        }
    }
}

/// A medium the forms **share**: matter is taken from one stock, and decay returns it.
///
/// `FINDING-260` found the limit of the previous world: income came from nowhere, so maintainers never died and
/// the population froze. With a stock there are two differences that matter for the elephant:
///
/// * **death can come from scarcity** - a form that cannot draw its income starves, whatever its skin;
/// * **the boundary has a second direction** - what decays off a form goes back into the stock, so the medium is
///   no longer a pure sink. That is the exchange `GOAL.md` §1a asks about, in its smallest form.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SkinPool {
    pub stock: f64,
    pub stock_max: f64,
    /// What arrives each step before anyone eats.
    pub inflow: f64,
    /// Share of the lost integrity that returns to the medium.
    pub recovery: f64,
}

impl SkinPool {
    pub fn new(stock: f64, stock_max: f64, inflow: f64, recovery: f64) -> Self {
        Self {
            stock: stock.clamp(0.0, stock_max),
            stock_max,
            inflow,
            recovery: recovery.clamp(0.0, 1.0),
        }
    }

    /// What each form may draw when `n` forms compete for the current stock.
    pub fn share(&self, n: usize, income: f64) -> f64 {
        if n == 0 {
            return income;
        }
        let want = income * n as f64;
        if self.stock >= want {
            income
        } else {
            self.stock / n as f64
        }
    }
}

/// A population drawing on a shared pool.
#[derive(Debug, Clone, PartialEq)]
pub struct SkinShared {
    pub rules: SkinPopRules,
    pub pool: SkinPool,
    pub forms: Vec<SkinForm>,
    pub births: u64,
    pub deaths: u64,
    pub steps: usize,
    /// Total matter handed out, for the record.
    pub drawn: f64,
    /// Total matter returned by decay, for the record.
    pub returned: f64,
    /// Sum of the ages of everything that died, so the mean age of death can be read.
    pub age_at_death: u64,
}

impl SkinShared {
    pub fn new(rules: SkinPopRules, pool: SkinPool, q0: f64, energy: f64, u0: f64) -> Self {
        Self {
            rules,
            pool,
            forms: vec![SkinForm { q: q0, energy, u: u0, age: 0, pocket: 0.0 }],
            births: 0,
            deaths: 0,
            steps: 0,
            drawn: 0.0,
            returned: 0.0,
            age_at_death: 0,
        }
    }

    pub fn mean_u(&self) -> f64 {
        if self.forms.is_empty() {
            return f64::NAN;
        }
        self.forms.iter().map(|f| f.u).sum::<f64>() / self.forms.len() as f64
    }

    pub fn maintainers(&self) -> f64 {
        if self.forms.is_empty() {
            return f64::NAN;
        }
        let u_min = self.rules.skin.u_min();
        self.forms.iter().filter(|f| f.u >= u_min).count() as f64 / self.forms.len() as f64
    }

    /// Mean steps lived by those that died.
    pub fn mean_lifetime(&self) -> f64 {
        if self.deaths == 0 {
            return f64::NAN;
        }
        self.age_at_death as f64 / self.deaths as f64
    }

    pub fn step(&mut self, rng: &mut crate::Rng) {
        self.steps += 1;
        let skin = self.rules.skin;
        self.pool.stock = (self.pool.stock + self.pool.inflow).clamp(0.0, self.pool.stock_max);

        // What each form asks for, in three accountings (`FINDING-265`, `FINDING-266`):
        //
        //   fixed          every form asks for `income` - a ceiling of the modeller's making;
        //   demand_growth  a form asks for maintenance + price of its own repair + margin, which *rewards asking
        //                  for more*: the intensity inflates because a bigger ask buys a bigger ration;
        //   repair_from_pool  a form asks only for maintenance + margin and the pool pays for repair directly,
        //                  so an inflated intensity buys no extra energy - it only spends the commons.
        let demands: Vec<f64> = self
            .forms
            .iter()
            .map(|f| {
                if self.rules.repair_from_pool {
                    skin.maintenance + self.rules.demand_growth.unwrap_or(0.0)
                        + skin.repair_cost * f.u
                } else {
                    match self.rules.demand_growth {
                        Some(g) => skin.maintenance + skin.repair_cost * f.u + g,
                        None => skin.income,
                    }
                }
            })
            .collect();
        let total_demand: f64 = demands.iter().sum();
        // ration proportionally when the stock cannot cover everyone
        let ration = if total_demand > 0.0 {
            (self.pool.stock / total_demand).min(1.0)
        } else {
            0.0
        };
        let take = (total_demand * ration).min(self.pool.stock);
        self.pool.stock = (self.pool.stock - take).max(0.0);
        self.drawn += take;

        let mut returned = 0.0;
        for (f, demand) in self.forms.iter_mut().zip(demands.iter()) {
            let share = demand * ration;
            f.age += 1;
            let energy_in = if self.rules.repair_from_pool {
                // the repair part of the ration is matter delivered to the repair, not income to hoard
                share - skin.repair_cost * f.u * ration
            } else {
                share
            };
            f.energy += energy_in - skin.maintenance;
            // the decay is a loss to the form and, with recovery, a gain to the medium
            let lost = f.q * skin.decay;
            f.q -= lost;
            returned += lost * self.pool.recovery;

            let affordable = if skin.repair_cost > 0.0 {
                f.energy / skin.repair_cost
            } else {
                f64::INFINITY
            };
            if f.u > 0.0 && (f.energy > 0.0 || skin.repair_cost <= 0.0) {
                let missing = (1.0 - f.q).max(0.0);
                let done = f.u.min(missing).min(affordable).max(0.0);
                f.energy = (f.energy - done * skin.repair_cost).max(0.0);
                f.q = (f.q + done).min(1.0);
            }
        }
        self.pool.stock = (self.pool.stock + returned).clamp(0.0, self.pool.stock_max);
        self.returned += returned;

        let before = self.forms.len();
        let dying: usize = self
            .forms
            .iter()
            .filter(|f| !(f.q > skin.q_min && f.energy >= 0.0))
            .map(|f| f.age)
            .sum();
        self.age_at_death += dying as u64;
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
            let noise = 1.0 + (rng.uniform() - 0.5) * 2.0 * self.rules.u_noise;
            let shift = (rng.uniform() - 0.5) * 2.0 * self.rules.u_shift;
            let child = SkinForm {
                q: parent.q,
                energy: self.rules.birth_price,
                u: (parent.u * noise + shift).max(0.0),
                age: 0,
                pocket: 0.0,
            };
            self.forms[i].energy -= self.rules.birth_price;
            self.forms.push(child);
            self.births += 1;
        }
    }
}

/// Runs a shared-medium population for `steps`.
pub fn run_shared(
    rules: SkinPopRules,
    pool: SkinPool,
    q0: f64,
    energy: f64,
    u0: f64,
    steps: usize,
    seed: u64,
) -> SkinShared {
    let mut pop = SkinShared::new(rules, pool, q0, energy, u0);
    let mut rng = crate::Rng::new(seed);
    for _ in 0..steps {
        pop.step(&mut rng);
    }
    pop
}

/// A medium with **two** kinds of matter: what a form can use, and what it has already used.
///
/// `GOAL.md` §1 asks for the third thing this project never had: a form that **takes part in shaping the
/// conditions of its own further existence**. Here that is one mechanism, not a metaphor:
///
/// ```text
/// ready            what a form can draw
/// spent            what a form's decay returns - not usable as it stands
/// conversion rate  how fast the medium turns spent back into ready
/// ```
///
/// A form that keeps more integrity alive holds more matter in circulation, and therefore **loses more of it to
/// decay** every step. So maintaining yourself loads the medium - and if the medium cannot recycle fast enough,
/// the load is the form's own future supply.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SkinCycle {
    pub ready: f64,
    pub spent: f64,
    pub ready_max: f64,
    pub spent_max: f64,
    /// What arrives each step from outside.
    pub inflow: f64,
    /// Fraction of `spent` turned back into `ready` each step.
    pub conversion: f64,
}

impl SkinCycle {
    pub fn new(ready: f64, spent: f64, ready_max: f64, spent_max: f64, inflow: f64, conversion: f64) -> Self {
        Self {
            ready: ready.clamp(0.0, ready_max),
            spent: spent.clamp(0.0, spent_max),
            ready_max,
            spent_max,
            inflow,
            conversion: conversion.clamp(0.0, 1.0),
        }
    }

    pub fn ration(&self, demand: f64, n: usize) -> f64 {
        let total = demand * n as f64;
        if total <= 0.0 {
            return 1.0;
        }
        (self.ready / total).min(1.0)
    }
}

/// A population on a medium that recycles.
#[derive(Debug, Clone, PartialEq)]
pub struct SkinRecycle {
    pub rules: SkinPopRules,
    pub cycle: SkinCycle,
    pub forms: Vec<SkinForm>,
    pub births: u64,
    pub deaths: u64,
    pub steps: usize,
    pub returned: f64,
    pub drawn: f64,
}

impl SkinRecycle {
    pub fn new(rules: SkinPopRules, cycle: SkinCycle, q0: f64, energy: f64, u0: f64) -> Self {
        Self {
            rules,
            cycle,
            forms: vec![SkinForm { q: q0, energy, u: u0, age: 0, pocket: 0.0 }],
            births: 0,
            deaths: 0,
            steps: 0,
            returned: 0.0,
            drawn: 0.0,
        }
    }

    pub fn mean_u(&self) -> f64 {
        if self.forms.is_empty() {
            return f64::NAN;
        }
        self.forms.iter().map(|f| f.u).sum::<f64>() / self.forms.len() as f64
    }

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

        self.cycle.ready = (self.cycle.ready + self.cycle.inflow).clamp(0.0, self.cycle.ready_max);
        let recycled = (self.cycle.spent * self.cycle.conversion).min(self.cycle.spent);
        self.cycle.spent -= recycled;
        self.cycle.ready = (self.cycle.ready + recycled).clamp(0.0, self.cycle.ready_max);

        let n = self.forms.len();
        let demand = skin.maintenance + 0.1;
        let ration = self.cycle.ration(demand, n);
        let share = demand * ration;

        let mut returned = 0.0;
        for f in self.forms.iter_mut() {
            f.age += 1;
            f.energy += share - skin.maintenance;

            let lost = f.q * skin.decay;
            f.q -= lost;
            if self.rules.local_recycle {
                // part of the loss is the form's own; the rest still goes back to the stock it shares
                let local = (self.rules.local_share.clamp(0.0, 1.0) * lost).max(0.0);
                let room = match self.rules.pocket_max {
                    Some(cap) => (cap - f.pocket).max(0.0),
                    None => f64::INFINITY,
                };
                let stored = local.min(room);
                f.pocket += stored;
                returned += local - stored;
                returned += lost - local;
            } else {
                returned += lost;
            }

            if f.u > 0.0 {
                let missing = (1.0 - f.q).max(0.0);
                let want = f.u.min(missing).max(0.0);
                // the pocket pays first and costs nothing; only what is left must be paid for
                let from_pocket = if self.rules.local_recycle { want.min(f.pocket) } else { 0.0 };
                f.pocket = (f.pocket - from_pocket).max(0.0);
                let left = want - from_pocket;
                let affordable = if skin.repair_cost > 0.0 {
                    f.energy / skin.repair_cost
                } else {
                    f64::INFINITY
                };
                let done = left.min(affordable).max(0.0);
                f.energy = (f.energy - done * skin.repair_cost).max(0.0);
                f.q = (f.q + from_pocket + done).min(1.0);
            }
        }
        let taken = (share * n as f64).min(self.cycle.ready);
        self.cycle.ready = (self.cycle.ready - taken).max(0.0);
        self.drawn += taken;

        self.cycle.spent = (self.cycle.spent + returned).min(self.cycle.spent_max);
        self.returned += returned;

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
            let noise = 1.0 + (rng.uniform() - 0.5) * 2.0 * self.rules.u_noise;
            let shift = (rng.uniform() - 0.5) * 2.0 * self.rules.u_shift;
            let child = SkinForm {
                q: parent.q,
                energy: self.rules.birth_price,
                u: (parent.u * noise + shift).max(0.0),
                age: 0,
                pocket: 0.0,
            };
            self.forms[i].energy -= self.rules.birth_price;
            self.forms.push(child);
            self.births += 1;
        }
    }
}

/// Runs a recycling population for `steps`.
pub fn run_recycle(
    rules: SkinPopRules,
    cycle: SkinCycle,
    q0: f64,
    energy: f64,
    u0: f64,
    steps: usize,
    seed: u64,
) -> SkinRecycle {
    let mut pop = SkinRecycle::new(rules, cycle, q0, energy, u0);
    let mut rng = crate::Rng::new(seed);
    for _ in 0..steps {
        pop.step(&mut rng);
    }
    pop
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
            demand_growth: None,
            repair_from_pool: false,
            local_recycle: false,
            local_share: 1.0,
            pocket_max: None,
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

    fn shared_rules() -> SkinPopRules {
        pop_rules(0.30, 0.003)
    }

    #[test]
    fn the_intensity_converges_towards_the_need_from_above_and_below() {
        // FINDING-262: started twice above the need (0.02), the mean intensity in a scarce medium **falls**
        // towards it; started at zero (FINDING-259) it rose. Drift does not converge on one point from both
        // sides; selection does.
        let pool = || crate::skin::SkinPool::new(50.0, 500.0, 30.0, 1.0);
        let above = run_shared(shared_rules(), pool(), 1.0, 10.0, 0.02, 4000, 11);
        let below = run_shared(shared_rules(), pool(), 1.0, 10.0, 0.0, 4000, 11);
        let u_min = shared_rules().skin.u_min();

        assert!(above.forms.len() > 0 && below.forms.len() > 0);
        assert!(
            above.mean_u() < 0.02,
            "from above the intensity should fall towards the need, got {}",
            above.mean_u()
        );
        assert!(
            below.mean_u() > u_min,
            "from below it should settle above the need, got {}",
            below.mean_u()
        );
        // and both should end within a factor of two of the need
        for (label, mean) in [("above", above.mean_u()), ("below", below.mean_u())] {
            assert!(
                mean >= u_min && mean <= u_min * 2.5,
                "{label}: {mean} should sit within a factor of the need {u_min}"
            );
        }
    }

    #[test]
    fn the_share_is_capped_by_income_so_a_richer_pool_gives_nothing_more() {
        // FINDING-265: `share = min(income, stock / n)`. With a large stock each form still draws only
        // `income`, so making the medium richer cannot give a form more matter - it only lets more forms live.
        // This is my decision, not a property of a medium, and the control that exposed it was silent.
        let poor = crate::skin::SkinPool::new(50.0, 500.0, 30.0, 1.0);
        let rich = crate::skin::SkinPool::new(500.0, 5000.0, 3000.0, 1.0);
        assert_eq!(poor.share(10, 1.0), 1.0);
        assert_eq!(rich.share(10, 1.0), 1.0);
        // only when the stock is short does the pool bind
        assert!(poor.share(100, 1.0) < 1.0 || poor.stock < 100.0);
    }

    #[test]
    fn a_shared_stock_limits_the_population_before_any_ceiling() {
        // FINDING-261: with a tight inflow the population stops well below `max_population`, because the stock
        // cannot feed more forms - something an unshared income could never show.
        let pool = crate::skin::SkinPool::new(50.0, 500.0, 30.0, 1.0);
        let mut rules = shared_rules();
        rules.max_population = 300;
        let pop = run_shared(rules, pool, 1.0, 10.0, 0.0, 6000, 11);
        assert!(pop.forms.len() > 0 && pop.forms.len() < 300, "got {} forms", pop.forms.len());
    }

    #[test]
    fn decay_returns_matter_to_the_stock() {
        // the boundary is two-way: what falls off a form goes back into the medium
        let pool = crate::skin::SkinPool::new(50.0, 500.0, 600.0, 1.0);
        let pop = run_shared(shared_rules(), pool, 1.0, 10.0, 0.0, 500, 11);
        assert!(pop.returned > 0.0, "decay should return something");
        assert!(pop.drawn > 0.0, "forms should draw something");
        assert!(
            pop.returned < pop.drawn,
            "the return is a fraction of what is taken: {} vs {}",
            pop.returned,
            pop.drawn
        );
    }

    #[test]
    fn a_pocket_below_one_step_of_repair_is_worthless() {
        // FINDING-275: the real threshold is not the pocket's size in general but whether it can hold the NEXT
        // repair. Below `u_min` the population falls; at `u_min` and above it reaches the ceiling.
        fn run(cap: Option<f64>) -> usize {
            let rules = SkinPopRules {
                skin: SkinRules {
                    decay: 0.05,
                    q_min: 0.2,
                    repair_cost: 1.0,
                    income: 1.0,
                    maintenance: 0.0,
                },
                u_noise: 0.0,
                u_shift: 0.0,
                birth_price: 0.5,
                max_population: 5000,
                demand_growth: None,
                repair_from_pool: false,
                local_recycle: true,
                local_share: 1.0,
                pocket_max: cap,
            };
            let need = rules.skin.u_min();
            let cycle = crate::skin::SkinCycle::new(5.0, 0.0, 5.0, 100_000.0, 0.0, 1.0);
            let mut pop = run_recycle(rules, cycle, 1.0, 10.0, need, 0, 5);
            pop.forms.clear();
            for _ in 0..50 {
                pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: need, age: 0, pocket: 0.0 });
                pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: 0.0, age: 0, pocket: 0.0 });
            }
            let mut rng = crate::Rng::new(5);
            for _ in 0..4000 {
                pop.step(&mut rng);
            }
            pop.forms.len()
        }

        let need = 0.01; // d * q_min
        assert_eq!(run(Some(0.001)), 550);
        assert_eq!(run(Some(0.005)), 1000);
        assert_eq!(run(Some(need)), 5000, "at one step of repair the pocket stops binding");
        assert_eq!(run(Some(1.0)), run(None), "a large cap changes nothing");
    }

    #[test]
    fn capping_the_medium_makes_the_local_share_matter() {
        // FINDING-274: with the ceiling on the POPULATION every share gives the same population; with the ceiling
        // on the MATTER the share decides, because a pocket is matter the cap cannot hold. The relation is not
        // monotone - 550 at 0.2, 450 at 0.4, 1200 at 0.6 - and it is deterministic, since mutation is off.
        fn run(share: f64) -> usize {
            let rules = SkinPopRules {
                skin: SkinRules {
                    decay: 0.05,
                    q_min: 0.2,
                    repair_cost: 1.0,
                    income: 1.0,
                    maintenance: 0.0,
                },
                u_noise: 0.0,
                u_shift: 0.0,
                birth_price: 0.5,
                max_population: 5000,
                demand_growth: None,
                repair_from_pool: false,
                local_recycle: true,
                local_share: share,
                pocket_max: None,
            };
            let need = rules.skin.u_min();
            let cycle = crate::skin::SkinCycle::new(5.0, 0.0, 5.0, 100_000.0, 0.0, 1.0);
            let mut pop = run_recycle(rules, cycle, 1.0, 10.0, need, 0, 5);
            pop.forms.clear();
            for _ in 0..50 {
                pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: need, age: 0, pocket: 0.0 });
                pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: 0.0, age: 0, pocket: 0.0 });
            }
            let mut rng = crate::Rng::new(5);
            for _ in 0..4000 {
                pop.step(&mut rng);
            }
            pop.forms.len()
        }

        let a = run(0.2);
        let b = run(0.4);
        let c = run(0.6);
        assert_eq!((a, b, c), (550, 450, 1200), "the deterministic values from FINDING-274");
        assert!(c > a, "a large local share supports more forms than a small one");
    }

    #[test]
    fn there_is_no_tight_regime_between_plenty_and_death() {
        // FINDING-273: a form takes `c*d*q_min` and returns `q*d`, so the surplus is `d*(q - c*q_min)`. At `c = 1`
        // and any `q > q_min` it is a large surplus, and above the closure price the form cannot pay at all.
        // Nothing lies between, which is why three cycles could not stage a competition for scarce matter.
        //
        // The test must run on the CLOSED cycle: with a fixed income every price is payable and the claim cannot
        // be exercised at all - my first version of this test made exactly that mistake.
        let surplus: f64 = 0.05 * (1.0 - 1.0 * 0.2);
        assert!((surplus - 0.04).abs() < 1e-12, "surplus at c = 1, q = 1 is {surplus}");
        assert!(surplus > 3.0 * 0.01, "which is four times the need");

        let base = SkinPopRules {
            skin: SkinRules {
                decay: 0.05,
                q_min: 0.2,
                repair_cost: 1.0,
                income: 1.0,
                maintenance: 0.0,
            },
            u_noise: 0.0,
            u_shift: 0.0,
            birth_price: 1.5,
            max_population: 1,
            demand_growth: None,
            repair_from_pool: false,
            local_recycle: false,
            local_share: 1.0,
            pocket_max: None,
        };
        let closed = |cost: f64| {
            let mut r = base;
            r.skin.repair_cost = cost;
            let need = r.skin.u_min();
            run_recycle(
                r,
                crate::skin::SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, 1.0),
                1.0,
                10.0,
                need,
                200_000,
                1,
            )
            .forms
            .len()
        };
        assert_eq!(closed(1.0), 1, "at the closure price the form lives on its own decay");
        assert_eq!(closed(1.5), 0, "above it the form cannot pay and dies");
        assert_eq!(closed(0.5), 1, "and below it, of course");
    }

    #[test]
    fn a_pocket_makes_a_form_self_sufficient_and_empties_the_medium() {
        // FINDING-271: with the pocket the decay returns to the form itself, and since `q*d >= u` for any living
        // form (`q >= q_min`), maintenance becomes free. The medium is then untouched: `spent` stays at zero.
        let base = SkinPopRules {
            skin: SkinRules {
                decay: 0.05,
                q_min: 0.2,
                repair_cost: 1.0,
                income: 1.0,
                maintenance: 0.0,
            },
            u_noise: 0.0,
            u_shift: 0.0,
            birth_price: 0.5,
            max_population: 200,
            demand_growth: None,
            repair_from_pool: false,
            local_recycle: true,
            local_share: 1.0,
            pocket_max: None,
        };
        let need = base.skin.u_min();
        let mut r = base;
        r.local_recycle = false;
        let communal = run_recycle(
            r,
            crate::skin::SkinCycle::new(0.0, 0.0, 2000.0, 100_000.0, 0.0, 1.0),
            1.0,
            10.0,
            need,
            2000,
            5,
        );
        let local = run_recycle(
            base,
            crate::skin::SkinCycle::new(0.0, 0.0, 2000.0, 100_000.0, 0.0, 1.0),
            1.0,
            10.0,
            need,
            2000,
            5,
        );
        assert!(!local.forms.is_empty(), "a pocket should keep the population alive");
        assert_eq!(local.cycle.spent, 0.0, "nothing should return to the medium any more");
        assert!(
            local.cycle.spent <= communal.cycle.spent,
            "the pocket empties the medium that the communal cycle fills"
        );
    }

    #[test]
    fn on_a_closed_cycle_the_payers_take_everything() {
        // FINDING-270: non-payers die in 32 steps and their bodies go back to the MEDIUM, not to their kin, so
        // dying subsidises the competitors - and a child inherits the parent's already-decayed `q`, so the
        // non-paying line erodes as well. Payers take the whole population at any ceiling.
        let rules = SkinPopRules {
            skin: SkinRules {
                decay: 0.05,
                q_min: 0.2,
                repair_cost: 1.0,
                income: 1.0,
                maintenance: 0.0,
            },
            u_noise: 0.0,
            u_shift: 0.0,
            birth_price: 0.5,
            max_population: 5000,
            demand_growth: None,
            repair_from_pool: false,
            local_recycle: false,
            local_share: 1.0,
            pocket_max: None,
        };
        let need = rules.skin.u_min();
        let cycle = crate::skin::SkinCycle::new(200.0, 0.0, 2000.0, 100_000.0, 0.0, 1.0);
        let mut pop = run_recycle(rules, cycle, 1.0, 10.0, need, 0, 5);
        pop.forms.clear();
        for _ in 0..50 {
            pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: need, age: 0, pocket: 0.0 });
            pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: 0.0, age: 0, pocket: 0.0 });
        }
        let mut rng = crate::Rng::new(5);
        for _ in 0..4000 {
            pop.step(&mut rng);
        }
        let payers = pop.forms.iter().filter(|f| f.u >= need).count();
        assert!(!pop.forms.is_empty());
        assert_eq!(
            payers,
            pop.forms.len(),
            "every survivor should be a payer, got {payers} of {}",
            pop.forms.len()
        );
    }

    #[test]
    fn a_population_survives_on_a_closed_cycle_and_its_bodies_are_the_food() {
        // FINDING-269: with no external inflow at all, a population on a recycling medium reaches its ceiling and
        // keeps turning over, because the dead return their matter. `ready` sits at zero - in a closed world all
        // the matter is locked in bodies.
        let rules = SkinPopRules {
            skin: SkinRules {
                decay: 0.05,
                q_min: 0.2,
                repair_cost: 1.0,
                income: 1.0,
                maintenance: 0.0,
            },
            u_noise: 0.3,
            u_shift: 0.003,
            birth_price: 0.5,
            max_population: 300,
            demand_growth: None,
            repair_from_pool: false,
            local_recycle: false,
            local_share: 1.0,
            pocket_max: None,
        };
        let cycle = crate::skin::SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, 1.0);
        let pop = run_recycle(rules, cycle, 1.0, 10.0, 0.01, 8000, 3);
        assert_eq!(pop.forms.len(), 300, "the population should reach its ceiling");
        assert!(pop.births > 100, "and keep turning over, got {} births", pop.births);
        assert!(pop.cycle.ready < 1.0, "in a closed world the free matter is near zero");
    }

    #[test]
    fn a_closed_cycle_is_possible_and_the_criterion_is_the_price() {
        // FINDING-268: with perfect recycling and NO external inflow, a form lives only if what it takes does not
        // exceed what its decay returns. At the need, `q` settles at `q_min`, so the criterion is
        // `c*q_min <= q_min`, i.e. `c <= 1`. Speed of recycling does not matter; the price does.
        let base = SkinPopRules {
            skin: SkinRules {
                decay: 0.05,
                q_min: 0.2,
                repair_cost: 1.0,
                income: 1.0,
                maintenance: 0.0,
            },
            u_noise: 0.0,
            u_shift: 0.0,
            birth_price: 1.5,
            max_population: 1,
            demand_growth: None,
            repair_from_pool: false,
            local_recycle: false,
            local_share: 1.0,
            pocket_max: None,
        };
        let need = base.skin.u_min();

        let closed = run_recycle(
            base,
            crate::skin::SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, 1.0),
            1.0,
            10.0,
            need,
            200_000,
            1,
        );
        assert_eq!(closed.forms.len(), 1, "a cheap skin should close the cycle");

        let mut dear = base;
        dear.skin.repair_cost = 2.0;
        let open = run_recycle(
            dear,
            crate::skin::SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, 1.0),
            1.0,
            10.0,
            dear.skin.u_min(),
            200_000,
            1,
        );
        assert!(open.forms.is_empty(), "a dear skin should not close it, whatever the recycling");

        // and the recycling speed is not what decides
        let slow = run_recycle(
            base,
            crate::skin::SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, 0.05),
            1.0,
            10.0,
            need,
            200_000,
            1,
        );
        let fast = run_recycle(
            base,
            crate::skin::SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, 1.0),
            1.0,
            10.0,
            need,
            200_000,
            1,
        );
        assert_eq!(slow.forms.len(), fast.forms.len(), "the conversion rate should not decide");
    }

    #[test]
    fn maintenance_depends_on_throughput_and_persistence_does_not() {
        // FINDING-267: a passive form lives `ln(q_min)/ln(1-d)` steps at ANY income, because nothing in it
        // depends on the medium. A maintained form's life tracks the income and becomes unbounded exactly at
        // `c*u_min`. That difference is the operational mark of maintenance rather than persistence.
        let base = SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 10.0,
            income: 1.0,
            maintenance: 0.0,
        };
        let threshold = base.skin_cost();
        let mut passive_lives = Vec::new();
        let mut repaired_lives = Vec::new();
        for income in [0.02, 0.05, 0.09, 0.10, 0.20] {
            let r = SkinRules { income, ..base };
            passive_lives.push(run(r, 1.0, 10.0, 0.0, 200_000).steps);
            repaired_lives.push(run(r, 1.0, 10.0, r.u_min(), 200_000).steps);
        }
        assert!(
            passive_lives.iter().all(|s| *s == passive_lives[0]),
            "the passive life must not depend on the medium: {passive_lives:?}"
        );
        assert!(
            repaired_lives.windows(2).all(|w| w[1] >= w[0]),
            "the repaired life must order with the income: {repaired_lives:?}"
        );
        assert_eq!(
            repaired_lives[3], 200_000,
            "at exactly the skin cost the form should live forever"
        );
        assert!(
            repaired_lives[2] < 200_000,
            "just below the skin cost it should not"
        );
        assert!((threshold - 0.1).abs() < 1e-12);
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
