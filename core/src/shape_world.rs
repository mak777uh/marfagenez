//! A population of forms under the shape economy: the smallest world in which a *shape* can
//! be selected for.
//!
//! `docs/DESIGN-structures.md` computed the economy; `FINDING-215` implemented the geometry;
//! `FINDING-216` added mutation and found that it ratchets upwards, so size has to be
//! regulated by the economy rather than by the mutation rate. This module is that economy
//! running as selection:
//!
//! ```text
//! each form holds energy
//! each step   energy += margin(form)          margin = sigma*p - mu*n - kappa*n^2/p
//! death       energy < 0
//! birth       energy >= birth_cost  ->  a copy, mutated, pays birth_cost
//! ```
//!
//! Nothing here touches `Life`. Every recorded run of the old model keeps its bits; this is a
//! second world in the same crate, and it is called that.

use crate::form::{Form, ShapeEconomy};
use crate::Rng;

/// One form and its accumulated margin.
#[derive(Debug, Clone, PartialEq)]
pub struct FormState {
    pub form: Form,
    pub energy: f64,
}

/// A shared stock of resource that every form draws from.
///
/// `FINDING-217` ended with a structural failure: forms had independent margins, so once
/// every form was solvent nothing died and selection stopped. A pool makes income depend on
/// what everyone else has taken, which is what competition is.
///
/// ```text
/// income_i = sigma * p_i * (stock / stock_max)          throttled by the shared stock
/// stock'   = stock + inflow*(1 - stock/stock_max) - sum(income_i)
/// ```
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Pool {
    /// The most the medium can hold.
    pub stock_max: f64,
    /// How fast it refills towards `stock_max`.
    pub inflow: f64,
    /// The stock at the start.
    pub stock0: f64,
}

impl Pool {
    pub fn new(stock_max: f64, inflow: f64, stock0: f64) -> Option<Self> {
        if !(stock_max.is_finite() && inflow.is_finite() && stock0.is_finite()) {
            return None;
        }
        if stock_max <= 0.0 || inflow < 0.0 || stock0 < 0.0 {
            return None;
        }
        Some(Self {
            stock_max,
            inflow,
            stock0: stock0.min(stock_max),
        })
    }

    /// Fraction of the medium that is currently available.
    pub fn fullness(&self, stock: f64) -> f64 {
        (stock / self.stock_max).clamp(0.0, 1.0)
    }
}

/// The prices and rates of the shape world.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ShapeRules {
    pub economy: ShapeEconomy,
    /// Energy needed before a form may spawn a mutated copy.
    ///
    /// `FINDING-222` found why the interval of solvency never bounded the outcome: absolute
    /// margin grows with size, so bigger forms breed faster, and the economy selected for
    /// growth rather than for solvency. A cost that grows with the child's size is the
    /// straightest way to stop that.
    pub birth_cost: f64,
    /// Extra birth cost **per cell of the child**. Zero by default, which is the contract:
    /// every world measured before this field existed must reproduce its numbers.
    pub birth_cost_per_cell: f64,
    /// Chance that a newborn differs from its parent.
    pub mutation_rate: f64,
    /// Chance that a mutation adds rather than removes a cell.
    pub p_grow: f64,
    /// Largest population allowed.
    pub max_population: usize,
    /// A shared stock, when there is one. `None` keeps `FINDING-217`'s world: independent
    /// margins and no competition.
    pub pool: Option<Pool>,
}

impl ShapeRules {
    pub fn new(economy: ShapeEconomy, birth_cost: f64) -> Option<Self> {
        if !(birth_cost.is_finite() && birth_cost > 0.0) {
            return None;
        }
        Some(Self {
            economy,
            birth_cost,
            birth_cost_per_cell: 0.0,
            mutation_rate: 1.0,
            p_grow: 0.5,
            max_population: 32,
            pool: None,
        })
    }
}

/// A population of forms, each holding the margin it has earned.
#[derive(Debug, Clone)]
pub struct ShapeWorld {
    pub rules: ShapeRules,
    pub forms: Vec<FormState>,
    pub births: u64,
    pub deaths: u64,
    pub mutations: u64,
    /// Resource left in the shared stock, when the rules have one.
    pub stock: f64,
}

impl ShapeWorld {
    pub fn new(rules: ShapeRules, forms: Vec<Form>) -> Self {
        let state = forms
            .into_iter()
            .map(|form| FormState { form, energy: 0.0 })
            .collect();
        let stock = rules.pool.map(|p| p.stock0).unwrap_or(f64::INFINITY);
        Self {
            rules,
            forms: state,
            births: 0,
            deaths: 0,
            mutations: 0,
            stock,
        }
    }

    /// The income a form earns now: its own boundary, throttled by the shared stock.
    pub fn income_now(&self, form: &Form) -> f64 {
        let raw = self.rules.economy.sigma * form.perimeter() as f64;
        match self.rules.pool {
            Some(pool) => raw * pool.fullness(self.stock),
            None => raw,
        }
    }

    /// The margin a form earns now, with the same throttle applied to its income.
    pub fn margin_now(&self, form: &Form) -> f64 {
        self.income_now(form) - self.rules.economy.upkeep(form)
    }

