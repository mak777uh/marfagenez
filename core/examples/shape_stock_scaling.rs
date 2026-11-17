//! Does the extinction threshold scale with the starting stock?
//!
//! `FINDING-227` explained the boundary between `f0 = 11` and `f0 = 12` by the stock the world
//! actually has: the first step of consumption leaves the pool at `f = 0.760`, and the requirement
//! is `f >= f0 / 14.679`. With a starting stock of half the capacity, the same argument predicts a
//! **lower** threshold: `f` after the first step should be about half, so `f0` should be affordable
//! up to about half as much.
//!
//! PREDICTION, before the run:
//!   (a) with `stock0 = 50` the threshold falls to roughly half of the full-stock threshold,
//!       i.e. to about 5.5 ... 6, instead of 11 ... 12;
//!   (b) the ordering is preserved: fewer survivors as `f0` rises, in both settings;
//!   (c) at `stock0 = 50` and `f0 = 8` nothing survives, while at `f0 = 5` something does.
//!
//! If (a) fails - if the threshold does not move with the starting stock - then the mechanism of
//! 227 is not what sets the boundary and the explanation has to be redone.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

fn rules(f0: f64, stock0: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(100.0, 300.0, stock0);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
    r
}

fn survivors(f0: f64, stock0: f64, runs: u64) -> usize {
    let mut alive_end = 0;
    for seed in 1..=runs {
        let mut world = ShapeWorld::new(rules(f0, stock0), vec![Form::square(3)]);
        let mut rng = Rng::new(seed);
        for _ in 0..400 {
            world.step(&mut rng);
        }
        if world.alive() > 0 {
            alive_end += 1;
        }
    }
    alive_end
}

fn main() {
    let runs = 8u64;
    println!("{:>8} {:>7} {:>12}", "stock0", "f0", "survivors");
    let mut rows = Vec::new();
    for stock0 in [100.0, 50.0] {
        for f0 in [4.0, 5.0, 6.0, 8.0, 11.0, 12.0] {
            let s = survivors(f0, stock0, runs);
            println!("{stock0:>8.0} {f0:>7.1} {s:>9}/{runs}");
            rows.push((stock0, f0, s));
        }
        println!();
    }

    let full: Vec<(f64, usize)> = rows
        .iter()
        .filter(|(s, _, _)| *s == 100.0)
        .map(|(_, f, k)| (*f, *k))
        .collect();
    let half: Vec<(f64, usize)> = rows
        .iter()
        .filter(|(s, _, _)| *s == 50.0)
        .map(|(_, f, k)| (*f, *k))
        .collect();
    let bracket = |xs: &[(f64, usize)]| -> Option<(f64, f64)> {
        xs.windows(2)
            .find(|w| w[0].1 > 0 && w[1].1 == 0)
            .map(|w| (w[0].0, w[1].0))
    };
    println!("full-stock bracket: {:?}", bracket(&full));
    println!("half-stock bracket: {:?}", bracket(&half));
    println!();
    println!("(a) the half-stock threshold should be roughly half of the full-stock one");
    println!("(b) survivors should fall as f0 rises, in both settings");
    println!("(c) at half stock, f0 = 8 should kill and f0 = 5 should not");
}
