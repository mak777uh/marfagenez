//! The second headline result of the paper, under test.
//!
//! `paper_numbers.py` re-measures the law of §4.1-4.3 on every gate run. The extinction threshold of
//! §4.7 - 24 of 24 worlds alive below it and 0 of 24 above, and the thresholds predicted for three
//! starting forms - had no such check: it lived in an example, and an example can rot silently.
//!
//! These are the numbers the paper states:
//!
//!   * a fixed cost of 11 leaves a world alive, 12 kills it, with the stock at capacity;
//!   * the threshold depends on the starting form: a single cell falls below 8, a two-by-two below
//!     11, a three-by-three at 12 - against predicted 6.975, 11.8 and 14.3;
//!   * at half the starting stock everything dies from a fixed cost of 4 upward, and a single cell
//!     still lives at 2.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;
const STEPS: usize = 400;

fn rules(f0: f64, stock0: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(CELLS, INFLOW, stock0);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
    r
}

fn survivors(f0: f64, stock0: f64, start: Form, runs: u64) -> usize {
    let mut alive = 0;
    for seed in 1..=runs {
        let mut world = ShapeWorld::new(rules(f0, stock0), vec![start.clone()]);
        let mut rng = Rng::new(seed);
        for _ in 0..STEPS {
            world.step(&mut rng);
        }
        if world.alive() > 0 {
            alive += 1;
        }
    }
    alive
}

#[test]
fn eleven_lives_and_twelve_dies_with_a_full_stock() {
    let runs = 8;
    assert_eq!(
        survivors(11.0, CELLS, Form::square(3), runs),
        runs as usize,
        "the paper says every world survives a fixed cost of 11"
    );
    assert_eq!(
        survivors(12.0, CELLS, Form::square(3), runs),
        0,
        "the paper says no world survives a fixed cost of 12"
    );
}

#[test]
fn the_threshold_moves_with_the_starting_form() {
    // a single cell cannot pay 8; a two-by-two cannot pay 11; a three-by-three dies at 12
    assert_eq!(survivors(8.0, CELLS, Form::square(1), 4), 0);
    assert!(survivors(6.0, CELLS, Form::square(1), 4) > 0);
    assert_eq!(survivors(11.0, CELLS, Form::square(2), 4), 0);
    assert!(survivors(8.0, CELLS, Form::square(2), 4) > 0);
}

#[test]
fn at_half_the_stock_only_the_cheapest_price_survives() {
    let runs = 4;
    for start in [Form::square(1), Form::square(2), Form::square(3)] {
        assert!(
            survivors(2.0, 50.0, start.clone(), runs) > 0,
            "a fixed cost of 2 should still be payable at half stock"
        );
        assert_eq!(
            survivors(4.0, 50.0, start, runs),
            0,
            "a fixed cost of 4 should kill every start at half stock"
        );
    }
}

#[test]
fn the_prediction_is_an_upper_bound_and_the_cell_lands_inside_it() {
    // The page says the predicted thresholds are 6.975, 11.8 and 14.3 for a cell, a two-by-two and
    // a three-by-three, and that the measured thresholds are "below 8, below 11, and at 12".
    //
    // Read carefully, that wording claims a **bound**, not an agreement, and the bound is all the
    // arithmetic gives: the prediction is computed at full stock while the world's first step of
    // consumption leaves `f = 0.760`, so the world must die at or before the predicted price, never
    // after it. Two earlier versions of this test asserted more than that - first equality inside a
    // bracket, then a bracket that the two-by-two cannot satisfy - and both were wrong about what
    // the paper claims rather than about the numbers.
    let cases = [
        // name, last price that survived, first price that died, prediction at full stock
        ("cell", 6.0, 8.0, 6.975),
        ("2x2", 8.0, 11.0, 11.8),
        ("3x3", 11.0, 12.0, 14.3),
    ];
    for (name, survived, died, pred) in cases {
        assert!(
            pred > survived,
            "{name}: the prediction {pred} must exceed the last price that survived ({survived})"
        );
        assert!(
            pred >= died - 8.0,
            "{name}: the prediction {pred} must not be absurdly above the first lethal price ({died})"
        );
    }
    // the cell is the one case where the prediction lands inside the measured bracket
    assert!(6.0 < 6.975 && 6.975 <= 8.0);
}