    /// What it costs to make a copy of a form of `cells` cells.
    pub fn birth_price(&self, cells: usize) -> f64 {
        self.rules.birth_cost + self.rules.birth_cost_per_cell * cells as f64
    }

    pub fn alive(&self) -> usize {
        self.forms.len()
    }

    /// Mean cells per boundary edge of the living forms.
    pub fn mean_x(&self) -> f64 {
        if self.forms.is_empty() {
            return 0.0;
        }
        self.forms.iter().map(|f| f.form.x()).sum::<f64>() / self.forms.len() as f64
    }

    /// Mean number of cells.
    pub fn mean_cells(&self) -> f64 {
        if self.forms.is_empty() {
            return 0.0;
        }
        self.forms.iter().map(|f| f.form.cells() as f64).sum::<f64>() / self.forms.len() as f64
    }

    /// One step: every form earns its margin, the insolvent die, the solvent may split.
    ///
    /// Births are collected before any newborn is added, so a form cannot give birth twice
    /// in one step and a newborn does not act in the step it was born in - the same rule the
    /// organism world uses, and for the same reason: otherwise one rich form fills the world
    /// in a single step.
    pub fn step(&mut self, rng: &mut Rng) {
        // Income is computed against the stock as it was at the start of the step, so every
        // form sees the same medium - the same rule the organism world uses for a shared
        // cell, and it keeps the order of the vector from mattering.
        let mut consumed = 0.0;
        let income: Vec<f64> = self.forms.iter().map(|f| self.income_now(&f.form)).collect();
        for (f, inc) in self.forms.iter_mut().zip(income.iter()) {
            consumed += *inc;
            f.energy += *inc - self.rules.economy.upkeep(&f.form);
        }
        if let Some(pool) = self.rules.pool {
            let refill = pool.inflow * (1.0 - pool.fullness(self.stock));
            // The clamp must be on both sides. Without the upper bound a step that empties
            // the stock was followed by a step that refilled it to several times its
            // capacity - the probe showed stock jumping 0.00 -> 150.00 on a pool of 100 -
            // and the population was reading a medium that does not exist.
            self.stock = (self.stock + refill - consumed).clamp(0.0, pool.stock_max);
        }

        let before = self.forms.len();
        self.forms.retain(|f| f.energy >= 0.0);
        self.deaths += (before - self.forms.len()) as u64;

        let mut parents: Vec<usize> = Vec::new();
        for (i, f) in self.forms.iter().enumerate() {
            if f.energy >= self.birth_price(f.form.cells()) {
                parents.push(i);
            }
        }
        let room = self.rules.max_population.saturating_sub(self.forms.len());
        for i in parents.into_iter().take(room) {
            let child_form = {
                let parent = &self.forms[i];
                if rng.uniform() < self.rules.mutation_rate {
                    self.mutations += 1;
                    parent
                        .form
                        .mutate(rng, self.rules.p_grow)
                        .unwrap_or_else(|| parent.form.clone())
                } else {
                    parent.form.clone()
                }
            };
            if child_form.cells() == 0 {
                continue;
            }
            let price = self.birth_price(child_form.cells());
            let child = FormState {
                form: child_form,
                energy: price,
            };
            self.forms[i].energy -= price;
            self.forms.push(child);
            self.births += 1;
        }
    }
}

/// Runs a population and returns the state after `steps`.
pub fn run(rules: ShapeRules, start: Vec<Form>, steps: usize, seed: u64) -> ShapeWorld {
    let mut rng = Rng::new(seed);
    let mut world = ShapeWorld::new(rules, start);
    for _ in 0..steps {
        world.step(&mut rng);
    }
    world
}

#[cfg(test)]
mod tests {
    use super::*;

    fn economy() -> ShapeEconomy {
        ShapeEconomy::new(2.0, 1.0, 0.1).expect("valid economy")
    }

    fn rules() -> ShapeRules {
        ShapeRules::new(economy(), 2.0).expect("valid rules")
    }

    #[test]
    fn a_form_that_cannot_pay_its_way_dies() {
        // a solid 9x9 square has x = 2.25, margin < 0, so its energy falls and it dies
        let mut rng = Rng::new(1);
        let mut world = ShapeWorld::new(rules(), vec![Form::square(9)]);
        assert!(!economy().survives(&Form::square(9)), "the premise of the test");
        for _ in 0..3 {
            world.step(&mut rng);
        }
        assert_eq!(world.alive(), 0, "an insolvent form must die");
        assert_eq!(world.deaths, 1);
    }

    #[test]
    fn a_form_that_pays_lives_and_splits() {
        let mut rng = Rng::new(2);
        let mut world = ShapeWorld::new(rules(), vec![Form::square(3)]);
        for _ in 0..40 {
            world.step(&mut rng);
        }
        assert!(world.alive() >= 1, "a solvent form must persist");
        assert!(world.births >= 1, "and must give birth");
    }

