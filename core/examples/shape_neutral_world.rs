//! The world at the neutral mutation rate: does the interval show up once mutation stops
//! exploding?
//!
//! `FINDING-221` measured the neutral point at `p_grow = 0.27` and showed that every earlier
//! shape world ran at 0.5 - 1.9 times above it, inside the explosion regime. So the interval of
//! `FINDING-219` was never tested against a mutation that leaves size alone.
//!
//! PREDICTION, before the run:
//!   (a) with `p_grow = 0.0` the sizes stay at the start, because nothing moves them;
//!   (b) with `p_grow = 0.27` the sizes stay near the start instead of growing to double digits;
//!   (c) with `p_grow = 0.50` the growth of `FINDING-220` reproduces;
//!   (d) if the interval is real, at 0.27 the surviving sides sit inside 1.6 ... 5.4.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

fn rules(p_grow: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(10.0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(100.0, 300.0, 100.0);
    r.p_grow = p_grow;
    r
}

fn side_of(f: &Form) -> f64 {
    let (lo, hi) = f.extent();
    ((hi.0 - lo.0 + 1) as f64).max((hi.1 - lo.1 + 1) as f64)
}

fn main() {
    let steps = 400;
    for p_grow in [0.0, 0.27, 0.50] {
        let mut world = ShapeWorld::new(rules(p_grow), vec![Form::square(3)]);
        let mut rng = Rng::new(41);
        let mut mean_path = Vec::new();
        for step in 0..steps {
            world.step(&mut rng);
            if step % 50 == 0 {
                mean_path.push((step, world.alive(), world.mean_cells(), world.stock));
            }
        }
        let mut sides: Vec<f64> = world.forms.iter().map(|f| side_of(&f.form)).collect();
        sides.sort_by(|a, b| a.partial_cmp(b).unwrap());
        println!("=== p_grow {p_grow} ===");
        for (step, alive, cells, stock) in &mean_path {
            println!(
                "  step {step:>3}: alive {alive:>3}  mean_cells {cells:>6.1}  stock {stock:>6.2}"
            );
        }
        println!(
            "  final: alive {:>3}  mean_cells {:>6.1}  mean_x {:.3}  sides [{:.1}, {:.1}]  \
             births {}  deaths {}",
            world.alive(),
            world.mean_cells(),
            world.mean_x(),
            sides.first().copied().unwrap_or(0.0),
            sides.last().copied().unwrap_or(0.0),
            world.births,
            world.deaths
        );
        println!();
    }
}
