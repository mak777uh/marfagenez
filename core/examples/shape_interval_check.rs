//! The four predictions of `FINDING-219`, checked in a world instead of on paper.
//!
//! Predicted, before the run:
//!   1. with `f0 = 10` the atoms die - nothing of size one survives;
//!   2. the population settles on squares of side 1.6 ... 5.4;
//!   3. no form has side above 5.4, because transport eats it;
//!   4. with `f0 = 15` the world is empty, because no square can pay that much.
//!
//! A refutation of any of these means the interval arithmetic is wrong, and the arithmetic has
//! to be redone rather than the experiment adjusted.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

fn rules(f0: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(100.0, 300.0, 100.0);
    r
}

fn side_of(f: &Form) -> f64 {
    let (lo, hi) = f.extent();
    let w = (hi.0 - lo.0 + 1) as f64;
    let h = (hi.1 - lo.1 + 1) as f64;
    w.max(h)
}

fn main() {
    // The final-state table hid the interesting part: at f0 = 10 the world ends empty, and
    // an empty world satisfies three of the four predictions for the wrong reason. The
    // trajectory is what needs reading.
    for f0 in [10.0] {
        let mut world = ShapeWorld::new(rules(f0), vec![Form::square(3)]);
        let mut rng = Rng::new(41);
        println!("f0 {f0}: trajectory");
        for step in 0..120 {
            world.step(&mut rng);
            if step % 5 == 0 || world.alive() == 0 {
                println!(
                    "  step {step:>3}: alive {:>3}  stock {:>7.2}  mean_cells {:>5.1}",
                    world.alive(),
                    world.stock,
                    world.mean_cells()
                );
            }
            if world.alive() == 0 {
                println!("  the world is empty at step {step}");
                break;
            }
        }
        println!(
            "  births {}, deaths {}, mutations {}",
            world.births, world.deaths, world.mutations
        );
        println!();
    }

    for f0 in [0.0, 10.0, 15.0] {
        let mut world = ShapeWorld::new(rules(f0), vec![Form::square(3)]);
        let mut rng = Rng::new(41);
        for _ in 0..400 {
            world.step(&mut rng);
        }
        let mut sizes: Vec<usize> = world.forms.iter().map(|f| f.form.cells()).collect();
        sizes.sort_unstable();
        let mut sides: Vec<f64> = world.forms.iter().map(|f| side_of(&f.form)).collect();
        sides.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let atoms = sizes.iter().filter(|s| **s == 1).count();
        println!(
            "f0 {f0:>5.1}: alive {:>3}  atoms {:>2}  mean_cells {:>5.1}  mean_x {:.3}  \
             sides [{:.1}, {:.1}]",
            world.alive(),
            atoms,
            world.mean_cells(),
            world.mean_x(),
            sides.first().copied().unwrap_or(0.0),
            sides.last().copied().unwrap_or(0.0)
        );
        println!(
            "            sizes {:?}",
            if sizes.len() > 10 { sizes[..10].to_vec() } else { sizes.clone() }
        );
    }
}