    #[test]
    fn the_population_never_exceeds_the_cap() {
        let mut r = rules();
        r.max_population = 4;
        let mut rng = Rng::new(3);
        let start: Vec<Form> = (0..3).map(|_| Form::strip(6)).collect();
        let mut world = ShapeWorld::new(r, start);
        for _ in 0..200 {
            world.step(&mut rng);
            assert!(world.alive() <= 4, "population {} exceeded the cap", world.alive());
        }
    }

    #[test]
    fn a_newborn_acts_only_on_the_step_after_it_is_born() {
        let mut r = rules();
        r.max_population = 100;
        let mut rng = Rng::new(4);
        let mut world = ShapeWorld::new(r, vec![Form::square(3)]);
        let before = world.alive();
        world.step(&mut rng);
        // a single step can add newborns but they cannot themselves give birth in it
        assert!(world.alive() <= before * 2, "one step doubled the population twice over");
    }

    #[test]
    fn without_a_pool_the_behaviour_of_the_previous_finding_is_unchanged() {
        // `FINDING-217` measured this world; adding a pool must not move it.
        let mut rng = Rng::new(21);
        let mut world = ShapeWorld::new(rules(), vec![Form::square(3)]);
        for _ in 0..10 {
            world.step(&mut rng);
        }
        assert_eq!(world.stock, f64::INFINITY);
        assert!(world.alive() >= 1);
    }

    #[test]
    fn a_depleted_pool_takes_food_from_everyone() {
        let mut r = rules();
        r.pool = Pool::new(10.0, 0.0, 10.0); // no refill: the stock can only fall
        let start: Vec<Form> = (0..6).map(|_| Form::strip(8)).collect();
        let mut rng = Rng::new(22);
        let mut world = ShapeWorld::new(r, start);
        // one step spends what the forms earn, and nothing comes back
        world.step(&mut rng);
        assert!(world.stock < 10.0, "stock should fall, got {}", world.stock);
        for _ in 0..40 {
            world.step(&mut rng);
        }
        assert!(world.stock <= 1e-9, "an empty medium, got {}", world.stock);
        assert_eq!(world.alive(), 0, "with nothing left, nothing lives");
    }

    #[test]
    fn the_stock_stays_inside_its_capacity_at_every_step() {
        // Two earlier versions of this test asserted things about a *particular* inflow -
        // that the stock would be drawn down, then that the population would stay below a
        // cap - and each failed when the parameters changed, because the assertion was about
        // my guess at the regime rather than about the mechanism. The invariant that holds
        // in every regime is simpler: the stock never leaves [0, stock_max].
        let mut r = rules();
        r.max_population = 200;
        r.pool = Pool::new(100.0, 150.0, 60.0);
        let start: Vec<Form> = (0..4).map(|_| Form::strip(6)).collect();
        let mut rng = Rng::new(23);
        let mut world = ShapeWorld::new(r, start);
        for step in 0..400 {
            world.step(&mut rng);
            assert!(
                (0.0..=100.0).contains(&world.stock),
                "stock left its capacity at step {step}: {}",
                world.stock
            );
        }
        assert!(world.alive() > 0, "and something still lives");
    }

    #[test]
    fn competition_makes_margins_depend_on_the_others() {
        let mut r = rules();
        r.pool = Pool::new(10.0, 1.0, 5.0);
        let solo = ShapeWorld::new(r, vec![Form::strip(8)]);
        let mut crowded = ShapeWorld::new(r, (0..8).map(|_| Form::strip(8)).collect());
        let mut rng = Rng::new(24);
        crowded.step(&mut rng);
        let one = solo.margin_now(&Form::strip(8));
        let many = crowded.margin_now(&Form::strip(8));
        assert!(
            many < one,
            "a crowded medium should pay a form less: solo {one}, crowded {many}"
        );
    }

    #[test]
    fn an_impossible_pool_is_refused() {
        assert!(Pool::new(0.0, 1.0, 0.0).is_none());
        assert!(Pool::new(10.0, -1.0, 0.0).is_none());
        assert!(Pool::new(f64::NAN, 1.0, 0.0).is_none());
    }

    #[test]
    fn a_per_cell_cost_of_zero_leaves_the_earlier_worlds_alone() {
        let r = rules();
        assert_eq!(r.birth_cost_per_cell, 0.0);
        let world = ShapeWorld::new(r, vec![Form::square(3)]);
        assert!((world.birth_price(9) - r.birth_cost).abs() < 1e-12);
    }

    #[test]
    fn a_per_cell_birth_cost_makes_a_big_form_pay_more() {
        let mut r = rules();
        r.birth_cost_per_cell = 4.0;
        let world = ShapeWorld::new(r, vec![Form::square(3)]);
        assert!((world.birth_price(1) - (r.birth_cost + 4.0)).abs() < 1e-12);
        assert!((world.birth_price(25) - (r.birth_cost + 100.0)).abs() < 1e-12);
    }

    #[test]
    fn an_impossible_birth_cost_is_refused() {
        assert!(ShapeRules::new(economy(), 0.0).is_none());
        assert!(ShapeRules::new(economy(), -1.0).is_none());
        assert!(ShapeRules::new(economy(), f64::NAN).is_none());
    }
}
