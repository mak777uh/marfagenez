//! With a shared stock, does a stable distribution of shapes appear?
//!
//! `FINDING-217` ended with a structural failure: forms had independent margins, so once
//! everyone was solvent selection stopped. `ShapeRules::pool` makes income depend on what
//! everyone has taken.
//!
//! PREDICTION, before the run:
//!   (a) with a pool the population is limited by the stock rather than by the cap: the
//!       stock sits below its maximum and the population varies;
//!   (b) the mean `x` settles at a value below the starting mean, and does not drift;
//!   (c) at a low inflow the population is small, at a high inflow it is larger.
//!
//! If (b) fails - if the composition keeps moving - then there is no stable distribution to
//! report and the honest statement is that the world does not settle.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

fn rules(inflow: f64) -> ShapeRules {
    let mut r =
        ShapeRules::new(ShapeEconomy::new(2.0, 1.0, 0.1).expect("economy"), 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(100.0, inflow, 100.0);
    r
}

fn line(world: &ShapeWorld) -> String {
    let mut sizes: Vec<usize> = world.forms.iter().map(|f| f.form.cells()).collect();
    sizes.sort_unstable();
    format!(
        "alive {:>3}  stock {:>6.2}  mean_cells {:>5.1}  mean_x {:.3}  sizes {:?}",
        world.alive(),
        world.stock,
        world.mean_cells(),
        world.mean_x(),
        if sizes.len() > 6 { sizes[..6].to_vec() } else { sizes.clone() }
    )
}

fn main() {
    for inflow in [60.0, 150.0, 400.0] {
        println!("=== inflow {inflow} ===");
        let start: Vec<Form> = (2..=7).map(Form::square).collect();
        let mut world = ShapeWorld::new(rules(inflow), start);
        let mut rng = Rng::new(31);
        println!("{:>5}  {}", "step", line(&world));
        for step in 1..=600 {
            world.step(&mut rng);
            if step <= 3 || step % 50 == 0 {
                println!("{step:>5}  {}", line(&world));
            }
        }
        println!(
            "births {}, deaths {}, mutations {}",
            world.births, world.deaths, world.mutations
        );
        println!();
    }
}
