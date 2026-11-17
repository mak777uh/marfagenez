//! The open check from `FINDING-228`: with a **small** starting form, does the threshold halve
//! when the starting stock halves?
//!
//! `FINDING-228` refuted the scaling prediction for a reason that had nothing to do with the
//! mechanism: the initial 3x3 form cannot pay for itself at half stock, so the world died on step
//! one at every price. The mechanism of `FINDING-227` therefore remains untested on that axis.
//!
//! This repeats the measurement with starts that **are** viable at half stock: a single cell and a
//! two-by-two.
//!
//! PREDICTION, before the run:
//!   (a) with a small start the threshold appears again at half stock, and sits at roughly **half**
//!       the full-stock threshold - about 5 to 6 instead of 11 to 12;
//!   (b) the ordering holds: survivors fall to zero as `f0` crosses that point;
//!   (c) at full stock the threshold stays at 11 ... 12 whatever the starting form, because the pool
//!       refills faster than a small form can drain it.
//!
//! If (a) fails again - if no threshold appears at half stock even with a viable start - then the
//! scaling argument of `FINDING-227` is wrong and the explanation has to be redone.

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

fn survivors(f0: f64, stock0: f64, start: Form, runs: u64) -> usize {
    let mut alive_end = 0;
    for seed in 1..=runs {
        let mut world = ShapeWorld::new(rules(f0, stock0), vec![start.clone()]);
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
    let starts = [("cell", Form::square(1)), ("2x2", Form::square(2)), ("3x3", Form::square(3))];
    println!("{:>6} {:>6} {:>7} {:>10}", "start", "stock0", "f0", "survivors");
    for (name, start) in starts {
        for stock0 in [100.0, 50.0] {
            for f0 in [2.0, 4.0, 6.0, 8.0, 11.0, 12.0] {
                let s = survivors(f0, stock0, start.clone(), runs);
                println!("{name:>6} {stock0:>6.0} {f0:>7.1} {s:>7}/{runs}");
            }
            println!();
        }
    }
    println!("(a) with a small start, a threshold should appear at half stock near 5 ... 6");
    println!("(b) survivors should fall to zero across that threshold");
    println!("(c) at full stock the threshold should stay at 11 ... 12 for every start");
}
