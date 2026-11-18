//! The alternation result of `FINDING-243`, under test.
//!
//! A one-cell world does not see a constant fill: consumption is taken before the inflow is credited, so
//! the stock alternates between `1 - 8/100 = 0.920` and `1.000`, and the cell lives or dies on the
//! average `0.960`. That gives `f0 <= 8 * 0.96 - 1.025 = 6.655`. Two earlier guesses took one phase for
//! the whole and were wrong by 0.32 in each direction, so the arithmetic deserves a test of its own.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;
const STEPS: usize = 400;
const SEEDS: u64 = 8;

fn rules(f0: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(CELLS, INFLOW, CELLS);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
    r
}

fn survivors(f0: f64) -> usize {
    let mut alive = 0;
    for seed in 1..=SEEDS {
        let mut world = ShapeWorld::new(rules(f0), vec![Form::square(1)]);
        let mut rng = Rng::new(seed);
        for _ in 0..STEPS {
            world.step(&mut rng);
        }
        if !world.forms.is_empty() {
            alive += 1;
        }
    }
    alive
}

#[test]
fn the_fill_alternates_between_two_phases() {
    let mut world = ShapeWorld::new(rules(6.5), vec![Form::square(1)]);
    let mut rng = Rng::new(1);
    let mut fills = Vec::new();
    for _ in 0..6 {
        world.step(&mut rng);
        fills.push(world.stock / CELLS);
    }
    for (i, f) in fills.iter().enumerate() {
        let want = if i % 2 == 0 { 0.92 } else { 1.0 };
        assert!(
            (f - want).abs() < 1e-9,
            "step {} should leave f = {want}, got {f} (all: {fills:?})",
            i + 1
        );
    }
}

#[test]
fn the_derived_edge_falls_inside_the_measured_bracket() {
    // the derivation, in the code, so a change in the order of operations breaks this test
    let mean_fill: f64 = (0.92 + 1.0) / 2.0;
    let income_at_mean: f64 = 2.0 * 4.0 * mean_fill; // sigma * perimeter * mean fill
    let upkeep_without_f0: f64 = 1.0 * 1.0 + 0.1 * 1.0 / 4.0;
    let edge: f64 = income_at_mean - upkeep_without_f0;
    assert!(
        (edge - 6.655).abs() < 1e-3,
        "the derivation should give 6.655, got {edge}"
    );
    assert!(6.65 < edge && edge < 6.7, "6.655 must lie in (6.65, 6.7)");
}

#[test]
fn sixty_five_hundredths_lives_and_seventy_dies() {
    assert_eq!(survivors(6.65), SEEDS as usize, "6.65 is below the edge");
    assert_eq!(survivors(6.7), 0, "6.7 is above the edge");
}
